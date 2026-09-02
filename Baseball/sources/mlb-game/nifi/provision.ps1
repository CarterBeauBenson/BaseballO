[CmdletBinding()]
param(
    [switch] $RunProof,
    [switch] $RunBackfill,
    [switch] $StartDaily,
    [ValidatePattern('^\d+$')][string] $ProofGamePk = '566279'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$api = $script:NiFiApiUri
$contractPath = Join-Path $PSScriptRoot 'flow-contract.json'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
if ([string]$contract.artifactType -ne 'baseballo-nifi-source-flow-contract' -or [string]$contract.sourceModule -ne 'mlb-game') {
    throw "Unsupported MLB Game flow contract: $contractPath"
}
$schedule = $contract.scheduleDiscovery
if ([string]$schedule.dailyCron -ne '0 0 5 * * ?' -or [string]$schedule.timeZone -ne 'America/New_York') {
    throw 'MLB Game daily acquisition must run at 05:00 America/New_York.'
}
$proofReleasePolicy = $contract.proofRelease
if (
    [int]$proofReleasePolicy.readinessRetryCount -ne 60 -or
    [string]$proofReleasePolicy.readinessRetryDelay -ne '30 sec' -or
    [string]$proofReleasePolicy.exhaustedAction -ne 'source-local-schedule-quarantine'
) {
    throw 'MLB Game proof release must wait up to 30 minutes and then quarantine locally.'
}
$stageScript = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\pipeline\stage.ps1'))
$scheduleParser = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "sources\mlb-game\$([string]$schedule.parser)"))
$batchMaterializer = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "sources\mlb-game\$([string]$contract.batchMaterialization.processor)"))
$proofReleaseScript = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'scripts\pipeline\check-source-proof-release.py'))
foreach ($required in @($stageScript, $scheduleParser, $batchMaterializer, $proofReleaseScript)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "MLB Game NiFi executable is missing: $required"
    }
}
$transientDirectory = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'pipeline\transient\mlb-game'))
$powershell = Join-Path $PSHOME 'powershell.exe'
$python = (Get-Command python -ErrorAction Stop).Source
[void](New-Item -ItemType Directory -Force -Path $transientDirectory)

function Invoke-NiFi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('GET', 'POST', 'PUT', 'DELETE')][string] $Method,
        [Parameter(Mandatory = $true)][string] $Path,
        $Body
    )
    $arguments = @{
        Uri = "$api$Path"
        Method = $Method
        TimeoutSec = 60
    }
    if ($null -ne $Body) {
        $arguments.ContentType = 'application/json'
        $arguments.Body = $Body | ConvertTo-Json -Depth 30
    }
    return Invoke-RestMethod @arguments
}

