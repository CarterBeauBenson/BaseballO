[CmdletBinding()]
param(
    [string] $OutputDirectory,
    [switch] $VerifyBaseline
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:RepositoryRoot 'benchmarks\advanced-query-audit'
}

$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
$baselineJsonPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.json'
$baselineMarkdownPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.md'
$queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
$mappingPath = Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl'
$sampleRoot = Join-Path $script:RepositoryRoot 'data\raw\samples\2026-08-03'
$catalogPath = Join-Path $script:RepositoryRoot 'sparql\advanced\advanced-query-catalog.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Get-TextSha256 {
    param([AllowEmptyString()][Parameter(Mandatory = $true)][string] $Text)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return -join ($algorithm.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    }
    finally { $algorithm.Dispose() }
}

function Get-RepositoryRelativePath {
    param([Parameter(Mandatory = $true)][string] $Path)
    $rootPrefix = [System.IO.Path]::GetFullPath($script:RepositoryRoot).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the repository: $fullPath"
    }
    return $fullPath.Substring($rootPrefix.Length) -replace '\\', '/'
}

function Invoke-TimedSelect {
    param([Parameter(Mandatory = $true)][string] $Query)
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $Query } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 120
    $stopwatch.Stop()
    if ($null -eq $result.head -or $null -eq $result.results) {
        throw 'The advanced-query audit accepts SELECT queries returning SPARQL Results JSON only.'
    }
    return [PSCustomObject]@{
        ElapsedMilliseconds = [Math]::Round([double]$stopwatch.Elapsed.TotalMilliseconds, 3)
        Result = $result
    }
}

function Get-CanonicalRows {
    param([Parameter(Mandatory = $true)] $Result)
    $variables = @($Result.head.vars | ForEach-Object { [string]$_ })
    $rows = foreach ($binding in @($Result.results.bindings)) {
        $parts = foreach ($variable in $variables) {
            $property = $binding.PSObject.Properties[$variable]
            if ($null -eq $property) {
                "$variable=<unbound>"
                continue
            }
            $term = $property.Value
            $datatype = if ($null -eq $term.PSObject.Properties['datatype']) { '' } else { [string]$term.datatype }
            $language = if ($null -eq $term.PSObject.Properties['xml:lang']) { '' } else { [string]$term.'xml:lang' }
            "$variable=$($term.type)|$datatype|$language|$($term.value)"
        }
        $parts -join "`u{001F}"
    }
    return @($rows | Sort-Object)
}

$catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json
$catalogQueries = @($catalog.queries)
if ($catalogQueries.Count -ne 16) {
    throw "Expected 16 cataloged advanced queries; found $($catalogQueries.Count)."
}

$sourceFiles = @(
    Get-ChildItem -LiteralPath $sampleRoot -Filter '*.json' -File |
        Where-Object { $_.BaseName -match '^\d+$' } |
        Sort-Object BaseName
)
if ($sourceFiles.Count -ne 8) {
    throw "Expected exactly eight completed 2026-08-03 game files; found $($sourceFiles.Count)."
}

$graphIris = @($sourceFiles | ForEach-Object { "https://w3id.org/baseball/graph/game/$($_.BaseName)" })
$graphValuesClause = ($graphIris | ForEach-Object { "<$_>" }) -join ' '
$graphCountQuery = "SELECT ?graph (COUNT(*) AS ?triples) WHERE { VALUES ?graph { $graphValuesClause } GRAPH ?graph { ?s ?p ?o } } GROUP BY ?graph"
$graphCountResult = (Invoke-TimedSelect -Query $graphCountQuery).Result
$graphCounts = @{}
foreach ($binding in @($graphCountResult.results.bindings)) {
    $graphCounts[[string]$binding.graph.value] = [int64]$binding.triples.value
}
if ($graphCounts.Count -ne 8) {
    throw 'The complete eight-game authoritative corpus is not loaded.'
}

$graphSnapshots = @()
foreach ($sourceFile in $sourceFiles) {
    $graphIri = "https://w3id.org/baseball/graph/game/$($sourceFile.BaseName)"
    $graphSnapshots += [ordered]@{
        gamePk = [string]$sourceFile.BaseName
        graphIri = $graphIri
        sourcePath = Get-RepositoryRelativePath -Path $sourceFile.FullName
        sourceSha256 = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        authoritativeTripleCount = [int64]$graphCounts[$graphIri]
    }
}

