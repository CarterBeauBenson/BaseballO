[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$launcher = Join-Path $PSScriptRoot 'launch-explorer.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Explorer launcher is missing: $launcher"
}

$shell = New-Object -ComObject WScript.Shell
$desktop = [string]$shell.SpecialFolders.Item('Desktop')
if (-not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw "Windows Desktop directory was not found: $desktop"
}

$shortcutPath = Join-Path $desktop 'BaseballO Explorer.lnk'
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $PSHOME 'powershell.exe'
$shortcut.Arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
$shortcut.WorkingDirectory = $script:RepositoryRoot
$shortcut.Description = 'Start BaseballO services and open the local Knowledge Graph Explorer'
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,14"
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "Installed BaseballO Explorer shortcut at $shortcutPath"