function Remove-ConnectionIfPresent([string] $GroupId, [string] $Name) {
    $matches = @((Get-GroupFlow -GroupId $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) {
        throw "More than one connection is named '$Name'."
    }
    if ($matches.Count -eq 0) {
        return
    }
    $entity = Invoke-NiFi -Method GET -Path "/connections/$($matches[0].id)"
    $queued = 0
    if ($null -ne $entity.status -and $null -ne $entity.status.aggregateSnapshot -and $entity.status.aggregateSnapshot.PSObject.Properties.Name -contains 'flowFilesQueued') {
        $queued = [int64]$entity.status.aggregateSnapshot.flowFilesQueued
    }
    if ($queued -gt 0) {
        throw "Cannot replace connection '$Name' while it contains queued FlowFiles."
    }
    Invoke-NiFi -Method DELETE -Path "/connections/$($entity.id)?version=$($entity.revision.version)" | Out-Null
}

function Get-GroupFlow([string] $GroupId) {
    return (Invoke-NiFi -Method GET -Path "/flow/process-groups/$GroupId").processGroupFlow.flow
}

function Get-OrCreateProcessGroup {
    param(
        [Parameter(Mandatory = $true)][string] $ParentId,
        [Parameter(Mandatory = $true)][string] $Name,
        [int] $X,
        [int] $Y
    )
    $matches = @((Get-GroupFlow -GroupId $ParentId).processGroups | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) {
        throw "More than one NiFi process group is named '$Name'."
    }
    if ($matches.Count -eq 1) {
        return $matches[0].id
    }
    $created = Invoke-NiFi -Method POST -Path "/process-groups/$ParentId/process-groups" -Body @{
        revision = @{ version = 0 }
        component = @{
            name = $Name
            position = @{ x = $X; y = $Y }
            comments = 'Owned by the BaseballO detachable source-module contract.'
        }
    }
    return $created.id
}

function Stop-OwnedProcessGroupForReconciliation {
    param([Parameter(Mandatory = $true)][string] $GroupId)

    $active = @(
        (Get-GroupFlow -GroupId $GroupId).processors |
            Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') }
    )
    if ($active.Count -eq 0) {
        return
    }
    Invoke-NiFi -Method PUT -Path "/flow/process-groups/$GroupId" -Body @{
        id = $GroupId
        state = 'STOPPED'
        disconnectedNodeAcknowledged = $false
    } | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $remaining = @(
            (Get-GroupFlow -GroupId $GroupId).processors |
                Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') }
        )
        if ($remaining.Count -eq 0) {
            return
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "The owned MLB Game process group did not stop before reconciliation: $(@($remaining.component.name) -join ', ')"
}

function Get-ProcessorType([string] $Type) {
    $response = Invoke-NiFi -Method GET -Path "/flow/processor-types?type=$([Uri]::EscapeDataString($Type))"
    $matches = @($response.processorTypes | Where-Object { $_.type -eq $Type })
    if ($matches.Count -ne 1) {
        throw "NiFi processor type is not uniquely available: $Type"
    }
    return $matches[0]
}

function Ensure-Processor {
    param(
        [Parameter(Mandatory = $true)][string] $GroupId,
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Type,
        [Parameter(Mandatory = $true)][hashtable] $Properties,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $AutoTerminate,
        [int] $X,
        [int] $Y,
        [string] $SchedulingPeriod = '0 sec',
        [ValidateSet('TIMER_DRIVEN', 'CRON_DRIVEN')][string] $SchedulingStrategy = 'TIMER_DRIVEN'
    )
    $matches = @((Get-GroupFlow -GroupId $GroupId).processors | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) {
        throw "More than one processor is named '$Name' in the MLB Game group."
    }
    $processorType = Get-ProcessorType -Type $Type
    $config = @{
        properties = $Properties
        schedulingPeriod = $SchedulingPeriod
        schedulingStrategy = $SchedulingStrategy
        executionNode = 'ALL'
        concurrentlySchedulableTaskCount = 1
        penaltyDuration = '30 sec'
        yieldDuration = '1 sec'
        bulletinLevel = 'WARN'
        autoTerminatedRelationships = $AutoTerminate
    }
    if ($matches.Count -eq 0) {
        $entity = Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/processors" -Body @{
            revision = @{ version = 0 }
            component = @{
                name = $Name
                type = $Type
                bundle = $processorType.bundle
                position = @{ x = $X; y = $Y }
                config = $config
            }
        }
        return $entity.id
    }
    $current = Invoke-NiFi -Method GET -Path "/processors/$($matches[0].id)"
    if ($current.component.type -ne $Type) {
        throw "Processor '$Name' has type $($current.component.type), expected $Type."
    }
    $updated = Invoke-NiFi -Method PUT -Path "/processors/$($current.id)" -Body @{
        revision = @{ version = $current.revision.version }
        component = @{
            id = $current.id
            name = $Name
            position = @{ x = $X; y = $Y }
            config = $config
        }
    }
    return $updated.id
}

function Ensure-Connection {
    param(
        [Parameter(Mandatory = $true)][string] $GroupId,
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $SourceId,
        [Parameter(Mandatory = $true)][string] $DestinationId,
        [Parameter(Mandatory = $true)][string[]] $Relationships
    )
    $matches = @((Get-GroupFlow -GroupId $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) {
        throw "More than one connection is named '$Name'."
    }
    if ($matches.Count -eq 1) {
        $component = $matches[0].component
        if (
            $component.source.id -ne $SourceId -or
            $component.destination.id -ne $DestinationId -or
            (@($component.selectedRelationships) -join '|') -ne (@($Relationships) -join '|')
        ) {
            throw "Existing connection '$Name' differs from its source-module contract."
        }
        return $matches[0].id
    }
    $entity = Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/connections" -Body @{
        revision = @{ version = 0 }
        component = @{
            name = $Name
            source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = $Relationships
            flowFileExpiration = '0 sec'
            backPressureObjectThreshold = 1000
            backPressureDataSizeThreshold = '1 GB'
            loadBalanceStrategy = 'DO_NOT_LOAD_BALANCE'
            loadBalanceCompression = 'DO_NOT_COMPRESS'
            bends = @()
        }
    }
    return $entity.id
}

function Stage-Arguments([string] $Action, [bool] $NeedsInput, [bool] $NeedsFailureStage) {
    $arguments = "-NoLogo;-NoProfile;-NonInteractive;-ExecutionPolicy;Bypass;-File;$stageScript;-Action;$Action;-GamePk;`${game.pk};-RunId;`${pipeline.run.id}"
    if ($Action -eq 'rml') {
        $arguments += ';-ScheduleEvidencePath;${schedule.evidence.path}'
    }
    if ($NeedsInput) {
        $arguments += ';-InputJson;${transient.path}'
    }
    if ($NeedsFailureStage) {
        $arguments += ';-FailureStage;${failure.stage}'
    }
    return $arguments
}

function Ensure-StageProcessor {
    param([string] $GroupId, [string] $Name, [string] $Action, [bool] $NeedsInput, [int] $X, [int] $Y)
    return Ensure-Processor -GroupId $GroupId -Name $Name -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X $X -Y $Y -AutoTerminate @('output stream', 'nonzero status') -Properties @{
        'Working Directory' = $repositoryRoot
        'Command Path' = $powershell
        'Command Arguments Strategy' = 'Command Arguments Property'
        'Command Arguments' = Stage-Arguments -Action $Action -NeedsInput $NeedsInput -NeedsFailureStage $false
        'Argument Delimiter' = ';'
        'Ignore STDIN' = 'true'
        'Output Destination Attribute' = "stage.$Action.output"
        'Max Attribute Length' = '65536'
        'Output MIME Type' = 'application/json'
    }
}

function Ensure-ExitGate([string] $GroupId, [string] $Stage, [int] $X, [int] $Y) {
    return Ensure-Processor -GroupId $GroupId -Name "Require $Stage Success" -Type 'org.apache.nifi.processors.standard.RouteOnAttribute' -X $X -Y $Y -AutoTerminate @() -Properties @{
        'Routing Strategy' = 'Route to Property name'
        'passed' = "`${execution.status:equals('0')}"
    }
}

function Ensure-RetryProcessor(
    [string] $GroupId,
    [string] $Stage,
    [int] $X,
    [int] $Y,
    [int] $MaximumRetries = 3
) {
    return Ensure-Processor -GroupId $GroupId -Name "Retry $Stage" -Type 'org.apache.nifi.processors.standard.RetryFlowFile' -X $X -Y $Y -AutoTerminate @('failure') -SchedulingPeriod '1 sec' -Properties @{
        'Retry Attribute' = "retry.$($Stage.ToLowerInvariant().Replace(' ', '-'))"
        'Maximum Retries' = [string]$MaximumRetries
        'Penalize Retries' = 'true'
        'Fail on Nonnumerical Overwrite' = 'true'
        'Reuse Mode' = 'fail'
    }
}

function Ensure-FailureStageProcessor([string] $GroupId, [string] $Stage, [int] $X, [int] $Y) {
    return Ensure-Processor -GroupId $GroupId -Name "Fail $Stage" -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X $X -Y $Y -AutoTerminate @() -Properties @{
        'Delete Attributes Expression' = ''
        'Store State' = 'Do not store state'
        'Stateful Variables Initial Value' = ''
        'Cache Value Lookup Cache Size' = '100'
        'failure.stage' = $Stage.ToLowerInvariant().Replace(' ', '-')
    }
}

$rootId = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow.id
$baseballGroupId = Get-OrCreateProcessGroup -ParentId $rootId -Name $script:NiFiRootProcessGroupName -X 100 -Y 100
$groupId = Get-OrCreateProcessGroup -ParentId $baseballGroupId -Name $script:MlbGameProcessGroupName -X 100 -Y 100
Stop-OwnedProcessGroupForReconciliation -GroupId $groupId

foreach ($obsoleteConnection in @(
    '08 RML complete',
    '09 SHACL complete',
    '10 graph pair promoted',
    '13 promotion passed to materialization',
    '11 SQL materialized',
    '12 cleanup complete',
    'retry RML input',
    'retry SHACL input',
    'retry Promotion input',
    'retry Materialization input',
    'retry Cleanup input',
    '01 schedule batch prepared',
    'proof release failed'
)) {
    Remove-ConnectionIfPresent -GroupId $groupId -Name $obsoleteConnection
}

$processors = @{}
$processors.request = Ensure-Processor -GroupId $groupId -Name 'Proof Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y 0 -SchedulingPeriod '365 days' -AutoTerminate @() -Properties @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false';
    'Custom Text' = "{`"gamePk`":`"$ProofGamePk`",`"materializeMode`":`"immediate`",`"scheduleEvidencePath`":`"none`"}"; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
}
$processors.readRequest = Ensure-Processor -GroupId $groupId -Name 'Read Request' -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 320 -Y 0 -AutoTerminate @() -Properties @{
    'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn';
    'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB'; 'game.pk' = '$.gamePk';
    'materialize.mode' = '$.materializeMode'; 'batch.id' = '$.batchId';
    'schedule.evidence.path' = '$.scheduleEvidencePath'
}
$backfillText = $schedule.backfillRequest | ConvertTo-Json -Depth 10 -Compress
$processors.backfillRequest = Ensure-Processor -GroupId $groupId -Name 'Backfill Schedule Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -360 -SchedulingPeriod '365 days' -AutoTerminate @() -Properties @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false';
    'Custom Text' = $backfillText; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
}
$processors.readScheduleRequest = Ensure-Processor -GroupId $groupId -Name 'Read Schedule Request' -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 320 -Y -360 -AutoTerminate @() -Properties @{
    'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn';
    'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB';
    'start.date' = '$.startDate'; 'end.date' = '$.endDate'; 'request.kind' = '$.requestKind'
}
$processors.dailyRequest = Ensure-Processor -GroupId $groupId -Name 'Daily 05:00 Eastern Schedule' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -640 -SchedulingPeriod ([string]$schedule.dailyCron) -SchedulingStrategy 'CRON_DRIVEN' -AutoTerminate @() -Properties @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false';
    'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
}
$processors.prepareDailySchedule = Ensure-Processor -GroupId $groupId -Name 'Prepare Daily Schedule Request' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 320 -Y -640 -AutoTerminate @() -Properties @{
    'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = '';
    'Cache Value Lookup Cache Size' = '100';
    'start.date' = '${now():minus(86400000):format("yyyy-MM-dd","America/New_York")}';
    'end.date' = '${now():minus(86400000):format("yyyy-MM-dd","America/New_York")}';
    'request.kind' = 'daily'
}
$processors.prepareSchedule = Ensure-Processor -GroupId $groupId -Name 'Prepare Schedule Batch' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 640 -Y -420 -AutoTerminate @() -Properties @{
    'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = '';
    'Cache Value Lookup Cache Size' = '100'; 'batch.id' = "`${uuid:replace('-', '')}"
}
$proofReleaseArguments = "-B;$proofReleaseScript;--state-root;$script:StateRoot;--contract;$contractPath"
$processors.proofRelease = Ensure-Processor -GroupId $groupId -Name 'Check Proof Release' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 800 -Y -580 -AutoTerminate @('output stream', 'nonzero status') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property';
    'Command Arguments' = $proofReleaseArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true';
    'Output Destination Attribute' = 'proof.release.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}
