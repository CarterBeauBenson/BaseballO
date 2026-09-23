[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
if (-not $script:RdfStorageAvailable) { throw $script:RdfStorageError }
$root = Join-Path $script:StateRoot 'recovery'
[void](New-Item -ItemType Directory -Force -Path $root)
$settings = Join-Path $root 'settings.json'
@{
    stateRoot=$script:StateRoot;server=$script:FusekiBaseUri;dataset='baseball-dev'
    backups=(Join-Path $script:FusekiState 'backups')
    exportDirectory=(Join-Path $root 'exports')
    restoreRoot=(Join-Path (Split-Path -Parent $script:FusekiState) 'recovery-proofs')
    java=(Get-JavaExecutable);jena=(Join-Path $script:FusekiHome 'fuseki-server.jar')
    reserveBytes=20GB
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $settings -Encoding UTF8
$worker = Join-Path $root 'worker.json'
@{
    group='RDF Recovery';createGroup=$true;name='Advance RDF Recovery';period='15 min';x=1500;y=1000
    workingDirectory=$repositoryRoot;python=(Get-Command python).Source
    arguments=@('-B',(Join-Path $repositoryRoot 'scripts\pipeline\recovery_tick.py'),'--config',$settings)
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $worker -Encoding UTF8
& python (Join-Path $repositoryRoot 'scripts\infra\nifi_worker.py') --config $worker
if ($LASTEXITCODE -ne 0) { throw 'RDF recovery worker deployment failed.' }
