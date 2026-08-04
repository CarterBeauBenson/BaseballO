[CmdletBinding()]
param(
    [string] $GamePk = '566279',
    [ValidateRange(1, 100)][int] $Iterations = 10,
    [string] $OutputDirectory
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
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:StateRoot 'benchmarks\query-index'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Force -Path $outputRoot)

$queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
$sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
$indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
$pairManifestPath = Join-Path $script:RepositoryRoot 'sparql\query-index\benchmarks\benchmark-pairs.json'
$pairManifest = Get-Content -LiteralPath $pairManifestPath -Raw | ConvertFrom-Json

function Get-ScopedQuery {
    param(
        [Parameter(Mandatory = $true)][string] $RelativePath,
        [Parameter(Mandatory = $true)][string] $GraphIri
    )

    $queryPath = Join-Path $script:RepositoryRoot ($RelativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $queryPath -PathType Leaf)) {
        throw "Benchmark query was not found: $queryPath"
    }
    $query = Get-Content -LiteralPath $queryPath -Raw
    $graphPattern = [regex]::new('GRAPH\s+\?graph\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($graphPattern.Matches($query).Count -ne 1) {
        throw "Benchmark query must contain exactly one GRAPH ?graph block: $RelativePath"
    }
    return $graphPattern.Replace($query, "GRAPH <$GraphIri> {")
}

function Invoke-TimedQuery {
    param([Parameter(Mandatory = $true)][string] $Query)

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $Query } -Headers @{ Accept = 'application/sparql-results+json' }
    $stopwatch.Stop()
    return [PSCustomObject]@{
        ElapsedMilliseconds = [double]$stopwatch.Elapsed.TotalMilliseconds
        Result = $result
    }
}

function Get-CanonicalRows {
    param([Parameter(Mandatory = $true)] $Result)

    $variables = @($Result.head.vars)
    $rows = foreach ($binding in @($Result.results.bindings)) {
        $parts = foreach ($variable in $variables) {
            $termProperty = $binding.PSObject.Properties[[string]$variable]
            if ($null -eq $termProperty) {
                "$variable=<unbound>"
                continue
            }
            $term = $termProperty.Value
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

function Assert-EquivalentResults {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)] $Authoritative,
        [Parameter(Mandatory = $true)] $Indexed
    )

    $authoritativeRows = @(Get-CanonicalRows -Result $Authoritative)
    $indexedRows = @(Get-CanonicalRows -Result $Indexed)
    if ($authoritativeRows.Count -ne $indexedRows.Count) {
        throw "$Name result count differs: authoritative=$($authoritativeRows.Count); indexed=$($indexedRows.Count)"
    }
    if ($authoritativeRows.Count -gt 0) {
        $difference = @(Compare-Object -ReferenceObject $authoritativeRows -DifferenceObject $indexedRows)
        if ($difference.Count -ne 0) {
            $sample = ($difference | Select-Object -First 5 | Out-String).Trim()
            throw "$Name result bindings differ.`n$sample"
        }
    }
    return $authoritativeRows.Count
}

function Get-TimingStatistics {
    param([Parameter(Mandatory = $true)][double[]] $Values)

    $ordered = @($Values | Sort-Object)
    $middle = [int][Math]::Floor($ordered.Count / 2)
    if (($ordered.Count % 2) -eq 0) {
        $median = ($ordered[$middle - 1] + $ordered[$middle]) / 2.0
    }
    else {
        $median = $ordered[$middle]
    }
    $measurement = $ordered | Measure-Object -Average -Minimum -Maximum
    return [ordered]@{
        medianMilliseconds = [Math]::Round([double]$median, 3)
        meanMilliseconds = [Math]::Round([double]$measurement.Average, 3)
        minimumMilliseconds = [Math]::Round([double]$measurement.Minimum, 3)
        maximumMilliseconds = [Math]::Round([double]$measurement.Maximum, 3)
        samplesMilliseconds = @($Values | ForEach-Object { [Math]::Round([double]$_, 3) })
    }
}

$metadataAsk = "ASK { GRAPH <$sourceGraph> { <https://baseballontology.org/data/game/$GamePk> a <https://baseballontology.org/BaseballGame> } GRAPH <$indexGraph> { <https://w3id.org/baseball/query-index-build/game/$GamePk> a <https://w3id.org/baseball/query-index/QueryIndex> } }"
$metadataResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $metadataAsk } -Headers @{ Accept = 'application/sparql-results+json' }
if ($metadataResult.boolean -ne $true) {
    throw "Both authoritative and indexed graphs must be loaded for game $GamePk."
}

$countQuery = "SELECT ?sourceTriples ?indexTriples WHERE { { SELECT (COUNT(*) AS ?sourceTriples) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } } } { SELECT (COUNT(*) AS ?indexTriples) WHERE { GRAPH <$indexGraph> { ?s ?p ?o } } } }"
$countResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $countQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$sourceTripleCount = [int64]$countResult.results.bindings[0].sourceTriples.value
$indexTripleCount = [int64]$countResult.results.bindings[0].indexTriples.value

