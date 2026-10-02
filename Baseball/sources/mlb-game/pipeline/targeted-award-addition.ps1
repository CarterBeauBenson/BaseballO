[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-award-addition' -Action {
    $worker = Join-Path $PSScriptRoot 'targeted-award-addition.py'
    $selection = & python -B $worker --state-root $script:StateRoot --next
    if ($LASTEXITCODE -ne 0) { throw 'W1 retained-input inventory failed.' }
    $candidate = $selection | ConvertFrom-Json
    if ($null -eq $candidate) { return }
    $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $candidate.gamePk -TimeoutSeconds 60
    try {
        & python -B $worker --state-root $script:StateRoot --game-pk $candidate.gamePk `
            --input $candidate.path --input-sha256 $candidate.sha256 `
            --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
            --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
        if ($LASTEXITCODE -ne 0) { throw 'W1 failed; terminal evidence records the bounded retry.' }
    }
    finally { $lock.Dispose() }
}
