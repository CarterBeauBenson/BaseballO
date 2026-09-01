[CmdletBinding()]
param([switch] $RunProof, [switch] $RunBackfill, [switch] $StartDaily)
try {
    & (Join-Path $PSScriptRoot '..\..\..\scripts\infra\provision-nifi-source.ps1') -ContractPath (Join-Path $PSScriptRoot 'flow-contract.json') -RunProof:$RunProof -RunBackfill:$RunBackfill -StartDaily:$StartDaily
}
catch {
    Write-Error $_
    exit 1
}