$processors.scheduleHttp = Ensure-Processor -GroupId $groupId -Name 'Acquire MLB Schedule' -Type 'org.apache.nifi.processors.standard.InvokeHTTP' -X 960 -Y -420 -AutoTerminate @('Original') -Properties @{
    'HTTP Method' = 'GET'; 'HTTP URL' = [string]$schedule.url;
    'HTTP/2 Disabled' = 'False'; 'Connection Timeout' = '15 secs'; 'Socket Read Timeout' = '120 secs';
    'Socket Write Timeout' = '60 secs'; 'Request Body Enabled' = 'false'; 'Request User-Agent' = 'BaseballO/1.0';
    'Response Body Ignored' = 'false'; 'Response Generation Required' = 'true'; 'Response Redirects Enabled' = 'True'
}
$scheduleArguments = "-B;$scheduleParser;--state-root;$script:StateRoot;--batch-id;`${batch.id};--request-kind;`${request.kind};--start-date;`${start.date};--end-date;`${end.date}"
$processors.prepareScheduleRequests = Ensure-Processor -GroupId $groupId -Name 'Prepare Final Game Requests' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 1280 -Y -420 -AutoTerminate @('original') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property';
    'Command Arguments' = $scheduleArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'false';
    'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}
$processors.splitSchedule = Ensure-Processor -GroupId $groupId -Name 'Split Final Game Requests' -Type 'org.apache.nifi.processors.standard.SplitJson' -X 1600 -Y -420 -AutoTerminate @('original') -Properties @{
    'JsonPath Expression' = [string]$schedule.recordsJsonPath; 'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB'
}
$processors.http = Ensure-Processor -GroupId $groupId -Name 'Acquire MLB Game' -Type 'org.apache.nifi.processors.standard.InvokeHTTP' -X 640 -Y 0 -AutoTerminate @('Original') -Properties @{
    'HTTP Method' = 'GET'; 'HTTP URL' = 'https://statsapi.mlb.com/api/v1.1/game/${game.pk}/feed/live';
    'HTTP/2 Disabled' = 'False'; 'Connection Timeout' = '15 secs'; 'Socket Read Timeout' = '60 secs';
    'Socket Write Timeout' = '60 secs'; 'Request Body Enabled' = 'false'; 'Request User-Agent' = 'BaseballO/1.0';
    'Response Body Ignored' = 'false'; 'Response Generation Required' = 'true'; 'Response Redirects Enabled' = 'True'
}
$processors.readResponse = Ensure-Processor -GroupId $groupId -Name 'Read MLB Response' -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 960 -Y 0 -AutoTerminate @() -Properties @{
    'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn';
    'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB';
    'payload.game.pk' = '$.gamePk'; 'payload.state' = '$.gameData.status.abstractGameState'
}
$processors.requireFinal = Ensure-Processor -GroupId $groupId -Name 'Require Final Game' -Type 'org.apache.nifi.processors.standard.RouteOnAttribute' -X 1280 -Y 0 -AutoTerminate @() -Properties @{
    'Routing Strategy' = 'Route to Property name';
    'final' = '${payload.game.pk:equals(${game.pk}):and(${payload.state:equals(''Final'')})}'
}
$processors.namePayload = Ensure-Processor -GroupId $groupId -Name 'Name Transient Payload' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 1600 -Y 0 -AutoTerminate @() -Properties @{
    'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = '';
    'Cache Value Lookup Cache Size' = '100'; 'filename' = 'game-${game.pk}-${uuid}.json';
    'pipeline.run.id' = "`${uuid:replace('-', '')}"; 'transient.path' = "$transientDirectory\game-`${game.pk}-`${uuid}.json"
}
$processors.put = Ensure-Processor -GroupId $groupId -Name 'Write Transient Payload' -Type 'org.apache.nifi.processors.standard.PutFile' -X 1920 -Y 0 -AutoTerminate @() -Properties @{
    'Directory' = $transientDirectory; 'Conflict Resolution Strategy' = 'fail'; 'Create Missing Directories' = 'true'
}
$processors.rml = Ensure-StageProcessor -GroupId $groupId -Name 'RML' -Action 'rml' -NeedsInput $true -X 2240 -Y 0
$processors.shacl = Ensure-StageProcessor -GroupId $groupId -Name 'Source SHACL' -Action 'shacl' -NeedsInput $false -X 2560 -Y 0
$processors.promote = Ensure-StageProcessor -GroupId $groupId -Name 'Promote Graph Pair' -Action 'promote' -NeedsInput $true -X 2880 -Y 0
$processors.chooseMaterialization = Ensure-Processor -GroupId $groupId -Name 'Choose Materialization Mode' -Type 'org.apache.nifi.processors.standard.RouteOnAttribute' -X 3120 -Y 0 -AutoTerminate @() -Properties @{
    'Routing Strategy' = 'Route to Property name';
    'immediate' = "`${materialize.mode:equals('immediate')}";
    'deferred' = "`${materialize.mode:equals('deferred')}"
}
$processors.materialize = Ensure-StageProcessor -GroupId $groupId -Name 'Materialize SQL' -Action 'materialize' -NeedsInput $false -X 3200 -Y 0
$processors.cleanup = Ensure-StageProcessor -GroupId $groupId -Name 'Cleanup Transient Artifacts' -Action 'cleanup' -NeedsInput $true -X 3520 -Y 0
$processors.success = Ensure-Processor -GroupId $groupId -Name 'Record Success' -Type 'org.apache.nifi.processors.standard.LogAttribute' -X 3840 -Y 0 -AutoTerminate @('success') -Properties @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(game|pipeline|stage|transient)\..*$';
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO MLB Game success'; 'Character Set' = 'UTF-8'
}
$processors.batchMaterializationTrigger = Ensure-Processor -GroupId $groupId -Name 'Check Pending Batch Materialization' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 2880 -Y -520 -SchedulingPeriod ([string]$contract.batchMaterialization.checkPeriod) -AutoTerminate @() -Properties @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false';
    'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
}
$batchMaterializationArguments = "-B;$batchMaterializer;--state-root;$script:StateRoot"
$processors.batchMaterialize = Ensure-Processor -GroupId $groupId -Name 'Materialize Ready Schedule Batches' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 3200 -Y -520 -AutoTerminate @('output stream', 'nonzero status') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property';
    'Command Arguments' = $batchMaterializationArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true';
    'Output Destination Attribute' = 'batch.materialization.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}
