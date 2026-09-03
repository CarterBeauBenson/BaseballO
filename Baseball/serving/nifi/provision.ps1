[CmdletBinding()]
param(
    [switch] $Start,
    [switch] $RunFullRebuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
Initialize-LocalLayout

$contractPath = Join-Path $PSScriptRoot 'flow-contract.json'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
if (
    [string]$contract.artifactType -ne 'baseballo-nifi-serving-flow-contract' -or
    [int]$contract.contractVersion -ne 1 -or
    [string]$contract.input.artifactType -ne 'baseballo-promoted-graph-event' -or
    [int]$contract.input.contractVersion -ne 1 -or
    [bool]$contract.failurePolicy.authoritativeRdfUnaffected -ne $true -or
    [bool]$contract.failurePolicy.sourceLanesUnaffected -ne $true -or
    [bool]$contract.failurePolicy.priorServingPointerUnaffected -ne $true
) {
    throw "Unsupported analytical-serving NiFi contract: $contractPath"
}
$materializer = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.authorityMaterialization.processor)))
$authorityContract = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.authorityMaterialization.contract)))
foreach ($required in @($materializer, $authorityContract)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Analytical-serving artifact is missing: $required"
    }
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$api = $script:NiFiApiUri
$python = (Get-Command python -ErrorAction Stop).Source

function Invoke-NiFi {
    param([Parameter(Mandatory = $true)][ValidateSet('GET', 'POST', 'PUT', 'DELETE')][string] $Method, [Parameter(Mandatory = $true)][string] $Path, $Body)
    $arguments = @{ Uri = "$api$Path"; Method = $Method; TimeoutSec = 60 }
    if ($null -ne $Body) {
        $arguments.ContentType = 'application/json'
        $arguments.Body = $Body | ConvertTo-Json -Depth 30
    }
    return Invoke-RestMethod @arguments
}

function Get-GroupFlow([string] $GroupId) {
    return (Invoke-NiFi -Method GET -Path "/flow/process-groups/$GroupId").processGroupFlow.flow
}

