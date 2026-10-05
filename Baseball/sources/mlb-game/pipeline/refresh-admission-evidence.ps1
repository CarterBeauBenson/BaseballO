[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
# Targeted repairs also refresh these evidence files before retiring inputs.
# Share their existing lease so two writers cannot overwrite one proof set.
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'admission-evidence' -Action {
    & python -B (Join-Path $PSScriptRoot 'admission-evidence-queue.py') --state-root $script:StateRoot `
        --java (Get-JavaExecutable) --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
    if ($LASTEXITCODE -ne 0) { throw 'Admission evidence maintenance failed.' }
}
