[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
$mapper = Get-RMLMapperJar
foreach ($gamePk in @('822846', '824467')) {
    $lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $gamePk -TimeoutSeconds 60
    try {
        & python -B (Join-Path $PSScriptRoot 'targeted-history-addition.py') --state-root $script:StateRoot `
            --game-pk $gamePk --java (Get-JavaExecutable) --mapper $mapper `
            --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
        if ($LASTEXITCODE -ne 0) { Write-Warning "Q7 game $gamePk failed; terminal evidence records the bounded retry." }
    }
    finally { $lock.Dispose() }
}
