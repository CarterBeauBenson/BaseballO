[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $GamePk,
    [string] $ComponentRoot,
    [string] $SourceRdfFile,
    [ValidatePattern('^[0-9a-f]{64}$')][string] $SourceRdfSha256
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if ($GamePk -notmatch '^\d+$') {
    throw "GamePk must contain only digits: $GamePk"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not running on port 3031.'
}

$sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
$indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
$gameIri = "https://baseballontology.org/data/game/$GamePk"
$indexResource = "https://w3id.org/baseball/query-index-build/game/$GamePk"
$queryEndpoint = 'http://127.0.0.1:3031/baseball-dev/query'
$indexDataEndpoint = "http://127.0.0.1:3031/baseball-dev/data?graph=$([Uri]::EscapeDataString($indexGraph))"
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
$shaclValidatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-shacl.py'
$queryIndexShapePath = Join-Path $script:RepositoryRoot 'shacl\query-index.ttl'
$jenaQueryIndexPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\JenaQueryIndex.java'
$implementationHash = Get-QueryIndexImplementationHash
$semanticAdmission = Get-QueryIndexSemanticAdmission
$isolatedJena = -not [string]::IsNullOrWhiteSpace($SourceRdfFile)
$sourceRdfPath = $null
if ($isolatedJena) {
    $sourceRdfPath = [System.IO.Path]::GetFullPath($SourceRdfFile)
    if (-not (Test-Path -LiteralPath $sourceRdfPath -PathType Leaf)) {
        throw "Source RDF file was not found: $sourceRdfPath"
    }
    if (-not (Test-Path -LiteralPath $jenaQueryIndexPath -PathType Leaf)) {
        throw "The isolated Jena query-index processor is missing: $jenaQueryIndexPath"
    }
}

[void](New-Item -ItemType Directory -Force -Path $componentOutputRoot)
[void](New-Item -ItemType Directory -Force -Path $manifestRoot)
$builtAt = [DateTime]::UtcNow
$fusekiWriteLock = $null
$indexGraphWritten = $false
if (-not $isolatedJena) {
    $fusekiWriteLock = Enter-FusekiWriteLock
}

try {
    $sourceAsk = "ASK { GRAPH <$sourceGraph> { <$gameIri> a <https://baseballontology.org/BaseballGame> } }"
    $sourceAskResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $sourceAsk } -Headers @{ Accept = 'application/sparql-results+json' }
    if ($sourceAskResult.boolean -ne $true) {
        throw "The authoritative graph for game $GamePk is not loaded: $sourceGraph"
    }

    $componentFiles = @(Get-ChildItem -LiteralPath $componentRoot -Filter '*.rq' -File | Sort-Object Name)
    if ($componentFiles.Count -eq 0) {
        throw "No query-index CONSTRUCT components were found at $componentRoot"
    }

    if ($isolatedJena) {
        $java = Get-JavaExecutable
        $jenaClasspath = Join-Path $script:FusekiHome 'fuseki-server.jar'
        & $java '-Xms64m' '-Xmx512m' '--class-path' $jenaClasspath $jenaQueryIndexPath $sourceRdfPath $sourceGraph $gameIri $indexResource $componentRoot $componentOutputRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Isolated Jena query-index execution failed for game $GamePk."
        }
    }
    else {
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
            # Fuseki currently returns text/turtle without a charset parameter.
            # Windows PowerShell 5.1 decodes response.Content as ISO-8859-1 in that
            # case, corrupting UTF-8 labels before compilation. Preserve the exact
            # response bytes and let rdflib parse Turtle as UTF-8.
            $rawStream = $response.RawContentStream
            if ($null -eq $rawStream) {
                throw "Fuseki returned no raw response stream for $($componentFile.Name)"
            }
            if ($rawStream.CanSeek) {
                $rawStream.Position = 0
            }
            $outputStream = [System.IO.File]::Open(
                $componentOutput,
                [System.IO.FileMode]::Create,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::None
            )
            try {
                $rawStream.CopyTo($outputStream)
            }
            finally {
                $outputStream.Dispose()
            }
        }
    }

    & python $compilerPath --inputs $componentOutputRoot --output $compiledPath --stats $statsPath --game-pk $GamePk --source-graph $sourceGraph --index-resource $indexResource
    if ($LASTEXITCODE -ne 0) {
        throw "Query-index compilation failed for game $GamePk."
    }

    $shaclArguments = @($shaclValidatorPath, '--profile', 'query-index', '--data', $compiledPath)
    if ($isolatedJena) {
        $shaclArguments += @(
            '--engine', 'jena',
            '--java', (Get-JavaExecutable),
            '--jena-classpath', (Join-Path $script:FusekiHome 'fuseki-server.jar'),
            '--jena-max-heap', '384m'
        )
    }
    & python @shaclArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Query-index SHACL validation failed for game $GamePk."
    }

    $sourceCountQuery = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } }"
    $sourceCountResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $sourceCountQuery } -Headers @{ Accept = 'application/sparql-results+json' }
    $sourceTripleCount = [int64]$sourceCountResult.results.bindings[0].count.value
    $stats = Get-Content -LiteralPath $statsPath -Raw | ConvertFrom-Json
    $indexTripleCount = [int64]$stats.tripleCount
    if ($indexTripleCount -le 0 -or $indexTripleCount -ge $sourceTripleCount) {
        throw "Query index is not a smaller projection: source=$sourceTripleCount; index=$indexTripleCount"
    }

    if ($null -eq $fusekiWriteLock) {
        $fusekiWriteLock = Enter-FusekiWriteLock
    }
    Invoke-WebRequest -Uri $indexDataEndpoint -Method Put -ContentType 'application/n-triples' -InFile $compiledPath -UseBasicParsing | Out-Null
    $indexGraphWritten = $true

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
    if ($isolatedJena) {
        Exit-FusekiWriteLock -LockHandle $fusekiWriteLock
        $fusekiWriteLock = $null
    }

    # A shape-valid but incomplete or lexically corrupted index is unsafe.
    # Compare all supported semantic row sets, including exact labels, before
    # recording this build as current.
    & (Join-Path $PSScriptRoot 'test-query-index.ps1') -GamePk $GamePk -SkipBuild -SkipManifestCheck

    if (-not $usesCanonicalComponents) {
        throw 'A noncanonical component root is test-only and cannot produce a current query-index graph.'
    }

    Copy-Item -LiteralPath $compiledPath -Destination $finalPath -Force
    $indexSha256 = (Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifestSourceRdfPath = Join-Path $pipelineRoot "rdf\game-$GamePk.ttl"
    $manifestSourceRdfSha256 = $null
    if (-not [string]::IsNullOrWhiteSpace($SourceRdfSha256)) {
        if (-not $isolatedJena) {
            throw '-SourceRdfSha256 is valid only with -SourceRdfFile.'
        }
        $manifestSourceRdfSha256 = $SourceRdfSha256
    }
    elseif (Test-Path -LiteralPath $manifestSourceRdfPath -PathType Leaf) {
        $manifestSourceRdfSha256 = (Get-FileHash -LiteralPath $manifestSourceRdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
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
        semanticContractId = $semanticAdmission.ContractId
        semanticContractPath = $semanticAdmission.ContractPath
        semanticContractSha256 = $semanticAdmission.ContractSha256
        implementationSha256 = $implementationHash
        implementationFingerprintAlgorithm = 'query-index-generation-file-set-v1'
        contractSha256 = $implementationHash
        sourceRdfSha256 = $manifestSourceRdfSha256
        sourceTripleCount = $sourceTripleCount
        indexPath = $finalPath
        indexSha256 = $indexSha256
        indexTripleCount = $indexTripleCount
        shaclProfile = 'query-index'
        shaclShapePath = $queryIndexShapePath
        shaclShapeSha256 = (Get-FileHash -LiteralPath $queryIndexShapePath -Algorithm SHA256).Hash.ToLowerInvariant()
        shaclValidatorSha256 = (Get-FileHash -LiteralPath $shaclValidatorPath -Algorithm SHA256).Hash.ToLowerInvariant()
        shaclEngine = if ($isolatedJena) { 'jena' } else { 'pyshacl' }
        queryExecution = if ($isolatedJena) { 'isolated-jena' } else { 'fuseki-http' }
        componentFiles = @($stats.componentFiles)
        factCounts = $stats.factCounts
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Write-Host "Built query-index graph: $indexGraph"
    Write-Host "Source triples: $sourceTripleCount; index triples: $indexTripleCount"
    Write-Host "Index semantic contract: $($semanticAdmission.ContractId) ($($semanticAdmission.ContractSha256))"
    Write-Host "Index implementation SHA-256: $implementationHash"
    Write-Host "Query-index manifest: $manifestPath"
}
catch {
    if ($indexGraphWritten) {
        if ($null -eq $fusekiWriteLock) {
            $fusekiWriteLock = Enter-FusekiWriteLock
        }
        try {
            Invoke-WebRequest -Uri $indexDataEndpoint -Method Delete -UseBasicParsing | Out-Null
        }
        catch {
            # The outer graph-pair transaction restores the previous graph.
        }
    }
    throw
}
finally {
    try {
        if (Test-Path -LiteralPath $workRoot -PathType Container) {
            $resolvedWorkRoot = [System.IO.Path]::GetFullPath($workRoot)
            $resolvedIndexRoot = [System.IO.Path]::GetFullPath($indexRoot)
            if (-not $resolvedWorkRoot.StartsWith($resolvedIndexRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Refusing to remove an unexpected query-index work path: $resolvedWorkRoot"
            }
            Remove-Item -LiteralPath $resolvedWorkRoot -Recurse -Force
        }
    }
    finally {
        if ($null -ne $fusekiWriteLock) {
            Exit-FusekiWriteLock -LockHandle $fusekiWriteLock
        }
    }
}
