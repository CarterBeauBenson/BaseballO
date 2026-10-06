[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-runner-addition' -Action {
    $admissionWorker = Join-Path $PSScriptRoot 'admission-evidence-queue.py'
    # Give the already-published eligibility backlog its existing bounded
    # turn before adding more graph versions that need dependent checks.
    $admissionJson = & python -B $admissionWorker --state-root $script:StateRoot `
        --java (Get-JavaExecutable) --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
    if ($LASTEXITCODE -ne 0) { throw 'Pending admission maintenance failed; preserve its recorded retry.' }
    $admissionJson
    $admission = $admissionJson | ConvertFrom-Json
    $outcomes = $admission.PSObject.Properties['outcomes']
    if ($null -ne $outcomes -and @($outcomes.Value.PSObject.Properties | Where-Object {
            $_.Name -in @('waiting-for-memory', 'failed', 'partial-refreshed', 'refreshed') -and $_.Value -gt 0
        }).Count -gt 0) { return }
    $worker = Join-Path $PSScriptRoot 'targeted-empty-game-addition.py'
    $selection = & python -B $worker --state-root $script:StateRoot --next
    if ($LASTEXITCODE -ne 0) { throw 'Empty Games repair inventory failed.' }
    $candidate = $selection | ConvertFrom-Json
    if ($null -eq $candidate) {
        $worker = Join-Path $PSScriptRoot 'targeted-clock-correction.py'
        $selection = & python -B $worker --state-root $script:StateRoot --next
        if ($LASTEXITCODE -ne 0) { throw 'Clock retained-input inventory failed.' }
        $candidate = $selection | ConvertFrom-Json
    }
    if ($null -eq $candidate) {
        $worker = Join-Path $PSScriptRoot 'targeted-pitcher-correction.py'
        $selection = & python -B $worker --state-root $script:StateRoot --next
        if ($LASTEXITCODE -ne 0) { throw 'P1 retained-input inventory failed.' }
        $candidate = $selection | ConvertFrom-Json
    }
    if ($null -eq $candidate) {
        $worker = Join-Path $PSScriptRoot 'targeted-runner-addition.py'
        $selection = & python -B $worker --state-root $script:StateRoot --next
        if ($LASTEXITCODE -ne 0) { throw 'R1 retained-input inventory failed.' }
        $candidate = $selection | ConvertFrom-Json
    }
    if ($null -eq $candidate) { return }
    $emptyGames = [System.IO.Path]::GetFileName($worker) -eq 'targeted-empty-game-addition.py'
    $batch = [Diagnostics.Stopwatch]::StartNew()
    $processed = 0
    # Keep the existing single-worker lease for a bounded batch. Otherwise a
    # long SQL build wins the slot after almost every individual repair.
    do {
        $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $candidate.gamePk -TimeoutSeconds 60
        try {
            if ($emptyGames) {
                & python -B $worker --state-root $script:StateRoot --game-pk $candidate.gamePk `
                    --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
                    --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
            }
            else {
                & python -B $worker --state-root $script:StateRoot --game-pk $candidate.gamePk `
                    --input $candidate.path --input-sha256 $candidate.sha256 `
                    --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
                    --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
            }
            if ($LASTEXITCODE -ne 0) {
                if (-not $emptyGames) { throw 'Targeted repair failed; terminal evidence records the bounded retry.' }
                Write-Warning 'Empty Games repair failed; its owner records and limits retries before selecting the next game.'
            }
            elseif ($emptyGames) {
                # Finish this game's dependent checks before the next repair,
                # with both the game lock and heavy-worker lease still held.
                $admissionJson = & python -B $admissionWorker --state-root $script:StateRoot --game-pk $candidate.gamePk `
                    --java (Get-JavaExecutable) --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
                if ($LASTEXITCODE -ne 0) { throw 'Post-repair admission refresh failed; preserve its recorded retry.' }
                $admissionJson
                $admission = $admissionJson | ConvertFrom-Json
                $outcomes = $admission.PSObject.Properties['outcomes']
                if ($null -ne $outcomes -and @($outcomes.Value.PSObject.Properties | Where-Object {
                        $_.Name -in @('waiting-for-memory', 'failed', 'partial-refreshed', 'refreshed') -and $_.Value -gt 0
                    }).Count -gt 0) { return }
            }
        }
        finally { $lock.Dispose() }
        $processed++
        if (-not $emptyGames -or $processed -ge 20 -or $batch.Elapsed.TotalSeconds -ge 600) { break }
        $selection = & python -B $worker --state-root $script:StateRoot --next
        if ($LASTEXITCODE -ne 0) { throw 'Empty Games repair inventory failed.' }
        $candidate = $selection | ConvertFrom-Json
    }
    while ($null -ne $candidate)
}
