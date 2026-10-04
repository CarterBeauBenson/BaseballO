function Release-MlbFusekiWorkingSet {
    # TDB's file-backed pages can occupy the reserve even with a small JVM
    # heap. Ask Windows to page out this project's Fuseki working set only.
    # No graph, heap limit, process state or user application is changed.
    $stateVariable = Get-Variable -Name FusekiState -Scope Script -ErrorAction SilentlyContinue
    $homeVariable = Get-Variable -Name FusekiHome -Scope Script -ErrorAction SilentlyContinue
    if ($null -eq $stateVariable -or $null -eq $homeVariable) { return }
    $pidPath = Join-Path $stateVariable.Value 'fuseki.pid'
    if (-not (Test-Path -LiteralPath $pidPath -PathType Leaf)) { return }
    $process = $null
    try {
        $fusekiPid = [int](Get-Content -LiteralPath $pidPath -Raw)
        $process = Get-Process -Id $fusekiPid -ErrorAction Stop
        if ($process.WorkingSet64 -le 1GB) { return }
        $record = Get-CimInstance Win32_Process -Filter "ProcessId=$fusekiPid"
        $jar = Join-Path $homeVariable.Value 'fuseki-server.jar'
        if ($record.ExecutablePath -ne (Get-JavaExecutable) -or
            -not $record.CommandLine.Contains('"' + $jar + '"')) { return }
        if (-not ('BaseballO.RepairMemory' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace BaseballO {
    public static class RepairMemory {
        [DllImport("psapi.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool EmptyWorkingSet(IntPtr process);
    }
}
'@
        }
        [void][BaseballO.RepairMemory]::EmptyWorkingSet($process.Handle)
    }
    catch { Write-Verbose "Fuseki memory could not be reclaimed: $_" }
    finally { if ($null -ne $process) { $process.Dispose() } }
}

function Invoke-MlbRepairBudget {
    param(
        [Parameter(Mandatory = $true)][string] $StateRoot,
        [Parameter(Mandatory = $true)][string] $Worker,
        [Parameter(Mandatory = $true)][scriptblock] $Action,
        [ValidateRange(0, 2147483647)][long] $RequiredMemoryBytes = 1GB,
        [ValidateRange(0, 60)][int] $TimeoutSeconds = 0
    )

    # A queued SQL build has no priority over upstream repairs. A worker that
    # is already running still owns its memory until it exits.
    $progressFiles = @(Get-ChildItem -LiteralPath (Join-Path $StateRoot 'serving\builds') -Filter '*.progress.json' -ErrorAction SilentlyContinue)
    $dashboardProgress = Join-Path $StateRoot 'serving\dashboard\progress.json'
    if (Test-Path -LiteralPath $dashboardProgress -PathType Leaf) { $progressFiles += Get-Item -LiteralPath $dashboardProgress }
    foreach ($file in $progressFiles) {
        $progress = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        if ($progress.status -ne 'running') { continue }
        if ($null -ne $progress.PSObject.Properties['processId'] -and
                $null -ne (Get-Process -Id $progress.processId -ErrorAction SilentlyContinue)) {
            @{status='deferred'; reason='serving-worker-active'; worker=$Worker} | ConvertTo-Json -Compress
            return
        }
    }
    # These small additive jobs share one memory slot. NiFi still owns their
    # independent schedules and retries; the OS releases this handle on a crash.
    $root = Join-Path $StateRoot 'pipeline\work\mlb-game-locks'
    [void](New-Item -ItemType Directory -Force -Path $root)
    $path = Join-Path $root 'targeted-repair-budget.lock'
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lease = $null
    do {
        try {
            $lease = [IO.File]::Open($path, [IO.FileMode]::OpenOrCreate,
                [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        }
        catch [IO.IOException] {
            if ([DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 250 }
        }
    } while ($null -eq $lease -and [DateTime]::UtcNow -lt $deadline)
    if ($null -eq $lease) {
        @{status='deferred'; reason='repair-slot-busy'; worker=$Worker} | ConvertTo-Json -Compress
        return
    }
    try {
        # Mapping (256 MiB) exits before the retained-graph SHACL session
        # (384 MiB) starts. Reserve room for Python and JVM native memory too.
        $available = [long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024
        if ($available -lt 1GB) {
            Release-MlbFusekiWorkingSet
            $available = [long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024
        }
        if ($available -lt $RequiredMemoryBytes) {
            @{status='deferred'; reason='waiting-for-memory'; worker=$Worker;
                availableMemoryBytes=$available; requiredMemoryBytes=$RequiredMemoryBytes} | ConvertTo-Json -Compress
            return
        }
        & $Action
    }
    finally { $lease.Dispose() }
}
