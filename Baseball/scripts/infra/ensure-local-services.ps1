[CmdletBinding()]
param([switch] $Pause, [switch] $Resume, [switch] $CheckOnly)

. (Join-Path $PSScriptRoot 'common.ps1')
if ($Pause -and $Resume) { throw 'Choose Pause or Resume, not both.' }
$operationsRoot = Join-Path $script:StateRoot 'operations'
[void](New-Item -ItemType Directory -Force -Path $operationsRoot)
$pausePath = Join-Path $operationsRoot 'maintenance.json'
if ($Pause) {
    @{ pausedAtUtc = [DateTime]::UtcNow.ToString('o'); reason = 'operator-maintenance' } |
        ConvertTo-Json | Set-Content -LiteralPath $pausePath -Encoding UTF8
    # Wait for any already-admitted startup to finish before an operator stops
    # the stack. A timeout leaves supervision paused and prevents stop-stack
    # from racing an in-flight starter.
    $pauseLock = [Threading.Mutex]::new($false, 'Local\BaseballO.LocalServices')
    $pauseAcquired = $false
    try {
        try { $pauseAcquired = $pauseLock.WaitOne(60000) }
        catch [Threading.AbandonedMutexException] { $pauseAcquired = $true }
        if (-not $pauseAcquired) { throw 'Supervision is paused but a startup is still finishing. Retry the stop after it finishes.' }
    }
    finally { if ($pauseAcquired) { $pauseLock.ReleaseMutex() }; $pauseLock.Dispose() }
    Write-Output 'Local service supervision paused. Existing processes remain running.'
    return
}
if ($Resume) { Remove-Item -LiteralPath $pausePath -ErrorAction SilentlyContinue }
if (Test-Path -LiteralPath $pausePath) {
    Write-Output 'Local service supervision is paused for maintenance.'
    return
}

$services = @(
    @{ name = 'fuseki'; port = 3031; script = 'start-fuseki.ps1'; arguments = @(); uri = 'http://127.0.0.1:3031/$/ping' },
    @{ name = 'nifi'; port = 8080; script = 'start-nifi.ps1'; arguments = @(); uri = 'http://127.0.0.1:8080/nifi-api/flow/process-groups/root' },
    @{ name = 'explorer'; port = 4173; script = 'launch-explorer.ps1'; arguments = @('-NoBrowser', '-SkipNiFi'); uri = 'http://127.0.0.1:4173/health/live' }
)
$results = @()
$runLock = [Threading.Mutex]::new($false, 'Local\BaseballO.LocalServices')
$runAcquired = $false
try {
    try { $runAcquired = $runLock.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $runAcquired = $true }
    if (-not $runAcquired) { Write-Output 'Another local service check is active.'; return }
    foreach ($service in $services) {
        if (Test-Path -LiteralPath $pausePath) { Write-Output 'Maintenance requested; remaining startup checks skipped.'; return }
        $started = $false
        try {
            if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $service.port)) {
                if ($CheckOnly) { throw 'Service is not listening.' }
                # Existing starters retain runtime/storage identity checks. Never kill
                # a listener or use a data-readiness failure to restart a workflow.
                $starter = Join-Path $PSScriptRoot $service.script
                $starterArguments = @('-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $starter + '"')) + $service.arguments
                # Waiting on captured pipeline output can wait forever when a
                # daemon inherits its handles. Wait on the starter process itself.
                $starterProcess = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $starterArguments `
                    -RedirectStandardOutput (Join-Path $operationsRoot ($service.name + '-start.stdout.log')) `
                    -RedirectStandardError (Join-Path $operationsRoot ($service.name + '-start.stderr.log')) `
                    -WindowStyle Hidden -PassThru
                try {
                    # Keep the native handle open so Windows PowerShell retains
                    # the exit code after the process exits.
                    $null = $starterProcess.Handle
                    if (-not $starterProcess.WaitForExit(660000)) {
                        $starterProcess.Kill()
                        throw 'Starter exceeded eleven minutes. Inspect service logs before retrying.'
                    }
                    if ($starterProcess.ExitCode -ne 0) { throw "Starter failed with exit code $($starterProcess.ExitCode). Inspect the service logs." }
                }
                finally { $starterProcess.Dispose() }
                $started = $true
            }
            $health = Invoke-RestMethod -Uri $service.uri -TimeoutSec 5
            if ($service.name -eq 'fuseki' -and -not (Test-BaseballFusekiService)) {
                throw 'The BaseballO Fuseki dataset is unavailable.'
            }
            if ($service.name -eq 'explorer' -and ($health.service -ne 'baseballo-explorer' -or $health.status -ne 'alive')) {
                throw 'Unexpected Explorer identity.'
            }
            if ($service.name -eq 'nifi' -and [string]::IsNullOrWhiteSpace([string]$health.processGroupFlow.id)) {
                throw 'Unexpected NiFi identity.'
            }
            $results += @{ service = $service.name; status = 'alive'; started = $started }
        }
        catch {
            $results += @{ service = $service.name; status = 'unavailable'; started = $started; error = $_.Exception.Message }
        }
    }
    $report = @{ artifactType = 'baseballo-local-service-status'; checkedAtUtc = [DateTime]::UtcNow.ToString('o');
        checkOnly = [bool]$CheckOnly; services = $results; dataReadinessChecked = $false }
    $temporary = Join-Path $operationsRoot ('status-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $statusPath = Join-Path $operationsRoot 'services.json'
    try {
        $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporary -Encoding UTF8
        if (Test-Path -LiteralPath $statusPath) { [IO.File]::Replace($temporary, $statusPath, [NullString]::Value) }
        else { [IO.File]::Move($temporary, $statusPath) }
    }
    finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
    $report | ConvertTo-Json -Depth 6
    if (@($results | Where-Object { $_.status -ne 'alive' }).Count) { exit 1 }
}
finally { if ($runAcquired) { $runLock.ReleaseMutex() }; $runLock.Dispose() }
