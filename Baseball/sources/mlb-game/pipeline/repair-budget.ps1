function Invoke-MlbRepairBudget {
    param(
        [Parameter(Mandatory = $true)][string] $StateRoot,
        [Parameter(Mandatory = $true)][string] $Worker,
        [Parameter(Mandatory = $true)][scriptblock] $Action,
        [ValidateRange(0, 60)][int] $TimeoutSeconds = 60
    )

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
        if ($available -lt 1024MB) {
            @{status='deferred'; reason='waiting-for-memory'; worker=$Worker;
                availableMemoryBytes=$available; requiredMemoryBytes=1GB} | ConvertTo-Json -Compress
            return
        }
        & $Action
    }
    finally { $lease.Dispose() }
}
