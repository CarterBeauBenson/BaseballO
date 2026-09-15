[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
# Explicit startup ends maintenance without scheduling or running acquisition.
. (Join-Path $PSScriptRoot 'common.ps1')
$maintenancePath = Join-Path $script:StateRoot 'operations\maintenance.json'
Remove-Item -LiteralPath $maintenancePath -ErrorAction SilentlyContinue

& (Join-Path $PSScriptRoot 'start-fuseki.ps1')

& (Join-Path $PSScriptRoot 'start-nifi.ps1')

Write-Host ''
Write-Host 'BaseballO development services are running.'