function Get-OrCreateProcessGroup([string] $ParentId, [string] $Name, [int] $X, [int] $Y) {
    $matches = @((Get-GroupFlow $ParentId).processGroups | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one NiFi process group is named '$Name'." }
    if ($matches.Count -eq 1) { return $matches[0].id }
    return (Invoke-NiFi -Method POST -Path "/process-groups/$ParentId/process-groups" -Body @{
        revision = @{ version = 0 }
        component = @{ name = $Name; position = @{ x = $X; y = $Y }; comments = 'Shared post-promotion analytical work; source lanes do not depend on this group.' }
    }).id
}

function Stop-Group([string] $GroupId) {
    $active = @((Get-GroupFlow $GroupId).processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
    if ($active.Count -eq 0) { return }
    Invoke-NiFi -Method PUT -Path "/flow/process-groups/$GroupId" -Body @{ id = $GroupId; state = 'STOPPED'; disconnectedNodeAcknowledged = $false } | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $remaining = @((Get-GroupFlow $GroupId).processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Analytical Serving did not stop for reconciliation."
}

function Get-ProcessorType([string] $Type) {
    $matches = @((Invoke-NiFi -Method GET -Path "/flow/processor-types?type=$([Uri]::EscapeDataString($Type))").processorTypes | Where-Object { $_.type -eq $Type })
    if ($matches.Count -ne 1) { throw "NiFi processor type is not uniquely available: $Type" }
    return $matches[0]
}

function Ensure-Processor {
    param([string] $GroupId, [string] $Name, [string] $Type, [hashtable] $Properties, [string[]] $AutoTerminate, [int] $X, [int] $Y, [string] $SchedulingPeriod = '0 sec')
    $matches = @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one processor is named '$Name' in Analytical Serving." }
    $processorType = Get-ProcessorType $Type
    $config = @{
        properties = $Properties; schedulingPeriod = $SchedulingPeriod; schedulingStrategy = 'TIMER_DRIVEN'; executionNode = 'ALL'
        concurrentlySchedulableTaskCount = 1; penaltyDuration = '30 sec'; yieldDuration = '1 sec'; bulletinLevel = 'WARN'
        autoTerminatedRelationships = $AutoTerminate
    }
    if ($matches.Count -eq 0) {
        return (Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/processors" -Body @{
            revision = @{ version = 0 }
            component = @{ name = $Name; type = $Type; bundle = $processorType.bundle; position = @{ x = $X; y = $Y }; config = $config }
        }).id
    }
    $current = Invoke-NiFi -Method GET -Path "/processors/$($matches[0].id)"
    if ([string]$current.component.type -ne $Type) { throw "Processor '$Name' has the wrong type." }
    return (Invoke-NiFi -Method PUT -Path "/processors/$($current.id)" -Body @{
        revision = @{ version = $current.revision.version }
        component = @{ id = $current.id; name = $Name; position = @{ x = $X; y = $Y }; config = $config }
    }).id
}

function Ensure-Connection([string] $GroupId, [string] $Name, [string] $SourceId, [string] $DestinationId, [string[]] $Relationships) {
    $matches = @((Get-GroupFlow $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one connection is named '$Name'." }
    if ($matches.Count -eq 1) {
        $component = $matches[0].component
        if ($component.source.id -ne $SourceId -or $component.destination.id -ne $DestinationId -or (@($component.selectedRelationships) -join '|') -ne (@($Relationships) -join '|')) {
            throw "Existing connection '$Name' differs from its contract."
        }
        return
    }
    Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/connections" -Body @{
        revision = @{ version = 0 }
        component = @{
            name = $Name; source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = $Relationships; flowFileExpiration = '0 sec'; backPressureObjectThreshold = 10
            backPressureDataSizeThreshold = '10 MB'; loadBalanceStrategy = 'DO_NOT_LOAD_BALANCE'; loadBalanceCompression = 'DO_NOT_COMPRESS'; bends = @()
        }
    } | Out-Null
}

$rootId = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow.id
$baseballId = Get-OrCreateProcessGroup $rootId ([string]$contract.rootProcessGroup) 100 100
$groupId = Get-OrCreateProcessGroup $baseballId ([string]$contract.processGroup) 100 1500
Stop-Group $groupId
$flow = Get-GroupFlow $groupId
if (@($flow.connections | Where-Object { [int64]$_.status.aggregateSnapshot.flowFilesQueued -gt 0 }).Count -gt 0) {
    throw 'Analytical Serving has queued FlowFiles and cannot be reconciled.'
}

$incrementalArguments = "-B;$materializer;--state-root;$script:StateRoot;--max-events;$([int]$contract.authorityMaterialization.maximumEventsPerBuild)"
$fullArguments = "-B;$materializer;--state-root;$script:StateRoot;--full-rebuild"
$processors = @{}
$processors.trigger = Ensure-Processor $groupId 'Check Promoted Graph Events' 'org.apache.nifi.processors.standard.GenerateFlowFile' @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'; 'Custom Text' = '{}'
    'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
} @() 0 0 ([string]$contract.authorityMaterialization.checkPeriod)
$processors.fullTrigger = Ensure-Processor $groupId 'Full Authority RDF Rebuild Request' 'org.apache.nifi.processors.standard.GenerateFlowFile' @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'; 'Custom Text' = '{}'
    'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
} @() 0 -240 '365 days'
$processors.incremental = Ensure-Processor $groupId 'Materialize Pending Authority Events' 'org.apache.nifi.processors.standard.ExecuteStreamCommand' @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = $incrementalArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'authority.materialization.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
} @('output stream', 'nonzero status') 320 0
$processors.full = Ensure-Processor $groupId 'Rebuild Authority Serving From RDF' 'org.apache.nifi.processors.standard.ExecuteStreamCommand' @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = $fullArguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'authority.materialization.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
} @('output stream', 'nonzero status') 320 -240
$processors.incrementalGate = Ensure-Processor $groupId 'Require Incremental Materialization Success' 'org.apache.nifi.processors.standard.RouteOnAttribute' @{
    'Routing Strategy' = 'Route to Property name'; 'passed' = "`${execution.status:equals('0')}"
} @() 640 0
$processors.fullGate = Ensure-Processor $groupId 'Require Full Rebuild Success' 'org.apache.nifi.processors.standard.RouteOnAttribute' @{
    'Routing Strategy' = 'Route to Property name'; 'passed' = "`${execution.status:equals('0')}"
} @() 640 -240
$processors.incrementalRetry = Ensure-Processor $groupId 'Retry Incremental Authority Materialization' 'org.apache.nifi.processors.standard.RetryFlowFile' @{
    'Retry Attribute' = 'retry.authority-materialization'; 'Maximum Retries' = [string]$contract.failurePolicy.maximumRetries
    'Penalize Retries' = 'true'; 'Fail on Nonnumerical Overwrite' = 'true'; 'Reuse Mode' = 'fail'
} @('failure') 800 260 '1 min'
$processors.fullRetry = Ensure-Processor $groupId 'Retry Full Authority Rebuild' 'org.apache.nifi.processors.standard.RetryFlowFile' @{
    'Retry Attribute' = 'retry.authority-full-rebuild'; 'Maximum Retries' = [string]$contract.failurePolicy.maximumRetries
    'Penalize Retries' = 'true'; 'Fail on Nonnumerical Overwrite' = 'true'; 'Reuse Mode' = 'fail'
} @('failure') 800 460 '1 min'
$processors.success = Ensure-Processor $groupId 'Record Authority Materialization Result' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(authority|execution)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO authority materialization'; 'Character Set' = 'UTF-8'
} @('success') 960 -100
$processors.failure = Ensure-Processor $groupId 'Record Authority Materialization Failure' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'error'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(authority|execution|retry)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO authority materialization failure'; 'Character Set' = 'UTF-8'
} @('success') 1120 260

