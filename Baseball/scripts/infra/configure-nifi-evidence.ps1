[CmdletBinding()]
param(
    [ValidateSet(
        'mapping-shacl-validation',
        'selective-reasoning',
        'canned-query-audit',
        'advanced-query-audit',
        'authoritative-index-equivalence',
        'benchmark-evidence',
        'repository-validation'
    )]
    [string[]] $EnableStage = @()
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443)) {
    throw 'NiFi is not running on port 8443.'
}

$contractPath = Join-Path $script:RepositoryRoot 'infra\nifi\repeatable-stages.json'
$runnerPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\run-nifi-evidence-stage.py'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
if ([int]$contract.contractVersion -ne 1) {
    throw 'Unsupported repeatable NiFi stage contract version.'
}
$stageNames = @($contract.stages.PSObject.Properties.Name)
if ($stageNames.Count -eq 0) {
    throw 'The repeatable NiFi stage contract defines no stages.'
}
$python = (Get-Command python -ErrorAction Stop).Source
$powerShell = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'
$evidenceQuarantine = Join-Path $script:StateRoot 'pipeline\quarantine\nifi-evidence\processor-output'
[void](New-Item -ItemType Directory -Force -Path $evidenceQuarantine)

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
        param([string] $ParentId, [string] $Name)
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

    function Get-ProcessorEntity([string] $ProcessorId) {
        return Invoke-RestMethod -Uri "$baseUri/processors/$ProcessorId" -Headers $headers -Method Get
    }

    function Set-ProcessorState {
        param([string] $ProcessorId, [ValidateSet('RUNNING', 'STOPPED')][string] $State)
        $entity = Get-ProcessorEntity -ProcessorId $ProcessorId
        $body = @{ revision = @{ version = $entity.revision.version }; state = $State }
        return Invoke-RestMethod -Uri "$baseUri/processors/$ProcessorId/run-status" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 5)
    }

    function Ensure-Processor {
        param([string] $GroupId, [hashtable] $Definition)
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
                        artifact = $Definition.Artifact
                        version = $script:Versions.NiFi.Version
                    }
                    comments = $Definition.Comments
                    position = @{ x = $Definition.X; y = $Definition.Y }
                    state = 'STOPPED'
                    config = $config
                }
            }
            return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
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
        return Invoke-RestMethod -Uri "$baseUri/processors/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
    }

    function Get-Connections([string] $GroupId) {
        $response = Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Get
        return @($response.connections)
    }

    function Ensure-Connection {
        param([string] $GroupId, [string] $Name, [string] $SourceId, [string] $DestinationId, [string] $Relationship)
        $existing = Get-Connections -GroupId $GroupId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        $component = @{
            name = $Name
            source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = @($Relationship)
            flowFileExpiration = '0 sec'
            backPressureObjectThreshold = 100
            backPressureDataSizeThreshold = '100 MB'
            prioritizers = @()
        }
        if ($null -eq $existing) {
            $body = @{ revision = @{ version = 0 }; component = $component }
            return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 10)
        }
        $component.id = [string]$existing.component.id
        $body = @{ revision = @{ version = $existing.revision.version }; component = $component }
        return Invoke-RestMethod -Uri "$baseUri/connections/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 10)
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers -Method Get
    $rootId = [string]$root.processGroupFlow.id
    $baseballGroupId = Find-ChildProcessGroup -ParentId $rootId -Name 'BaseballO - MLB Ingestion'
    $evidenceGroupId = Find-ChildProcessGroup -ParentId $baseballGroupId -Name '91 Repeatable Validation and Evidence'

    $success = Ensure-Processor -GroupId $evidenceGroupId -Definition @{
        Name = '80 Record successful stage evidence'
        Type = 'org.apache.nifi.processors.standard.LogAttribute'
        Artifact = 'nifi-standard-nar'
        Comments = 'Records the compact stage evidence manifest in NiFi provenance and application logs.'
        X = 1050; Y = 0; SchedulingPeriod = '0 sec'; AutoTerminate = @('success'); Properties = @{}
    }
    $failure = Ensure-Processor -GroupId $evidenceGroupId -Definition @{
        Name = '90 Persist failed stage output'
        Type = 'org.apache.nifi.processors.standard.PutFile'
        Artifact = 'nifi-standard-nar'
        Comments = 'Persists processor output; the runner also writes a structured manifest and full log to the stage quarantine directory.'
        X = 1050; Y = 350; SchedulingPeriod = '0 sec'; AutoTerminate = @('success', 'failure')
        Properties = @{
            'Directory' = $evidenceQuarantine
            'Conflict Resolution Strategy' = 'fail'
            'Create Missing Directories' = 'true'
        }
    }

    $stageProcessors = @{}
    $row = 0
    foreach ($stageName in $stageNames) {
        $stage = $contract.stages.$stageName
        $y = $row * 180
        $trigger = Ensure-Processor -GroupId $evidenceGroupId -Definition @{
            Name = "10 Trigger $stageName"
            Type = 'org.apache.nifi.processors.standard.GenerateFlowFile'
            Artifact = 'nifi-standard-nar'
            Comments = "Timer trigger only. The authoritative command and dependencies are loaded from infra/nifi/repeatable-stages.json. $($stage.description)"
            X = 0; Y = $y; SchedulingPeriod = [string]$stage.schedule; AutoTerminate = @()
            Properties = @{
                'File Size' = '0B'
                'Batch Size' = '1'
                'Data Format' = 'Text'
                'Unique FlowFiles' = 'false'
                'filename' = "$stageName-`${uuid}.json"
                'baseballo.evidence.stage' = $stageName
            }
        }
        $arguments = @(
            '-u', $runnerPath,
            '--contract', $contractPath,
            '--stage', $stageName,
            '--state-root', $script:StateRoot
        ) -join ';'
        $execute = Ensure-Processor -GroupId $evidenceGroupId -Definition @{
            Name = "20 Run $stageName"
            Type = 'org.apache.nifi.processors.standard.ExecuteStreamCommand'
            Artifact = 'nifi-standard-nar'
            Comments = 'Runs one allowlisted stage through the shared dependency fingerprint, evidence manifest, and quarantine boundary.'
            X = 500; Y = $y; SchedulingPeriod = '0 sec'; AutoTerminate = @('original')
            Properties = @{
                'Command Path' = $python
                'Command Arguments Strategy' = 'Command Arguments Property'
                'Command Arguments' = $arguments
                'Argument Delimiter' = ';'
                'Ignore STDIN' = 'true'
                'Output MIME Type' = 'application/json'
                'Working Directory' = $script:RepositoryRoot
                'BASEBALLO_LOCAL_ROOT' = $script:LocalRoot
                'BASEBALLO_POWERSHELL' = $powerShell
            }
        }
        [void](Ensure-Connection -GroupId $evidenceGroupId -Name "$stageName trigger" -SourceId $trigger.component.id -DestinationId $execute.component.id -Relationship 'success')
        [void](Ensure-Connection -GroupId $evidenceGroupId -Name "$stageName success" -SourceId $execute.component.id -DestinationId $success.component.id -Relationship 'output stream')
        [void](Ensure-Connection -GroupId $evidenceGroupId -Name "$stageName failure" -SourceId $execute.component.id -DestinationId $failure.component.id -Relationship 'nonzero status')
        $stageProcessors[$stageName] = @{ Trigger = $trigger; Execute = $execute }
        $row++
    }

    $deadline = (Get-Date).AddSeconds(30)
    do {
        $current = @(Get-Processors -GroupId $evidenceGroupId)
        $invalid = @($current | Where-Object { $_.component.validationStatus -ne 'VALID' })
        if ($invalid.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    if ($invalid.Count -ne 0) {
        $details = $invalid | ForEach-Object { "$($_.component.name): $($_.component.validationErrors -join '; ')" }
        throw "NiFi evidence processors are not valid: $($details -join ' | ')"
    }

    if ($EnableStage.Count -gt 0) {
        [void](Set-ProcessorState -ProcessorId $success.component.id -State 'RUNNING')
        [void](Set-ProcessorState -ProcessorId $failure.component.id -State 'RUNNING')
        foreach ($stageName in $EnableStage) {
            [void](Set-ProcessorState -ProcessorId $stageProcessors[$stageName].Execute.component.id -State 'RUNNING')
            [void](Set-ProcessorState -ProcessorId $stageProcessors[$stageName].Trigger.component.id -State 'RUNNING')
            Write-Host "Enabled NiFi evidence stage: $stageName"
        }
    }
    else {
        Write-Host 'NiFi evidence stages are configured, connected, valid, and stopped.'
    }
}
finally {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCertificateCallback
}
