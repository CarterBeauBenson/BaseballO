[CmdletBinding()]
param(
    [ValidateSet('all', 'mlb-game', 'mlb-teams', 'mlb-leagues', 'mlb-divisions', 'mlb-people', 'mlb-venues', 'mlb-transactions')]
    [string[]] $Module = @('all'),
    [switch] $PreflightOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening at $script:NiFiBaseUri."
}

$contracts = [ordered]@{
    'mlb-game' = @{ group = 'MLB Game'; trigger = 'Backfill Schedule Request'; releases = @('Check Proof Release') }
    'mlb-teams' = @{ group = 'MLB Teams'; trigger = 'Backfill Request'; releases = @('Check Proof Release') }
    'mlb-leagues' = @{ group = 'MLB Leagues'; trigger = 'Backfill Request'; releases = @('Check Proof Release') }
    'mlb-divisions' = @{ group = 'MLB Divisions'; trigger = 'Backfill Request'; releases = @('Check Proof Release') }
    'mlb-people' = @{ group = 'MLB People'; trigger = 'Population Request'; releases = @('Check Population Proof Release') }
    'mlb-venues' = @{ group = 'MLB Venues'; trigger = 'Population Request'; releases = @('Check Population Proof Release') }
    'mlb-transactions' = @{ group = 'MLB Transactions'; trigger = 'Backfill Request'; releases = @('Check Proof Release') }
}

$requested = @($Module | Select-Object -Unique)
if ('all' -in $requested -and $requested.Count -ne 1) {
    throw "Use -Module all by itself or list explicit source modules."
}
$selected = if ($requested -contains 'all') { @($contracts.Keys) } else { $requested }

$api = $script:NiFiApiUri
function Invoke-NiFi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('GET', 'PUT')][string] $Method,
        [Parameter(Mandatory = $true)][string] $Path,
        $Body
    )
    $arguments = @{ Uri = "$api$Path"; Method = $Method; TimeoutSec = 60 }
    if ($null -ne $Body) {
        $arguments.ContentType = 'application/json'
        $arguments.Body = $Body | ConvertTo-Json -Depth 10
    }
    Invoke-RestMethod @arguments
}

$root = (Invoke-NiFi -Method GET -Path '/flow/process-groups/root').processGroupFlow
$baseballGroups = @($root.flow.processGroups | Where-Object { $_.component.name -eq $script:NiFiRootProcessGroupName })
if ($baseballGroups.Count -ne 1) {
    throw "Expected one BaseballO process group, found $($baseballGroups.Count)."
}
$baseballFlow = (Invoke-NiFi -Method GET -Path "/flow/process-groups/$($baseballGroups[0].id)").processGroupFlow.flow

$ready = [System.Collections.Generic.List[object]]::new()
foreach ($moduleId in $selected) {
    $expected = $contracts[$moduleId]
    $groups = @($baseballFlow.processGroups | Where-Object { $_.component.name -eq [string]$expected.group })
    if ($groups.Count -ne 1) {
        throw "Expected one $($expected.group) process group, found $($groups.Count)."
    }
    $flow = (Invoke-NiFi -Method GET -Path "/flow/process-groups/$($groups[0].id)").processGroupFlow.flow
    $invalid = @($flow.processors | Where-Object { $_.component.validationStatus -ne 'VALID' })
    if ($invalid.Count -gt 0) {
        throw "$moduleId has invalid processors: $(@($invalid.component.name) -join ', ')"
    }
    foreach ($releaseName in @($expected.releases)) {
        $release = @($flow.processors | Where-Object { $_.component.name -eq $releaseName })
        if ($release.Count -ne 1 -or [string]$release[0].component.state -ne 'RUNNING') {
            throw "$moduleId release gate '$releaseName' is not uniquely present and running."
        }
    }
    $triggers = @($flow.processors | Where-Object { $_.component.name -eq [string]$expected.trigger })
    if ($triggers.Count -ne 1) {
        throw "$moduleId corpus trigger '$($expected.trigger)' is not uniquely present."
    }
    $trigger = Invoke-NiFi -Method GET -Path "/processors/$($triggers[0].id)"
    if ([string]$trigger.component.state -ne 'STOPPED') {
        throw "$moduleId corpus trigger is already $($trigger.component.state); no submission was made."
    }
    $ready.Add([pscustomobject]@{ module = $moduleId; trigger = $trigger })
}

if ($PreflightOnly) {
    Write-Host "Corpus submission preflight passed for: $(@($ready.module) -join ', ')."
    Write-Host 'No corpus request was submitted.'
    return
}

foreach ($item in $ready) {
    $trigger = $item.trigger
    Invoke-NiFi -Method PUT -Path "/processors/$($trigger.id)/run-status" -Body @{
        revision = @{ version = $trigger.revision.version }
        state = 'RUN_ONCE'
        disconnectedNodeAcknowledged = $false
    } | Out-Null
    Write-Host "Submitted asynchronous corpus request for $($item.module)."
}

Write-Host 'Submission complete. NiFi owns execution, retries, quarantine, promotion, and evidence; this command does not poll.'
