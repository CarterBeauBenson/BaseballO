[CmdletBinding()]
param([switch] $Start)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
$control = Join-Path $script:StateRoot 'pipeline\control\mlb-game'
[void](New-Item -ItemType Directory -Force -Path $control)
$config = Join-Path $control 'compound-addition-worker.json'
@{
    group='MLB Game'; name='Add Approved K1 Compound Results'; period='1 min'
    timerEnabled=[bool]$Start
    workingDirectory=$repositoryRoot; python=(Get-Command powershell.exe).Source
    arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',
        (Join-Path $repositoryRoot 'sources\mlb-game\pipeline\targeted-compound-addition.ps1'))
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $config -Encoding UTF8
& python (Join-Path $repositoryRoot 'scripts\infra\nifi_worker.py') --config $config
if ($LASTEXITCODE -ne 0) { throw 'Targeted K1 worker deployment failed.' }
