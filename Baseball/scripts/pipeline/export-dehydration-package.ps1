[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $GamePk,
    [Parameter(Mandatory = $true)][string] $PackageDirectory,
    [switch] $AllowDirtyRepository
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if ($GamePk -notmatch '^\d+$') {
    throw "GamePk must contain only digits: $GamePk"
}
$packageRoot = [System.IO.Path]::GetFullPath($PackageDirectory)
if (Test-Path -LiteralPath $packageRoot) {
    throw "PackageDirectory already exists; choose a new path: $packageRoot"
}
[void](New-Item -ItemType Directory -Path $packageRoot)

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$rmlManifestPath = Join-Path $pipelineRoot "manifests\game-$GamePk-rml.json"
$indexManifestPath = Join-Path $pipelineRoot "manifests\game-$GamePk-query-index.json"
foreach ($required in @($rmlManifestPath, $indexManifestPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required local build manifest is missing: $required"
    }
}
$rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
$indexManifest = Get-Content -LiteralPath $indexManifestPath -Raw | ConvertFrom-Json
if ([string]$rmlManifest.gamePk -ne $GamePk -or [string]$indexManifest.gamePk -ne $GamePk) {
    throw 'Build manifest gamePk does not match the requested package.'
}
if ([string]$indexManifest.contractSha256 -ne (Get-QueryIndexContractHash)) {
    throw 'Refusing to package a stale query-index generation contract.'
}

$rawPath = [System.IO.Path]::GetFullPath([string]$rmlManifest.inputPath)
$authoritativeRdfPath = [System.IO.Path]::GetFullPath([string]$rmlManifest.outputPath)
$indexRdfPath = [System.IO.Path]::GetFullPath([string]$indexManifest.indexPath)
foreach ($required in @($rawPath, $authoritativeRdfPath, $indexRdfPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required package artifact is missing: $required"
    }
}
if ((Get-FileHash -LiteralPath $rawPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$rmlManifest.inputSha256) {
    throw 'Raw archive hash differs from the RML build manifest.'
}
if ((Get-FileHash -LiteralPath $authoritativeRdfPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$rmlManifest.outputSha256) {
    throw 'Authoritative RDF hash differs from the RML build manifest.'
}
if ((Get-FileHash -LiteralPath $indexRdfPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$indexManifest.indexSha256) {
    throw 'Query-index RDF hash differs from the index build manifest.'
}
if ([string]$indexManifest.sourceRdfSha256 -ne [string]$rmlManifest.outputSha256) {
    throw 'Query-index source hash does not match the authoritative RDF hash.'
}

$repositoryPrefix = [System.IO.Path]::GetFullPath($script:RepositoryRoot).TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar
function Get-RepositoryRelativePath {
    param([Parameter(Mandatory = $true)][string] $Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Contract file is outside the repository: $fullPath"
    }
    return $fullPath.Substring($repositoryPrefix.Length) -replace '\\', '/'
}

$fileRecords = New-Object System.Collections.Generic.List[object]
$destinations = @{}
function Add-PackageFile {
    param(
        [Parameter(Mandatory = $true)][string] $Source,
        [Parameter(Mandatory = $true)][string] $RelativeDestination,
        [Parameter(Mandatory = $true)][string] $Role
    )
    $normalized = $RelativeDestination -replace '\\', '/'
    if ($normalized.StartsWith('/') -or $normalized -match '(^|/)\.\.(/|$)') {
        throw "Unsafe package destination: $normalized"
    }
    if ($destinations.ContainsKey($normalized)) {
        return
    }
    $sourcePath = [System.IO.Path]::GetFullPath($Source)
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Package source file is missing: $sourcePath"
    }
    $destination = Join-Path $packageRoot ($normalized -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination))
    Copy-Item -LiteralPath $sourcePath -Destination $destination
    $fileRecords.Add([ordered]@{
        path = $normalized
        role = $Role
        bytes = (Get-Item -LiteralPath $destination).Length
        sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    })
    $destinations[$normalized] = $true
}

Add-PackageFile -Source $rawPath -RelativeDestination "raw/game-$GamePk.json" -Role 'raw-source'
Add-PackageFile -Source $authoritativeRdfPath -RelativeDestination "rdf/authoritative-game-$GamePk.ttl" -Role 'authoritative-rdf'
Add-PackageFile -Source $indexRdfPath -RelativeDestination "rdf/query-index-game-$GamePk.nt" -Role 'query-index-rdf'
Add-PackageFile -Source $rmlManifestPath -RelativeDestination 'provenance/rml-build-manifest.json' -Role 'rml-build-manifest'
Add-PackageFile -Source $indexManifestPath -RelativeDestination 'provenance/query-index-build-manifest.json' -Role 'query-index-build-manifest'

$repositoryContractFiles = @(
    (Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl'),
    (Join-Path $script:RepositoryRoot 'mappings\direct\validate_direct_mapping.py'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\run-rml.ps1'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\prepare-rml-context.py'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-generated-rdf.py'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\export-dehydration-package.ps1'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\restore-dehydration-package.ps1'),
    (Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-dehydration-package.py'),
    (Join-Path $script:RepositoryRoot 'scripts\infra\common.ps1'),
    (Join-Path $script:RepositoryRoot 'infra\versions.psd1'),
    (Join-Path $script:RepositoryRoot 'requirements-dev.txt')
) + @(Get-QueryIndexContractFiles | ForEach-Object { $_.FullName })
foreach ($contractFile in @($repositoryContractFiles | Sort-Object -Unique)) {
    $relative = Get-RepositoryRelativePath -Path $contractFile
    Add-PackageFile -Source $contractFile -RelativeDestination "contracts/repository/$relative" -Role 'repository-contract'
}

$safeDirectory = $script:RepositoryRoot -replace '\\', '/'
$repositoryCommit = (& git -c "safe.directory=$safeDirectory" -C $script:RepositoryRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $repositoryCommit -notmatch '^[0-9a-f]{40}$') {
    throw 'Could not identify the repository commit for the package manifest.'
}
$repositoryStatus = @(& git -c "safe.directory=$safeDirectory" -C $script:RepositoryRoot status --porcelain -- Baseball)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not inspect the repository state for the package manifest.'
}
$repositoryTreeState = if ($repositoryStatus.Count -eq 0) { 'clean' } else { 'dirty' }
if ($repositoryTreeState -ne 'clean' -and -not $AllowDirtyRepository) {
    throw 'Refusing to export a package from a dirty Baseball repository tree. Commit or stash changes first.'
}

$manifest = [ordered]@{
    artifactType = 'baseball-dehydration-package'
    packageVersion = 1
    gamePk = $GamePk
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
    repositoryCommit = $repositoryCommit
    repositoryTreeState = $repositoryTreeState
    rawSource = [ordered]@{
        path = "raw/game-$GamePk.json"
        sha256 = [string]$rmlManifest.inputSha256
    }
    authoritativeGraph = [ordered]@{
        graphIri = [string]$rmlManifest.graphIri
        path = "rdf/authoritative-game-$GamePk.ttl"
        sha256 = [string]$rmlManifest.outputSha256
        tripleCount = [int64]$indexManifest.sourceTripleCount
    }
    queryIndexGraph = [ordered]@{
        graphIri = [string]$indexManifest.indexGraph
        path = "rdf/query-index-game-$GamePk.nt"
        sha256 = [string]$indexManifest.indexSha256
        tripleCount = [int64]$indexManifest.indexTripleCount
        contractVersion = [int]$indexManifest.contractVersion
        contractSha256 = [string]$indexManifest.contractSha256
    }
    generation = [ordered]@{
        mapperVersion = [string]$rmlManifest.mapperVersion
        mappingSha256 = [string]$rmlManifest.mappingSha256
        effectiveMappingSha256 = [string]$rmlManifest.effectiveMappingSha256
        contextBuilderSha256 = [string]$rmlManifest.contextBuilderSha256
        executionContextSha256 = [string]$rmlManifest.executionContextSha256
    }
    rehydrationOrder = @(
        'validate every packaged file against manifest.json',
        'load the authoritative RDF into authoritativeGraph.graphIri',
        'load the query-index RDF into queryIndexGraph.graphIri',
        'verify both graph counts and the query-index metadata resource'
    )
    files = @($fileRecords | Sort-Object { $_.path })
}
$manifestPath = Join-Path $packageRoot 'manifest.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 12) + "`n"), $utf8)

$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-dehydration-package.py'
& python $validatorPath $packageRoot
if ($LASTEXITCODE -ne 0) {
    throw "Dehydration package validation failed: $packageRoot"
}

Write-Host "Dehydration package: $packageRoot"
Write-Host "Raw SHA-256: $($rmlManifest.inputSha256)"
Write-Host "Authoritative triples: $($indexManifest.sourceTripleCount); query-index triples: $($indexManifest.indexTripleCount)"
