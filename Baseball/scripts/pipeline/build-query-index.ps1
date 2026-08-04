[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $GamePk,
    [string] $ComponentRoot
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if ($GamePk -notmatch '^\d+$') {
    throw "GamePk must contain only digits: $GamePk"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}

$sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
$indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
$gameIri = "https://baseballontology.org/data/game/$GamePk"
$indexResource = "https://w3id.org/baseball/query-index-build/game/$GamePk"
$queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
$indexDataEndpoint = "http://127.0.0.1:3030/baseball-dev/data?graph=$([Uri]::EscapeDataString($indexGraph))"
$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$indexRoot = Join-Path $pipelineRoot 'query-index'
$manifestRoot = Join-Path $pipelineRoot 'manifests'
$runId = [Guid]::NewGuid().ToString('N')
$workRoot = Join-Path $indexRoot "work\$runId"
$componentOutputRoot = Join-Path $workRoot 'components'
$compiledPath = Join-Path $workRoot "game-$GamePk.nt"
$statsPath = Join-Path $workRoot "game-$GamePk-stats.json"
$finalPath = Join-Path $indexRoot "game-$GamePk.nt"
$manifestPath = Join-Path $manifestRoot "game-$GamePk-query-index.json"
$canonicalComponentRoot = [System.IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot 'sparql\query-index\components'))
if ([string]::IsNullOrWhiteSpace($ComponentRoot)) {
    $componentRoot = $canonicalComponentRoot
}
else {
    $componentRoot = [System.IO.Path]::GetFullPath($ComponentRoot)
}
$usesCanonicalComponents = $componentRoot.Equals($canonicalComponentRoot, [System.StringComparison]::OrdinalIgnoreCase)
$compilerPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\compile-query-index.py'
$contractHash = Get-QueryIndexContractHash

$sourceAsk = "ASK { GRAPH <$sourceGraph> { <$gameIri> a <https://baseballontology.org/BaseballGame> } }"
$sourceAskResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $sourceAsk } -Headers @{ Accept = 'application/sparql-results+json' }
if ($sourceAskResult.boolean -ne $true) {
    throw "The authoritative graph for game $GamePk is not loaded: $sourceGraph"
}

[void](New-Item -ItemType Directory -Force -Path $componentOutputRoot)
[void](New-Item -ItemType Directory -Force -Path $manifestRoot)
$builtAt = [DateTime]::UtcNow

