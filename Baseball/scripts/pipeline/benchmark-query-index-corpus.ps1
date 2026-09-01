[CmdletBinding()]
param(
    [ValidateRange(1, 100)][int] $Iterations = 20,
    [string] $OutputDirectory
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not running on port 3031.'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:RepositoryRoot 'benchmarks\query-index'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Force -Path $outputRoot)

$queryEndpoint = 'http://127.0.0.1:3031/baseball-dev/query'
$sampleRoot = Join-Path $script:RepositoryRoot 'data\raw\samples\2026-08-03'
$pairManifestPath = Join-Path $script:RepositoryRoot 'sparql\query-index\benchmarks\benchmark-pairs.json'
$auditBaselinePath = Join-Path $script:RepositoryRoot 'benchmarks\canned-query-audit\corpus-2026-08-03-baseline.json'
$pairManifest = Get-Content -LiteralPath $pairManifestPath -Raw | ConvertFrom-Json
$auditBaseline = Get-Content -LiteralPath $auditBaselinePath -Raw | ConvertFrom-Json
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Get-TextSha256 {
    param([AllowEmptyString()][Parameter(Mandatory = $true)][string] $Text)

    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return -join ($algorithm.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-ScopedQuery {
    param(
        [Parameter(Mandatory = $true)][string] $RelativePath,
        [Parameter(Mandatory = $true)][string[]] $GraphIris
    )

    $queryPath = Join-Path $script:RepositoryRoot ($RelativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $queryPath -PathType Leaf)) {
        throw "Benchmark query was not found: $queryPath"
    }
    $query = Get-Content -LiteralPath $queryPath -Raw
    $wherePattern = [regex]::new('\bWHERE\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($wherePattern.Matches($query).Count -lt 1) {
        throw "Benchmark query must contain an outer WHERE block: $RelativePath"
    }
    $values = ($GraphIris | ForEach-Object { "<$_>" }) -join ' '
    return $wherePattern.Replace($query, "WHERE {`n  VALUES ?graph { $values }", 1)
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
    $difference = @(Compare-Object -ReferenceObject $authoritativeRows -DifferenceObject $indexedRows)
    if ($difference.Count -ne 0) {
        $sample = @(
            $difference | Select-Object -First 5 | ForEach-Object {
                "$($_.SideIndicator) $($_.InputObject)"
            }
        ) -join "`n"
        throw "$Name result bindings differ.`n$sample"
    }
    return [PSCustomObject]@{
        RowCount = $authoritativeRows.Count
        RowSetSha256 = Get-TextSha256 -Text ($authoritativeRows -join "`n")
    }
}

function Get-TimingStatistics {
    param([Parameter(Mandatory = $true)][double[]] $Values)

    $ordered = @($Values | Sort-Object)
    $middle = [int][Math]::Floor($ordered.Count / 2)
    $median = if (($ordered.Count % 2) -eq 0) {
        ($ordered[$middle - 1] + $ordered[$middle]) / 2.0
    }
    else {
        $ordered[$middle]
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

$gamePks = @(
    Get-ChildItem -LiteralPath $sampleRoot -Filter '*.json' -File |
        Where-Object { $_.BaseName -match '^\d+$' } |
        Sort-Object BaseName |
        ForEach-Object { [string]$_.BaseName }
)
if ($gamePks.Count -ne 8) {
    throw "Expected exactly eight completed 2026-08-03 game files; found $($gamePks.Count)."
}
$sourceGraphs = @($gamePks | ForEach-Object { "https://w3id.org/baseball/graph/game/$_" })
$indexGraphs = @($gamePks | ForEach-Object { "https://w3id.org/baseball/graph/query-index/game/$_" })

function Get-GraphCounts {
    param([Parameter(Mandatory = $true)][string[]] $GraphIris)

    $values = ($GraphIris | ForEach-Object { "<$_>" }) -join ' '
    $query = "SELECT ?graph (COUNT(*) AS ?triples) WHERE { VALUES ?graph { $values } GRAPH ?graph { ?s ?p ?o } } GROUP BY ?graph"
    $response = (Invoke-TimedQuery -Query $query).Result
    $counts = @{}
    foreach ($binding in @($response.results.bindings)) {
        $counts[[string]$binding.graph.value] = [int64]$binding.triples.value
    }
    if ($counts.Count -ne $GraphIris.Count) {
        $missing = @($GraphIris | Where-Object { -not $counts.ContainsKey($_) })
        throw "Required benchmark graphs are not loaded: $($missing -join ', ')"
    }
    return $counts
}

$sourceCounts = Get-GraphCounts -GraphIris $sourceGraphs
$indexCounts = Get-GraphCounts -GraphIris $indexGraphs
$sourceTripleCount = [int64](($sourceGraphs | ForEach-Object { [int64]$sourceCounts[$_] } | Measure-Object -Sum).Sum)
$indexTripleCount = [int64](($indexGraphs | ForEach-Object { [int64]$indexCounts[$_] } | Measure-Object -Sum).Sum)

$semanticContractIds = @()
$semanticContractHashes = @()
$implementationHashes = @()
$admissionModes = @()
foreach ($gamePk in $gamePks) {
    $manifestPath = Join-Path $script:StateRoot "pipeline\manifests\game-$gamePk-query-index.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Query-index manifest is missing for game $gamePk."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $manifestAdmission = Resolve-QueryIndexManifestAdmission -Manifest $manifest
    $semanticContractIds += [string]$manifestAdmission.SemanticContractId
    $semanticContractHashes += [string]$manifestAdmission.SemanticContractSha256
    $implementationHashes += [string]$manifestAdmission.ImplementationSha256
    $admissionModes += [string]$manifestAdmission.Mode
}
$semanticContractIds = @($semanticContractIds | Sort-Object -Unique)
$semanticContractHashes = @($semanticContractHashes | Sort-Object -Unique)
$implementationHashes = @($implementationHashes | Sort-Object -Unique)
$admissionModes = @($admissionModes | Sort-Object -Unique)
if ($semanticContractIds.Count -ne 1 -or $semanticContractHashes.Count -ne 1) {
    throw 'The corpus does not resolve to one admitted query-index semantic contract.'
}

$benchmarkResults = @()
foreach ($pair in @($pairManifest.pairs)) {
    $authoritativePath = [string]$pair.authoritative
    $indexedPath = [string]$pair.indexed
    $authoritativeQuery = Get-ScopedQuery -RelativePath $authoritativePath -GraphIris $sourceGraphs
    $indexedQuery = Get-ScopedQuery -RelativePath $indexedPath -GraphIris $indexGraphs

    $authoritativeInitial = Invoke-TimedQuery -Query $authoritativeQuery
    $indexedInitial = Invoke-TimedQuery -Query $indexedQuery
    $equivalence = Assert-EquivalentResults -Name ([string]$pair.name) -Authoritative $authoritativeInitial.Result -Indexed $indexedInitial.Result

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
    $authoritativeFile = Join-Path $script:RepositoryRoot ($authoritativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $indexedFile = Join-Path $script:RepositoryRoot ($indexedPath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $benchmarkResults += [ordered]@{
        name = [string]$pair.name
        family = [string]$pair.family
        authoritativeQuery = $authoritativePath
        authoritativeQuerySha256 = Get-CanonicalTextSha256 -Path $authoritativeFile
        indexedQuery = $indexedPath
        indexedQuerySha256 = Get-CanonicalTextSha256 -Path $indexedFile
        resultRows = $equivalence.RowCount
        rowSetSha256 = $equivalence.RowSetSha256
        initialAuthoritativeMilliseconds = [Math]::Round($authoritativeInitial.ElapsedMilliseconds, 3)
        initialIndexedMilliseconds = [Math]::Round($indexedInitial.ElapsedMilliseconds, 3)
        authoritative = $authoritativeStats
        indexed = $indexedStats
        medianSpeedup = $speedup
    }
    Write-Host "$($pair.name): rows=$($equivalence.RowCount); authoritative median=$($authoritativeStats.medianMilliseconds) ms; indexed median=$($indexedStats.medianMilliseconds) ms; ratio=$speedup"
}

$generatedAt = [DateTime]::UtcNow
$report = [ordered]@{
    artifactType = 'baseball-query-index-corpus-benchmark'
    benchmarkVersion = 2
    generatedAtUtc = $generatedAt.ToString('o')
    scope = 'eight completed 2026-08-03 games; fixture 566279 excluded'
    iterationsPerQueryAndLayer = $Iterations
    authoritativeGraphs = $sourceGraphs
    queryIndexGraphs = $indexGraphs
    authoritativeTripleCount = $sourceTripleCount
    queryIndexTripleCount = $indexTripleCount
    corpusSha256 = [string]$auditBaseline.corpusSha256
    queryIndexSemanticContractId = [string]$semanticContractIds[0]
    queryIndexSemanticContractSha256 = [string]$semanticContractHashes[0]
    queryIndexImplementationSha256Set = $implementationHashes
    queryIndexAdmissionModeSet = $admissionModes
    queryPairManifest = 'sparql/query-index/benchmarks/benchmark-pairs.json'
    powershellVersion = [string]$PSVersionTable.PSVersion
    results = $benchmarkResults
}

$jsonPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.json'
$markdownPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.md'
[System.IO.File]::WriteAllText($jsonPath, (($report | ConvertTo-Json -Depth 12) + "`n"), $utf8)

$markdown = New-Object System.Collections.Generic.List[string]
$markdown.Add('# Query-index corpus benchmark: 2026-08-03')
$markdown.Add('')
$markdown.Add("Generated: $($generatedAt.ToString('o'))")
$markdown.Add('')
$markdown.Add('This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.')
$markdown.Add('')
$markdown.Add("- Authoritative graphs: $($sourceGraphs.Count), $sourceTripleCount triples")
$markdown.Add("- Query-index graphs: $($indexGraphs.Count), $indexTripleCount triples")
$markdown.Add("- Repeated samples per query and layer: $Iterations")
$markdown.Add("- Corpus SHA-256: ``$($auditBaseline.corpusSha256)``")
$markdown.Add("- Query-index semantic contract: ``$($semanticContractIds[0])`` (``$($semanticContractHashes[0])``)")
$markdown.Add("- Query-index implementation SHA-256 set (provenance only): ``$($implementationHashes -join ', ')``")
$markdown.Add('')
$markdown.Add('| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |')
$markdown.Add('| --- | ---: | ---: | ---: | ---: | ---: | ---: |')
foreach ($result in $benchmarkResults) {
    $markdown.Add("| $($result.name) | $($result.resultRows) | $($result.initialAuthoritativeMilliseconds) | $($result.initialIndexedMilliseconds) | $($result.authoritative.medianMilliseconds) | $($result.indexed.medianMilliseconds) | $($result.medianSpeedup)x |")
}
$markdown.Add('')
$markdown.Add('A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.')
[System.IO.File]::WriteAllText($markdownPath, (($markdown -join "`n") + "`n"), $utf8)

Write-Host 'Query-index corpus benchmark completed with exact result equivalence.'
Write-Host "JSON report: $jsonPath"
Write-Host "Markdown report: $markdownPath"
