[CmdletBinding()]
param(
    [switch] $Start,
    [switch] $RunOnce
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
Initialize-LocalLayout

$contractPath = Join-Path $PSScriptRoot 'flow-contract.json'
$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
if (
    [string]$contract.artifactType -ne 'baseballo-nifi-repository-evidence-flow-contract' -or
    [int]$contract.contractVersion -ne 1 -or
    [string]$contract.observer.timeZone -ne 'America/New_York' -or
    [bool]$contract.failurePolicy.controlsSourceLanes -ne $false -or
    [bool]$contract.failurePolicy.changesAuthoritativeRdf -ne $false -or
    [bool]$contract.failurePolicy.changesServingPointers -ne $false -or
    [bool]$contract.failurePolicy.evidenceIsImmutable -ne $true
) {
    throw "Unsupported repository-evidence NiFi contract: $contractPath"
}
$observer = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ([string]$contract.observer.processor)))
if (-not (Test-Path -LiteralPath $observer -PathType Leaf)) {
    throw "Repository validation observer is missing: $observer"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$api = $script:NiFiApiUri
$python = (Get-Command python -ErrorAction Stop).Source

function Invoke-NiFi {
    param([Parameter(Mandatory = $true)][ValidateSet('GET', 'POST', 'PUT')][string] $Method, [Parameter(Mandatory = $true)][string] $Path, $Body)
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
            comments = 'Asynchronous aggregate repository validation observer; never controls source lanes or data promotion.'
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
    throw 'Repository Evidence did not stop for reconciliation.'
}

function Get-ProcessorType([string] $Type) {
    $matches = @((Invoke-NiFi -Method GET -Path "/flow/processor-types?type=$([Uri]::EscapeDataString($Type))").processorTypes | Where-Object { $_.type -eq $Type })
    if ($matches.Count -ne 1) { throw "NiFi processor type is not uniquely available: $Type" }
    return $matches[0]
}

function Ensure-Processor {
    param(
        [string] $GroupId, [string] $Name, [string] $Type, [hashtable] $Properties,
        [string[]] $AutoTerminate, [int] $X, [int] $Y,
        [string] $SchedulingPeriod = '0 sec', [string] $SchedulingStrategy = 'TIMER_DRIVEN'
    )
    $matches = @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -eq $Name })
    if ($matches.Count -gt 1) { throw "More than one processor is named '$Name' in Repository Evidence." }
    $processorType = Get-ProcessorType $Type
    $config = @{
        properties = $Properties; schedulingPeriod = $SchedulingPeriod; schedulingStrategy = $SchedulingStrategy
        executionNode = 'ALL'; concurrentlySchedulableTaskCount = 1; penaltyDuration = '30 sec'
        yieldDuration = '1 sec'; bulletinLevel = 'WARN'; autoTerminatedRelationships = $AutoTerminate
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
            name = $Name
            source = @{ id = $SourceId; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $DestinationId; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = $Relationships; flowFileExpiration = '0 sec'; backPressureObjectThreshold = 2
            backPressureDataSizeThreshold = '1 MB'; loadBalanceStrategy = 'DO_NOT_LOAD_BALANCE'
            loadBalanceCompression = 'DO_NOT_COMPRESS'; bends = @()
        }
    } | Out-Null
}

$rootId = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow.id
$baseballId = Get-OrCreateProcessGroup $rootId ([string]$contract.rootProcessGroup) 100 100
$groupId = Get-OrCreateProcessGroup $baseballId ([string]$contract.processGroup) 1500 1500
Stop-Group $groupId
$flow = Get-GroupFlow $groupId
if (@($flow.connections | Where-Object { [int64]$_.status.aggregateSnapshot.flowFilesQueued -gt 0 }).Count -gt 0) {
    throw 'Repository Evidence has queued FlowFiles and cannot be reconciled.'
}

