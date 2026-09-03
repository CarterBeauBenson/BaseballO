[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $ContractPath,
    [switch] $RunProof,
    [switch] $RunBackfill,
    [switch] $StartDaily
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

$contractFile = [System.IO.Path]::GetFullPath($ContractPath)
$sourcesRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'sources')) + [System.IO.Path]::DirectorySeparatorChar
if (-not $contractFile.StartsWith($sourcesRoot, [System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $contractFile -PathType Leaf)) {
    throw 'A source-owned flow contract under Baseball/sources is required.'
}
$contract = Get-Content -LiteralPath $contractFile -Raw | ConvertFrom-Json
if ([string]$contract.artifactType -ne 'baseballo-nifi-source-flow-contract' -or [int]$contract.contractVersion -ne 1) {
    throw "Unsupported source flow contract: $contractFile"
}
$moduleId = [string]$contract.sourceModule
$groupName = [string]$contract.sourceProcessGroup
$moduleRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "sources\$moduleId"))
if (-not $contractFile.StartsWith(($moduleRoot + [System.IO.Path]::DirectorySeparatorChar), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Flow contract is not owned by source module $moduleId."
}
$eventContract = $contract.promotedGraphEvents
if (
    [int]$eventContract.contractVersion -ne 1 -or
    [string]$eventContract.emitter -ne 'scripts/pipeline/emit-promoted-graph-event.py' -or
    [string]$eventContract.outbox -ne 'pipeline/events/promoted-graphs' -or
    [string]$eventContract.delivery -ne 'immutable-idempotent-before-transient-cleanup'
) {
    throw "$moduleId must declare the promoted-graph event v1 delivery contract."
}
$acquisitions = @($contract.acquisitions)
$hasPopulationDiscovery = $contract.PSObject.Properties.Name -contains 'populationDiscovery'
$hasBackfillRequest = $contract.PSObject.Properties.Name -contains 'backfillRequest'
$hasDailySchedule = $contract.PSObject.Properties.Name -contains 'dailySchedule'
if ($acquisitions.Count -lt 1 -or $acquisitions.Count -gt 2) {
    throw "$moduleId must declare one or two independent API acquisitions."
}
$keys = @($acquisitions | ForEach-Object { [string]$_.key })
if (@($keys | Sort-Object -Unique).Count -ne $keys.Count -or @($keys | Where-Object { $_ -notmatch '^[a-z0-9-]+$' }).Count -gt 0) {
    throw "$moduleId acquisition keys must be unique safe tokens."
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$api = $script:NiFiApiUri
$stageScript = Join-Path $repositoryRoot 'scripts\pipeline\process-source-stage.ps1'
$proofReleaseScript = Join-Path $repositoryRoot 'scripts\pipeline\check-source-proof-release.py'
$eventEmitter = Join-Path $repositoryRoot ([string]$eventContract.emitter)
$transientDirectory = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot "pipeline\transient\$moduleId"))
$powershell = Join-Path $PSHOME 'powershell.exe'
foreach ($required in @($proofReleaseScript, $eventEmitter)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Source-lane executable is missing: $required"
    }
}
$pythonCommand = Get-Command python -ErrorAction Stop
$python = $pythonCommand.Source
[void](New-Item -ItemType Directory -Force -Path $transientDirectory)

function Invoke-NiFi {
    param([Parameter(Mandatory = $true)][ValidateSet('GET', 'POST', 'PUT', 'DELETE')][string] $Method, [Parameter(Mandatory = $true)][string] $Path, $Body)
    $arguments = @{ Uri = "$api$Path"; Method = $Method; TimeoutSec = 60 }
    if ($null -ne $Body) {
        $arguments.ContentType = 'application/json'
        $arguments.Body = $Body | ConvertTo-Json -Depth 40
    }
    return Invoke-RestMethod @arguments
}

