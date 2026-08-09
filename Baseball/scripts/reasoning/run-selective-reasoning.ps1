[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^\d+$')][string] $GamePk,
    [Parameter(Mandatory = $true)][ValidatePattern('^https://baseballontology\.org/data/game/\d+/plate-appearance/\d+$')][string] $Anchor,
    [ValidateSet('event-order', 'event-structure', 'participation')][string] $Profile = 'event-order',
    [string] $RdfFile,
    [string] $OutputDirectory,
    [string] $ClifRoot,
    [switch] $SyncClif,
    [switch] $Load
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$anchorGamePk = [regex]::Match($Anchor, '/game/(\d+)/plate-appearance/').Groups[1].Value
if ($anchorGamePk -ne $GamePk) {
    throw "Anchor game $anchorGamePk does not match requested game $GamePk."
}

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
if ([string]::IsNullOrWhiteSpace($RdfFile)) {
    $RdfFile = Join-Path $pipelineRoot "rdf\game-$GamePk.ttl"
}
$rdfPath = [System.IO.Path]::GetFullPath($RdfFile)
if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf)) {
    throw "Authoritative RDF file was not found: $rdfPath"
}

if ([string]::IsNullOrWhiteSpace($ClifRoot)) {
    $ClifRoot = Join-Path $script:RuntimesRoot 'bfo-clif-dd89f4a'
}
$clifPath = [System.IO.Path]::GetFullPath($ClifRoot)
$syncScript = Join-Path $script:RepositoryRoot 'scripts\reasoning\sync-bfo-clif.py'
if ($SyncClif) {
    & python $syncScript --output $clifPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Pinned BFO CLIF synchronization failed.'
    }
}
if (-not (Test-Path -LiteralPath $clifPath -PathType Container)) {
    throw "Pinned BFO CLIF cache is missing: $clifPath. Re-run with -SyncClif."
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $anchorBytes = [System.Text.Encoding]::UTF8.GetBytes($Anchor)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $anchorHash = ([System.BitConverter]::ToString($sha.ComputeHash($anchorBytes))).Replace('-', '').ToLowerInvariant().Substring(0, 16)
    }
    finally {
        $sha.Dispose()
    }
    $runId = [Guid]::NewGuid().ToString('N')
    $OutputDirectory = Join-Path $script:StateRoot "reasoning\builds\game-$GamePk\$Profile\$anchorHash\$runId"
}
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Force -Path $outputPath)

$profilePath = Join-Path $script:RepositoryRoot "reasoning\profiles\$Profile.json"
$reasonerPath = Join-Path $script:RepositoryRoot 'scripts\reasoning\selective_reasoner.py'
$proverPath = Join-Path $script:RepositoryRoot 'scripts\reasoning\prove-selective-reasoning.py'
$shaclValidatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-shacl.py'
$authoritativeShapePath = Join-Path $script:RepositoryRoot 'shacl\authoritative.ttl'
$reasoningShapePath = Join-Path $script:RepositoryRoot 'shacl\reasoning-output.ttl'
$preReasoningReport = Join-Path $outputPath 'pre-reasoning-shacl.json'
& python $shaclValidatorPath --profile authoritative --data $rdfPath --report-json $preReasoningReport
if ($LASTEXITCODE -ne 0) {
    throw "Authoritative SHACL failed before reasoning for $Anchor."
}
& python $reasonerPath `
    --input $rdfPath `
    --game-pk $GamePk `
    --anchor $Anchor `
    --profile $profilePath `
    --clif-root $clifPath `
    --output $outputPath
if ($LASTEXITCODE -ne 0) {
    throw "Selective reasoning failed for $Anchor with profile $Profile."
}

& python $proverPath --build $outputPath
if ($LASTEXITCODE -ne 0) {
    throw "Selective first-order proof failed for $Anchor with profile $Profile."
}

$manifestPath = Join-Path $outputPath 'manifest.json'
$publishedPath = Join-Path $outputPath 'published.nt'
$postReasoningReport = Join-Path $outputPath 'post-reasoning-shacl.json'
& python $shaclValidatorPath --profile reasoning-output --data $publishedPath --report-json $postReasoningReport
if ($LASTEXITCODE -ne 0) {
    throw "Reasoning-output SHACL failed before publication for $Anchor with profile $Profile."
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]$manifest.gamePk -ne $GamePk -or [string]$manifest.anchor -ne $Anchor -or [string]$manifest.profile -ne $Profile) {
    throw 'Selective reasoning manifest identity mismatch.'
}
$manifest | Add-Member -NotePropertyName shaclValidation -NotePropertyValue ([PSCustomObject]@{
    explicitGraphBeforeReasoning = [PSCustomObject]@{
        profile = 'authoritative'; conforms = $true
        shapeSha256 = (Get-FileHash -LiteralPath $authoritativeShapePath -Algorithm SHA256).Hash.ToLowerInvariant()
        reportPath = $preReasoningReport
        reportSha256 = (Get-FileHash -LiteralPath $preReasoningReport -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    inferredGraphBeforeLoad = [PSCustomObject]@{
        profile = 'reasoning-output'; conforms = $true
        shapeSha256 = (Get-FileHash -LiteralPath $reasoningShapePath -Algorithm SHA256).Hash.ToLowerInvariant()
        reportPath = $postReasoningReport
        reportSha256 = (Get-FileHash -LiteralPath $postReasoningReport -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}) -Force
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 16) + "`n"), $utf8)

if ($Load) {
    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
        throw 'Fuseki is not running on port 3030.'
    }
    $queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
    $sourceGraph = [string]$manifest.sourceGraph
    $gameIri = "https://baseballontology.org/data/game/$GamePk"
    $sourceAsk = "ASK { GRAPH <$sourceGraph> { <$gameIri> a <https://baseballontology.org/BaseballGame> } }"
    $sourceResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $sourceAsk } -Headers @{ Accept = 'application/sparql-results+json' }
    if ($sourceResult.boolean -ne $true) {
        throw "Authoritative source graph is not loaded: $sourceGraph"
    }

    $reasoningGraph = [string]$manifest.reasoningGraph
    $dataEndpoint = "http://127.0.0.1:3030/baseball-dev/data?graph=$([Uri]::EscapeDataString($reasoningGraph))"
    Invoke-WebRequest -Uri $dataEndpoint -Method Put -ContentType 'application/n-triples' -InFile $publishedPath -UseBasicParsing | Out-Null

    $countQuery = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$reasoningGraph> { ?s ?p ?o } }"
    $countResult = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $countQuery } -Headers @{ Accept = 'application/sparql-results+json' }
    $loadedCount = [int64]$countResult.results.bindings[0].count.value
    $expectedCount = [int64]$manifest.counts.publishedTriples
    if ($loadedCount -ne $expectedCount) {
        try {
            Invoke-WebRequest -Uri $dataEndpoint -Method Delete -UseBasicParsing | Out-Null
        }
        catch {
            # Absence is the safe state after a failed derived-graph load.
        }
        throw "Loaded reasoning graph count differs from its manifest: expected=$expectedCount; loaded=$loadedCount"
    }
    Write-Host "Loaded disposable reasoning graph: $reasoningGraph"
}

Write-Host "Selective reasoning manifest: $manifestPath"
Write-Host "Inferred triples: $($manifest.counts.inferredTriples)"
Write-Host "Complete first-order proof executed: $($manifest.fullFirstOrderProofExecuted)"
Write-Host "Selective first-order proof executed: $($manifest.selectiveFirstOrderProofExecuted)"