try {
    $componentFiles = @(Get-ChildItem -LiteralPath $componentRoot -Filter '*.rq' -File | Sort-Object Name)
    if ($componentFiles.Count -eq 0) {
        throw "No query-index CONSTRUCT components were found at $componentRoot"
    }

    foreach ($componentFile in $componentFiles) {
        $query = Get-Content -LiteralPath $componentFile.FullName -Raw
        $query = $query.Replace('<urn:baseball:query-index:source-graph>', "<$sourceGraph>")
        $query = $query.Replace('<urn:baseball:query-index:game>', "<$gameIri>")
        $query = $query.Replace('<urn:baseball:query-index:index-resource>', "<$indexResource>")
        if ($query.Contains('urn:baseball:query-index:')) {
            throw "Unresolved query-index placeholder in $($componentFile.Name)"
        }
        $response = Invoke-WebRequest -Uri $queryEndpoint -Method Post -Body @{ query = $query } -Headers @{ Accept = 'text/turtle' } -UseBasicParsing
        $componentOutput = Join-Path $componentOutputRoot "$($componentFile.BaseName).ttl"
        [System.IO.File]::WriteAllText($componentOutput, [string]$response.Content, [System.Text.UTF8Encoding]::new($false))
    }

    & python $compilerPath --inputs $componentOutputRoot --output $compiledPath --stats $statsPath --game-pk $GamePk --source-graph $sourceGraph --index-resource $indexResource
    if ($LASTEXITCODE -ne 0) {
        throw "Query-index compilation failed for game $GamePk."
    }

    $sourceCountQuery = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } }"
    $sourceCountResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $sourceCountQuery } -Headers @{ Accept = 'application/sparql-results+json' }
    $sourceTripleCount = [int64]$sourceCountResult.results.bindings[0].count.value
    $stats = Get-Content -LiteralPath $statsPath -Raw | ConvertFrom-Json
    $indexTripleCount = [int64]$stats.tripleCount
    if ($indexTripleCount -le 0 -or $indexTripleCount -ge $sourceTripleCount) {
        throw "Query index is not a smaller projection: source=$sourceTripleCount; index=$indexTripleCount"
    }

    Invoke-WebRequest -Uri $indexDataEndpoint -Method Put -ContentType 'application/n-triples' -InFile $compiledPath -UseBasicParsing | Out-Null

    $loadedCountQuery = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$indexGraph> { ?s ?p ?o } }"
    $loadedCountResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $loadedCountQuery } -Headers @{ Accept = 'application/sparql-results+json' }
    $loadedTripleCount = [int64]$loadedCountResult.results.bindings[0].count.value
    if ($loadedTripleCount -ne $indexTripleCount) {
        throw "Loaded index count differs from compiled index: compiled=$indexTripleCount; loaded=$loadedTripleCount"
    }

    $metadataAsk = "ASK { GRAPH <$indexGraph> { <$indexResource> a <https://w3id.org/baseball/query-index/QueryIndex> ; <https://w3id.org/baseball/query-index/sourceGraph> <$sourceGraph> ; <https://w3id.org/baseball/query-index/indexedGame> <$gameIri> } }"
    $metadataResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $metadataAsk } -Headers @{ Accept = 'application/sparql-results+json' }
    if ($metadataResult.boolean -ne $true) {
        throw 'Loaded query index has no valid provenance metadata resource.'
    }

    # A shape-valid but incomplete index is unsafe for negative queries. Compare
    # all supported semantic row sets before recording this build as current.
    & (Join-Path $PSScriptRoot 'test-query-index.ps1') -GamePk $GamePk -SkipBuild -SkipManifestCheck

    if (-not $usesCanonicalComponents) {
        throw 'A noncanonical component root is test-only and cannot produce a current query-index graph.'
    }

    Copy-Item -LiteralPath $compiledPath -Destination $finalPath -Force
    $indexSha256 = (Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $sourceRdfPath = Join-Path $pipelineRoot "rdf\game-$GamePk.ttl"
    $sourceRdfSha256 = $null
    if (Test-Path -LiteralPath $sourceRdfPath -PathType Leaf) {
        $sourceRdfSha256 = (Get-FileHash -LiteralPath $sourceRdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $manifest = [ordered]@{
        artifactType = 'baseball-query-index-build'
        contractVersion = 1
        gamePk = $GamePk
        builtAtUtc = $builtAt.ToString('o')
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        sourceGraph = $sourceGraph
        indexGraph = $indexGraph
        indexResource = $indexResource
        contractSha256 = $contractHash
        sourceRdfSha256 = $sourceRdfSha256
        sourceTripleCount = $sourceTripleCount
        indexPath = $finalPath
        indexSha256 = $indexSha256
        indexTripleCount = $indexTripleCount
        componentFiles = @($stats.componentFiles)
        factCounts = $stats.factCounts
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Write-Host "Built query-index graph: $indexGraph"
    Write-Host "Source triples: $sourceTripleCount; index triples: $indexTripleCount"
    Write-Host "Index contract SHA-256: $contractHash"
    Write-Host "Query-index manifest: $manifestPath"
}
catch {
    try {
        Invoke-WebRequest -Uri $indexDataEndpoint -Method Delete -UseBasicParsing | Out-Null
    }
    catch {
        # The derived graph may not exist. Its absence is the safe failure state.
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $workRoot -PathType Container) {
        $resolvedWorkRoot = [System.IO.Path]::GetFullPath($workRoot)
        $resolvedIndexRoot = [System.IO.Path]::GetFullPath($indexRoot)
        if (-not $resolvedWorkRoot.StartsWith($resolvedIndexRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove an unexpected query-index work path: $resolvedWorkRoot"
        }
        Remove-Item -LiteralPath $resolvedWorkRoot -Recurse -Force
    }
}
