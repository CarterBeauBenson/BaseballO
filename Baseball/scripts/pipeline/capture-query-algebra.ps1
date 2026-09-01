[CmdletBinding()]
param(
    [string] $OutputDirectory
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:StateRoot 'benchmarks\query-index\algebra'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Force -Path $outputRoot)

$java = Get-JavaExecutable
$fusekiJar = Join-Path $script:FusekiHome 'fuseki-server.jar'
if (-not (Test-Path -LiteralPath $fusekiJar -PathType Leaf)) {
    throw "Fuseki server JAR is missing: $fusekiJar"
}
$pairManifestPath = Join-Path $script:RepositoryRoot 'sparql\query-index\benchmarks\benchmark-pairs.json'
$pairManifest = Get-Content -LiteralPath $pairManifestPath -Raw | ConvertFrom-Json
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Capture-Algebra {
    param(
        [Parameter(Mandatory = $true)][string] $QueryPath,
        [Parameter(Mandatory = $true)][string] $OutputPath
    )

    $lines = @(& $java -cp $fusekiJar arq.qparse --print=opt --query $QueryPath 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "ARQ algebra capture failed for $QueryPath`n$($lines -join "`n")"
    }
    $text = ($lines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($OutputPath, $text, $utf8)
    return $text
}

function Get-AlgebraMetrics {
    param([Parameter(Mandatory = $true)][string] $Text)

    return [ordered]@{
        triplePatterns = ([regex]::Matches($Text, '\(triple\s')).Count
        basicGraphPatterns = ([regex]::Matches($Text, '\(bgp(?:\s|\r|\n)')).Count
        sequences = ([regex]::Matches($Text, '\(sequence(?:\s|\r|\n)')).Count
        leftJoins = ([regex]::Matches($Text, '\(leftjoin(?:\s|\r|\n)')).Count
        tables = ([regex]::Matches($Text, '\(table(?:\s|\r|\n)')).Count
        groups = ([regex]::Matches($Text, '\(group(?:\s|\r|\n)')).Count
        characters = $Text.Length
    }
}

$results = @()
foreach ($pair in @($pairManifest.pairs)) {
    $name = [string]$pair.name
    $authoritativePath = Join-Path $script:RepositoryRoot (([string]$pair.authoritative) -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $indexedPath = Join-Path $script:RepositoryRoot (([string]$pair.indexed) -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $authoritativeOutput = Join-Path $outputRoot "$name-authoritative-opt.txt"
    $indexedOutput = Join-Path $outputRoot "$name-indexed-opt.txt"
    $authoritativeText = Capture-Algebra -QueryPath $authoritativePath -OutputPath $authoritativeOutput
    $indexedText = Capture-Algebra -QueryPath $indexedPath -OutputPath $indexedOutput
    $authoritativeMetrics = Get-AlgebraMetrics -Text $authoritativeText
    $indexedMetrics = Get-AlgebraMetrics -Text $indexedText
    $results += [ordered]@{
        name = $name
        family = [string]$pair.family
        authoritativePlan = [System.IO.Path]::GetFileName($authoritativeOutput)
        indexedPlan = [System.IO.Path]::GetFileName($indexedOutput)
        authoritative = $authoritativeMetrics
        indexed = $indexedMetrics
        triplePatternReduction = [int]$authoritativeMetrics.triplePatterns - [int]$indexedMetrics.triplePatterns
    }
    Write-Host "${name}: authoritative triples=$($authoritativeMetrics.triplePatterns); indexed triples=$($indexedMetrics.triplePatterns)"
}

$generatedAt = [DateTime]::UtcNow
$report = [ordered]@{
    artifactType = 'baseball-query-index-optimized-algebra-comparison'
    reportVersion = 1
    generatedAtUtc = $generatedAt.ToString('o')
    jenaFusekiVersion = [string]$script:Versions.Fuseki.Version
    captureCommand = 'arq.qparse --print=opt --query <file>'
    scope = 'high-level optimized ARQ algebra; not TDB2 storage-specific runtime execution logging'
    queryPairManifest = 'sparql/query-index/benchmarks/benchmark-pairs.json'
    results = $results
}
$jsonPath = Join-Path $outputRoot 'optimized-algebra-summary.json'
$markdownPath = Join-Path $outputRoot 'optimized-algebra-summary.md'
[System.IO.File]::WriteAllText($jsonPath, (($report | ConvertTo-Json -Depth 10) + "`n"), $utf8)

$markdown = New-Object System.Collections.Generic.List[string]
$markdown.Add('# Authoritative/indexed optimized ARQ algebra')
$markdown.Add('')
$markdown.Add(('Generated with Apache Jena Fuseki {0} using `arq.qparse --print=opt`.' -f [string]$script:Versions.Fuseki.Version))
$markdown.Add('')
$markdown.Add('This captures high-level optimized ARQ algebra. It does not capture TDB2 storage-specific runtime join ordering; Jena execution logging is still required for that evidence.')
$markdown.Add('')
$markdown.Add('| Query | Authoritative triple patterns | Indexed triple patterns | Reduction |')
$markdown.Add('| --- | ---: | ---: | ---: |')
foreach ($result in $results) {
    $markdown.Add("| $($result.name) | $($result.authoritative.triplePatterns) | $($result.indexed.triplePatterns) | $($result.triplePatternReduction) |")
}
$markdown.Add('')
$markdown.Add('Raw optimized algebra for each layer is stored beside this summary. See the [Apache Jena explanation documentation](https://jena.apache.org/documentation/query/explain.html) for the distinction between algebra optimization and storage-specific execution logging.')
[System.IO.File]::WriteAllText($markdownPath, (($markdown -join "`n") + "`n"), $utf8)

Write-Host "Optimized algebra JSON: $jsonPath"
Write-Host "Optimized algebra Markdown: $markdownPath"