$processors.batchMaterializationResult = Ensure-Processor -GroupId $groupId -Name 'Record Batch Materialization Result' -Type 'org.apache.nifi.processors.standard.LogAttribute' -X 3680 -Y -520 -AutoTerminate @('success') -Properties @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(batch|execution)\..*$';
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO MLB Game batch materialization'; 'Character Set' = 'UTF-8'
}
$processors.batchMaterializationFailure = Ensure-Processor -GroupId $groupId -Name 'Record Batch Materialization Failure' -Type 'org.apache.nifi.processors.standard.LogAttribute' -X 3680 -Y -300 -AutoTerminate @('success') -Properties @{
    'Log Level' = 'error'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(batch|execution)\..*$';
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO MLB Game batch materialization failure'; 'Character Set' = 'UTF-8'
}
$exitGates = [ordered]@{
    'RML' = Ensure-ExitGate $groupId 'RML' 2400 150
    'SHACL' = Ensure-ExitGate $groupId 'SHACL' 2720 150
    'Promotion' = Ensure-ExitGate $groupId 'Promotion' 3040 150
    'Materialization' = Ensure-ExitGate $groupId 'Materialization' 3360 150
    'Cleanup' = Ensure-ExitGate $groupId 'Cleanup' 3680 150
    'Batch Materialization' = Ensure-ExitGate $groupId 'Batch Materialization' 3440 -520
    'Proof Release' = Ensure-ExitGate $groupId 'Proof Release' 1040 -580
}

