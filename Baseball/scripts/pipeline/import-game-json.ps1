[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $InputJson,
    [switch] $ArchiveOnly,
    [switch] $ForceRdfLoad
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

$inputPath = [System.IO.Path]::GetFullPath($InputJson)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "Input game JSON was not found: $inputPath"
}

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$rawRoot = Join-Path $pipelineRoot 'raw\games'
$manifestRoot = Join-Path $pipelineRoot 'manifests\imports\games'
$quarantineRoot = Join-Path $pipelineRoot 'quarantine\manual-import'
$runId = [Guid]::NewGuid().ToString('N')
$startedAt = [DateTime]::UtcNow
$runStamp = $startedAt.ToString('yyyyMMddTHHmmssfffZ')
$inputHashBefore = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$manifestSourceFileName = [System.IO.Path]::GetFileName($inputPath)
$gamePk = $null
$season = $null
$rawPath = $null
$manifestPath = $null
$archivedNew = $false

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] $Value,
        [Parameter(Mandatory = $true)][string] $Path
    )

    Write-AtomicJsonFile -Path $Path -Value $Value -Depth 12
}

function Test-GameGraphCurrent {
    param(
        [Parameter(Mandatory = $true)][string] $GamePkValue,
        [Parameter(Mandatory = $true)][string] $InputSha256
    )

    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
        return $false
    }
    $rmlManifestPath = Join-Path $pipelineRoot "manifests\game-$GamePkValue-rml.json"
    if (-not (Test-Path -LiteralPath $rmlManifestPath -PathType Leaf)) {
        return $false
    }
    try {
        $rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
        $mappingPath = Join-Path $script:RepositoryRoot 'sources\mlb-game\mapping\mlb-game.rml.ttl'
        $contextBuilderPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\prepare-rml-context.py'
        $mappingHash = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $contextBuilderHash = (Get-FileHash -LiteralPath $contextBuilderPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if (
            [string]$rmlManifest.inputSha256 -ne $InputSha256 -or
            [string]$rmlManifest.mappingSha256 -ne $mappingHash -or
            [string]$rmlManifest.contextBuilderSha256 -ne $contextBuilderHash -or
            [string]$rmlManifest.mapperVersion -ne [string]$script:Versions.RMLMapper.Version
        ) {
            return $false
        }
        $queryIndexManifestPath = Join-Path $pipelineRoot "manifests\game-$GamePkValue-query-index.json"
        if (-not (Test-Path -LiteralPath $queryIndexManifestPath -PathType Leaf)) {
            return $false
        }
        $queryIndexManifest = Get-Content -LiteralPath $queryIndexManifestPath -Raw | ConvertFrom-Json
        [void](Resolve-QueryIndexManifestAdmission -Manifest $queryIndexManifest)
        $sourceGraph = "https://w3id.org/baseball/graph/game/$GamePkValue"
        $indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePkValue"
        $expectedIndexPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "query-index\game-$GamePkValue.nt"))
        if (
            [string]$queryIndexManifest.sourceGraph -ne $sourceGraph -or
            [string]$queryIndexManifest.indexGraph -ne $indexGraph -or
            [string]$queryIndexManifest.sourceRdfSha256 -ne [string]$rmlManifest.outputSha256 -or
            [int64]$queryIndexManifest.sourceTripleCount -le 0 -or
            [int64]$queryIndexManifest.indexTripleCount -le 0 -or
            [string]::IsNullOrWhiteSpace([string]$queryIndexManifest.indexPath) -or
            [System.IO.Path]::GetFullPath([string]$queryIndexManifest.indexPath) -ne $expectedIndexPath -or
            -not (Test-Path -LiteralPath $expectedIndexPath -PathType Leaf) -or
            (Get-FileHash -LiteralPath $expectedIndexPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$queryIndexManifest.indexSha256
        ) {
            return $false
        }
    }
    catch {
        return $false
    }

    $graphIri = "https://w3id.org/baseball/graph/game/$GamePkValue"
    $indexGraphIri = "https://w3id.org/baseball/graph/query-index/game/$GamePkValue"
    $gameIri = "https://baseballontology.org/data/game/$GamePkValue"
    $indexResource = "https://w3id.org/baseball/query-index-build/game/$GamePkValue"
    $query = "SELECT ?sourceCount ?indexCount WHERE { { SELECT (COUNT(*) AS ?sourceCount) WHERE { GRAPH <$graphIri> { ?s ?p ?o } } } { SELECT (COUNT(*) AS ?indexCount) WHERE { GRAPH <$indexGraphIri> { ?is ?ip ?io } } } FILTER EXISTS { GRAPH <$graphIri> { <$gameIri> a <https://baseballontology.org/BaseballGame> } } FILTER EXISTS { GRAPH <$indexGraphIri> { <$indexResource> a <https://w3id.org/baseball/query-index/QueryIndex> ; <https://w3id.org/baseball/query-index/sourceGraph> <$graphIri> ; <https://w3id.org/baseball/query-index/indexedGame> <$gameIri> ; <https://w3id.org/baseball/query-index/contractVersion> '1' } } }"
    try {
        $result = Invoke-RestMethod -Uri 'http://127.0.0.1:3031/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
        $binding = @($result.results.bindings)[0]
        return (
            [int64]$binding.sourceCount.value -eq [int64]$queryIndexManifest.sourceTripleCount -and
            [int64]$binding.indexCount.value -eq [int64]$queryIndexManifest.indexTripleCount
        )
    }
    catch {
        return $false
    }
}

