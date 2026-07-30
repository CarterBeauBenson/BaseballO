Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:Versions = Import-PowerShellDataFile (Join-Path $script:RepositoryRoot 'infra\versions.psd1')

if ($env:BASEBALLO_LOCAL_ROOT) {
    $script:LocalRoot = [System.IO.Path]::GetFullPath($env:BASEBALLO_LOCAL_ROOT)
}
else {
    $script:LocalRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BaseballO'
}

$script:DownloadsRoot = Join-Path $script:LocalRoot 'downloads'
$script:RuntimesRoot = Join-Path $script:LocalRoot 'runtimes'
$script:StateRoot = Join-Path $script:LocalRoot 'state'
$script:JavaHome = Join-Path $script:RuntimesRoot $script:Versions.Java.InstallDirectory
$script:NiFiHome = Join-Path $script:RuntimesRoot $script:Versions.NiFi.InstallDirectory
$script:FusekiHome = Join-Path $script:RuntimesRoot $script:Versions.Fuseki.InstallDirectory
$script:RMLMapperHome = Join-Path $script:RuntimesRoot $script:Versions.RMLMapper.InstallDirectory
$script:RMLMapperJar = Join-Path $script:RMLMapperHome $script:Versions.RMLMapper.FileName
$script:NiFiState = Join-Path $script:StateRoot 'nifi'
$script:FusekiState = Join-Path $script:StateRoot 'fuseki'

function Initialize-LocalLayout {
    $paths = @(
        $script:DownloadsRoot,
        $script:RuntimesRoot,
        $script:StateRoot,
        $script:NiFiState,
        $script:FusekiState
    )
    foreach ($path in $paths) {
        [void](New-Item -ItemType Directory -Force -Path $path)
    }
}

function Get-JavaExecutable {
    $java = Join-Path $script:JavaHome 'bin\java.exe'
    if (-not (Test-Path -LiteralPath $java -PathType Leaf)) {
        throw "Java 21 is not installed at $java. Run scripts\infra\bootstrap.ps1 first."
    }
    return $java
}

function Get-RMLMapperJar {
    if (-not (Test-Path -LiteralPath $script:RMLMapperJar -PathType Leaf)) {
        throw "RMLMapper is not installed at $script:RMLMapperJar. Run scripts\infra\bootstrap.ps1 first."
    }
    return $script:RMLMapperJar
}

function ConvertTo-JavaPropertyPath([string] $Path) {
    return ([System.IO.Path]::GetFullPath($Path) -replace '\\', '/')
}

function Set-KeyValueProperty {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Key,
        [AllowEmptyString()][string] $Value
    )

    $lines = [System.Collections.Generic.List[string]](Get-Content -LiteralPath $Path)
    $prefix = "$Key="
    $found = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index].StartsWith($prefix, [System.StringComparison]::Ordinal)) {
            $lines[$index] = "$Key=$Value"
            $found = $true
            break
        }
    }
    if (-not $found) {
        $lines.Add("$Key=$Value")
    }
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string] $HostName,
        [Parameter(Mandatory = $true)][int] $Port,
        [int] $TimeoutMilliseconds = 1000
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne($TimeoutMilliseconds, $false)) {
            return $false
        }
        $client.EndConnect($result)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Wait-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string] $HostName,
        [Parameter(Mandatory = $true)][int] $Port,
        [Parameter(Mandatory = $true)][bool] $Open,
        [int] $TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ((Test-TcpPort -HostName $HostName -Port $Port) -eq $Open) {
            return $true
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Get-RandomSecret([int] $Bytes = 24) {
    $buffer = New-Object byte[] $Bytes
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($buffer)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($buffer)
}

function Set-JavaEnvironment {
    $env:JAVA_HOME = $script:JavaHome
    $env:PATH = "$(Join-Path $script:JavaHome 'bin');$env:PATH"
}