$stageProcessors = [ordered]@{
    'Schedule HTTP' = $processors.scheduleHttp
    'Schedule Parse' = $processors.prepareScheduleRequests
    'HTTP' = $processors.http
    'Write Payload' = $processors.put
    'RML' = $processors.rml
    'SHACL' = $processors.shacl
    'Promotion' = $processors.promote
    'Materialization' = $processors.materialize
    'Cleanup' = $processors.cleanup
}
$retrySourceProcessors = @{
    'Schedule HTTP' = $processors.scheduleHttp
    'Schedule Parse' = $processors.prepareScheduleRequests
    'HTTP' = $processors.http
    'Write Payload' = $processors.put
    'RML' = $exitGates.RML
    'SHACL' = $exitGates.SHACL
    'Promotion' = $exitGates.Promotion
    'Materialization' = $exitGates.Materialization
    'Cleanup' = $exitGates.Cleanup
}
$retryProcessors = @{}
$failureProcessors = @{}
$retryX = 640
foreach ($entry in $stageProcessors.GetEnumerator()) {
    $retryProcessors[$entry.Key] = Ensure-RetryProcessor -GroupId $groupId -Stage $entry.Key -X $retryX -Y 300
    $failureProcessors[$entry.Key] = Ensure-FailureStageProcessor -GroupId $groupId -Stage $entry.Key -X $retryX -Y 560
    $retryX += 320
}
$processors.proofReleaseWait = Ensure-RetryProcessor -GroupId $groupId -Stage 'Proof Release Readiness' -X 1040 -Y -820 -MaximumRetries ([int]$proofReleasePolicy.readinessRetryCount)
foreach ($stage in @('Request', 'Response', 'Eligibility', 'Schedule Request', 'Schedule Split', 'Materialization Mode', 'Proof Release')) {
    $failureProcessors[$stage] = Ensure-FailureStageProcessor -GroupId $groupId -Stage $stage -X $retryX -Y 560
    $retryX += 240
}