function Remove-ConnectionIfPresent([string] $GroupId, [string] $Name) {
    $matches = @((Get-GroupFlow $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one connection named '$Name' exists in $groupName." }
    if ($matches.Count -eq 0) { return }
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

function Stop-OwnedProcessGroupForReconciliation([string] $GroupId) {
    $flow = Get-GroupFlow $GroupId
    $queued = @($flow.connections | Where-Object { [int64]$_.status.aggregateSnapshot.flowFilesQueued -gt 0 })
    if ($queued.Count -gt 0) {
        throw "$groupName has queued FlowFiles and cannot be reconciled."
    }
    $active = @($flow.processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
    if ($active.Count -eq 0) { return }
    Invoke-NiFi -Method PUT -Path "/flow/process-groups/$GroupId" -Body @{
        id = $GroupId
        state = 'STOPPED'
        disconnectedNodeAcknowledged = $false
    } | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $remaining = @((Get-GroupFlow $GroupId).processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "$groupName did not stop before reconciliation: $(@($remaining.component.name) -join ', ')"
}

function Get-OrCreateProcessGroup([string] $ParentId, [string] $Name, [int] $X, [int] $Y) {
    $matches = @((Get-GroupFlow $ParentId).processGroups | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one NiFi process group is named '$Name'." }
    if ($matches.Count -eq 1) { return $matches[0].id }
    return (Invoke-NiFi -Method POST -Path "/process-groups/$ParentId/process-groups" -Body @{
        revision = @{ version = 0 }
        component = @{
            name = $Name
            position = @{ x = $X; y = $Y }
            comments = "Owned by detachable source module $moduleId."
        }
    }).id
}

function Get-ProcessorType([string] $Type) {
    $response = Invoke-NiFi -Method GET -Path "/flow/processor-types?type=$([Uri]::EscapeDataString($Type))"
    $matches = @($response.processorTypes | Where-Object { $_.type -eq $Type })
    if ($matches.Count -ne 1) { throw "NiFi processor type is not uniquely available: $Type" }
    return $matches[0]
}

function Ensure-Processor {
    param(
        [string] $GroupId, [string] $Name, [string] $Type, [hashtable] $Properties,
        [AllowEmptyCollection()][string[]] $AutoTerminate, [int] $X, [int] $Y,
        [string] $SchedulingPeriod = '0 sec',
        [ValidateSet('TIMER_DRIVEN', 'CRON_DRIVEN')][string] $SchedulingStrategy = 'TIMER_DRIVEN'
    )
    $matches = @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one processor named '$Name' exists in $groupName." }
    $processorType = Get-ProcessorType $Type
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
        return (Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/processors" -Body @{
            revision = @{ version = 0 }
            component = @{ name = $Name; type = $Type; bundle = $processorType.bundle; position = @{ x = $X; y = $Y }; config = $config }
        }).id
    }
    $current = Invoke-NiFi -Method GET -Path "/processors/$($matches[0].id)"
    if ([string]$current.component.state -ne 'STOPPED') {
        throw "Processor '$Name' must be stopped before its source-owned contract is updated."
    }
    if ([string]$current.component.type -ne $Type) {
        throw "Processor '$Name' has type $($current.component.type), expected $Type."
    }
    return (Invoke-NiFi -Method PUT -Path "/processors/$($current.id)" -Body @{
        revision = @{ version = $current.revision.version }
        component = @{ id = $current.id; name = $Name; position = @{ x = $X; y = $Y }; config = $config }
    }).id
}

function Ensure-Connection([string] $GroupId, [string] $Name, [string] $SourceId, [string] $DestinationId, [string[]] $Relationships) {
    $matches = @((Get-GroupFlow $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one connection named '$Name' exists in $groupName." }
    if ($matches.Count -eq 1) {
        $component = $matches[0].component
        if ($component.source.id -ne $SourceId -or $component.destination.id -ne $DestinationId -or (@($component.selectedRelationships) -join '|') -ne (@($Relationships) -join '|')) {
            throw "Existing connection '$Name' differs from the $moduleId contract."
        }
        return $matches[0].id
    }
    return (Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/connections" -Body @{
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
    }).id
}

function Stage-Arguments([string] $Action, [bool] $Failure) {
    $arguments = "-NoLogo;-NoProfile;-NonInteractive;-ExecutionPolicy;Bypass;-File;$stageScript;-Action;$Action;-ContractPath;$contractFile;-RunId;`${pipeline.run.id};-ScopeKey;`${scope.key}"
    foreach ($attribute in @('request.scope', 'season', 'person.id', 'resource.kind')) {
        if ($contract.requestAttributes.PSObject.Properties.Name -contains $attribute -or $contract.derivedAttributes.PSObject.Properties.Name -contains $attribute) {
            $parameter = switch ($attribute) { 'request.scope' { 'RequestScope' }; 'season' { 'Season' }; 'person.id' { 'PersonId' }; 'resource.kind' { 'ResourceKind' } }
            $arguments += ";-$parameter;`${$attribute}"
        }
    }
    if ($acquisitions.Count -ge 1) {
        $arguments += ";-InputOneKey;$($keys[0]);-InputOnePath;`${transient.$($keys[0]).path}"
    }
    if ($acquisitions.Count -ge 2) {
        $arguments += ";-InputTwoKey;$($keys[1]);-InputTwoPath;`${transient.$($keys[1]).path}"
    }
    if ($Failure) { $arguments += ';-FailureStage;${failure.stage}' }
    return $arguments
}

function Ensure-Stage([string] $GroupId, [string] $Name, [string] $Action, [int] $X, [int] $Y) {
    return Ensure-Processor -GroupId $GroupId -Name $Name -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X $X -Y $Y -AutoTerminate @('output stream', 'nonzero status') -Properties @{
        'Working Directory' = $repositoryRoot
        'Command Path' = $powershell
        'Command Arguments Strategy' = 'Command Arguments Property'
        'Command Arguments' = Stage-Arguments $Action $false
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

function Ensure-Retry([string] $GroupId, [string] $Stage, [int] $X, [int] $Y) {
    return Ensure-Processor -GroupId $GroupId -Name "Retry $Stage" -Type 'org.apache.nifi.processors.standard.RetryFlowFile' -X $X -Y $Y -AutoTerminate @('failure') -SchedulingPeriod '1 sec' -Properties @{
        'Retry Attribute' = "retry.$($Stage.ToLowerInvariant().Replace(' ', '-'))"
        'Maximum Retries' = [string]$contract.failurePolicy.maximumRetriesPerStage
        'Penalize Retries' = 'true'
        'Fail on Nonnumerical Overwrite' = 'true'
        'Reuse Mode' = 'fail'
    }
}

function Ensure-Failure([string] $GroupId, [string] $Stage, [int] $X, [int] $Y) {
    return Ensure-Processor -GroupId $GroupId -Name "Fail $Stage" -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X $X -Y $Y -AutoTerminate @() -Properties @{
        'Delete Attributes Expression' = ''
        'Store State' = 'Do not store state'
        'Stateful Variables Initial Value' = ''
        'Cache Value Lookup Cache Size' = '100'
        'failure.stage' = $Stage.ToLowerInvariant().Replace(' ', '-')
    }
}

$rootId = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow.id
$baseballGroupId = Get-OrCreateProcessGroup $rootId ([string]$contract.rootProcessGroup) 100 100
$catalog = Get-Content -LiteralPath (Join-Path $repositoryRoot 'sources\source-modules.json') -Raw | ConvertFrom-Json
$moduleIndex = [array]::IndexOf(@($catalog.modules.id), $moduleId)
$groupY = if ($moduleIndex -ge 0) { 100 + ($moduleIndex * 180) } else { 100 }
$groupId = Get-OrCreateProcessGroup $baseballGroupId $groupName 100 $groupY
Stop-OwnedProcessGroupForReconciliation $groupId

foreach ($obsoleteConnection in @(
    '81 context to RML',
    '82 RML to SHACL',
    '83 SHACL to promotion',
    '84 promotion to cleanup',
    '85 cleanup to success',
    '88 promotion passed to cleanup',
    '89 cleanup command to exit gate',
    '90 cleanup passed to success',
    'retry Context input',
    'retry RML input',
    'retry SHACL input',
    'retry Promotion input',
    'retry Cleanup input',
    'population split to person reader',
    'person read to request prep',
    'discovered person to detail connector',
    'population request parsed',
    'daily population request prepared'
)) {
    Remove-ConnectionIfPresent $groupId $obsoleteConnection
}
if ($acquisitions.Count -gt 0) {
    Remove-ConnectionIfPresent $groupId ("01 to {0}" -f [string]$acquisitions[0].processorName)
}

$processors = @{}
$proofText = $contract.proofRequest | ConvertTo-Json -Depth 10 -Compress
$processors.request = Ensure-Processor -GroupId $groupId -Name 'Proof Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y 0 -SchedulingPeriod '365 days' -AutoTerminate @() -Properties @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
    'Custom Text' = $proofText; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'; 'request.mode' = 'proof'
}
$manualRequestProcessorIds = @($processors.request)
$backfillRequestProcessorId = $null
if ($hasBackfillRequest -and -not $hasPopulationDiscovery) {
    $backfillText = $contract.backfillRequest | ConvertTo-Json -Depth 10 -Compress
    $processors.backfillRequest = Ensure-Processor -GroupId $groupId -Name 'Backfill Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -220 -SchedulingPeriod '365 days' -AutoTerminate @() -Properties @{
        'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
        'Custom Text' = $backfillText; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'; 'request.mode' = 'bulk'
    }
    $backfillRequestProcessorId = $processors.backfillRequest
    $manualRequestProcessorIds += $processors.backfillRequest
}
$readProperties = @{
    'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn'
    'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB'
}
foreach ($property in $contract.requestAttributes.PSObject.Properties) { $readProperties[$property.Name] = [string]$property.Value }
$processors.read = Ensure-Processor -GroupId $groupId -Name 'Read Request' -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 320 -Y 0 -AutoTerminate @() -Properties $readProperties
$enrichProperties = @{
    'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = ''
    'Cache Value Lookup Cache Size' = '100'; 'pipeline.run.id' = "`${uuid:replace('-', '')}"
}
foreach ($property in $contract.derivedAttributes.PSObject.Properties) { $enrichProperties[$property.Name] = [string]$property.Value }
$processors.enrich = Ensure-Processor -GroupId $groupId -Name 'Prepare Request Attributes' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 640 -Y 0 -AutoTerminate @() -Properties $enrichProperties

$releaseArguments = "-B;$proofReleaseScript;--state-root;$script:StateRoot;--contract;$contractFile"
$processors.releaseRoute = Ensure-Processor -GroupId $groupId -Name 'Route Proof Or Released Request' -Type 'org.apache.nifi.processors.standard.RouteOnAttribute' -X 880 -Y 0 -AutoTerminate @() -Properties @{
    'Routing Strategy' = 'Route to Property name'
    'proof' = "`${request.mode:equals('proof')}"
    'release' = "`${request.mode:equals('bulk')}"
}
$processors.proofRelease = Ensure-Processor -GroupId $groupId -Name 'Check Proof Release' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 1120 -Y 180 -AutoTerminate @('output stream', 'nonzero status') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = $releaseArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'proof.release.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}
$processors.proofReleaseGate = Ensure-ExitGate $groupId 'Proof Release' 1360 180
Ensure-Connection -GroupId $groupId -Name '00 enriched request to release route' -SourceId $processors.enrich -DestinationId $processors.releaseRoute -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '00 bulk request to proof release' -SourceId $processors.releaseRoute -DestinationId $processors.proofRelease -Relationships @('release') | Out-Null
Ensure-Connection -GroupId $groupId -Name '00 proof release command to exit gate' -SourceId $processors.proofRelease -DestinationId $processors.proofReleaseGate -Relationships @('original') | Out-Null

$current = $null
$currentRelationship = @()
$sequence = 1
$stageProcessors = [ordered]@{}
$retrySourceProcessors = @{}
$retryRelationships = @{}
$acquisitionProcessors = @{}
foreach ($acquisition in $acquisitions) {
    $key = [string]$acquisition.key
    $x = 640 + ($sequence * 640)
    $httpName = [string]$acquisition.processorName
    $httpId = Ensure-Processor -GroupId $groupId -Name $httpName -Type 'org.apache.nifi.processors.standard.InvokeHTTP' -X $x -Y 0 -AutoTerminate @('Original') -Properties @{
        'HTTP Method' = 'GET'; 'HTTP URL' = [string]$acquisition.url
        'HTTP/2 Disabled' = 'False'; 'Connection Timeout' = '15 secs'; 'Socket Read Timeout' = '60 secs'
        'Socket Write Timeout' = '60 secs'; 'Request Body Enabled' = 'false'; 'Request User-Agent' = 'BaseballO/1.0'
        'Response Body Ignored' = 'false'; 'Response Generation Required' = 'true'; 'Response Redirects Enabled' = 'True'
    }
    $acquisitionProcessors[$key] = $httpId
    if ($sequence -eq 1) {
        Ensure-Connection -GroupId $groupId -Name ("01 proof to {0}" -f $httpName) -SourceId $processors.releaseRoute -DestinationId $httpId -Relationships @('proof') | Out-Null
        Ensure-Connection -GroupId $groupId -Name ("01 released request to {0}" -f $httpName) -SourceId $processors.proofReleaseGate -DestinationId $httpId -Relationships @('passed') | Out-Null
    }
    else {
        Ensure-Connection -GroupId $groupId -Name ("{0:D2} to {1}" -f $sequence, $httpName) -SourceId $current -DestinationId $httpId -Relationships $currentRelationship | Out-Null
    }
    $nameId = Ensure-Processor -GroupId $groupId -Name "Name $key Payload" -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X ($x + 260) -Y 0 -AutoTerminate @() -Properties @{
        'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = ''
        'Cache Value Lookup Cache Size' = '100'; 'filename' = [string]$acquisition.filename
        "transient.$key.path" = "$transientDirectory\$([string]$acquisition.filename)"
    }
    Ensure-Connection -GroupId $groupId -Name ("{0:D2} {1} response" -f $sequence, $key) -SourceId $httpId -DestinationId $nameId -Relationships @('Response') | Out-Null
    $putId = Ensure-Processor -GroupId $groupId -Name "Write $key Payload" -Type 'org.apache.nifi.processors.standard.PutFile' -X ($x + 520) -Y 0 -AutoTerminate @() -Properties @{
        'Directory' = $transientDirectory; 'Conflict Resolution Strategy' = 'fail'; 'Create Missing Directories' = 'true'
    }
    Ensure-Connection -GroupId $groupId -Name ("{0:D2} {1} named" -f $sequence, $key) -SourceId $nameId -DestinationId $putId -Relationships @('success') | Out-Null
    $stageProcessors["HTTP $key"] = $httpId
    $retrySourceProcessors["HTTP $key"] = $httpId
    $retryRelationships["HTTP $key"] = @('Failure', 'Retry')
    $stageProcessors["Write $key"] = $putId
    $retrySourceProcessors["Write $key"] = $putId
    $retryRelationships["Write $key"] = @('failure')
    $current = $putId
    $currentRelationship = @('success')
    $sequence++
}

if ($hasBackfillRequest -and -not $hasPopulationDiscovery) {
    Ensure-Connection -GroupId $groupId -Name '00 backfill to request reader' -SourceId $processors.backfillRequest -DestinationId $processors.read -Relationships @('success') | Out-Null
}

if ($hasDailySchedule -and -not $hasPopulationDiscovery) {
    $daily = $contract.dailySchedule
    if ([string]$daily.timeZone -ne 'America/New_York' -or [string]$daily.cron -ne '0 0 5 * * ?') {
        throw "$moduleId daily schedule must be 05:00 America/New_York."
    }
    $processors.dailyRequest = Ensure-Processor -GroupId $groupId -Name 'Daily 05:00 Eastern Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -440 -SchedulingPeriod ([string]$daily.cron) -SchedulingStrategy 'CRON_DRIVEN' -AutoTerminate @() -Properties @{
        'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
        'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
    }
    $dailyProperties = @{
        'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = ''
        'Cache Value Lookup Cache Size' = '100'; 'request.mode' = 'bulk'
    }
    foreach ($property in $daily.attributeExpressions.PSObject.Properties) {
        $dailyProperties[$property.Name] = [string]$property.Value
    }
    $processors.prepareDaily = Ensure-Processor -GroupId $groupId -Name 'Prepare Daily Request' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 320 -Y -440 -AutoTerminate @() -Properties $dailyProperties
    Ensure-Connection -GroupId $groupId -Name 'daily request to preparation' -SourceId $processors.dailyRequest -DestinationId $processors.prepareDaily -Relationships @('success') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'daily request prepared' -SourceId $processors.prepareDaily -DestinationId $processors.enrich -Relationships @('success') | Out-Null
    $manualRequestProcessorIds += $processors.dailyRequest
}

if ($hasPopulationDiscovery) {
    $discovery = $contract.populationDiscovery
    $detailMatches = @($acquisitions | Where-Object { $_.processorName -eq [string]$discovery.detailConnector })
    if ($detailMatches.Count -ne 1) {
        throw "$moduleId population discovery does not identify one detail connector."
    }
    $detailKey = [string]$detailMatches[0].key
    $populationRequestText = $discovery.backfillRequest | ConvertTo-Json -Depth 10 -Compress
    $processors.populationRequest = Ensure-Processor -GroupId $groupId -Name 'Population Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -420 -SchedulingPeriod '365 days' -AutoTerminate @() -Properties @{
        'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
        'Custom Text' = $populationRequestText; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'; 'request.mode' = 'bulk'
    }
    $manualRequestProcessorIds += $processors.populationRequest
    $backfillRequestProcessorId = $processors.populationRequest
    $populationReadProperties = @{
        'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn'
        'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB'
    }
    foreach ($property in $discovery.requestAttributes.PSObject.Properties) {
        $populationReadProperties[$property.Name] = [string]$property.Value
    }
    $processors.readPopulation = Ensure-Processor -GroupId $groupId -Name 'Read Population Request' -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 320 -Y -420 -AutoTerminate @() -Properties $populationReadProperties
    $processors.discoverPopulation = Ensure-Processor -GroupId $groupId -Name ([string]$discovery.processorName) -Type 'org.apache.nifi.processors.standard.InvokeHTTP' -X 640 -Y -420 -AutoTerminate @('Original') -Properties @{
        'HTTP Method' = 'GET'; 'HTTP URL' = [string]$discovery.url
        'HTTP/2 Disabled' = 'False'; 'Connection Timeout' = '15 secs'; 'Socket Read Timeout' = '60 secs'
        'Socket Write Timeout' = '60 secs'; 'Request Body Enabled' = 'false'; 'Request User-Agent' = 'BaseballO/1.0'
        'Response Body Ignored' = 'false'; 'Response Generation Required' = 'true'; 'Response Redirects Enabled' = 'True'
    }
    $processors.splitPopulation = Ensure-Processor -GroupId $groupId -Name ([string]$discovery.splitProcessorName) -Type 'org.apache.nifi.processors.standard.SplitJson' -X 960 -Y -420 -AutoTerminate @('original') -Properties @{
        'JsonPath Expression' = [string]$discovery.recordsJsonPath
        'Null Value Representation' = 'empty string'
        'Max String Length' = '20 MB'
    }
    $discoveredIdAttribute = [string]$discovery.idAttribute
    if ($discoveredIdAttribute -notmatch '^[a-z][a-z0-9.]*$') {
        throw "$moduleId population discovery has an unsafe idAttribute."
    }
    $processors.readDiscovered = Ensure-Processor -GroupId $groupId -Name ([string]$discovery.readProcessorName) -Type 'org.apache.nifi.processors.standard.EvaluateJsonPath' -X 1280 -Y -420 -AutoTerminate @() -Properties @{
        'Destination' = 'flowfile-attribute'; 'Return Type' = 'auto-detect'; 'Path Not Found Behavior' = 'warn'
        'Null Value Representation' = 'empty string'; 'Max String Length' = '20 MB'; $discoveredIdAttribute = [string]$discovery.idJsonPath
    }
    $discoveredProperties = @{
        'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = ''
        'Cache Value Lookup Cache Size' = '100'; 'pipeline.run.id' = "`${uuid:replace('-', '')}"
    }
    foreach ($property in $discovery.downstreamAttributes.PSObject.Properties) {
        $discoveredProperties[$property.Name] = [string]$property.Value
    }
    $processors.prepareDiscovered = Ensure-Processor -GroupId $groupId -Name ([string]$discovery.prepareProcessorName) -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 1600 -Y -420 -AutoTerminate @() -Properties $discoveredProperties
    $processors.populationProofRelease = Ensure-Processor -GroupId $groupId -Name 'Check Population Proof Release' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X 640 -Y -640 -AutoTerminate @('output stream', 'nonzero status') -Properties @{
        'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property'
        'Command Arguments' = $releaseArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
        'Output Destination Attribute' = 'proof.release.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
    }
    $processors.populationProofReleaseGate = Ensure-ExitGate $groupId 'Population Proof Release' 880 -640
    Ensure-Connection -GroupId $groupId -Name 'population request to reader' -SourceId $processors.populationRequest -DestinationId $processors.readPopulation -Relationships @('success') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population request parsed' -SourceId $processors.readPopulation -DestinationId $processors.populationProofRelease -Relationships @('matched') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population proof release command to exit gate' -SourceId $processors.populationProofRelease -DestinationId $processors.populationProofReleaseGate -Relationships @('original') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'released population request to discovery' -SourceId $processors.populationProofReleaseGate -DestinationId $processors.discoverPopulation -Relationships @('passed') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population response to splitter' -SourceId $processors.discoverPopulation -DestinationId $processors.splitPopulation -Relationships @('Response') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population split to record reader' -SourceId $processors.splitPopulation -DestinationId $processors.readDiscovered -Relationships @('split') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population record read to request prep' -SourceId $processors.readDiscovered -DestinationId $processors.prepareDiscovered -Relationships @('matched') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'discovered record to detail connector' -SourceId $processors.prepareDiscovered -DestinationId $acquisitionProcessors[$detailKey] -Relationships @('success') | Out-Null
    if ($hasDailySchedule) {
        $daily = $contract.dailySchedule
        if ([string]$daily.timeZone -ne 'America/New_York' -or [string]$daily.cron -ne '0 0 5 * * ?') {
            throw "$moduleId daily schedule must be 05:00 America/New_York."
        }
        $processors.dailyRequest = Ensure-Processor -GroupId $groupId -Name 'Daily 05:00 Eastern Request' -Type 'org.apache.nifi.processors.standard.GenerateFlowFile' -X 0 -Y -680 -SchedulingPeriod ([string]$daily.cron) -SchedulingStrategy 'CRON_DRIVEN' -AutoTerminate @() -Properties @{
            'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
            'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
        }
        $dailyPopulationProperties = @{
            'Delete Attributes Expression' = ''; 'Store State' = 'Do not store state'; 'Stateful Variables Initial Value' = ''
            'Cache Value Lookup Cache Size' = '100'; 'request.mode' = 'bulk'
        }
        foreach ($property in $daily.attributeExpressions.PSObject.Properties) {
            $dailyPopulationProperties[$property.Name] = [string]$property.Value
        }
        $processors.prepareDaily = Ensure-Processor -GroupId $groupId -Name 'Prepare Daily Population Request' -Type 'org.apache.nifi.processors.attributes.UpdateAttribute' -X 320 -Y -680 -AutoTerminate @() -Properties $dailyPopulationProperties
        Ensure-Connection -GroupId $groupId -Name 'daily population request to preparation' -SourceId $processors.dailyRequest -DestinationId $processors.prepareDaily -Relationships @('success') | Out-Null
        Ensure-Connection -GroupId $groupId -Name 'daily population request prepared' -SourceId $processors.prepareDaily -DestinationId $processors.populationProofRelease -Relationships @('success') | Out-Null
        $manualRequestProcessorIds += $processors.dailyRequest
    }
    $stageProcessors['HTTP population discovery'] = $processors.discoverPopulation
    $retrySourceProcessors['HTTP population discovery'] = $processors.discoverPopulation
    $retryRelationships['HTTP population discovery'] = @('Failure', 'Retry')
}

$baseX = 640 + (($acquisitions.Count + 1) * 640)
$processors.context = Ensure-Stage $groupId 'Prepare Source Context' 'context' $baseX 0
$processors.rml = Ensure-Stage $groupId 'RML' 'rml' ($baseX + 320) 0
$processors.shacl = Ensure-Stage $groupId 'Source SHACL' 'shacl' ($baseX + 640) 0
$processors.promote = Ensure-Stage $groupId 'Promote Authoritative Graph' 'promote' ($baseX + 960) 0
$processors.emit = Ensure-Stage $groupId 'Emit Promoted Graph Event' 'emit' ($baseX + 1280) 0
$processors.cleanup = Ensure-Stage $groupId 'Cleanup Transient Artifacts' 'cleanup' ($baseX + 1600) 0
$processors.success = Ensure-Processor -GroupId $groupId -Name 'Record Success' -Type 'org.apache.nifi.processors.standard.LogAttribute' -X ($baseX + 1920) -Y 0 -AutoTerminate @('success') -Properties @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(pipeline|scope|request|transient|stage)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = "BaseballO $moduleId success"; 'Character Set' = 'UTF-8'
}
$exitGates = [ordered]@{
    'Context' = Ensure-ExitGate $groupId 'Context' ($baseX + 160) 150
    'RML' = Ensure-ExitGate $groupId 'RML' ($baseX + 480) 150
    'SHACL' = Ensure-ExitGate $groupId 'SHACL' ($baseX + 800) 150
    'Promotion' = Ensure-ExitGate $groupId 'Promotion' ($baseX + 1120) 150
    'Promoted Graph Event' = Ensure-ExitGate $groupId 'Promoted Graph Event' ($baseX + 1440) 150
    'Cleanup' = Ensure-ExitGate $groupId 'Cleanup' ($baseX + 1760) 150
}

Ensure-Connection -GroupId $groupId -Name '00 proof to request reader' -SourceId $processors.request -DestinationId $processors.read -Relationships @('success') | Out-Null
Ensure-Connection -GroupId $groupId -Name '00 request parsed' -SourceId $processors.read -DestinationId $processors.enrich -Relationships @('matched') | Out-Null
Ensure-Connection -GroupId $groupId -Name '80 acquisitions to context' -SourceId $current -DestinationId $processors.context -Relationships $currentRelationship | Out-Null
Ensure-Connection -GroupId $groupId -Name '81 context command to exit gate' -SourceId $processors.context -DestinationId $exitGates.Context -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '82 context passed to RML' -SourceId $exitGates.Context -DestinationId $processors.rml -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '83 RML command to exit gate' -SourceId $processors.rml -DestinationId $exitGates.RML -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '84 RML passed to SHACL' -SourceId $exitGates.RML -DestinationId $processors.shacl -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '85 SHACL command to exit gate' -SourceId $processors.shacl -DestinationId $exitGates.SHACL -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '86 SHACL passed to promotion' -SourceId $exitGates.SHACL -DestinationId $processors.promote -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '87 promotion command to exit gate' -SourceId $processors.promote -DestinationId $exitGates.Promotion -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '88 promotion passed to event emission' -SourceId $exitGates.Promotion -DestinationId $processors.emit -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '89 event command to exit gate' -SourceId $processors.emit -DestinationId $exitGates['Promoted Graph Event'] -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '90 event passed to cleanup' -SourceId $exitGates['Promoted Graph Event'] -DestinationId $processors.cleanup -Relationships @('passed') | Out-Null
Ensure-Connection -GroupId $groupId -Name '91 cleanup command to exit gate' -SourceId $processors.cleanup -DestinationId $exitGates.Cleanup -Relationships @('original') | Out-Null
Ensure-Connection -GroupId $groupId -Name '92 cleanup passed to success' -SourceId $exitGates.Cleanup -DestinationId $processors.success -Relationships @('passed') | Out-Null

$semanticStages = [ordered]@{'Context'=$processors.context; 'RML'=$processors.rml; 'SHACL'=$processors.shacl; 'Promotion'=$processors.promote; 'Promoted Graph Event'=$processors.emit; 'Cleanup'=$processors.cleanup}
foreach ($entry in $semanticStages.GetEnumerator()) {
    $stageProcessors[$entry.Key] = $entry.Value
    $retrySourceProcessors[$entry.Key] = $exitGates[$entry.Key]
    $retryRelationships[$entry.Key] = @('unmatched')
}

$quarantine = Ensure-Processor -GroupId $groupId -Name 'Quarantine' -Type 'org.apache.nifi.processors.standard.ExecuteStreamCommand' -X ($baseX + 640) -Y 820 -AutoTerminate @('original', 'output stream', 'nonzero status') -Properties @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $powershell; 'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = Stage-Arguments 'quarantine' $true; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'quarantine.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
}

$retryX = 1000
foreach ($entry in $stageProcessors.GetEnumerator()) {
    $stage = $entry.Key
    $retry = Ensure-Retry $groupId $stage $retryX 320
    $failure = Ensure-Failure $groupId $stage $retryX 560
    Ensure-Connection -GroupId $groupId -Name "retry $stage input" -SourceId $retrySourceProcessors[$stage] -DestinationId $retry -Relationships $retryRelationships[$stage] | Out-Null
    Ensure-Connection -GroupId $groupId -Name "retry $stage loop" -SourceId $retry -DestinationId $entry.Value -Relationships @('retry') | Out-Null
    Ensure-Connection -GroupId $groupId -Name "retry $stage exhausted" -SourceId $retry -DestinationId $failure -Relationships @('retries_exceeded') | Out-Null
    Ensure-Connection -GroupId $groupId -Name "fail $stage to quarantine" -SourceId $failure -DestinationId $quarantine -Relationships @('success') | Out-Null
    if ($stage.StartsWith('HTTP ')) {
        Ensure-Connection -GroupId $groupId -Name "$stage no retry" -SourceId $entry.Value -DestinationId $failure -Relationships @('No Retry') | Out-Null
    }
    $retryX += 260
}
$requestFailure = Ensure-Failure $groupId 'Request' 740 560
Ensure-Connection -GroupId $groupId -Name 'request parse failure' -SourceId $processors.read -DestinationId $requestFailure -Relationships @('failure', 'unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'fail Request to quarantine' -SourceId $requestFailure -DestinationId $quarantine -Relationships @('success') | Out-Null
$proofReleaseFailure = Ensure-Failure $groupId 'Proof Release' 1000 740
Ensure-Connection -GroupId $groupId -Name 'proof release failed' -SourceId $processors.proofReleaseGate -DestinationId $proofReleaseFailure -Relationships @('unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'unknown release route' -SourceId $processors.releaseRoute -DestinationId $proofReleaseFailure -Relationships @('unmatched') | Out-Null
Ensure-Connection -GroupId $groupId -Name 'fail Proof Release to quarantine' -SourceId $proofReleaseFailure -DestinationId $quarantine -Relationships @('success') | Out-Null
if ($hasPopulationDiscovery) {
    Ensure-Connection -GroupId $groupId -Name 'population proof release failed' -SourceId $processors.populationProofReleaseGate -DestinationId $proofReleaseFailure -Relationships @('unmatched') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population request parse failure' -SourceId $processors.readPopulation -DestinationId $requestFailure -Relationships @('failure', 'unmatched') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population split failure' -SourceId $processors.splitPopulation -DestinationId $requestFailure -Relationships @('failure') | Out-Null
    Ensure-Connection -GroupId $groupId -Name 'population record parse failure' -SourceId $processors.readDiscovered -DestinationId $requestFailure -Relationships @('failure', 'unmatched') | Out-Null
}

$invalid = @()
foreach ($summary in @((Get-GroupFlow $groupId).processors)) {
    $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
    if ([string]$entity.component.validationStatus -ne 'VALID') {
        $errors = if ($entity.component.PSObject.Properties.Name -contains 'validationErrors') { @($entity.component.validationErrors) } else { @('validation status is not VALID') }
        $invalid += "$($entity.component.name): $($errors -join '; ')"
    }
}
if ($invalid.Count -gt 0) { throw "$groupName contains invalid processors:`n$($invalid -join "`n")" }

if ($RunProof -or $RunBackfill -or $StartDaily) {
    foreach ($summary in @((Get-GroupFlow $groupId).processors | Where-Object { $_.id -notin $manualRequestProcessorIds })) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
        if ([string]$entity.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
                revision = @{ version = $entity.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
    }
    if ($StartDaily -and $processors.ContainsKey('dailyRequest')) {
        $dailyRequest = Invoke-NiFi -Method GET -Path "/processors/$($processors.dailyRequest)"
        Invoke-NiFi -Method PUT -Path "/processors/$($dailyRequest.id)/run-status" -Body @{
            revision = @{ version = $dailyRequest.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host "Enabled 05:00 Eastern daily acquisition for $moduleId."
    }
    if ($RunProof) {
        $request = Invoke-NiFi -Method GET -Path "/processors/$($processors.request)"
        Invoke-NiFi -Method PUT -Path "/processors/$($request.id)/run-status" -Body @{
            revision = @{ version = $request.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host "Submitted one bounded proof for $moduleId."
    }
    if ($RunBackfill) {
        if ([string]::IsNullOrWhiteSpace([string]$backfillRequestProcessorId)) {
            throw "$moduleId has no backfill request contract."
        }
        $backfillRequest = Invoke-NiFi -Method GET -Path "/processors/$backfillRequestProcessorId"
        Invoke-NiFi -Method PUT -Path "/processors/$($backfillRequest.id)/run-status" -Body @{
            revision = @{ version = $backfillRequest.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host "Submitted one asynchronous backfill request for $moduleId."
    }
}
else {
    Write-Host "Provisioned $groupName in STOPPED state."
}
