function Enter-MlbGameLock {
    param(
        [Parameter(Mandatory = $true)][string] $StateRoot,
        [Parameter(Mandatory = $true)][ValidatePattern('^\d+$')][string] $GamePk,
        [ValidateRange(1, 7200)][int] $TimeoutSeconds = 7200
    )

    $lockRoot = Join-Path $StateRoot 'pipeline\work\mlb-game-locks'
    [void](New-Item -ItemType Directory -Force -Path $lockRoot)
    $lockPath = Join-Path $lockRoot "$GamePk.lock"
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            # Windows releases the exclusive handle if the worker crashes.
            # Different games have separate files and can proceed together.
            return [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate,
                [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        }
        catch [IO.IOException] {
            Start-Sleep -Milliseconds 250
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for the MLB-game stage lock: $GamePk"
}
