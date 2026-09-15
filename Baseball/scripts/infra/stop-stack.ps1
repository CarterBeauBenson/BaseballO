[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'ensure-local-services.ps1') -Pause

& (Join-Path $PSScriptRoot 'stop-nifi.ps1')

& (Join-Path $PSScriptRoot 'stop-fuseki.ps1')
