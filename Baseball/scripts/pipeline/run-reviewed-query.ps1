[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Name,
    [ValidateSet('Auto', 'Authoritative', 'Indexed')][string] $Layer = 'Auto',
    [switch] $VerifyEquivalent
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not running on port 3031.'
}

$queryEndpoint = 'http://127.0.0.1:3031/baseball-dev/query'
$sourceGraphPrefix = 'https://w3id.org/baseball/graph/game/'
$indexGraphPrefix = 'https://w3id.org/baseball/graph/query-index/game/'
$routingPath = Join-Path $script:RepositoryRoot 'sparql\query-index\operational-query-routing.json'
$routing = Get-Content -LiteralPath $routingPath -Raw | ConvertFrom-Json
$route = @($routing.routes | Where-Object { [string]$_.name -eq $Name })
if ($route.Count -ne 1) {
    throw "Unknown or ambiguous reviewed query name: $Name"
}
$route = $route[0]

function Invoke-Sparql {
    param([Parameter(Mandatory = $true)][string] $Query)

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $Query } -Headers @{ Accept = 'application/sparql-results+json' }
    $stopwatch.Stop()
    return [PSCustomObject]@{
        Result = $result
        ElapsedMilliseconds = [math]::Round([double]$stopwatch.Elapsed.TotalMilliseconds, 3)
    }
}

function Get-ScopedQuery {
    param(
        [Parameter(Mandatory = $true)][string] $RelativePath,
        [Parameter(Mandatory = $true)][string[]] $GraphIris
    )

    $queryPath = [System.IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot ($RelativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)))
    $repositoryPrefix = [System.IO.Path]::GetFullPath($script:RepositoryRoot).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $queryPath.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Reviewed query path is outside the repository: $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $queryPath -PathType Leaf)) {
        throw "Reviewed query file was not found: $RelativePath"
    }
    $query = Get-Content -LiteralPath $queryPath -Raw
    $wherePattern = [regex]::new('\bWHERE\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($wherePattern.Matches($query).Count -lt 1) {
        throw "Reviewed query must contain an outer WHERE block: $RelativePath"
    }
    $values = ($GraphIris | ForEach-Object { "<$_>" }) -join ' '
    return $wherePattern.Replace($query, "WHERE {`n  VALUES ?graph { $values }", 1)
}

function Get-CanonicalRows {
    param([Parameter(Mandatory = $true)] $Result)

    $variables = @($Result.head.vars)
    $rows = foreach ($binding in @($Result.results.bindings)) {
        $parts = foreach ($variable in $variables) {
            $property = $binding.PSObject.Properties[[string]$variable]
            if ($null -eq $property) {
                "$variable=<unbound>"
                continue
            }
            $term = $property.Value
            $datatypeProperty = $term.PSObject.Properties['datatype']
            $languageProperty = $term.PSObject.Properties['xml:lang']
            $datatype = if ($null -eq $datatypeProperty) { '' } else { [string]$datatypeProperty.Value }
            $language = if ($null -eq $languageProperty) { '' } else { [string]$languageProperty.Value }
            "$variable=$($term.type)|$datatype|$language|$($term.value)"
        }
        $parts -join "`u{001F}"
    }
    return @($rows | Sort-Object -Unique)
}

function Get-LoadedGraphSet {
    $query = @"
PREFIX base: <https://baseballontology.org/>
SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph { ?game a base:BaseballGame . }
  FILTER(STRSTARTS(STR(?graph), "$sourceGraphPrefix"))
}
ORDER BY ?graph
"@
    $response = Invoke-Sparql -Query $query
    $sourceGraphs = @($response.Result.results.bindings | ForEach-Object { [string]$_.graph.value })
    if ($sourceGraphs.Count -eq 0) {
        throw 'No authoritative BaseballO game graphs are loaded.'
    }
    foreach ($graph in $sourceGraphs) {
        if ($graph -notmatch '^https://w3id\.org/baseball/graph/game/(?<gamePk>\d+)$') {
            throw "Unexpected authoritative graph IRI: $graph"
        }
    }
    $indexGraphs = @($sourceGraphs | ForEach-Object { $_.Replace($sourceGraphPrefix, $indexGraphPrefix) })
    return [PSCustomObject]@{
        SourceGraphs = $sourceGraphs
        IndexGraphs = $indexGraphs
    }
}