function Save-ByteIdenticalArchive {
    param(
        [Parameter(Mandatory = $true)][string] $Source,
        [Parameter(Mandatory = $true)][string] $DestinationDirectory,
        [Parameter(Mandatory = $true)][string] $Sha256
    )

    [void](New-Item -ItemType Directory -Force -Path $DestinationDirectory)
    $destination = Join-Path $DestinationDirectory "$Sha256.json"
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $existingHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingHash -ne $Sha256) {
            throw "Content-addressed archive collision at $destination"
        }
        return [PSCustomObject]@{ Path = $destination; ArchivedNew = $false }
    }

    $temporaryArchive = Join-Path $DestinationDirectory ".$runId.partial"
    Copy-Item -LiteralPath $Source -Destination $temporaryArchive
    $copiedHash = (Get-FileHash -LiteralPath $temporaryArchive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($copiedHash -ne $Sha256) {
        Remove-Item -LiteralPath $temporaryArchive -Force
        throw 'The archived copy is not byte-identical to the supplied JSON.'
    }
    Move-Item -LiteralPath $temporaryArchive -Destination $destination
    return [PSCustomObject]@{ Path = $destination; ArchivedNew = $true }
}

try {
    try {
        $document = Get-Content -LiteralPath $inputPath -Raw | ConvertFrom-Json
    }
    catch {
        throw "The supplied file is not valid JSON: $($_.Exception.Message)"
    }

    $gamePk = [string]$document.gamePk
    if ($gamePk -notmatch '^\d+$') {
        throw "The supplied JSON has no safe numeric gamePk: $gamePk"
    }
    $season = [string]$document.gameData.game.season
    if ($season -notmatch '^\d{4}$') {
        throw "Game $gamePk has no safe four-digit gameData.game.season value."
    }

    $archive = Save-ByteIdenticalArchive -Source $inputPath -DestinationDirectory (Join-Path (Join-Path $rawRoot $season) $gamePk) -Sha256 $inputHashBefore
    $rawPath = $archive.Path
    $archivedNew = $archive.ArchivedNew
    $manifestPath = Join-Path (Join-Path (Join-Path $manifestRoot $season) $gamePk) "$runStamp-$runId.json"
    $state = [string]$document.gameData.status.abstractGameState
    $status = $null
    $graphIri = $null

    if ($state -ne 'Final') {
        $status = 'archived-not-final'
    }
    elseif ($ArchiveOnly) {
        $status = 'archived-only'
    }
    elseif (-not $ForceRdfLoad -and -not $archivedNew -and (Test-GameGraphCurrent -GamePkValue $gamePk -InputSha256 $inputHashBefore)) {
        $status = 'unchanged-current-graph'
        $graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
    }
    else {
        & (Join-Path $PSScriptRoot 'run-rml.ps1') -InputJson $rawPath
        $rdfPath = Join-Path $pipelineRoot "rdf\game-$gamePk.ttl"
        & (Join-Path $PSScriptRoot 'load-game-graph.ps1') -RdfFile $rdfPath -GamePk $gamePk
        & (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $gamePk
        $status = 'loaded'
        $graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
    }

    $inputHashAfter = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($inputHashAfter -ne $inputHashBefore) {
        throw 'The supplied JSON changed during import.'
    }

    Write-JsonFile -Path $manifestPath -Value ([ordered]@{
        artifactType = 'game-json-manual-import'
        ingestionMode = 'manual-local-file'
        pipelineRunId = $runId
        gamePk = $gamePk
        season = $season
        sourceFileName = $manifestSourceFileName
        importedAtUtc = $startedAt.ToString('o')
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        contentSha256 = $inputHashBefore
        byteCount = (Get-Item -LiteralPath $rawPath).Length
        rawPath = $rawPath
        archivedNew = $archivedNew
        feedAbstractGameState = $state
        status = $status
        graphIri = $graphIri
    })

    Write-Host "Manual import status: $status"
    Write-Host "Raw archive: $rawPath"
    Write-Host "Import manifest: $manifestPath"
}
catch {
    $failureDirectory = Join-Path $quarantineRoot "$runStamp-$runId"
    [void](New-Item -ItemType Directory -Force -Path $failureDirectory)
    $quarantinedInput = Join-Path $failureDirectory 'input.json'
    Copy-Item -LiteralPath $inputPath -Destination $quarantinedInput
    Write-JsonFile -Path (Join-Path $failureDirectory 'failure.json') -Value ([ordered]@{
        pipeline = 'game-json-manual-import'
        pipelineRunId = $runId
        failedAtUtc = [DateTime]::UtcNow.ToString('o')
        error = $_.Exception.Message
        gamePk = $gamePk
        season = $season
        inputSha256 = $inputHashBefore
        rawPath = $rawPath
        importManifestPath = $manifestPath
        quarantinedInput = $quarantinedInput
    })
    throw "Manual game JSON import failed; the supplied bytes and failure metadata are quarantined at $failureDirectory`n$($_.Exception.Message)"
}
