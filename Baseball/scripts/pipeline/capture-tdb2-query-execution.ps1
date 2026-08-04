[CmdletBinding()]
param([string] $OutputDirectory)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

if (Test-TcpPort -HostName '127.0.0.1' -Port 3030) {
    throw 'Fuseki must be stopped before opening its TDB2 datastore directly.'
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $script:RepositoryRoot 'benchmarks\query-index\tdb2-execution'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Force -Path $outputRoot)

$databasePath = Join-Path $script:FusekiState 'databases\baseball-dev'
$java = Get-JavaExecutable
$fusekiJar = Join-Path $script:FusekiHome 'fuseki-server.jar'
$pairManifestPath = Join-Path $script:RepositoryRoot 'sparql\query-index\benchmarks\benchmark-pairs.json'
$auditBaselinePath = Join-Path $script:RepositoryRoot 'benchmarks\canned-query-audit\corpus-2026-08-03-baseline.json'
$pairManifest = Get-Content -LiteralPath $pairManifestPath -Raw | ConvertFrom-Json
$auditBaseline = Get-Content -LiteralPath $auditBaselinePath -Raw | ConvertFrom-Json
$sampleRoot = Join-Path $script:RepositoryRoot 'data\raw\samples\2026-08-03'
$workRoot = Join-Path $script:StateRoot "benchmarks\query-index\tdb2-execution\$([Guid]::NewGuid().ToString('N'))"
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
    $query = Get-Content -LiteralPath $queryPath -Raw
    $wherePattern = [regex]::new('\bWHERE\s*\{', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($wherePattern.Matches($query).Count -lt 1) {
        throw "Execution-capture query must contain an outer WHERE block: $RelativePath"
    }
    $values = ($GraphIris | ForEach-Object { "<$_>" }) -join ' '
    return $wherePattern.Replace($query, "WHERE {`n  VALUES ?graph { $values }", 1)
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

[void](New-Item -ItemType Directory -Force -Path $workRoot)
try {
    $results = @()
    foreach ($pair in @($pairManifest.pairs)) {
        foreach ($layer in @('authoritative', 'indexed')) {
            $relativePath = if ($layer -eq 'authoritative') { [string]$pair.authoritative } else { [string]$pair.indexed }
            $graphIris = if ($layer -eq 'authoritative') { $sourceGraphs } else { $indexGraphs }
            $query = Get-ScopedQuery -RelativePath $relativePath -GraphIris $graphIris
            $queryPath = Join-Path $workRoot "$($pair.name)-$layer.rq"
            [System.IO.File]::WriteAllText($queryPath, $query, $utf8)

            $lines = @(
                & $java -cp $fusekiJar tdb2.tdbquery `
                    "--loc=$databasePath" `
                    "--query=$queryPath" `
                    --set 'arq:logExec=ALL' `
                    --results=none 2>&1
            )
            if ($LASTEXITCODE -ne 0) {
                throw "TDB2 execution capture failed for $($pair.name) $layer`n$($lines -join "`n")"
            }
            $text = ($lines -join "`n") + "`n"
            $normalized = [regex]::Replace($text, '(?m)^\d{2}:\d{2}:\d{2}\s+', '')
            $normalized = [regex]::Replace($normalized, '(?m)[ \t]+$', '')
            $firstExecution = [regex]::Match(
                $normalized,
                '(?ms)\A(?<capture>.*?^INFO\s+exec\s+:: Execute\s*\n.*?)(?=^INFO\s+exec\s+:: (?:TDB2|Execute)\s*$|\z)'
            )
            if (-not $firstExecution.Success) {
                throw "TDB2 output is missing its initial execution section: $($pair.name) $layer"
            }
            $normalized = $firstExecution.Groups['capture'].Value.TrimEnd() + "`n"
            $logName = "$($pair.name)-$layer.log"
            [System.IO.File]::WriteAllText((Join-Path $outputRoot $logName), $normalized, $utf8)

            $tdb2Match = [regex]::Match($normalized, '(?ms)^INFO\s+exec\s+:: TDB2\s*\n(?<body>.*?)(?=^INFO\s+exec\s+:: Execute)')
            $executeMatch = [regex]::Match($normalized, '(?ms)^INFO\s+exec\s+:: Execute\s*\n(?<body>.*)\z')
            if (-not $tdb2Match.Success -or -not $executeMatch.Success) {
                throw "TDB2 execution log is missing expected sections: $logName"
            }
            $tdb2Body = $tdb2Match.Groups['body'].Value
            $executionBody = $executeMatch.Groups['body'].Value.Trim()
            $executionTraceLines = if ([string]::IsNullOrWhiteSpace($executionBody)) {
                0
            }
            else {
                @($executionBody -split "\r?\n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count
            }
            $quadPatternCount = [regex]::Matches($tdb2Body, '\(quad\s').Count
            $queryFile = Join-Path $script:RepositoryRoot ($relativePath -replace '/', [System.IO.Path]::DirectorySeparatorChar)
            $results += [ordered]@{
                name = [string]$pair.name
                family = [string]$pair.family
                layer = $layer
                query = $relativePath
                querySha256 = (Get-FileHash -LiteralPath $queryFile -Algorithm SHA256).Hash.ToLowerInvariant()
                log = $logName
                logSha256 = Get-TextSha256 -Text $normalized
                tdb2QuadPatterns = $quadPatternCount
                tdb2BasicGraphPatterns = [regex]::Matches($tdb2Body, '\(bgp(?:\s|\r|\n)').Count
                tdb2Sequences = [regex]::Matches($tdb2Body, '\(sequence(?:\s|\r|\n)').Count
                tdb2LeftJoins = [regex]::Matches($tdb2Body, '\(leftjoin(?:\s|\r|\n)').Count
                executionTraceLineCount = $executionTraceLines
            }
            Write-Host "$($pair.name) ${layer}: TDB2 quads=$quadPatternCount; execution trace lines=$executionTraceLines"
        }
    }

    $generatedAt = [DateTime]::UtcNow
    $report = [ordered]@{
        artifactType = 'baseball-query-index-tdb2-execution-capture'
        reportVersion = 1
        generatedAtUtc = $generatedAt.ToString('o')
        jenaFusekiVersion = [string]$script:Versions.Fuseki.Version
        captureCommand = 'tdb2.tdbquery --set arq:logExec=ALL --results=none'
        scope = 'eight completed 2026-08-03 games; fixture 566279 excluded; direct read-only TDB2 execution with Fuseki stopped'
        corpusSha256 = [string]$auditBaseline.corpusSha256
        queryIndexContractSha256 = Get-QueryIndexContractHash
        resultCount = $results.Count
        results = $results
    }
    $summaryJsonPath = Join-Path $outputRoot 'tdb2-execution-summary.json'
    $summaryMarkdownPath = Join-Path $outputRoot 'README.md'
    [System.IO.File]::WriteAllText($summaryJsonPath, (($report | ConvertTo-Json -Depth 10) + "`n"), $utf8)

    $markdown = New-Object System.Collections.Generic.List[string]
    $markdown.Add('# TDB2 execution capture')
    $markdown.Add('')
    $markdown.Add("Generated with Apache Jena Fuseki $($script:Versions.Fuseki.Version) and ``tdb2.tdbquery --set arq:logExec=ALL --results=none``.")
    $markdown.Add('')
    $markdown.Add("The $($results.Count) normalized logs capture Jena query text, optimized algebra, TDB2 algebra, and the initial reordered execution pattern for each authoritative/indexed benchmark pair. Repeated aggregate subexecution traces are omitted. Fuseki was stopped so the command could open the same persistent TDB2 datastore read-only. Result tables were suppressed.")
    $markdown.Add('')
    $markdown.Add("- Corpus SHA-256: ``$($auditBaseline.corpusSha256)``")
    $markdown.Add("- Query-index contract SHA-256: ``$($report.queryIndexContractSha256)``")
    $markdown.Add('')
    $markdown.Add('| Query | Layer | TDB2 quad patterns | BGPs | Sequences | Left joins | Execution trace lines | Log |')
    $markdown.Add('| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |')
    foreach ($result in $results) {
        $markdown.Add("| $($result.name) | $($result.layer) | $($result.tdb2QuadPatterns) | $($result.tdb2BasicGraphPatterns) | $($result.tdb2Sequences) | $($result.tdb2LeftJoins) | $($result.executionTraceLineCount) | [$($result.log)]($($result.log)) |")
    }
    $markdown.Add('')
    $markdown.Add('These captures are storage-level query-planning evidence, not timing measurements. Each log is timestamp-normalized, limited to the first execution section, and content-hashed in the JSON summary.')
    [System.IO.File]::WriteAllText($summaryMarkdownPath, (($markdown -join "`n") + "`n"), $utf8)

    Write-Host "TDB2 execution captures written to $outputRoot"
}
finally {
    if (Test-Path -LiteralPath $workRoot -PathType Container) {
        $resolvedWorkRoot = [System.IO.Path]::GetFullPath($workRoot)
        $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'benchmarks\query-index\tdb2-execution'))
        if (-not $resolvedWorkRoot.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected TDB2 capture work path: $resolvedWorkRoot"
        }
        Remove-Item -LiteralPath $resolvedWorkRoot -Recurse -Force
    }
}
