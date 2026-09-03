[CmdletBinding()]
param(
    [switch] $Start,
    [switch] $RunFullBackfill
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
Initialize-LocalLayout

$contractPath = Join-Path $PSScriptRoot 'flow-contract.json'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
if (
    [string]$contract.artifactType -ne 'baseballo-nifi-dsq-sql-flow-contract' -or
    [int]$contract.contractVersion -ne 1 -or
    [int]$contract.materialization.queryCount -ne 56 -or
    [int]$contract.materialization.readOnlyWorkers -ne 2 -or
    [string]$contract.materialization.tableOwnership -ne 'one-dedicated-table-per-dsq' -or
    [bool]$contract.failurePolicy.authoritativeRdfUnaffected -ne $true -or
    [bool]$contract.failurePolicy.queryIndexRdfUnaffected -ne $true -or
    [bool]$contract.failurePolicy.sourceLanesUnaffected -ne $true -or
    [bool]$contract.failurePolicy.priorServingPointerUnaffected -ne $true -or
    [bool]$contract.failurePolicy.uiAdmissionUnaffected -ne $true
) {
    throw "Unsupported DSQ SQL NiFi contract: $contractPath"
}

$materializer = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.materialization.processor)))
$catalog = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.materialization.catalog)))
$schema = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.materialization.schema)))
foreach ($required in @($materializer, $catalog, $schema)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "DSQ SQL artifact is missing: $required"
    }
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$api = $script:NiFiApiUri
$python = (Get-Command python -ErrorAction Stop).Source

function Invoke-NiFi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('GET', 'POST', 'PUT', 'DELETE')][string] $Method,
        [Parameter(Mandatory = $true)][string] $Path,
        $Body
    )
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
        component = @{
            name = $Name
            position = @{ x = $X; y = $Y }
            comments = 'Full SQL materialization of every approved DSQ. Authoritative RDF and UI admission do not depend on this group.'
        }
    }).id
}

function Stop-Group([string] $GroupId) {
    $active = @((Get-GroupFlow $GroupId).processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
    if ($active.Count -eq 0) { return }
    Invoke-NiFi -Method PUT -Path "/flow/process-groups/$GroupId" -Body @{
        id = $GroupId; state = 'STOPPED'; disconnectedNodeAcknowledged = $false
    } | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $remaining = @((Get-GroupFlow $GroupId).processors | Where-Object { [string]$_.component.state -notin @('STOPPED', 'DISABLED') })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "DSQ SQL Materialization did not stop for reconciliation."
}

function Get-ProcessorType([string] $Type) {
    $matches = @((Invoke-NiFi -Method GET -Path "/flow/processor-types?type=$([Uri]::EscapeDataString($Type))").processorTypes | Where-Object { $_.type -eq $Type })
    if ($matches.Count -ne 1) { throw "NiFi processor type is not uniquely available: $Type" }
    return $matches[0]
}

function Ensure-Processor {
    param(
        [string] $GroupId,
        [string] $Name,
        [string] $Type,
        [hashtable] $Properties,
        [string[]] $AutoTerminate,
        [int] $X,
        [int] $Y,
        [string] $SchedulingPeriod = '0 sec'
    )
    $matches = @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one processor is named '$Name' in DSQ SQL Materialization." }
    $processorType = Get-ProcessorType $Type
    $config = @{
        properties = $Properties
        schedulingPeriod = $SchedulingPeriod
        schedulingStrategy = 'TIMER_DRIVEN'
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
            component = @{
                name = $Name; type = $Type; bundle = $processorType.bundle
                position = @{ x = $X; y = $Y }; config = $config
            }
        }).id
    }
    $current = Invoke-NiFi -Method GET -Path "/processors/$($matches[0].id)"
    if ([string]$current.component.type -ne $Type) { throw "Processor '$Name' has the wrong type." }
    return (Invoke-NiFi -Method PUT -Path "/processors/$($current.id)" -Body @{
        revision = @{ version = $current.revision.version }
        component = @{
            id = $current.id; name = $Name; position = @{ x = $X; y = $Y }; config = $config
        }
    }).id
}

