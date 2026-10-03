[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'repair-budget.ps1')
# Discovery and reuse of already verified evidence do not allocate a JVM.
# The Python owner retains the full 1 GiB requirement before mapping/SHACL,
# acquires each game's lock, and yields after ten cases or 45 seconds.
Invoke-MlbRepairBudget -StateRoot $script:StateRoot -Worker 'targeted-history-addition' -RequiredMemoryBytes 256MB -Action {
    $mapper = Get-RMLMapperJar
    & python -B (Join-Path $PSScriptRoot 'targeted-history-addition.py') --state-root $script:StateRoot `
        --drain --java (Get-JavaExecutable) --mapper $mapper `
        --jena-classpath (Join-Path $script:FusekiHome 'fuseki-server.jar')
    if ($LASTEXITCODE -ne 0) { throw 'Q7 bounded repair tick failed; retained terminal evidence is available.' }
}
