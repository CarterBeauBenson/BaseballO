[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-foul-addition' -Action {
    $worker = Join-Path $PSScriptRoot 'targeted-foul-addition.py'
    $selection = & python -B $worker --state-root $script:StateRoot --next
    if ($LASTEXITCODE -ne 0) { throw 'Counted-foul repair inventory failed.' }
    $case = $selection | ConvertFrom-Json
    if ($null -eq $case) { return }
    $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $case.gamePk -TimeoutSeconds 60
    try {
        & python -B $worker --state-root $script:StateRoot --game-pk $case.gamePk `
            --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
            --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
        if ($LASTEXITCODE -ne 0) { throw 'Counted-foul repair failed; terminal evidence records the bounded retry.' }
    }
    finally { $lock.Dispose() }
}
