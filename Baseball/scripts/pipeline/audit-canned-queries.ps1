[CmdletBinding()]
param(
    [string] $OutputDirectory,
    [switch] $VerifyBaseline
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not running on port 3031.'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:RepositoryRoot 'benchmarks\canned-query-audit'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
$baselineJsonPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.json'
$baselineMarkdownPath = Join-Path $outputRoot 'corpus-2026-08-03-baseline.md'
$queryEndpoint = 'http://127.0.0.1:3031/baseball-dev/query'
$mappingPath = Join-Path $script:RepositoryRoot 'sources\mlb-game\mapping\mlb-game.rml.ttl'
$sampleRoot = Join-Path $script:RepositoryRoot 'data\raw\samples\2026-08-03'
$evidenceRegisterPath = Join-Path $script:RepositoryRoot 'benchmarks\query-audit-evidence-register.json'
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
    $result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $Query } -Headers @{ Accept = 'application/sparql-results+json' }
    $stopwatch.Stop()
    if ($null -eq $result.head -or $null -eq $result.results) {
        throw 'The canned-query audit accepts SELECT queries returning SPARQL Results JSON only.'
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
            $termProperty = $binding.PSObject.Properties[$variable]
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
    return @($rows | Sort-Object)
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
$graphValues = $graphIris | ForEach-Object { "<$_>" }
$graphValuesClause = $graphValues -join ' '
$graphCountQuery = @"
SELECT ?graph (COUNT(*) AS ?triples)
WHERE {
  VALUES ?graph { $graphValuesClause }
  GRAPH ?graph { ?subject ?predicate ?object }
}
GROUP BY ?graph
"@
$graphCountResult = (Invoke-TimedSelect -Query $graphCountQuery).Result
$graphCounts = @{}
foreach ($binding in @($graphCountResult.results.bindings)) {
    $graphCounts[[string]$binding.graph.value] = [int64]$binding.triples.value
}
if ($graphCounts.Count -ne $graphIris.Count) {
    $missing = @($graphIris | Where-Object { -not $graphCounts.ContainsKey($_) })
    throw "The complete eight-game authoritative corpus is not loaded. Missing: $($missing -join ', ')"
}

$graphSnapshots = @()
for ($index = 0; $index -lt $sourceFiles.Count; $index++) {
    $sourceFile = $sourceFiles[$index]
    $graphIri = $graphIris[$index]
    $graphSnapshots += [ordered]@{
        gamePk = [string]$sourceFile.BaseName
        graphIri = $graphIri
        sourcePath = Get-RepositoryRelativePath -Path $sourceFile.FullName
        sourceSha256 = (Get-FileHash -LiteralPath $sourceFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        authoritativeTripleCount = [int64]$graphCounts[$graphIri]
    }
}

$queryFiles = @(
    Get-ChildItem -LiteralPath (Join-Path $script:RepositoryRoot 'sparql') -Filter '*.rq' -File -Recurse |
        Where-Object {
            $_.FullName -notlike '*\query-index\components\*' -and
            $_.FullName -notlike '*\query-index\benchmarks\indexed\*' -and
            $_.FullName -notlike '*\advanced\*' -and
            $_.FullName -notlike '*\serving\*'
        } |
        Sort-Object FullName
)
if ($queryFiles.Count -ne 51) {
    throw "Expected 51 authoritative canned queries; found $($queryFiles.Count)."
}

$results = @()
foreach ($queryFile in $queryFiles) {
    $relativePath = Get-RepositoryRelativePath -Path $queryFile.FullName
    $query = Get-Content -LiteralPath $queryFile.FullName -Raw
    $graphVariables = @(
        [regex]::Matches($query, 'GRAPH\s+(\?[A-Za-z_][A-Za-z0-9_-]*)\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase) |
            ForEach-Object { $_.Groups[1].Value.ToLowerInvariant() } |
            Sort-Object -Unique
    )
    if ($graphVariables.Count -ne 1 -or $graphVariables[0] -ne '?graph') {
        throw "$relativePath must isolate all joins through the single named-graph variable ?graph."
    }

    $wherePattern = [regex]::new('\bWHERE\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($wherePattern.Matches($query).Count -lt 1) {
        throw "$relativePath does not contain an outer WHERE block."
    }
    $scopedQuery = $wherePattern.Replace(
        $query,
        "WHERE {`n  VALUES ?graph { $graphValuesClause }",
        1
    )
    $execution = Invoke-TimedSelect -Query $scopedQuery
    $canonicalRows = @(Get-CanonicalRows -Result $execution.Result)
    $distinctRows = @($canonicalRows | Sort-Object -Unique)
    $variables = @($execution.Result.head.vars | ForEach-Object { [string]$_ })
    $pathSegments = $relativePath -split '/'
    $family = if ($pathSegments.Count -eq 2) { 'root' } else { [string]$pathSegments[1] }
    $results += [ordered]@{
        query = $relativePath
        family = $family
        querySha256 = Get-CanonicalTextSha256 -Path $queryFile.FullName
        graphBlockCount = [regex]::Matches($query, 'GRAPH\s+\?graph\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
        variables = $variables
        rowCount = $canonicalRows.Count
        distinctRowCount = $distinctRows.Count
        duplicateRowCount = $canonicalRows.Count - $distinctRows.Count
        rowSetSha256 = Get-TextSha256 -Text ($canonicalRows -join "`n")
        elapsedMilliseconds = $execution.ElapsedMilliseconds
    }
    Write-Host "$relativePath`: rows=$($canonicalRows.Count); duplicates=$($canonicalRows.Count - $distinctRows.Count); $($execution.ElapsedMilliseconds) ms"
}

$mappingSha256 = Get-CanonicalTextSha256 -Path $mappingPath
$corpusSignatureLines = @("mapping=$mappingSha256") + @(
    $graphSnapshots | ForEach-Object {
        "$($_.graphIri)|$($_.sourceSha256)|$($_.authoritativeTripleCount)"
    }
)
$generatedAt = [DateTime]::UtcNow
$report = [ordered]@{
    artifactType = 'baseball-authoritative-canned-query-corpus-audit'
    auditVersion = 1
    generatedAtUtc = $generatedAt.ToString('o')
    scope = 'eight completed 2026-08-03 games; checked-in fixture 566279 excluded'
    graphIsolation = 'Every query is scoped to the eight explicit authoritative named graphs through ?graph.'
    mappingSha256 = $mappingSha256
    corpusSha256 = Get-TextSha256 -Text ($corpusSignatureLines -join "`n")
    authoritativeGraphCount = $graphSnapshots.Count
    authoritativeTripleCount = [int64](($graphSnapshots | ForEach-Object { [int64]$_['authoritativeTripleCount'] } | Measure-Object -Sum).Sum)
    graphSnapshots = $graphSnapshots
    queryCount = $results.Count
    nonEmptyQueryCount = @($results | Where-Object { $_.rowCount -gt 0 }).Count
    zeroRowQueryCount = @($results | Where-Object { $_.rowCount -eq 0 }).Count
    queriesWithDuplicateRows = @($results | Where-Object { $_.duplicateRowCount -gt 0 }).Count
    results = $results
}

if ($VerifyBaseline) {
    if (-not (Test-Path -LiteralPath $baselineJsonPath -PathType Leaf)) {
        throw "Canned-query baseline was not found: $baselineJsonPath"
    }
    $expected = Get-Content -LiteralPath $baselineJsonPath -Raw | ConvertFrom-Json
    $register = Get-Content -LiteralPath $evidenceRegisterPath -Raw | ConvertFrom-Json
    $capture = @($register.captures | Where-Object { [string]$_.id -eq 'canned-2026-08-03' })
    if ($capture.Count -ne 1) {
        throw 'Canned-query evidence register entry is missing or ambiguous.'
    }
    $querySetLines = @($results | Sort-Object query | ForEach-Object { "$($_.query)=$($_.querySha256)" })
    $querySetSha256 = Get-TextSha256 -Text ($querySetLines -join "`n")
    if (
        [string]$capture[0].compatibleQueryHashAlgorithm -ne 'canonical-text-v1' -or
        [int]$capture[0].compatibleQueryCount -ne $results.Count -or
        [string]$capture[0].compatibleQuerySetSha256 -ne $querySetSha256
    ) {
        throw 'Current canned-query text differs from the reviewed historical-capture compatibility set.'
    }
    if ([string]$expected.corpusSha256 -ne [string]$report.corpusSha256) {
        throw "Canned-query corpus signature changed: expected $($expected.corpusSha256), got $($report.corpusSha256)"
    }
    $expectedByPath = @{}
    foreach ($result in @($expected.results)) {
        $expectedByPath[[string]$result.query] = $result
    }
    foreach ($result in $results) {
        $expectedResult = $expectedByPath[[string]$result.query]
        if ($null -eq $expectedResult) {
            throw "Baseline does not contain $($result.query)."
        }
        foreach ($field in @('rowCount', 'distinctRowCount', 'duplicateRowCount', 'rowSetSha256')) {
            if ([string]$expectedResult.$field -ne [string]$result.$field) {
                throw "$($result.query) $field changed: expected $($expectedResult.$field), got $($result.$field)"
            }
        }
    }
    Write-Host "All $($results.Count) authoritative canned queries match the checked-in eight-game baseline."
    exit 0
}

[void](New-Item -ItemType Directory -Force -Path $outputRoot)
[System.IO.File]::WriteAllText($baselineJsonPath, (($report | ConvertTo-Json -Depth 12) + "`n"), $utf8)

$markdown = New-Object System.Collections.Generic.List[string]
$markdown.Add('# Authoritative canned-query corpus audit')
$markdown.Add('')
$markdown.Add("Generated: $($generatedAt.ToString('o'))")
$markdown.Add('')
$markdown.Add('This baseline covers the eight completed 2026-08-03 games only. The older checked-in development fixture is deliberately excluded. Every query is executed against an explicit `VALUES ?graph` allowlist, so joins cannot cross games or use query-index graphs.')
$markdown.Add('')
$markdown.Add("- Authoritative graphs: $($report.authoritativeGraphCount)")
$markdown.Add("- Authoritative triples: $($report.authoritativeTripleCount)")
$markdown.Add("- Canned queries: $($report.queryCount)")
$markdown.Add("- Non-empty queries: $($report.nonEmptyQueryCount)")
$markdown.Add("- Zero-row queries: $($report.zeroRowQueryCount)")
$markdown.Add("- Queries with duplicate result rows: $($report.queriesWithDuplicateRows)")
$markdown.Add("- Corpus SHA-256: ``$($report.corpusSha256)``")
$markdown.Add('')
$markdown.Add('| Query | Rows | Distinct | Duplicates | Row-set SHA-256 | Time (ms) |')
$markdown.Add('| --- | ---: | ---: | ---: | --- | ---: |')
foreach ($result in $results) {
    $markdown.Add("| ``$($result.query)`` | $($result.rowCount) | $($result.distinctRowCount) | $($result.duplicateRowCount) | ``$($result.rowSetSha256)`` | $($result.elapsedMilliseconds) |")
}
$markdown.Add('')
$markdown.Add('Row-set hashes preserve term type, datatype, language, variable name, unbound values, and duplicate multiplicity while ignoring response order. Timings are diagnostic loopback observations, not benchmark claims.')
[System.IO.File]::WriteAllText($baselineMarkdownPath, (($markdown -join "`n") + "`n"), $utf8)

Write-Host 'Authoritative canned-query corpus audit completed.'
Write-Host "JSON baseline: $baselineJsonPath"
Write-Host "Markdown report: $baselineMarkdownPath"
