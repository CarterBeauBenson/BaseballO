[CmdletBinding()]
param()
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout
$release = $script:Versions.Node
$runtimeRoot = Join-Path $script:LocalRoot 'runtimes'
$installation = Join-Path $runtimeRoot $release.InstallDirectory
$executable = Join-Path $installation 'node.exe'
if (Test-Path -LiteralPath $executable -PathType Leaf) {
    $observed = & $executable --version
    if ($LASTEXITCODE -ne 0 -or $observed -ne ('v' + $release.Version)) { throw 'Installed Explorer runtime differs from the pinned version.' }
    Write-Host "Explorer runtime already installed: $observed"
    exit 0
}
if (Test-Path -LiteralPath $installation) { throw 'An incomplete runtime installation exists; inspect it before retrying.' }
$archive = Join-Path (Join-Path $script:LocalRoot 'downloads') $release.ArchiveName
if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
    Invoke-WebRequest -UseBasicParsing -Uri $release.Url -OutFile $archive -TimeoutSec 120
}
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $release.Hash) {
    throw 'Explorer runtime archive checksum mismatch. Nothing was installed.'
}
Expand-Archive -LiteralPath $archive -DestinationPath $runtimeRoot
$observed = & $executable --version
if ($LASTEXITCODE -ne 0 -or $observed -ne ('v' + $release.Version)) { throw 'Extracted Explorer runtime failed its version check.' }
Write-Host "Verified and installed Explorer runtime: $observed"