function Ensure-Connection {
    param(
        [string] $GroupId,
        [string] $Name,
        [string] $SourceId,
        [string] $DestinationId,
        [string[]] $Relationships
    )
    $matches = @((Get-GroupFlow $GroupId).connections | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one connection is named '$Name'." }
    if ($matches.Count -eq 1) {
        $component = $matches[0].component
        if (
            $component.source.id -ne $SourceId -or
            $component.destination.id -ne $DestinationId -or
            (@($component.selectedRelationships) -join '|') -ne (@($Relationships) -join '|')
        ) {
            throw "Existing connection '$Name' differs from its contract."
        }
        return
    }
    Invoke-NiFi -Method POST -Path "/process-groups/$GroupId/connections" -Body @{
        revision = @{ version = 0 }
        component = @{
            name = $Name
            source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = $Relationships
            flowFileExpiration = '0 sec'
            backPressureObjectThreshold = 2
            backPressureDataSizeThreshold = '1 MB'
            loadBalanceStrategy = 'DO_NOT_LOAD_BALANCE'
            loadBalanceCompression = 'DO_NOT_COMPRESS'
            bends = @()
        }
    } | Out-Null
}

$rootId = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow.id
$baseballId = Get-OrCreateProcessGroup $rootId ([string]$contract.rootProcessGroup) 100 100
$groupId = Get-OrCreateProcessGroup $baseballId ([string]$contract.processGroup) 650 1500
Stop-Group $groupId
$flow = Get-GroupFlow $groupId
if (@($flow.connections | Where-Object { [int64]$_.status.aggregateSnapshot.flowFilesQueued -gt 0 }).Count -gt 0) {
    throw 'DSQ SQL Materialization has queued FlowFiles and cannot be reconciled.'
}

$arguments = "-B;$materializer;--state-root;$script:StateRoot;--retain-builds;3;--dsq-workers;$([int]$contract.materialization.readOnlyWorkers)"
$processors = @{}
$processors.trigger = Ensure-Processor $groupId 'Full DSQ SQL Backfill Request' 'org.apache.nifi.processors.standard.GenerateFlowFile' @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'; 'Custom Text' = '{}'
    'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
} @() 0 0 '365 days'
$processors.materialize = Ensure-Processor $groupId 'Materialize All DSQs' 'org.apache.nifi.processors.standard.ExecuteStreamCommand' @{
    'Working Directory' = $repositoryRoot
    'Command Path' = $python
    'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = $arguments
    'Argument Delimiter' = ';'
    'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'dsq.materialization.output'
    'Max Attribute Length' = '65536'
    'Output MIME Type' = 'application/json'
} @('output stream', 'nonzero status') 300 0
$processors.gate = Ensure-Processor $groupId 'Require DSQ Materialization Success' 'org.apache.nifi.processors.standard.RouteOnAttribute' @{
    'Routing Strategy' = 'Route to Property name'; 'passed' = "`${execution.status:equals('0')}"
} @() 620 0
$processors.retry = Ensure-Processor $groupId 'Retry DSQ Materialization' 'org.apache.nifi.processors.standard.RetryFlowFile' @{
    'Retry Attribute' = 'retry.dsq-materialization'
    'Maximum Retries' = [string]$contract.failurePolicy.maximumRetries
    'Penalize Retries' = 'true'
    'Fail on Nonnumerical Overwrite' = 'true'
    'Reuse Mode' = 'fail'
} @('failure') 620 250 '1 min'
$processors.success = Ensure-Processor $groupId 'Record DSQ Materialization Result' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(dsq|execution)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'
    'Log Prefix' = 'BaseballO DSQ SQL materialization'; 'Character Set' = 'UTF-8'
} @('success') 940 -80
$processors.failure = Ensure-Processor $groupId 'Record DSQ Materialization Failure' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'error'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(dsq|execution|retry)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'
    'Log Prefix' = 'BaseballO DSQ SQL materialization failure'; 'Character Set' = 'UTF-8'
} @('success') 940 250

Ensure-Connection $groupId 'backfill trigger' $processors.trigger $processors.materialize @('success')
Ensure-Connection $groupId 'materialization command result' $processors.materialize $processors.gate @('original')
Ensure-Connection $groupId 'materialization passed' $processors.gate $processors.success @('passed')
Ensure-Connection $groupId 'materialization retry input' $processors.gate $processors.retry @('unmatched')
Ensure-Connection $groupId 'materialization retry loop' $processors.retry $processors.materialize @('retry')
Ensure-Connection $groupId 'materialization retry exhausted' $processors.retry $processors.failure @('retries_exceeded')

$expected = @(
    'Full DSQ SQL Backfill Request', 'Materialize All DSQs', 'Require DSQ Materialization Success',
    'Retry DSQ Materialization', 'Record DSQ Materialization Result', 'Record DSQ Materialization Failure'
)
$unexpected = @((Get-GroupFlow $groupId).processors | Where-Object { $_.component.name -notin $expected })
if ($unexpected.Count -gt 0) {
    throw "DSQ SQL Materialization contains unexpected processors: $(@($unexpected.component.name) -join ', ')"
}
$invalid = @()
foreach ($summary in @((Get-GroupFlow $groupId).processors)) {
    $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
    if ([string]$entity.component.validationStatus -ne 'VALID') {
        $invalid += "$($entity.component.name): $(@($entity.component.validationErrors) -join '; ')"
    }
}
if ($invalid.Count -gt 0) { throw "DSQ SQL Materialization has invalid processors:`n$($invalid -join "`n")" }

if ($Start -or $RunFullBackfill) {
    foreach ($summary in @((Get-GroupFlow $groupId).processors | Where-Object { $_.id -ne $processors.trigger })) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
        if ([string]$entity.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
                revision = @{ version = $entity.revision.version }
                state = 'RUNNING'; disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
    }
    if ($RunFullBackfill) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($processors.trigger)"
        Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
            revision = @{ version = $entity.revision.version }
            state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host 'Submitted one asynchronous full DSQ SQL backfill.'
    }
    if ($Start) { Write-Host 'Enabled the DSQ SQL materialization worker group.' }
}
else {
    Write-Host 'Provisioned DSQ SQL Materialization in STOPPED state.'
}