$arguments = "-B;$observer;--state-root;$script:StateRoot;--timeout-seconds;$([int]$contract.observer.timeoutSeconds)"
$processors = @{}
$processors.scheduled = Ensure-Processor $groupId 'Daily Repository Evidence Trigger' 'org.apache.nifi.processors.standard.GenerateFlowFile' @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
    'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
} @() 0 0 ([string]$contract.observer.schedule) 'CRON_DRIVEN'
$processors.manual = Ensure-Processor $groupId 'Manual Repository Evidence Trigger' 'org.apache.nifi.processors.standard.GenerateFlowFile' @{
    'File Size' = '0B'; 'Batch Size' = '1'; 'Data Format' = 'Text'; 'Unique FlowFiles' = 'false'
    'Custom Text' = '{}'; 'Character Set' = 'UTF-8'; 'Mime Type' = 'application/json'
} @() 0 -220 '365 days'
$processors.run = Ensure-Processor $groupId 'Run Aggregate Repository Validation' 'org.apache.nifi.processors.standard.ExecuteStreamCommand' @{
    'Working Directory' = $repositoryRoot; 'Command Path' = $python; 'Command Arguments Strategy' = 'Command Arguments Property'
    'Command Arguments' = $arguments; 'Argument Delimiter' = ';'; 'Ignore STDIN' = 'true'
    'Output Destination Attribute' = 'repository.validation.output'; 'Max Attribute Length' = '65536'; 'Output MIME Type' = 'application/json'
} @('output stream', 'nonzero status') 340 0
$processors.gate = Ensure-Processor $groupId 'Require Repository Validation Success' 'org.apache.nifi.processors.standard.RouteOnAttribute' @{
    'Routing Strategy' = 'Route to Property name'; 'passed' = "`${execution.status:equals('0')}"
} @() 680 0
$processors.retry = Ensure-Processor $groupId 'Retry Repository Validation' 'org.apache.nifi.processors.standard.RetryFlowFile' @{
    'Retry Attribute' = 'retry.repository-validation'; 'Maximum Retries' = [string]$contract.failurePolicy.maximumRetries
    'Penalize Retries' = 'true'; 'Fail on Nonnumerical Overwrite' = 'true'; 'Reuse Mode' = 'fail'
} @('failure') 820 220 '1 min'
$processors.success = Ensure-Processor $groupId 'Record Repository Validation Pass' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'info'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(repository|execution)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO repository validation'; 'Character Set' = 'UTF-8'
} @('success') 1020 -80
$processors.failure = Ensure-Processor $groupId 'Record Repository Validation Failure' 'org.apache.nifi.processors.standard.LogAttribute' @{
    'Log Level' = 'error'; 'Log Payload' = 'false'; 'Attributes to Log Regular Expression' = '^(repository|execution|retry)\..*$'
    'Log FlowFile Properties' = 'true'; 'Output Format' = 'Line per Attribute'; 'Log Prefix' = 'BaseballO repository validation failure'; 'Character Set' = 'UTF-8'
} @('success') 1020 220

Ensure-Connection $groupId 'scheduled observation' $processors.scheduled $processors.run @('success')
Ensure-Connection $groupId 'manual observation' $processors.manual $processors.run @('success')
Ensure-Connection $groupId 'validation command result' $processors.run $processors.gate @('original')
Ensure-Connection $groupId 'validation passed' $processors.gate $processors.success @('passed')
Ensure-Connection $groupId 'validation retry input' $processors.gate $processors.retry @('unmatched')
Ensure-Connection $groupId 'validation retry loop' $processors.retry $processors.run @('retry')
Ensure-Connection $groupId 'validation retry exhausted' $processors.retry $processors.failure @('retries_exceeded')

$expected = @(
    'Daily Repository Evidence Trigger','Manual Repository Evidence Trigger','Run Aggregate Repository Validation',
    'Require Repository Validation Success','Retry Repository Validation','Record Repository Validation Pass',
    'Record Repository Validation Failure'
)
$unexpected = @((Get-GroupFlow $groupId).processors | Where-Object { $_.component.name -notin $expected })
if ($unexpected.Count -gt 0) { throw "Repository Evidence contains unexpected processors: $(@($unexpected.component.name) -join ', ')" }
$invalid = @()
foreach ($summary in @((Get-GroupFlow $groupId).processors)) {
    $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
    if ([string]$entity.component.validationStatus -ne 'VALID') {
        $invalid += "$($entity.component.name): $(@($entity.component.validationErrors) -join '; ')"
    }
}
if ($invalid.Count -gt 0) { throw "Repository Evidence has invalid processors:`n$($invalid -join "`n")" }

if ($Start -or $RunOnce) {
    foreach ($summary in @((Get-GroupFlow $groupId).processors | Where-Object { $_.id -ne $processors.manual })) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($summary.id)"
        if ([string]$entity.component.state -ne 'RUNNING') {
            Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
                revision = @{ version = $entity.revision.version }; state = 'RUNNING'; disconnectedNodeAcknowledged = $false
            } | Out-Null
        }
    }
    if ($RunOnce) {
        $entity = Invoke-NiFi -Method GET -Path "/processors/$($processors.manual)"
        Invoke-NiFi -Method PUT -Path "/processors/$($entity.id)/run-status" -Body @{
            revision = @{ version = $entity.revision.version }; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false
        } | Out-Null
        Write-Host 'Submitted one asynchronous aggregate repository validation.'
    }
    if ($Start) { Write-Host 'Enabled daily aggregate repository validation at 06:30 Eastern.' }
}
else {
    Write-Host 'Provisioned Repository Evidence in STOPPED state.'
}