$processors.quarantine = Ensure-Processor -GroupId $groupId -Name 'Quarantine' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 2400 -Y 820 -AutoTerminate @('original', 'output stream', 'nonzero status') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $powershell; 'Command Arguments Strategy' = 'Command Arguments Property';
    'Command Arguments' = Stage-Arguments -Action 'quarantine' -NeedsInput $true -NeedsFailureStage $true;
    'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'; 'Output Destination Attribute' = 'quarantine.output';
    'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}
$scheduleQuarantineDirectory = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'pipeline\quarantine\mlb-game\schedule'))
[void](New-Item -ItemType Directory -Force -Path $scheduleQuarantineDirectory)
$processors.nameScheduleQuarantine = Ensure-Processor -GroupId $groupId -Name 'Name Schedule Quarantine' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 1600 -Y -140 -AutoTerminate @() -Properties @{
    'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = '';
    'Cache Value Lookup Cache Size' = '100'; 'filename' = 'schedule-${batch.id}-${uuid}.json'
}
$processors.putScheduleQuarantine = Ensure-Processor -GroupId $groupId -Name 'Write Schedule Quarantine' -Type 'org.apache.nifi.processors.standard.PutFile' -X 1920 -Y -140 -AutoTerminate @('success') -Properties @{
    'Directory' = $scheduleQuarantineDirectory; 'Conflict Resolution Strategy' = 'fail'; 'Create Missing Directories' = 'true'
}
$processors.scheduleQuarantineFailure = Ensure-Processor -GroupId $groupId -Name 'Record Schedule Quarantine Failure' -Type 'org.apache.nifi.processors.standard.LogAttribute' -X 2240 -Y -140 -AutoTerminate @('success') -Properties @{
    'Log Level' = 'error'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(batch|failure|execution)\..*$';
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO MLB Game schedule quarantine failure'; 'Character Set' = 'UTF-8'
}

Ensure-Connection -GroupId $groupId -Name '01 proof to request reader' -SourceId $processors.request -DestinationId $processors.readRequest -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 backfill to schedule reader' -SourceId $processors.backfillRequest -DestinationId $processors.readScheduleRequest -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 schedule request parsed' -SourceId $processors.readScheduleRequest -DestinationId $processors.prepareSchedule -Relationships @('matched') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 daily schedule to preparation' -SourceId $processors.dailyRequest -DestinationId $processors.prepareDailySchedule -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 daily schedule prepared' -SourceId $processors.prepareDailySchedule -DestinationId $processors.prepareSchedule -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 schedule batch to proof release' -SourceId $processors.prepareSchedule -DestinationId $processors.proofRelease -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 proof release command to exit gate' -SourceId $processors.proofRelease -DestinationId $exitGates['Proof Release'] -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 released schedule to acquisition' -SourceId $exitGates['Proof Release'] -DestinationId $processors.scheduleHttp -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 schedule response to final-game preparation' -SourceId $processors.scheduleHttp -DestinationId $processors.prepareScheduleRequests -Relationships @('Response') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 final-game requests to splitter' -SourceId $processors.prepareScheduleRequests -DestinationId $processors.splitSchedule -Relationships @('output stream') | Out-Null
Ensure-Connection -GroupId $groupId -Name '01 final-game request to reader' -SourceId $processors.splitSchedule -DestinationId $processors.readRequest -Relationships @('split') | Out-Null
Ensure-Connection -GroupId $groupId -Name '02 request matched' -SourceId $processors.readRequest -DestinationId $processors.http -Relationships @('matched') | Out-Null
Ensure-Connection -GroupId $groupId -Name '03 HTTP response' -SourceId $processors.http -DestinationId $processors.readResponse -Relationships @('Response') | Out-Null
Ensure-Connection -GroupId $groupId -Name '04 response matched' -SourceId $processors.readResponse -DestinationId $processors.requireFinal -Relationships @('matched') | Out-Null
Ensure-Connection -GroupId $groupId -Name '05 final game' -SourceId $processors.requireFinal -DestinationId $processors.namePayload -Relationships @('final') | Out-Null
Ensure-Connection -GroupId $groupId -Name '06 payload named' -SourceId $processors.namePayload -DestinationId $processors.put -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '07 payload written' -SourceId $processors.put -DestinationId $processors.rml -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '08 RML command to exit gate' -SourceId $processors.rml -DestinationId $exitGates.RML -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '09 RML passed to SHACL' -SourceId $exitGates.RML -DestinationId $processors.shacl -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '10 SHACL command to exit gate' -SourceId $processors.shacl -DestinationId $exitGates.SHACL -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '11 SHACL passed to promotion' -SourceId $exitGates.SHACL -DestinationId $processors.promote -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '12 promotion command to exit gate' -SourceId $processors.promote -DestinationId $exitGates.Promotion -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '13 promotion passed to materialization choice' -SourceId $exitGates.Promotion -DestinationId $processors.chooseMaterialization -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '13 immediate materialization selected' -SourceId $processors.chooseMaterialization -DestinationId $processors.materialize -Relationships @('immediate') | Out-Null
Ensure-Connection -GroupId $groupId -Name '13 deferred materialization selected' -SourceId $processors.chooseMaterialization -DestinationId $processors.cleanup -Relationships @('deferred') | Out-Null
Ensure-Connection -GroupId $groupId -Name '14 materialization command to exit gate' -SourceId $processors.materialize -DestinationId $exitGates.Materialization -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '15 materialization passed to cleanup' -SourceId $exitGates.Materialization -DestinationId $processors.cleanup -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '16 cleanup command to exit gate' -SourceId $processors.cleanup -DestinationId $exitGates.Cleanup -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '17 cleanup passed to success' -SourceId $exitGates.Cleanup -DestinationId $processors.success -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'batch materialization trigger' -SourceId $processors.batchMaterializationTrigger -DestinationId $processors.batchMaterialize -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'batch materialization command to exit gate' -SourceId $processors.batchMaterialize -DestinationId $exitGates['Batch Materialization'] -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'batch materialization passed' -SourceId $exitGates['Batch Materialization'] -DestinationId $processors.batchMaterializationResult -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'batch materialization failed' -SourceId $exitGates['Batch Materialization'] -DestinationId $processors.batchMaterializationFailure -Relationships @('unmatched') | Out-Null

