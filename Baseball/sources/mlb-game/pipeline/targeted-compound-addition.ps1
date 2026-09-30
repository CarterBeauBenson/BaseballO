[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
$worker = Join-Path $PSScriptRoot 'targeted-compound-addition.py'
$selection = & python -B $worker --state-root $script:StateRoot --next
if ($LASTEXITCODE -ne 0) { throw 'K1 inventory failed.' }
$gamePk = $selection | ConvertFrom-Json
if ($null -eq $gamePk) { return }
$lock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $gamePk -TimeoutSeconds 60
try {
    & python -B $worker --state-root $script:StateRoot --game-pk $gamePk `
        --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
        --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
    if ($LASTEXITCODE -ne 0) { throw 'K1 failed; terminal evidence records the bounded retry.' }
}
finally { $lock.Dispose() }