function Get-IndexReadinessFailure {
    param([Parameter(Mandatory = $true)] $GraphSet)

    $valueRows = New-Object System.Collections.Generic.List[string]
    for ($index = 0; $index -lt $GraphSet.SourceGraphs.Count; $index++) {
        $sourceGraph = [string]$GraphSet.SourceGraphs[$index]
        $indexGraph = [string]$GraphSet.IndexGraphs[$index]
        $gamePk = $sourceGraph.Substring($sourceGraphPrefix.Length)
        $manifestPath = Join-Path $script:StateRoot "pipeline\manifests\game-$gamePk-query-index.json"
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            return "missing query-index manifest for game $gamePk"
        }
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        try {
            [void](Resolve-QueryIndexManifestAdmission -Manifest $manifest)
        }
        catch {
            return "query-index semantic admission failed for game ${gamePk}: $($_.Exception.Message)"
        }
        if ([string]$manifest.sourceGraph -ne $sourceGraph -or [string]$manifest.indexGraph -ne $indexGraph) {
            return "query-index manifest graph mismatch for game $gamePk"
        }
        $expectedIndexPath = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot "pipeline\query-index\game-$gamePk.nt"))
        if ([string]::IsNullOrWhiteSpace([string]$manifest.indexPath) -or [System.IO.Path]::GetFullPath([string]$manifest.indexPath) -ne $expectedIndexPath) {
            return "query-index manifest path mismatch for game $gamePk"
        }
        if (-not (Test-Path -LiteralPath $expectedIndexPath -PathType Leaf)) {
            return "missing local query-index artifact for game $gamePk"
        }
        $indexHash = (Get-FileHash -LiteralPath $expectedIndexPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($indexHash -ne [string]$manifest.indexSha256) {
            return "changed local query-index artifact for game $gamePk"
        }
        $sourceRdfPath = Join-Path $script:StateRoot "pipeline\rdf\game-$gamePk.ttl"
        if (-not [string]::IsNullOrWhiteSpace([string]$manifest.sourceRdfSha256)) {
            if (-not (Test-Path -LiteralPath $sourceRdfPath -PathType Leaf)) {
                return "missing local authoritative RDF artifact for game $gamePk"
            }
            $sourceRdfHash = (Get-FileHash -LiteralPath $sourceRdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($sourceRdfHash -ne [string]$manifest.sourceRdfSha256) {
                return "changed local authoritative RDF artifact for game $gamePk"
            }
        }
        $sourceTripleCount = [int64]$manifest.sourceTripleCount
        $indexTripleCount = [int64]$manifest.indexTripleCount
        if ($sourceTripleCount -le 0 -or $indexTripleCount -le 0) {
            return "invalid query-index manifest counts for game $gamePk"
        }
        $gameIri = "https://baseballontology.org/data/game/$gamePk"
        $indexResource = "https://w3id.org/baseball/query-index-build/game/$gamePk"
        $valueRows.Add("(<$sourceGraph> <$indexGraph> <$gameIri> <$indexResource> $sourceTripleCount $indexTripleCount)")
    }

    $metadataQuery = @"
PREFIX idx: <https://w3id.org/baseball/query-index/>
SELECT (COUNT(DISTINCT ?sourceGraph) AS ?readyGraphs) WHERE {
  VALUES (?sourceGraph ?indexGraph ?game ?indexResource ?expectedSourceCount ?expectedIndexCount) {
    $($valueRows -join "`n    ")
  }
  GRAPH ?indexGraph {
    ?indexResource a idx:QueryIndex ;
        idx:sourceGraph ?sourceGraph ;
        idx:indexedGame ?game ;
        idx:contractVersion "1" .
  }
  {
    SELECT ?sourceGraph (COUNT(*) AS ?actualSourceCount) WHERE {
      GRAPH ?sourceGraph { ?sourceSubject ?sourcePredicate ?sourceObject }
    }
    GROUP BY ?sourceGraph
  }
  {
    SELECT ?indexGraph (COUNT(*) AS ?actualIndexCount) WHERE {
      GRAPH ?indexGraph { ?indexSubject ?indexPredicate ?indexObject }
    }
    GROUP BY ?indexGraph
  }
  FILTER(?actualSourceCount = ?expectedSourceCount)
  FILTER(?actualIndexCount = ?expectedIndexCount)
}
"@
    $metadata = Invoke-Sparql -Query $metadataQuery
    $readyCount = [int]$metadata.Result.results.bindings[0].readyGraphs.value
    if ($readyCount -ne $GraphSet.SourceGraphs.Count) {
        return "only $readyCount of $($GraphSet.SourceGraphs.Count) loaded game indexes passed artifact, metadata, and graph-count checks"
    }
    return $null
}

$graphSet = Get-LoadedGraphSet
$requestedLayer = $Layer.ToLowerInvariant()
$selectedLayer = if ($Layer -eq 'Auto') { [string]$route.autoLayer } else { $requestedLayer }
$fallbackReason = $null
if ($selectedLayer -eq 'indexed') {
    $readinessFailure = Get-IndexReadinessFailure -GraphSet $graphSet
    if ($null -ne $readinessFailure) {
        if ($Layer -eq 'Auto') {
            $selectedLayer = 'authoritative'
            $fallbackReason = $readinessFailure
        }
        else {
            throw "Indexed execution refused: $readinessFailure"
        }
    }
}

$relativePath = if ($selectedLayer -eq 'indexed') { [string]$route.indexed } else { [string]$route.authoritative }
$graphIris = if ($selectedLayer -eq 'indexed') { $graphSet.IndexGraphs } else { $graphSet.SourceGraphs }
$query = Get-ScopedQuery -RelativePath $relativePath -GraphIris $graphIris
$execution = Invoke-Sparql -Query $query
$rowCount = @($execution.Result.results.bindings).Count

$equivalenceVerified = $false
if ($VerifyEquivalent -and $selectedLayer -eq 'indexed') {
    $authoritativeQuery = Get-ScopedQuery -RelativePath ([string]$route.authoritative) -GraphIris $graphSet.SourceGraphs
    $authoritativeExecution = Invoke-Sparql -Query $authoritativeQuery
    $indexedRows = @(Get-CanonicalRows -Result $execution.Result)
    $authoritativeRows = @(Get-CanonicalRows -Result $authoritativeExecution.Result)
    $difference = @(Compare-Object -ReferenceObject $authoritativeRows -DifferenceObject $indexedRows)
    if ($difference.Count -ne 0) {
        throw "Runtime equivalence failed for ${Name}: authoritative=$($authoritativeRows.Count); indexed=$($indexedRows.Count)"
    }
    $equivalenceVerified = $true
}

$report = [ordered]@{
    artifactType = 'baseball-reviewed-query-result'
    name = [string]$route.name
    requestedLayer = $requestedLayer
    selectedLayer = $selectedLayer
    fallbackReason = $fallbackReason
    graphCount = $graphIris.Count
    queryPath = $relativePath
    durationMilliseconds = $execution.ElapsedMilliseconds
    rowCount = $rowCount
    equivalenceVerified = $equivalenceVerified
    query = $query
    result = $execution.Result
}
$report | ConvertTo-Json -Depth 20