$retryRelationships = @{
    'Schedule HTTP' = @('Failure', 'Retry')
    'Schedule Parse' = @('nonzero status')
    'HTTP' = @('Failure', 'Retry')
    'Write Payload' = @('failure')
    'RML' = @('unmatched')
    'SHACL' = @('unmatched')
    'Promotion' = @('unmatched')
    'Materialization' = @('unmatched')
    'Cleanup' = @('unmatched')
}
foreach ($entry in $stageProcessors.GetEnumerator()) {
    $stage = $entry.Key
    $processorId = $entry.Value
    Ensure-Connection -GroupId $groupId -Name "retry $stage input" -SourceId $retrySourceProcessors[$stage] -DestinationId $retryProcessors[$stage] -Relationships $retryRelationships[$stage] | Out-Null
    Ensure-Connection -GroupId $groupId -Name "retry $stage loop" -SourceId $retryProcessors[$stage] -DestinationId $processorId -Relationships @('retry') | Out-Null
    Ensure-Connection -GroupId $groupId -Name "retry $stage exhausted" -SourceId $retryProcessors[$stage] -DestinationId $failureProcessors[$stage] -Relationships @('retries_exceeded') | Out-Null
    if ($stage.StartsWith('Schedule ')) {
        Ensure-Connection -GroupId $groupId -Name "fail $stage to schedule quarantine" -SourceId $failureProcessors[$stage] -DestinationId $processors.nameScheduleQuarantine -Relationships @('success') | Out-Null
    }
    else {
        Ensure-Connection -GroupId $groupId -Name "fail $stage to quarantine" -SourceId $failureProcessors[$stage] -DestinationId $processors.quarantine -Relationships @('success') | Out-Null
    }
}