$benchmarkResults = @()
foreach ($pair in @($pairManifest.pairs)) {
    $authoritativeQuery = Get-ScopedQuery -RelativePath ([string]$pair.authoritative) -GraphIri $sourceGraph
    $indexedQuery = Get-ScopedQuery -RelativePath ([string]$pair.indexed) -GraphIri $indexGraph

    # These initial executions validate equivalence and prime the local query
    # paths. They are reported separately and are not claimed to be cold-cache.
    $authoritativeInitial = Invoke-TimedQuery -Query $authoritativeQuery
    $indexedInitial = Invoke-TimedQuery -Query $indexedQuery
    $rowCount = Assert-EquivalentResults -Name ([string]$pair.name) -Authoritative $authoritativeInitial.Result -Indexed $indexedInitial.Result

    $authoritativeSamples = New-Object System.Collections.Generic.List[double]
    $indexedSamples = New-Object System.Collections.Generic.List[double]
    for ($iteration = 0; $iteration -lt $Iterations; $iteration++) {
        if (($iteration % 2) -eq 0) {
            $authoritativeSamples.Add((Invoke-TimedQuery -Query $authoritativeQuery).ElapsedMilliseconds)
            $indexedSamples.Add((Invoke-TimedQuery -Query $indexedQuery).ElapsedMilliseconds)
        }
        else {
            $indexedSamples.Add((Invoke-TimedQuery -Query $indexedQuery).ElapsedMilliseconds)
            $authoritativeSamples.Add((Invoke-TimedQuery -Query $authoritativeQuery).ElapsedMilliseconds)
        }
    }

    $authoritativeStats = Get-TimingStatistics -Values $authoritativeSamples.ToArray()
    $indexedStats = Get-TimingStatistics -Values $indexedSamples.ToArray()
    $speedup = if ([double]$indexedStats.medianMilliseconds -eq 0) {
        $null
    }
    else {
        [Math]::Round([double]$authoritativeStats.medianMilliseconds / [double]$indexedStats.medianMilliseconds, 3)
    }
    $benchmarkResults += [ordered]@{
        name = [string]$pair.name
        family = [string]$pair.family
        authoritativeQuery = [string]$pair.authoritative
        indexedQuery = [string]$pair.indexed
        resultRows = $rowCount
        initialAuthoritativeMilliseconds = [Math]::Round($authoritativeInitial.ElapsedMilliseconds, 3)
        initialIndexedMilliseconds = [Math]::Round($indexedInitial.ElapsedMilliseconds, 3)
        authoritative = $authoritativeStats
        indexed = $indexedStats
        medianSpeedup = $speedup
    }
    Write-Host "$($pair.name): rows=$rowCount; authoritative median=$($authoritativeStats.medianMilliseconds) ms; indexed median=$($indexedStats.medianMilliseconds) ms; ratio=$speedup"
}

$queryIndexManifestPath = Join-Path $script:StateRoot "pipeline\manifests\game-$GamePk-query-index.json"
$queryIndexManifest = Get-Content -LiteralPath $queryIndexManifestPath -Raw | ConvertFrom-Json
$generatedAt = [DateTime]::UtcNow
$report = [ordered]@{
    artifactType = 'baseball-query-index-exploratory-benchmark'
    benchmarkVersion = 1
    generatedAtUtc = $generatedAt.ToString('o')
    scope = 'single checked-in completed-game fixture; not a multi-game scale claim'
    gamePk = $GamePk
    iterationsPerQueryAndLayer = $Iterations
    authoritativeGraph = $sourceGraph
    queryIndexGraph = $indexGraph
    authoritativeTripleCount = $sourceTripleCount
    queryIndexTripleCount = $indexTripleCount
    queryIndexContractSha256 = [string]$queryIndexManifest.contractSha256
    queryPairManifest = 'sparql/query-index/benchmarks/benchmark-pairs.json'
    powershellVersion = [string]$PSVersionTable.PSVersion
    results = $benchmarkResults
}

$baseName = "fixture-$GamePk-baseline"
$jsonPath = Join-Path $outputRoot "$baseName.json"
$markdownPath = Join-Path $outputRoot "$baseName.md"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($jsonPath, (($report | ConvertTo-Json -Depth 12) + "`n"), $utf8)

$markdown = New-Object System.Collections.Generic.List[string]
$markdown.Add("# Query-index exploratory benchmark: game $GamePk")
$markdown.Add('')
$markdown.Add("Generated: $($generatedAt.ToString('o'))")
$markdown.Add('')
$markdown.Add('This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.')
$markdown.Add('')
$markdown.Add("- Authoritative graph: $sourceTripleCount triples")
$markdown.Add("- Query-index graph: $indexTripleCount triples")
$markdown.Add("- Repeated samples per query and layer: $Iterations")
$markdown.Add([string]::Format('- Query-index contract SHA-256: `{0}`', [string]$queryIndexManifest.contractSha256))
$markdown.Add('')
$markdown.Add('| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |')
$markdown.Add('| --- | ---: | ---: | ---: | ---: |')
foreach ($result in $benchmarkResults) {
    $markdown.Add("| $($result.name) | $($result.resultRows) | $($result.authoritative.medianMilliseconds) | $($result.indexed.medianMilliseconds) | $($result.medianSpeedup)x |")
}
$markdown.Add('')
$markdown.Add('A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.')
[System.IO.File]::WriteAllText($markdownPath, (($markdown -join "`n") + "`n"), $utf8)

Write-Host 'Query-index benchmark completed with exact result equivalence.'
Write-Host "JSON report: $jsonPath"
Write-Host "Markdown report: $markdownPath"
