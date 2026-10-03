[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
$control = Join-Path $script:StateRoot 'pipeline\control\mlb-game'
[void](New-Item -ItemType Directory -Force -Path $control)
$config = Join-Path $control 'admission-worker.json'
@{
    group='MLB Game'; name='Refresh Admission Evidence'; period='1 min'
    workingDirectory=$repositoryRoot; python=(Get-Command powershell.exe).Source
    arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',
        (Join-Path $repositoryRoot 'sources\mlb-game\pipeline\refresh-admission-evidence.ps1'))
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $config -Encoding UTF8
& python (Join-Path $repositoryRoot 'scripts\infra\nifi_worker.py') --config $config
if ($LASTEXITCODE -ne 0) { throw 'Admission evidence worker deployment failed.' }