Ensure-Connection -GroupId $groupId -Name 'Schedule HTTP no retry' -SourceId $processors.scheduleHttp -DestinationId $failureProcessors['Schedule HTTP'] -Relationships @('No Retry') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'HTTP no retry' -SourceId $processors.http -DestinationId $failureProcessors['HTTP'] -Relationships @('No Retry') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'request parse failure' -SourceId $processors.readRequest -DestinationId $failureProcessors['Request'] -Relationships @('failure', 'unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'schedule request parse failure' -SourceId $processors.readScheduleRequest -DestinationId $failureProcessors['Schedule Request'] -Relationships @('failure', 'unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'schedule split failure' -SourceId $processors.splitSchedule -DestinationId $failureProcessors['Schedule Split'] -Relationships @('failure') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'response parse failure' -SourceId $processors.readResponse -DestinationId $failureProcessors['Response'] -Relationships @('failure', 'unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'nonfinal response' -SourceId $processors.requireFinal -DestinationId $failureProcessors['Eligibility'] -Relationships @('unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'unknown materialization mode' -SourceId $processors.chooseMaterialization -DestinationId $failureProcessors['Materialization Mode'] -Relationships @('unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'proof release awaiting current proof' -SourceId $exitGates['Proof Release'] -DestinationId $processors.proofReleaseWait -Relationships @('unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'proof release readiness retry' -SourceId $processors.proofReleaseWait -DestinationId $processors.proofRelease -Relationships @('retry') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'proof release readiness exhausted' -SourceId $processors.proofReleaseWait -DestinationId $failureProcessors['Proof Release'] -Relationships @('retries_exceeded') | Out-Null
foreach ($stage in @('Request', 'Response', 'Eligibility', 'Materialization Mode')) {
    Ensure-Connection -GroupId $groupId -Name "fail $stage to quarantine" -SourceId $failureProcessors[$stage] -DestinationId $processors.quarantine -Relationships @('success') | Out-Null
}
foreach ($stage in @('Schedule Request', 'Schedule Split', 'Proof Release')) {
    Ensure-Connection -GroupId $groupId -Name "fail $stage to schedule quarantine" -SourceId $failureProcessors[$stage] -DestinationId $processors.nameScheduleQuarantine -Relationships @('success') | Out-Null
}
Ensure-Connection -GroupId $groupId -Name 'schedule quarantine named' -SourceId $processors.nameScheduleQuarantine -DestinationId $processors.putScheduleQuarantine -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'schedule quarantine write failed' -SourceId $processors.putScheduleQuarantine -DestinationId $processors.scheduleQuarantineFailure -Relationships @('failure') | Out-Null

$flow = Get-GroupFlow -GroupId $groupId
$unexpectedProcessors = @($flow.processors | Where-Object { $_.component.name -notin @(
    'Proof Request','Backfill Schedule Request','Read Schedule Request','Daily 05:00 Eastern Schedule',
    'Prepare Daily Schedule Request','Prepare Schedule Batch','Acquire MLB Schedule','Prepare Final Game Requests',
    'Check Proof Release','Require Proof Release Success',
    'Split Final Game Requests','Read Request','Acquire MLB Game','Read MLB Response','Require Final Game','Name Transient Payload',
    'Write Transient Payload','RML','Source SHACL','Promote Graph Pair','Materialize SQL','Cleanup Transient Artifacts',
    'Choose Materialization Mode','Check Pending Batch Materialization','Materialize Ready Schedule Batches',
    'Record Batch Materialization Result','Record Batch Materialization Failure','Require Batch Materialization Success',
    'Require RML Success','Require SHACL Success','Require Promotion Success','Require Materialization Success','Require Cleanup Success',
    'Record Success','Retry HTTP','Retry Write Payload','Retry RML','Retry SHACL','Retry Promotion','Retry Materialization',
    'Retry Cleanup','Retry Schedule HTTP','Retry Schedule Parse','Fail HTTP','Fail Write Payload','Fail RML','Fail SHACL',
    'Fail Promotion','Fail Materialization','Fail Cleanup','Fail Schedule HTTP','Fail Schedule Parse',
    'Fail Request','Fail Response','Fail Eligibility','Fail Schedule Request','Fail Schedule Split','Fail Materialization Mode','Fail Proof Release',
    'Quarantine','Name Schedule Quarantine','Write Schedule Quarantine','Record Schedule Quarantine Failure',
    'Retry Proof Release Readiness'
) })
if ($unexpectedProcessors.Count -gt 0) {
    throw "The owned MLB Game process group contains unexpected processors: $(@($unexpectedProcessors.component.name) -join ', ')"
}

$invalid = @()
foreach ($summary in @($flow.processors)) {
    $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
    if ([string]$entity.component.validationStatus -ne 'VALID') {
        $errors = if ($entity.component.PSObject.Properties.Name -contains 'validationErrors') { @($entity.component.validationErrors) } else { @('validation status is not VALID') }
        $invalid += "$($entity.component.name): $($errors -join '; ')"
    }
}
if ($invalid.Count -gt 0) {
    throw "NiFi MLB Game flow has invalid processors:`n$($invalid -join "`n")"
}

if ($RunProof -or $RunBackfill -or $StartDaily) {
    $requestProcessorIds = @(
        $processors.request,
        $processors.backfillRequest,
        $processors.dailyRequest,
        $processors.batchMaterializationTrigger
    )
    foreach ($summary in @((Get-GroupFlow -GroupId $groupId).processors | Where-Object { $_.id -notin $requestProcessorIds })) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
        if ([string]$entity.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
                revision = @{ version = $entity.revision.version }
                state = 'RUNNING'
                disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
    }
    if ($StartDaily) {
        foreach ($processorId in @($processors.dailyRequest, $processors.batchMaterializationTrigger)) {
            $entity = Invoke-NiFi -Method GET -Path "/processors/$processorId"
            Invoke-NiFi -Method PUT -Path "/processors/$processorId/run-status" -Body @{
                revision = @{ version = $entity.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
        Write-Host 'Enabled 05:00 Eastern MLB Game acquisition and pending-batch SQL materialization.'
    }
    if ($RunProof) {
        $requestEntity = Invoke-NiFi -Method GET -Path "/processors/$($processors.request)"
        Invoke-NiFi -Method PUT -Path "/processors/$($processors.request)/run-status" -Body @{
            revision = @{ version = $requestEntity.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host "Submitted one bounded proof for MLB game $ProofGamePk."
    }
    if ($RunBackfill) {
        $materializationTrigger = Invoke-NiFi -Method GET -Path "/processors/$($processors.batchMaterializationTrigger)"
        if ([string]$materializationTrigger.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($processors.batchMaterializationTrigger)/run-status" -Body @{
                revision = @{ version = $materializationTrigger.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
        $backfillEntity = Invoke-NiFi -Method GET -Path "/processors/$($processors.backfillRequest)"
        Invoke-NiFi -Method PUT -Path "/processors/$($processors.backfillRequest)/run-status" -Body @{
            revision = @{ version = $backfillEntity.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host 'Submitted one asynchronous MLB Game schedule backfill.'
    }
}
else {
    Write-Host 'Provisioned the MLB Game source group in STOPPED state.'
}
Write-Host "NiFi canvas: $script:NiFiBaseUri/nifi/"
