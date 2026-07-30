[CmdletBinding()]
param(
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string] $TestDate,
    [ValidatePattern('^\d+$')][string] $TestGamePk,
    [switch] $RunOnce,
    [switch] $EnableDaily
)

. (Join-Path $PSScriptRoot 'common.ps1')

if ($RunOnce -and ([string]::IsNullOrWhiteSpace($TestDate) -or [string]::IsNullOrWhiteSpace($TestGamePk))) {
    throw '-RunOnce requires both -TestDate and -TestGamePk.'
}
if ($EnableDaily -and (-not [string]::IsNullOrWhiteSpace($TestDate) -or -not [string]::IsNullOrWhiteSpace($TestGamePk))) {
    throw '-EnableDaily cannot be combined with test filters.'
}
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
            [Parameter(Mandatory = $true)][ValidateSet('RUNNING', 'STOPPED', 'RUN_ONCE')][string] $State
        )
        $entity = Get-ProcessorEntity -ProcessorId $ProcessorId
        $body = @{
            revision = @{ version = $entity.revision.version }
            state = $State
        }
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
            schedulingStrategy = $Definition.SchedulingStrategy
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
                        artifact = 'nifi-standard-nar'
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
            if ([string]$existing.component.source.id -ne $SourceId -or [string]$existing.component.destination.id -ne $DestinationId -or $Relationship -notin @($existing.component.selectedRelationships)) {
                throw "Existing NiFi connection does not match its contract: $Name"
            }
            Write-Host "Present connection: $Name"
            return $existing
        }
        $body = @{
            revision = @{ version = 0 }
            component = @{
                name = $Name
                source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
                destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
                selectedRelationships = @($Relationship)
                flowFileExpiration = '0 sec'
                backPressureObjectThreshold = 10000
                backPressureDataSizeThreshold = '1 GB'
                prioritizers = @()
            }
        }
        $created = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 10)
        Write-Host "Created connection: $Name"
        return $created
    }

    function Get-ProcessorFlowFilesIn([string] $ProcessorId) {
        $status = Invoke-RestMethod -Uri "$baseUri/flow/processors/$ProcessorId/status" -Headers $headers -Method Get
        return [int64]$status.processorStatus.aggregateSnapshot.flowFilesIn
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers -Method Get
    $rootId = [string]$root.processGroupFlow.id
    $baseballGroupId = Find-ChildProcessGroup -ParentId $rootId -Name 'BaseballO - MLB Ingestion'
    $gamesGroupId = Find-ChildProcessGroup -ParentId $baseballGroupId -Name '01 Games - Daily'

    $powerShell = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path -LiteralPath $powerShell -PathType Leaf)) {
        throw "Windows PowerShell executable is missing: $powerShell"
    }
    $acquisitionScript = Join-Path $script:RepositoryRoot 'scripts\pipeline\acquire-daily-games.ps1'
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $acquisitionScript)
    if (-not [string]::IsNullOrWhiteSpace($TestDate)) {
        $arguments += @('-Date', $TestDate)
    }
    if (-not [string]::IsNullOrWhiteSpace($TestGamePk)) {
        $arguments += @('-GamePk', $TestGamePk)
    }
    $commandArguments = $arguments -join ';'
    $nifiQuarantine = Join-Path $script:StateRoot 'pipeline\quarantine\nifi\games-daily'
    [void](New-Item -ItemType Directory -Force -Path $nifiQuarantine)

    $definitions = @(
        @{
            Key = 'Trigger'
            Name = '10 Daily trigger - 06:15 local'
            Type = 'org.apache.nifi.processors.standard.GenerateFlowFile'
            Comments = 'One trigger each day at 06:15 local time. The acquisition command looks back three completed dates so a sleeping or stopped workstation can catch up.'
            X = 0; Y = 0
            SchedulingStrategy = 'CRON_DRIVEN'; SchedulingPeriod = '0 15 6 * * ?'
            AutoTerminate = @()
            Properties = @{
                'Batch Size' = '1'
                'Data Format' = 'Text'
                'Custom Text' = 'BaseballO daily MLB game acquisition trigger'
                'Character Set' = 'UTF-8'
                'Unique FlowFiles' = 'false'
                'Mime Type' = 'text/plain'
            }
        },
        @{
            Key = 'Acquire'
            Name = '20 Acquire final games and load RDF'
            Type = 'org.apache.nifi.processors.standard.ExecuteStreamCommand'
            Comments = 'Invokes the tested acquisition harness: immutable MLB archive, separate manifest, final-game preflight, pinned RMLMapper, RDF validation, and idempotent Fuseki PUT.'
            X = 400; Y = 0
            SchedulingStrategy = 'TIMER_DRIVEN'; SchedulingPeriod = '0 sec'
            AutoTerminate = @('original')
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
            Key = 'Success'
            Name = '30 Log successful daily run'
            Type = 'org.apache.nifi.processors.standard.LogAttribute'
            Comments = 'Records the successful command output in NiFi provenance and application logs.'
            X = 800; Y = 0
            SchedulingStrategy = 'TIMER_DRIVEN'; SchedulingPeriod = '0 sec'
            AutoTerminate = @('success')
            Properties = @{}
        },
        @{
            Key = 'Failure'
            Name = '90 Persist failed daily run output'
            Type = 'org.apache.nifi.processors.standard.PutFile'
            Comments = 'Persists non-zero command output. The acquisition harness also moves its detailed failure.json and partial work into quarantine/acquisition.'
            X = 800; Y = 300
            SchedulingStrategy = 'TIMER_DRIVEN'; SchedulingPeriod = '0 sec'
            AutoTerminate = @('success', 'failure')
            Properties = @{
                'Directory' = $nifiQuarantine
                'Conflict Resolution Strategy' = 'fail'
                'Create Missing Directories' = 'true'
            }
        }
    )

    $processors = @{}
    foreach ($definition in $definitions) {
        $processors[$definition.Key] = Ensure-Processor -GroupId $gamesGroupId -Definition $definition
    }

    [void](Ensure-Connection -GroupId $gamesGroupId -Name 'daily trigger to acquisition' -SourceId $processors.Trigger.component.id -DestinationId $processors.Acquire.component.id -Relationship 'success')
    [void](Ensure-Connection -GroupId $gamesGroupId -Name 'successful acquisition output' -SourceId $processors.Acquire.component.id -DestinationId $processors.Success.component.id -Relationship 'output stream')
    [void](Ensure-Connection -GroupId $gamesGroupId -Name 'failed acquisition output' -SourceId $processors.Acquire.component.id -DestinationId $processors.Failure.component.id -Relationship 'nonzero status')

    $deadline = (Get-Date).AddSeconds(30)
    do {
        $current = @(Get-Processors -GroupId $gamesGroupId | Where-Object { $_.component.name -in $definitions.Name })
        $valid = @($current | Where-Object { $_.component.validationStatus -eq 'VALID' })
        if ($valid.Count -eq $definitions.Count) {
            break
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    if ($valid.Count -ne $definitions.Count) {
        $invalid = $current | Where-Object { $_.component.validationStatus -ne 'VALID' }
        $details = $invalid | ForEach-Object { "$($_.component.name): $($_.component.validationErrors -join '; ')" }
        throw "NiFi daily game processors are not valid: $($details -join ' | ')"
    }

    if ($RunOnce) {
        $successBefore = Get-ProcessorFlowFilesIn -ProcessorId $processors.Success.component.id
        $failureBefore = Get-ProcessorFlowFilesIn -ProcessorId $processors.Failure.component.id
        $outcome = $null
        try {
            [void](Set-ProcessorState -ProcessorId $processors.Success.component.id -State 'RUNNING')
            [void](Set-ProcessorState -ProcessorId $processors.Failure.component.id -State 'RUNNING')
            [void](Set-ProcessorState -ProcessorId $processors.Acquire.component.id -State 'RUNNING')
            [void](Set-ProcessorState -ProcessorId $processors.Trigger.component.id -State 'RUN_ONCE')
            Write-Host "Running one controlled NiFi acquisition for $TestDate game $TestGamePk..."

            $deadline = (Get-Date).AddSeconds(120)
            do {
                Start-Sleep -Seconds 2
                $successNow = Get-ProcessorFlowFilesIn -ProcessorId $processors.Success.component.id
                $failureNow = Get-ProcessorFlowFilesIn -ProcessorId $processors.Failure.component.id
                if ($failureNow -gt $failureBefore) {
                    $outcome = 'failure'
                    break
                }
                if ($successNow -gt $successBefore) {
                    $outcome = 'success'
                    break
                }
            } while ((Get-Date) -lt $deadline)
        }
        finally {
            foreach ($key in @('Trigger', 'Acquire', 'Success', 'Failure')) {
                try {
                    [void](Set-ProcessorState -ProcessorId $processors[$key].component.id -State 'STOPPED')
                }
                catch {
                    Write-Warning "Could not stop controlled-run processor $key`: $($_.Exception.Message)"
                }
            }
        }
        if ($outcome -ne 'success') {
            throw "Controlled NiFi acquisition did not complete successfully; outcome: $outcome"
        }
        Write-Host 'Controlled NiFi acquisition completed successfully; all daily processors are stopped.'
    }
    elseif ($EnableDaily) {
        [void](Set-ProcessorState -ProcessorId $processors.Success.component.id -State 'RUNNING')
        [void](Set-ProcessorState -ProcessorId $processors.Failure.component.id -State 'RUNNING')
        [void](Set-ProcessorState -ProcessorId $processors.Acquire.component.id -State 'RUNNING')
        [void](Set-ProcessorState -ProcessorId $processors.Trigger.component.id -State 'RUNNING')
        Write-Host 'NiFi daily game acquisition is enabled for 06:15 local time.'
    }
    else {
        Write-Host 'NiFi daily game acquisition is configured, connected, valid, and stopped.'
    }
}
finally {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCertificateCallback
}
