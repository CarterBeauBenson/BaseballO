[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-history-addition' -Action {
    $mapper = Get-RMLMapperJar
    $selection = & python -B (Join-Path $PSScriptRoot 'targeted-history-addition.py') --state-root $script:StateRoot --next
    if ($LASTEXITCODE -ne 0) { throw 'Q7 repair inventory failed.' }
    $gamePk = $selection | ConvertFrom-Json
    if ($null -ne $gamePk) {
        $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $gamePk -TimeoutSeconds 60
        try {
            & python -B (Join-Path $PSScriptRoot 'targeted-history-addition.py') --state-root $script:StateRoot `
                --game-pk $gamePk --java (Get-JavaExecutable) --mapper $mapper `
                --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
            if ($LASTEXITCODE -ne 0) { Write-Warning "Q7 game $gamePk failed; terminal evidence records the bounded retry." }
        }
        finally { $lock.Dispose() }
    }
}
