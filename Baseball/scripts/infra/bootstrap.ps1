[CmdletBinding()]
param(
    [switch] $SkipJava,
    [switch] $SkipNiFi,
    [switch] $SkipFuseki,
    [switch] $SkipRMLMapper
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

function Install-VerifiedArchive {
    param([Parameter(Mandatory = $true)][hashtable] $Package)

    $destination = Join-Path $script:RuntimesRoot $Package.InstallDirectory
    if (Test-Path -LiteralPath $destination -PathType Container) {
        Write-Host "$($Package.InstallDirectory) is already installed."
        return
    }

    $archive = Join-Path $script:DownloadsRoot $Package.ArchiveName
    $expectedHash = $Package.Hash.ToLowerInvariant()
    if (Test-Path -LiteralPath $archive -PathType Leaf) {
        Write-Host "Verifying cached $($Package.ArchiveName)..."
        $cachedHash = (Get-FileHash -LiteralPath $archive -Algorithm $Package.HashAlgorithm).Hash.ToLowerInvariant()
        if ($cachedHash -ne $expectedHash) {
            Write-Warning "Discarding an incomplete or invalid cached archive: $archive"
            Remove-Item -LiteralPath $archive -Force
        }
    }

    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
        $partial = "$archive.partial"
        if (Test-Path -LiteralPath $partial) {
            Remove-Item -LiteralPath $partial -Force
        }
        try {
            Write-Host "Downloading $($Package.ArchiveName)..."
            $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($null -ne $curl) {
                & $curl.Source --fail --location --silent --show-error --retry 3 --retry-all-errors --connect-timeout 30 --output $partial $Package.Url
                if ($LASTEXITCODE -ne 0) {
                    throw "curl.exe failed to download $($Package.Url)."
                }
            }
            else {
                Invoke-WebRequest -Uri $Package.Url -OutFile $partial -UseBasicParsing
            }
            Write-Host "Verifying $($Package.HashAlgorithm) checksum..."
            $actualHash = (Get-FileHash -LiteralPath $partial -Algorithm $Package.HashAlgorithm).Hash.ToLowerInvariant()
            if ($actualHash -ne $expectedHash) {
                throw "Checksum mismatch for $partial. Expected $expectedHash; got $actualHash."
            }
            Move-Item -LiteralPath $partial -Destination $archive
        }
        finally {
            if (Test-Path -LiteralPath $partial) {
                Remove-Item -LiteralPath $partial -Force
            }
        }
    }

    $staging = Join-Path $script:RuntimesRoot ('.extract-' + [Guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $staging)
    try {
        Write-Host "Extracting $($Package.ArchiveName)..."
        Expand-Archive -LiteralPath $archive -DestinationPath $staging
        $archiveRoot = Join-Path $staging $Package.ArchiveRoot
        if (-not (Test-Path -LiteralPath $archiveRoot -PathType Container)) {
            throw "Archive did not contain the expected root directory $($Package.ArchiveRoot)."
        }
        Move-Item -LiteralPath $archiveRoot -Destination $destination
    }
    finally {
        if (Test-Path -LiteralPath $staging) {
            Remove-Item -LiteralPath $staging -Recurse -Force
        }
    }
}

function Install-VerifiedFile {
    param([Parameter(Mandatory = $true)][hashtable] $Package)

    $destinationDirectory = Join-Path $script:RuntimesRoot $Package.InstallDirectory
    $destination = Join-Path $destinationDirectory $Package.FileName
    $expectedHash = $Package.Hash.ToLowerInvariant()
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $installedHash = (Get-FileHash -LiteralPath $destination -Algorithm $Package.HashAlgorithm).Hash.ToLowerInvariant()
        if ($installedHash -eq $expectedHash) {
            Write-Host "$($Package.FileName) is already installed."
            return
        }
        throw "Installed file failed checksum verification: $destination"
    }

    [void](New-Item -ItemType Directory -Force -Path $destinationDirectory)
    $partial = "$destination.partial"
    if (Test-Path -LiteralPath $partial) {
        Remove-Item -LiteralPath $partial -Force
    }
    try {
        Write-Host "Downloading $($Package.FileName)..."
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($null -ne $curl) {
            & $curl.Source --fail --location --silent --show-error --retry 3 --retry-all-errors --connect-timeout 30 --output $partial $Package.Url
            if ($LASTEXITCODE -ne 0) {
                throw "curl.exe failed to download $($Package.Url)."
            }
        }
        else {
            Invoke-WebRequest -Uri $Package.Url -OutFile $partial -UseBasicParsing
        }
        Write-Host "Verifying $($Package.HashAlgorithm) checksum..."
        $actualHash = (Get-FileHash -LiteralPath $partial -Algorithm $Package.HashAlgorithm).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            throw "Checksum mismatch for $partial. Expected $expectedHash; got $actualHash."
        }
        Move-Item -LiteralPath $partial -Destination $destination
    }
    finally {
        if (Test-Path -LiteralPath $partial) {
            Remove-Item -LiteralPath $partial -Force
        }
    }
}