Ensure-Connection $groupId 'incremental trigger' $processors.trigger $processors.incremental @('success')
Ensure-Connection $groupId 'full rebuild trigger' $processors.fullTrigger $processors.full @('success')
Ensure-Connection $groupId 'incremental command result' $processors.incremental $processors.incrementalGate @('original')
Ensure-Connection $groupId 'full rebuild command result' $processors.full $processors.fullGate @('original')
Ensure-Connection $groupId 'incremental success' $processors.incrementalGate $processors.success @('passed')
Ensure-Connection $groupId 'full rebuild success' $processors.fullGate $processors.success @('passed')
Ensure-Connection $groupId 'incremental retry input' $processors.incrementalGate $processors.incrementalRetry @('unmatched')
Ensure-Connection $groupId 'full rebuild retry input' $processors.fullGate $processors.fullRetry @('unmatched')
Ensure-Connection $groupId 'incremental retry loop' $processors.incrementalRetry $processors.incremental @('retry')
Ensure-Connection $groupId 'full rebuild retry loop' $processors.fullRetry $processors.full @('retry')
Ensure-Connection $groupId 'incremental retry exhausted' $processors.incrementalRetry $processors.failure @('retries_exceeded')
Ensure-Connection $groupId 'full rebuild retry exhausted' $processors.fullRetry $processors.failure @('retries_exceeded')

$expected = @(
    'Check Promoted Graph Events','Full Authority RDF Rebuild Request','Materialize Pending Authority Events','Rebuild Authority Serving From RDF',
    'Require Incremental Materialization Success','Require Full Rebuild Success','Retry Incremental Authority Materialization','Retry Full Authority Rebuild',
    'Record Authority Materialization Result','Record Authority Materialization Failure'
)
$unexpected = @((Get-GroupFlow $groupId).processors | Where-Object { $_.component.name -notin $expected })
if ($unexpected.Count -gt 0) { throw "Analytical Serving contains unexpected processors: $(@($unexpected.component.name) -join ', ')" }
$invalid = @()
foreach ($summary in @((Get-GroupFlow $groupId).processors)) {
    $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
    if ([string]$entity.component.validationStatus -ne 'VALID') {
        $invalid += "$($entity.component.name): $(@($entity.component.validationErrors) -join '; ')"
    }
}
if ($invalid.Count -gt 0) { throw "Analytical Serving has invalid processors:`n$($invalid -join "`n")" }

if ($Start -or $RunFullRebuild) {
    foreach ($summary in @((Get-GroupFlow $groupId).processors | Where-Object { $_.id -notin @($processors.fullTrigger) })) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
        if ([string]$entity.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{ revision = @{ version = $entity.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false } | Out-Null
        }
    }
    if ($RunFullRebuild) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($processors.fullTrigger)"
        Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{ revision = @{ version = $entity.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false } | Out-Null
        Write-Host 'Submitted one asynchronous authority-RDF serving rebuild.'
    }
    if ($Start) { Write-Host 'Enabled promoted-graph-event authority materialization.' }
}
else {
    Write-Host 'Provisioned Analytical Serving in STOPPED state.'
}
