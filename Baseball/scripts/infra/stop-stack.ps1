[CmdletBinding()]
param()

& (Join-Path $PSScriptRoot 'stop-nifi.ps1')

& (Join-Path $PSScriptRoot 'stop-fuseki.ps1')
