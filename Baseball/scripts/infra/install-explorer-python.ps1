[CmdletBinding()]
param()
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout
$release = $script:Versions.ExplorerPython
$installation = [IO.Path]::GetFullPath((Join-Path $script:RuntimesRoot $release.InstallDirectory))
$runtimePrefix = [IO.Path]::GetFullPath($script:RuntimesRoot).TrimEnd('\') + '\'
if (-not $installation.StartsWith($runtimePrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime destination escaped the runtime root.' }

function Test-ExplorerPython([string] $Directory) {
    $python = Join-Path $Directory 'python.exe'
    $observed = & $python -c 'import sys,rdflib,pyparsing,sqlite3; print(sys.version.split()[0], rdflib.__version__, pyparsing.__version__)'
    if ($LASTEXITCODE -ne 0 -or $observed -ne ($release.Version + ' ' + $release.Packages[0].Version + ' ' + $release.Packages[1].Version)) {
        throw 'Explorer Python or its libraries differ from their pins.'
    }
}
if (Test-Path -LiteralPath $installation) {
    Test-ExplorerPython $installation
    Write-Output 'Pinned Explorer Python is already installed and imports successfully.'
    return
}
$artifacts = @(@{ FileName = $release.ArchiveName; Url = $release.Url; Hash = $release.Hash }) + $release.Packages
foreach ($artifact in $artifacts) {
    $download = Join-Path $script:DownloadsRoot $artifact.FileName
    if (-not (Test-Path -LiteralPath $download -PathType Leaf)) {
        Invoke-WebRequest -UseBasicParsing -Uri $artifact.Url -OutFile $download -TimeoutSec 120
    }
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $artifact.Hash) {
        throw "Checksum mismatch for $($artifact.FileName); nothing was installed."
    }
}
$staging = [IO.Path]::GetFullPath((Join-Path $script:RuntimesRoot ($release.InstallDirectory + '.install-' + [Guid]::NewGuid().ToString('N'))))
if (-not $staging.StartsWith($runtimePrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Staging escaped the runtime root.' }
[void](New-Item -ItemType Directory -Path $staging)
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $script:DownloadsRoot $release.ArchiveName), $staging)
$libraries = Join-Path $staging 'Lib\site-packages'
[void](New-Item -ItemType Directory -Path $libraries -Force)
foreach ($package in $release.Packages) {
    [IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $script:DownloadsRoot $package.FileName), $libraries)
}
# Isolated import paths: no global packages, user site, PATH or pip mutation.
@('python313.zip', '.', 'Lib\site-packages') | Set-Content -LiteralPath (Join-Path $staging 'python313._pth') -Encoding ASCII
Test-ExplorerPython $staging
# Both absolute directory paths were checked against the intended runtime root.
Move-Item -LiteralPath $staging -Destination $installation
Write-Output ('Installed verified Explorer Python ' + $release.Version)
