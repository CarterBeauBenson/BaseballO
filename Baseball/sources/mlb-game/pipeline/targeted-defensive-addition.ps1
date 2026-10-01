[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-defensive-addition' -Action {
    $worker = Join-Path $PSScriptRoot 'targeted-defensive-addition.py'
    $selection = & python -B $worker --state-root $script:StateRoot --next
    if ($LASTEXITCODE -ne 0) { throw 'D1 retained-input inventory failed.' }
    $witness = $selection | ConvertFrom-Json
    if ($null -eq $witness) { return }
    $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $witness.gamePk -TimeoutSeconds 60
    try {
        & python -B $worker --state-root $script:StateRoot --source $witness.path `
            --game-pk $witness.gamePk --source-sha256 $witness.sha256 `
            --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
            --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
        if ($LASTEXITCODE -ne 0) { throw 'D1 failed; terminal evidence records the bounded retry.' }
    }
    finally { $lock.Dispose() }
}
