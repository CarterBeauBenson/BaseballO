[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-defensive-addition' -Action {
    $worker = Join-Path $PSScriptRoot 'targeted-defensive-addition.py'
    & python -B $worker --state-root $script:StateRoot --drain `
        --java (Get-JavaExecutable) --mapper (Get-RMLMapperJar) `
        --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
    if ($LASTEXITCODE -ne 0) { throw 'D1 bounded repair tick failed; terminal evidence records the failure.' }
}
