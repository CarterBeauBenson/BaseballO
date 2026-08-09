[CmdletBinding()]
param()

Write-Warning 'configure-nifi-rdf-skeleton.ps1 is retained as a compatibility entry point; it now configures the real stopped shared RDF flow.'
& (Join-Path $PSScriptRoot 'configure-nifi-rdf-flow.ps1')
