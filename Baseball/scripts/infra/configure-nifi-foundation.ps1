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

    function Get-NiFiChildGroups([string] $ParentId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$ParentId/process-groups" -Headers $headers -Method Get
        return @($response.processGroups)
    }

    function Ensure-NiFiProcessGroup {
        param(
            [Parameter(Mandatory = $true)][string] $ParentId,
            [Parameter(Mandatory = $true)][string] $Name,
            [Parameter(Mandatory = $true)][string] $Comments,
            [Parameter(Mandatory = $true)][double] $X,
            [Parameter(Mandatory = $true)][double] $Y
        )

        $existing = Get-NiFiChildGroups -ParentId $ParentId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        if ($null -ne $existing) {
            $entity = @{
                revision = @{ version = $existing.revision.version }
                component = @{
                    id = [string]$existing.component.id
                    name = $Name
                    comments = $Comments
                    position = @{ x = $X; y = $Y }
                }
            }
            $updated = Invoke-RestMethod -Uri "$baseUri/process-groups/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($entity | ConvertTo-Json -Depth 8)
            Write-Host "Aligned: $Name"
            return [string]$updated.component.id
        }

        $entity = @{
            revision = @{ version = 0 }
            component = @{
                name = $Name
                comments = $Comments
                position = @{ x = $X; y = $Y }
            }
        }
        $created = Invoke-RestMethod -Uri "$baseUri/process-groups/$ParentId/process-groups" -Headers $headers -Method Post -ContentType 'application/json' -Body ($entity | ConvertTo-Json -Depth 8)
        Write-Host "Created: $Name"
        return [string]$created.component.id
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers -Method Get
    $rootId = [string]$root.processGroupFlow.id
    $baseballGroupId = Ensure-NiFiProcessGroup -ParentId $rootId -Name 'BaseballO - MLB Ingestion' -Comments 'Local data movement and semantic processing. Raw source JSON remains unchanged; semantic output comes only from approved RML mappings.' -X 0 -Y 0

    $groups = @(
        @{ Name = '01 Games - Manual Inbox'; Comments = 'Process locally supplied completed-game JSON without making an external data request.'; X = 0; Y = 0 },
        @{ Name = '01 Games - Daily'; Comments = 'Parked network-acquisition design. Keep stopped pending an approved data-access source.'; X = 450; Y = 0 },
        @{ Name = '02 Transactions - Daily'; Comments = 'Reserved for a future approved transaction source; no executable acquisition is enabled.'; X = 900; Y = 0 },
        @{ Name = '03 Reference Data - Annual'; Comments = 'Reserved for a future approved reference source; no executable acquisition is enabled.'; X = 1350; Y = 0 },
        @{ Name = '90 Shared RDF Mapping and Load'; Comments = 'Invoke the pinned RML processor, validate RDF, and PUT complete named graphs to Fuseki.'; X = 450; Y = 350 },
        @{ Name = '99 Quarantine'; Comments = 'Hold failed import, mapping, validation, and graph-load artifacts with error metadata.'; X = 900; Y = 350 }
    )
    foreach ($group in $groups) {
        [void](Ensure-NiFiProcessGroup -ParentId $baseballGroupId -Name $group.Name -Comments $group.Comments -X $group.X -Y $group.Y)
    }

    Write-Host 'NiFi foundational process-group hierarchy is present.'
}
finally {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCertificateCallback
}