function Configure-NiFi {
    $properties = Join-Path $script:NiFiHome 'conf\nifi.properties'
    $bootstrap = Join-Path $script:NiFiHome 'conf\bootstrap.conf'
    if (-not (Test-Path -LiteralPath $properties -PathType Leaf)) {
        throw "NiFi properties were not found at $properties."
    }

    $directories = @(
        (Join-Path $script:NiFiState 'flow'),
        (Join-Path $script:NiFiState 'flow-archive'),
        (Join-Path $script:NiFiState 'database_repository'),
        (Join-Path $script:NiFiState 'flowfile_repository'),
        (Join-Path $script:NiFiState 'content_repository'),
        (Join-Path $script:NiFiState 'provenance_repository'),
        (Join-Path $script:NiFiState 'local-state'),
        (Join-Path $script:NiFiState 'secrets')
    )
    foreach ($directory in $directories) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }

    $settings = [ordered]@{
        'nifi.flow.configuration.file'                 = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'flow\flow.json.gz')
        'nifi.flow.configuration.archive.dir'          = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'flow-archive')
        'nifi.database.directory'                      = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'database_repository')
        'nifi.flowfile.repository.directory'           = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'flowfile_repository')
        'nifi.content.repository.directory.default'    = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'content_repository')
        'nifi.provenance.repository.directory.default' = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'provenance_repository')
        'nifi.provenance.repository.max.storage.size'  = '2 GB'
        'nifi.web.http.host'                           = '127.0.0.1'
        'nifi.web.http.port'                           = '8080'
        'nifi.web.https.host'                          = ''
        'nifi.web.https.port'                          = ''
        'nifi.web.proxy.host'                          = 'localhost:8080,127.0.0.1:8080'
        'nifi.remote.input.secure'                     = 'false'
        'nifi.cluster.is.node'                         = 'false'
    }
    foreach ($entry in $settings.GetEnumerator()) {
        Set-KeyValueProperty -Path $properties -Key $entry.Key -Value $entry.Value
    }

    $sensitiveKeyFile = Join-Path $script:NiFiState 'secrets\sensitive-properties-key.txt'
    if (-not (Test-Path -LiteralPath $sensitiveKeyFile -PathType Leaf)) {
        Set-Content -LiteralPath $sensitiveKeyFile -Value (Get-RandomSecret 32) -Encoding ASCII -NoNewline
    }
    $sensitiveKey = (Get-Content -LiteralPath $sensitiveKeyFile -Raw).Trim()
    Set-KeyValueProperty -Path $properties -Key 'nifi.sensitive.props.key' -Value $sensitiveKey

    if (Test-Path -LiteralPath $bootstrap -PathType Leaf) {
        Set-KeyValueProperty -Path $bootstrap -Key 'java.arg.2' -Value '-Xms512m'
        Set-KeyValueProperty -Path $bootstrap -Key 'java.arg.3' -Value '-Xmx1g'
    }

    $stateManagement = Join-Path $script:NiFiHome 'conf\state-management.xml'
    if (Test-Path -LiteralPath $stateManagement -PathType Leaf) {
        [xml]$stateDocument = Get-Content -LiteralPath $stateManagement -Raw
        $localProvider = @($stateDocument.stateManagement.'local-provider' | Where-Object { $_.id -eq 'local-provider' }) | Select-Object -First 1
        if ($null -eq $localProvider) {
            throw 'NiFi local state provider was not found.'
        }
        $directoryProperty = @($localProvider.property | Where-Object { $_.name -eq 'Directory' }) | Select-Object -First 1
        if ($null -eq $directoryProperty) {
            throw 'NiFi local state provider has no Directory property.'
        }
        $directoryProperty.InnerText = ConvertTo-JavaPropertyPath (Join-Path $script:NiFiState 'local-state')
        $stateDocument.Save($stateManagement)
    }

    # NiFi is bound only to loopback and uses local HTTP so routine automation
    # does not depend on generated single-user credentials.
}

function Configure-Fuseki {
    $directories = @(
        (Join-Path $script:FusekiState 'configuration'),
        (Join-Path $script:FusekiState 'databases\baseball-dev'),
        (Join-Path $script:FusekiState 'logs'),
        (Join-Path $script:FusekiState 'backups')
    )
    foreach ($directory in $directories) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }
    Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'infra\fuseki\configuration\baseball-dev.ttl') -Destination (Join-Path $script:FusekiState 'configuration\baseball-dev.ttl') -Force
}

function Configure-PipelineStorage {
    $pipelineRoot = Join-Path $script:StateRoot 'pipeline'
    $directories = @(
        (Join-Path $pipelineRoot 'transient\mlb-game'),
        (Join-Path $pipelineRoot 'work\mlb-game'),
        (Join-Path $pipelineRoot 'rdf'),
        (Join-Path $pipelineRoot 'manifests'),
        (Join-Path $pipelineRoot 'evidence\mlb-game'),
        (Join-Path $pipelineRoot 'quarantine\mlb-game')
    )
    foreach ($directory in $directories) {
        [void](New-Item -ItemType Directory -Force -Path $directory)
    }
}

if (-not $SkipJava) {
    Install-VerifiedArchive -Package $script:Versions.Java
}
if (-not $SkipNiFi) {
    Install-VerifiedArchive -Package $script:Versions.NiFi
    Configure-NiFi
}
if (-not $SkipFuseki) {
    Install-VerifiedArchive -Package $script:Versions.Fuseki
    Configure-Fuseki
}
if (-not $SkipRMLMapper) {
    Install-VerifiedFile -Package $script:Versions.RMLMapper
}
Configure-PipelineStorage

Write-Host ''
Write-Host "BaseballO local stack bootstrapped under $script:LocalRoot"
Write-Host 'Next: .\scripts\infra\start-stack.ps1'