$results = @()
foreach ($entry in $catalogQueries) {
    $queryFile = Join-Path $script:RepositoryRoot ([string]$entry.path -replace '/', '\\')
    if (-not (Test-Path -LiteralPath $queryFile -PathType Leaf)) {
        throw "Cataloged query not found: $($entry.path)"
    }
    $query = Get-Content -LiteralPath $queryFile -Raw
    $graphVariables = @(
        [regex]::Matches($query, 'GRAPH\s+(\?[A-Za-z_][A-Za-z0-9_-]*)\s*\{', 'IgnoreCase') |
            ForEach-Object { $_.Groups[1].Value.ToLowerInvariant() } | Sort-Object -Unique
    )
    if ($graphVariables.Count -ne 1 -or $graphVariables[0] -ne '?graph') {
        throw "$($entry.path) must isolate joins through the single named-graph variable ?graph."
    }
    $graphPrefixFilter = 'FILTER(STRSTARTS(STR(?graph), "https://w3id.org/baseball/graph/game/"))'
    if (-not $query.Contains($graphPrefixFilter)) {
        throw "$($entry.path) lacks the authoritative named-graph prefix filter."
    }
    # Replace every graph-prefix filter, including filters inside subqueries.
    # Injecting one outer VALUES clause is insufficient because SPARQL subquery
    # variables are scoped independently and can otherwise cross-join the corpus.
    $scopedQuery = $query.Replace($graphPrefixFilter, "VALUES ?graph { $graphValuesClause }")
    $execution = Invoke-TimedSelect -Query $scopedQuery
    $canonicalRows = @(Get-CanonicalRows -Result $execution.Result)
    $distinctRows = @($canonicalRows | Sort-Object -Unique)
    if ($canonicalRows.Count -eq 0 -and -not [bool]$entry.allowZeroRows) {
        throw "$($entry.path) unexpectedly returned zero rows."
    }
    if ($canonicalRows.Count -ne $distinctRows.Count) {
        throw "$($entry.path) returned duplicate projected rows."
    }
    $results += [ordered]@{
        id = [string]$entry.id
        query = [string]$entry.path
        semanticMode = [string]$entry.semanticMode
        allowZeroRows = [bool]$entry.allowZeroRows
        querySha256 = (Get-FileHash -LiteralPath $queryFile -Algorithm SHA256).Hash.ToLowerInvariant()
        variables = @($execution.Result.head.vars | ForEach-Object { [string]$_ })
        rowCount = $canonicalRows.Count
        distinctRowCount = $distinctRows.Count
        duplicateRowCount = $canonicalRows.Count - $distinctRows.Count
        rowSetSha256 = Get-TextSha256 -Text ($canonicalRows -join "`n")
        elapsedMilliseconds = $execution.ElapsedMilliseconds
    }
    Write-Host "$($entry.id): rows=$($canonicalRows.Count); $($execution.ElapsedMilliseconds) ms"
}

$mappingSha256 = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$signatureLines = @("mapping=$mappingSha256") + @($graphSnapshots | ForEach-Object { "$($_.graphIri)|$($_.sourceSha256)|$($_.authoritativeTripleCount)" })
$report = [ordered]@{
    artifactType = 'baseball-advanced-semantic-query-corpus-audit'
    auditVersion = 1
    generatedAtUtc = [DateTime]::UtcNow.ToString('o')
    scope = 'eight completed 2026-08-03 games; checked-in fixture 566279 excluded'
    mappingSha256 = $mappingSha256
    catalogSha256 = (Get-FileHash -LiteralPath $catalogPath -Algorithm SHA256).Hash.ToLowerInvariant()
    corpusSha256 = Get-TextSha256 -Text ($signatureLines -join "`n")
    authoritativeGraphCount = 8
    authoritativeTripleCount = [int64](($graphSnapshots | ForEach-Object { $_.authoritativeTripleCount } | Measure-Object -Sum).Sum)
    graphSnapshots = $graphSnapshots
    queryCount = $results.Count
    nonEmptyQueryCount = @($results | Where-Object { $_.rowCount -gt 0 }).Count
    zeroRowQueryCount = @($results | Where-Object { $_.rowCount -eq 0 }).Count
    integrityFindingCount = [int64](($results | Where-Object { $_.semanticMode -eq 'integrity-audit' } | ForEach-Object { $_.rowCount } | Measure-Object -Sum).Sum)
    queriesWithDuplicateRows = @($results | Where-Object { $_.duplicateRowCount -gt 0 }).Count
    results = $results
}

if ($VerifyBaseline) {
    $expected = Get-Content -LiteralPath $baselineJsonPath -Raw | ConvertFrom-Json
    foreach ($field in @('mappingSha256', 'catalogSha256', 'corpusSha256', 'queryCount')) {
        if ([string]$expected.$field -ne [string]$report.$field) { throw "Advanced-query baseline mismatch: $field" }
    }
    $expectedById = @{}; foreach ($item in @($expected.results)) { $expectedById[[string]$item.id] = $item }
    foreach ($item in $results) {
        $old = $expectedById[[string]$item.id]
        foreach ($field in @('querySha256', 'rowCount', 'distinctRowCount', 'duplicateRowCount', 'rowSetSha256')) {
            if ([string]$old.$field -ne [string]$item.$field) { throw "Advanced-query baseline mismatch for $($item.id): $field" }
        }
    }
    Write-Host 'Advanced-query baseline verification passed.'
    return
}

New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
[System.IO.File]::WriteAllText($baselineJsonPath, (($report | ConvertTo-Json -Depth 8) + "`n"), $utf8)
$lines = @(
    '# Advanced query audit: 2026-08-03 corpus', '',
    "- Authoritative graphs: **$($report.authoritativeGraphCount)**",
    "- Authoritative triples: **$($report.authoritativeTripleCount)**",
    "- Advanced queries: **$($report.queryCount)**",
    "- Non-empty queries: **$($report.nonEmptyQueryCount)**",
    "- Integrity findings: **$($report.integrityFindingCount)**", '',
    '| Query | Mode | Rows | Time (ms) |', '|---|---|---:|---:|'
)
foreach ($item in $results) { $lines += "| ``$($item.id)`` | $($item.semanticMode) | $($item.rowCount) | $($item.elapsedMilliseconds) |" }
$lines += @('', 'Row-set hashes and corpus provenance are recorded in `corpus-2026-08-03-baseline.json`.')
[System.IO.File]::WriteAllText($baselineMarkdownPath, (($lines -join "`n") + "`n"), $utf8)
Write-Host "Wrote $baselineJsonPath"
Write-Host "Wrote $baselineMarkdownPath"
