[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443)) {
    throw 'NiFi is not running on port 8443.'
}

$applicationLog = Join-Path $script:NiFiHome 'logs\nifi-app.log'
$credentialLines = Select-String -LiteralPath $applicationLog -Pattern 'Generated Username|Generated Password' | Select-Object -Last 2
$usernameLine = $credentialLines | Where-Object { $_.Line -match 'Generated Username' } | Select-Object -First 1
$passwordLine = $credentialLines | Where-Object { $_.Line -match 'Generated Password' } | Select-Object -First 1
if ($null -eq $usernameLine -or $null -eq $passwordLine) {
    throw 'Generated NiFi credentials were not found in nifi-app.log.'
}
$username = $usernameLine.Line -replace '^.*Generated Username \[([^]]+)\].*$', '$1'
$password = $passwordLine.Line -replace '^.*Generated Password \[([^]]+)\].*$', '$1'

$baseUri = 'https://127.0.0.1:8443/nifi-api'
$originalCertificateCallback = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

try {
    $token = Invoke-RestMethod -Uri "$baseUri/access/token" -Method Post -ContentType 'application/x-www-form-urlencoded' -Body @{ username = $username; password = $password }
    $headers = @{ Authorization = "Bearer $token" }

    function Get-ChildProcessGroups([string] $ParentId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$ParentId/process-groups" -Headers $headers -Method Get
        return @($response.processGroups)
    }

    function Find-ChildProcessGroup {
        param(
            [Parameter(Mandatory = $true)][string] $ParentId,
            [Parameter(Mandatory = $true)][string] $Name
        )

        $group = Get-ChildProcessGroups -ParentId $ParentId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        if ($null -eq $group) {
            throw "Required NiFi process group is missing: $Name. Run configure-nifi-foundation.ps1 first."
        }
        return [string]$group.component.id
    }

    function Get-Processors([string] $GroupId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Get
        return @($response.processors)
    }

    function Ensure-StoppedProcessor {
        param(
            [Parameter(Mandatory = $true)][string] $GroupId,
            [Parameter(Mandatory = $true)][hashtable] $Definition
        )

        $existing = Get-Processors -GroupId $GroupId | Where-Object { $_.component.name -eq $Definition.Name } | Select-Object -First 1
        if ($null -ne $existing) {
            Write-Host "Present: $($Definition.Name) [$($existing.component.state)]"
            return
        }

        $entity = @{
            revision = @{ version = 0 }
            component = @{
                name = $Definition.Name
                type = $Definition.Type
                bundle = @{
                    group = 'org.apache.nifi'
                    artifact = 'nifi-standard-nar'
                    version = $script:Versions.NiFi.Version
                }
                comments = $Definition.Comments
                position = @{ x = $Definition.X; y = $Definition.Y }
                state = 'STOPPED'
                config = @{
                    schedulingStrategy = 'TIMER_DRIVEN'
                    schedulingPeriod = '1 min'
                    executionNode = 'ALL'
                    autoTerminatedRelationships = @()
                }
            }
        }
        $created = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Post -ContentType 'application/json' -Body ($entity | ConvertTo-Json -Depth 10)
        if ([string]$created.component.state -ne 'STOPPED') {
            throw "NiFi created $($Definition.Name) in an unexpected state: $($created.component.state)"
        }
        Write-Host "Created stopped processor: $($Definition.Name)"
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers -Method Get
    $rootId = [string]$root.processGroupFlow.id
    $baseballGroupId = Find-ChildProcessGroup -ParentId $rootId -Name 'BaseballO - MLB Ingestion'
    $rdfGroupId = Find-ChildProcessGroup -ParentId $baseballGroupId -Name '90 Shared RDF Mapping and Load'

    $processors = @(
        @{
            Name = '10 Accept completed game JSON'
            Type = 'org.apache.nifi.processors.standard.LogAttribute'
            Comments = 'Boundary placeholder. Input content remains the byte-identical archived MLB response; gamePk and the raw path arrive as FlowFile attributes.'
            X = 0
            Y = 0
        },
        @{
            Name = '20 Run guarded RML mapping'
            Type = 'org.apache.nifi.processors.standard.ExecuteStreamCommand'
            Comments = 'Will invoke scripts/pipeline/run-rml.ps1 with the pinned RMLMapper. The harness materializes only guarded root IRI markers in a temporary mapping copy and validates the Turtle.'
            X = 400
            Y = 0
        },
        @{
            Name = '30 Validate generated RDF'
            Type = 'org.apache.nifi.processors.standard.ExecuteStreamCommand'
            Comments = 'Explicit RDF validation gate. No output may proceed unless Turtle parsing and the expected BaseballGame assertion succeed.'
            X = 800
            Y = 0
        },
        @{
            Name = '40 PUT complete game graph'
            Type = 'org.apache.nifi.processors.standard.InvokeHTTP'
            Comments = 'Will use Graph Store Protocol PUT for https://w3id.org/baseball/graph/game/{gamePk} in the local baseball-dev dataset.'
            X = 1200
            Y = 0
        },
        @{
            Name = '90 Quarantine failed artifact'
            Type = 'org.apache.nifi.processors.standard.PutFile'
            Comments = 'Failure destination under the local pipeline quarantine tree. The failed input, log, and error attributes remain available for diagnosis.'
            X = 600
            Y = 300
        }
    )
    foreach ($processor in $processors) {
        Ensure-StoppedProcessor -GroupId $rdfGroupId -Definition $processor
    }

    $current = Get-Processors -GroupId $rdfGroupId
    $unexpectedState = $current | Where-Object { $_.component.name -in $processors.Name -and $_.component.state -ne 'STOPPED' }
    if ($unexpectedState) {
        throw 'One or more RDF skeleton processors are not stopped.'
    }
    Write-Host 'NiFi RDF mapping/load skeleton is present and stopped.'
}
finally {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCertificateCallback
}
