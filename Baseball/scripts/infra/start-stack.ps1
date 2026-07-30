[CmdletBinding()]
param()

& (Join-Path $PSScriptRoot 'start-fuseki.ps1')

& (Join-Path $PSScriptRoot 'start-nifi.ps1')

Write-Host ''
Write-Host 'BaseballO development services are running.'
