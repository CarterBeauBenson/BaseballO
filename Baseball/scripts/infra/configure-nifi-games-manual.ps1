[CmdletBinding()]
param(
    [switch] $Enable
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

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

    function Get-ProcessorEntity([string] $ProcessorId) {
        return Invoke-RestMethod -Uri "$baseUri/processors/$ProcessorId" -Headers $headers -Method Get
    }

    function Get-Processors([string] $GroupId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Get
        return @($response.processors)
    }

    function Set-ProcessorState {
        param(
            [Parameter(Mandatory = $true)][string] $ProcessorId,
            [Parameter(Mandatory = $true)][ValidateSet('RUNNING', 'STOPPED')][string] $State
        )
        $entity = Get-ProcessorEntity -ProcessorId $ProcessorId
        $body = @{ revision = @{ version = $entity.revision.version }; state = $State }
        return Invoke-RestMethod -Uri "$baseUri/processors/$ProcessorId/run-status" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 5)
    }

    function Ensure-Processor {
        param(
            [Parameter(Mandatory = $true)][string] $GroupId,
            [Parameter(Mandatory = $true)][hashtable] $Definition
        )

        $existing = Get-Processors -GroupId $GroupId | Where-Object { $_.component.name -eq $Definition.Name } | Select-Object -First 1
        $config = @{
            properties = $Definition.Properties
            schedulingStrategy = 'TIMER_DRIVEN'
            schedulingPeriod = $Definition.SchedulingPeriod
            executionNode = 'ALL'
            concurrentlySchedulableTaskCount = 1
            autoTerminatedRelationships = $Definition.AutoTerminate
        }
        if ($null -eq $existing) {
            $body = @{
                revision = @{ version = 0 }
                component = @{
                    name = $Definition.Name
                    type = $Definition.Type
                    bundle = @{
                        group = 'org.apache.nifi'
                        artifact = if ($Definition.ContainsKey('Artifact')) { $Definition.Artifact } else { 'nifi-standard-nar' }
                        version = $script:Versions.NiFi.Version
                    }
                    comments = $Definition.Comments
                    position = @{ x = $Definition.X; y = $Definition.Y }
                    state = 'STOPPED'
                    config = $config
                }
            }
            $created = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
            Write-Host "Created stopped processor: $($Definition.Name)"
            return $created
        }

        if ([string]$existing.component.state -ne 'STOPPED') {
            [void](Set-ProcessorState -ProcessorId ([string]$existing.component.id) -State 'STOPPED')
            $existing = Get-ProcessorEntity -ProcessorId ([string]$existing.component.id)
        }
        $body = @{
            revision = @{ version = $existing.revision.version }
            component = @{
                id = [string]$existing.component.id
                name = $Definition.Name
                comments = $Definition.Comments
                position = @{ x = $Definition.X; y = $Definition.Y }
                config = $config
            }
        }
        $updated = Invoke-RestMethod -Uri "$baseUri/processors/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
        Write-Host "Configured stopped processor: $($Definition.Name)"
        return $updated
    }

    function Get-Connections([string] $GroupId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Get
        return @($response.connections)
    }

    function Ensure-Connection {
        param(
            [Parameter(Mandatory = $true)][string] $GroupId,
            [Parameter(Mandatory = $true)][string] $Name,
            [Parameter(Mandatory = $true)][string] $SourceId,
            [Parameter(Mandatory = $true)][string] $DestinationId,
            [Parameter(Mandatory = $true)][string] $Relationship
        )
        $existing = Get-Connections -GroupId $GroupId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        if ($null -ne $existing) {
            if ([string]$existing.component.source.id -eq $SourceId -and [string]$existing.component.destination.id -eq $DestinationId -and $Relationship -in @($existing.component.selectedRelationships)) {
                Write-Host "Present connection: $Name"
                return $existing
            }
            $body = @{
                revision = @{ version = $existing.revision.version }
                component = @{
                    id = [string]$existing.component.id
                    name = $Name
                    source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
                    destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
                    selectedRelationships = @($Relationship)
                    flowFileExpiration = '0 sec'
                    backPressureObjectThreshold = 1000
                    backPressureDataSizeThreshold = '1 GB'
                    prioritizers = @()
                }
            }
            $updated = Invoke-RestMethod -Uri "$baseUri/connections/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 10)
            Write-Host "Updated connection: $Name"
            return $updated
        }
        $body = @{
            revision = @{ version = 0 }
            component = @{
                name = $Name
                source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
                destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
                selectedRelationships = @($Relationship)
                flowFileExpiration = '0 sec'
                backPressureObjectThreshold = 1000
                backPressureDataSizeThreshold = '1 GB'
                prioritizers = @()
            }
        }
        return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 10)
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers -Method Get
    $rootId = [string]$root.processGroupFlow.id
    $baseballGroupId = Find-ChildProcessGroup -ParentId $rootId -Name 'BaseballO - MLB Ingestion'
    $manualGroupId = Find-ChildProcessGroup -ParentId $baseballGroupId -Name '01 Games - Manual Inbox'

    $powerShell = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'
    $processorScript = Join-Path $script:RepositoryRoot 'scripts\pipeline\process-staged-game-json.ps1'
    $inbox = Join-Path $script:StateRoot 'pipeline\inbox\games'
    $staging = Join-Path $script:StateRoot 'pipeline\staging\manual-inbox'
    $nifiQuarantine = Join-Path $script:StateRoot 'pipeline\quarantine\nifi\games-manual'
    $commandArguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $processorScript, '-InputJson', (Join-Path $staging '${filename}')) -join ';'
    foreach ($directory in @($inbox, $staging, $nifiQuarantine)) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }

    $definitions = @(
        @{
            Key = 'Inbox'; Name = '10 Read locally supplied game JSON'; Type = 'org.apache.nifi.processors.standard.GetFile'
            Comments = 'Reads JSON placed in the local manual inbox. This processor makes no network requests.'
            X = 0; Y = 0; SchedulingPeriod = '10 sec'; AutoTerminate = @()
            Properties = @{
                'Input Directory' = $inbox
                'File Filter' = '(?i)^.+\.json$'
                'Batch Size' = '10'
                'Keep Source File' = 'false'
                'Recurse Subdirectories' = 'false'
                'Minimum File Age' = '2 sec'
                'Ignore Hidden Files' = 'true'
            }
        },
        @{
            Key = 'Prepare'; Name = '15 Assign collision-safe staging name'; Type = 'org.apache.nifi.processors.attributes.UpdateAttribute'; Artifact = 'nifi-update-attribute-nar'
            Comments = 'Retains the submitted filename as an attribute and assigns a NiFi UUID filename for the isolated local staging handoff.'
            X = 300; Y = 0; SchedulingPeriod = '0 sec'; AutoTerminate = @()
            Properties = @{
                'source.filename' = '${filename}'
                'filename' = '${uuid}.json'
            }
        },
        @{
            Key = 'Stage'; Name = '17 Stage byte-identical local file'; Type = 'org.apache.nifi.processors.standard.PutFile'
            Comments = 'Writes the unchanged FlowFile bytes to an isolated local staging path for the guarded PowerShell process.'
            X = 600; Y = 0; SchedulingPeriod = '0 sec'; AutoTerminate = @()
            Properties = @{
                'Directory' = $staging
                'Conflict Resolution Strategy' = 'fail'
                'Create Missing Directories' = 'true'
            }
        },
        @{
            Key = 'Import'; Name = '20 Archive, map, validate, and load'; Type = 'org.apache.nifi.processors.standard.ExecuteStreamCommand'
            Comments = 'Passes only the generated local staging path to the guarded importer, then runs the approved RML mapping and Fuseki PUT.'
            X = 900; Y = 0; SchedulingPeriod = '0 sec'; AutoTerminate = @('original')
            Properties = @{
                'Command Path' = $powerShell
                'Command Arguments Strategy' = 'Command Arguments Property'
                'Command Arguments' = $commandArguments
                'Argument Delimiter' = ';'
                'Ignore STDIN' = 'true'
                'Output MIME Type' = 'text/plain'
                'Working Directory' = $script:RepositoryRoot
                'BASEBALLO_LOCAL_ROOT' = $script:LocalRoot
            }
        },
        @{
            Key = 'Success'; Name = '30 Log successful manual import'; Type = 'org.apache.nifi.processors.standard.LogAttribute'
            Comments = 'Records the successful import output in NiFi provenance and application logs.'
            X = 1300; Y = 0; SchedulingPeriod = '0 sec'; AutoTerminate = @('success'); Properties = @{}
        },
        @{
            Key = 'Failure'; Name = '90 Persist failed manual import output'; Type = 'org.apache.nifi.processors.standard.PutFile'
            Comments = 'Persists command output for a failed import. The importer separately quarantines the exact supplied bytes and structured failure metadata.'
            X = 1300; Y = 300; SchedulingPeriod = '0 sec'; AutoTerminate = @('success', 'failure')
            Properties = @{
                'Directory' = $nifiQuarantine
                'Conflict Resolution Strategy' = 'fail'
                'Create Missing Directories' = 'true'
            }
        }
    )

    $processors = @{}
    foreach ($definition in $definitions) {
        $processors[$definition.Key] = Ensure-Processor -GroupId $manualGroupId -Definition $definition
    }
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'manual inbox to guarded import' -SourceId $processors.Inbox.component.id -DestinationId $processors.Prepare.component.id -Relationship 'success')
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'prepared input to local staging' -SourceId $processors.Prepare.component.id -DestinationId $processors.Stage.component.id -Relationship 'success')
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'staged input to guarded import' -SourceId $processors.Stage.component.id -DestinationId $processors.Import.component.id -Relationship 'success')
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'failed staging to quarantine' -SourceId $processors.Stage.component.id -DestinationId $processors.Failure.component.id -Relationship 'failure')
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'successful manual import output' -SourceId $processors.Import.component.id -DestinationId $processors.Success.component.id -Relationship 'output stream')
    [void](Ensure-Connection -GroupId $manualGroupId -Name 'failed manual import output' -SourceId $processors.Import.component.id -DestinationId $processors.Failure.component.id -Relationship 'nonzero status')

    $deadline = (Get-Date).AddSeconds(30)
    do {
        $current = @(Get-Processors -GroupId $manualGroupId | Where-Object { $_.component.name -in $definitions.Name })
        $valid = @($current | Where-Object { $_.component.validationStatus -eq 'VALID' })
        if ($valid.Count -eq $definitions.Count) {
            break
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    if ($valid.Count -ne $definitions.Count) {
        $invalid = $current | Where-Object { $_.component.validationStatus -ne 'VALID' }
        $details = $invalid | ForEach-Object { "$($_.component.name): $($_.component.validationErrors -join '; ')" }
        throw "NiFi manual game processors are not valid: $($details -join ' | ')"
    }

    if ($Enable) {
        foreach ($key in @('Success', 'Failure', 'Import', 'Stage', 'Prepare', 'Inbox')) {
            [void](Set-ProcessorState -ProcessorId $processors[$key].component.id -State 'RUNNING')
        }
        Write-Host "NiFi manual game inbox is running. Drop JSON into: $inbox"
    }
    else {
        Write-Host "NiFi manual game inbox is configured, connected, valid, and stopped. Inbox: $inbox"
    }
}
finally {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCertificateCallback
}
