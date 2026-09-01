Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'canonical-text.ps1')

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
$script:StorageConfigPath = Join-Path $script:StateRoot 'storage.json'
$script:JavaHome = Join-Path $script:RuntimesRoot $script:Versions.Java.InstallDirectory
$script:NiFiHome = Join-Path $script:RuntimesRoot $script:Versions.NiFi.InstallDirectory
$script:FusekiHome = Join-Path $script:RuntimesRoot $script:Versions.Fuseki.InstallDirectory
$script:RMLMapperHome = Join-Path $script:RuntimesRoot $script:Versions.RMLMapper.InstallDirectory
$script:RMLMapperJar = Join-Path $script:RMLMapperHome $script:Versions.RMLMapper.FileName
$script:NiFiState = Join-Path $script:StateRoot 'nifi'
$script:FusekiState = Join-Path $script:StateRoot 'fuseki'
$script:RdfStorageMode = 'local'
$script:RdfStorageAvailable = $true
$script:RdfStorageError = $null

if (Test-Path -LiteralPath $script:StorageConfigPath -PathType Leaf) {
    $storageConfig = Get-Content -LiteralPath $script:StorageConfigPath -Raw | ConvertFrom-Json
    if (
        [string]$storageConfig.artifactType -ne 'baseballo-local-storage-config' -or
        [int]$storageConfig.contractVersion -ne 1 -or
        [string]$storageConfig.rdfStorage.mode -ne 'external'
    ) {
        throw "Unsupported BaseballO storage configuration: $script:StorageConfigPath"
    }
    $configuredRoot = [string]$storageConfig.rdfStorage.root
    $configuredMarkerId = [string]$storageConfig.rdfStorage.markerId
    if (
        [string]::IsNullOrWhiteSpace($configuredRoot) -or
        -not [System.IO.Path]::IsPathRooted($configuredRoot) -or
        [string]::IsNullOrWhiteSpace($configuredMarkerId)
    ) {
        throw "BaseballO storage configuration has an invalid external RDF root or marker."
    }
    $externalRdfRoot = [System.IO.Path]::GetFullPath($configuredRoot)
    $externalMarkerPath = Join-Path $externalRdfRoot '.baseballo-rdf-storage.json'
    $script:RdfStorageMode = 'external'
    $script:FusekiState = Join-Path $externalRdfRoot 'fuseki'
    if (-not (Test-Path -LiteralPath $externalMarkerPath -PathType Leaf)) {
        $script:RdfStorageAvailable = $false
        $script:RdfStorageError = "Configured external RDF storage is unavailable or is the wrong volume: $externalRdfRoot"
    }
    else {
        try {
            $externalMarker = Get-Content -LiteralPath $externalMarkerPath -Raw | ConvertFrom-Json
            if (
                [string]$externalMarker.artifactType -ne 'baseballo-external-rdf-storage-marker' -or
                [int]$externalMarker.contractVersion -ne 1 -or
                [string]$externalMarker.storageId -ne $configuredMarkerId
            ) {
                $script:RdfStorageAvailable = $false
                $script:RdfStorageError = "Configured external RDF storage marker does not match: $externalMarkerPath"
            }
        }
        catch {
            $script:RdfStorageAvailable = $false
            $script:RdfStorageError = "Configured external RDF storage marker cannot be read: $externalMarkerPath"
        }
    }
}
$script:FusekiPort = 3031
$script:FusekiBaseUri = "http://127.0.0.1:$($script:FusekiPort)"
$script:FusekiDatasetUri = "$($script:FusekiBaseUri)/baseball-dev"
$script:NiFiPort = 8080
$script:NiFiBaseUri = "http://127.0.0.1:$($script:NiFiPort)"
$script:NiFiApiUri = "$($script:NiFiBaseUri)/nifi-api"
$script:NiFiRootProcessGroupName = 'BaseballO'
$script:MlbGameProcessGroupName = 'MLB Game'

function Initialize-LocalLayout {
    if (-not $script:RdfStorageAvailable) {
        throw $script:RdfStorageError
    }
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

function Enter-FusekiWriteLock {
    param(
        [int] $TimeoutSeconds = 7200,
        [int] $RetryMilliseconds = 250
    )

    if ($TimeoutSeconds -le 0 -or $RetryMilliseconds -le 0) {
        throw 'Fuseki write-lock timeout and retry interval must be positive.'
    }
    $lockRoot = Join-Path $script:StateRoot 'pipeline\work\fuseki-locks'
    [void](New-Item -ItemType Directory -Force -Path $lockRoot)
    $lockPath = Join-Path $lockRoot 'baseball-dev.write.lock'
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $stream = [System.IO.File]::Open(
                $lockPath,
                [System.IO.FileMode]::OpenOrCreate,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            if ($stream.Length -eq 0) {
                $stream.WriteByte(0)
                $stream.Flush()
            }
            return $stream
        }
        catch [System.IO.IOException] {
            Start-Sleep -Milliseconds $RetryMilliseconds
        }
        catch [System.UnauthorizedAccessException] {
            Start-Sleep -Milliseconds $RetryMilliseconds
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for the process-wide Fuseki write lock: $lockPath"
}

function Exit-FusekiWriteLock {
    param([Parameter(Mandatory = $true)] $LockHandle)
    $LockHandle.Dispose()
}

function Assert-RdfStorageAvailable {
    if (-not $script:RdfStorageAvailable) {
        throw $script:RdfStorageError
    }
}

function Test-BaseballFusekiService {
    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:FusekiPort)) {
        return $false
    }
    try {
        $response = Invoke-RestMethod -Uri "$($script:FusekiDatasetUri)/query" -Method Post -Body @{ query = 'ASK { }' } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 5
        return $response.boolean -eq $true
    }
    catch {
        return $false
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

function Write-AtomicJsonFile {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)] $Value,
        [ValidateRange(2, 64)][int] $Depth = 16
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $directory = Split-Path -Parent $fullPath
    [void](New-Item -ItemType Directory -Force -Path $directory)
    $temporary = Join-Path $directory ".$([System.IO.Path]::GetFileName($fullPath)).$([Guid]::NewGuid().ToString('N')).partial"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    try {
        [System.IO.File]::WriteAllText(
            $temporary,
            (($Value | ConvertTo-Json -Depth $Depth) + "`n"),
            $utf8
        )
        Move-Item -LiteralPath $temporary -Destination $fullPath -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Set-JavaEnvironment {
    $env:JAVA_HOME = $script:JavaHome
    $env:PATH = "$(Join-Path $script:JavaHome 'bin');$env:PATH"
}
