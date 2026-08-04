[CmdletBinding()]
param(
    [string] $InputJson,
    [switch] $ForceRdfLoad
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

if ([string]::IsNullOrWhiteSpace($InputJson)) {
    $InputJson = Join-Path $script:RepositoryRoot 'data\raw\game-566279.json'
}
$inputPath = [System.IO.Path]::GetFullPath($InputJson)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "Offline test input was not found: $inputPath"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}

$document = Get-Content -LiteralPath $inputPath -Raw | ConvertFrom-Json
$gamePk = [string]$document.gamePk
$season = [string]$document.gameData.game.season
if ($gamePk -notmatch '^\d+$' -or $season -notmatch '^\d{4}$') {
    throw 'Offline test input has an unsafe gamePk or season.'
}
$inputHashBefore = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$expectedPitchCount = 0
foreach ($play in @($document.liveData.plays.allPlays)) {
    foreach ($event in @($play.playEvents)) {
        if ($event.isPitch -eq $true) {
            $expectedPitchCount++
        }
    }
}

$arguments = @{ InputJson = $inputPath }
if ($ForceRdfLoad) {
    $arguments.ForceRdfLoad = $true
}
& (Join-Path $PSScriptRoot 'import-game-json.ps1') @arguments

$inputHashAfter = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($inputHashAfter -ne $inputHashBefore) {
    throw 'Offline vertical-slice test changed its source fixture.'
}

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$rawPath = Join-Path $pipelineRoot "raw\games\$season\$gamePk\$inputHashBefore.json"
if (-not (Test-Path -LiteralPath $rawPath -PathType Leaf)) {
    throw "Expected content-addressed raw archive is missing: $rawPath"
}
$rawHash = (Get-FileHash -LiteralPath $rawPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($rawHash -ne $inputHashBefore) {
    throw 'Archived raw JSON is not byte-identical to the test fixture.'
}

$rmlManifestPath = Join-Path $pipelineRoot "manifests\game-$gamePk-rml.json"
$rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
if ([string]$rmlManifest.inputSha256 -ne $inputHashBefore) {
    throw 'RML manifest input hash does not match the source fixture.'
}
if ([string]::IsNullOrWhiteSpace([string]$rmlManifest.contextBuilderSha256) -or
    [string]::IsNullOrWhiteSpace([string]$rmlManifest.executionContextSha256)) {
    throw 'RML manifest does not record the execution-context provenance hashes.'
}

$graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
$query = @"
SELECT (COUNT(*) AS ?triples)
WHERE { GRAPH <$graphIri> { ?subject ?predicate ?object } }
"@
$countResult = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
$triples = [int64]$countResult.results.bindings[0].triples.value

$typeQuery = @"
SELECT ?plateAppearances ?pitches ?contextualizedPitches
WHERE {
  {
    SELECT (COUNT(DISTINCT ?plateAppearance) AS ?plateAppearances)
    WHERE { GRAPH <$graphIri> { ?plateAppearance a <https://baseballontology.org/PlateAppearance> } }
  }
  {
    SELECT (COUNT(DISTINCT ?pitch) AS ?pitches)
    WHERE { GRAPH <$graphIri> { ?pitch a <https://baseballontology.org/PitchAct> } }
  }
  {
    SELECT (COUNT(DISTINCT ?contextualizedPitch) AS ?contextualizedPitches)
    WHERE { GRAPH <$graphIri> {
      ?contextualizedPitch a <https://baseballontology.org/PitchAct> ;
          <http://purl.obolibrary.org/obo/BFO_0000132> ?pitchPlateAppearance ;
          <http://purl.obolibrary.org/obo/BFO_0000057> ?pitcher ;
          <http://purl.obolibrary.org/obo/BFO_0000055> ?pitcherRole .
      ?pitchPlateAppearance a <https://baseballontology.org/PlateAppearance> .
      ?pitcher a <https://www.commoncoreontologies.org/ont00001262> .
      ?pitcherRole a <https://baseballontology.org/PitcherRole> ;
          <http://purl.obolibrary.org/obo/BFO_0000197> ?pitcher .
    } }
  }
}
"@
$result = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $typeQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$binding = $result.results.bindings[0]
$plateAppearances = [int64]$binding.plateAppearances.value
$pitches = [int64]$binding.pitches.value
$contextualizedPitches = [int64]$binding.contextualizedPitches.value
if ($triples -le 0 -or
    $plateAppearances -ne @($document.liveData.plays.allPlays).Count -or
    $pitches -ne $expectedPitchCount -or
    $contextualizedPitches -ne $expectedPitchCount) {
    throw "Fuseki verification failed: triples=$triples; plateAppearances=$plateAppearances; pitches=$pitches; contextualizedPitches=$contextualizedPitches"
}

$emptyGamesQueryPath = Join-Path $script:RepositoryRoot 'sparql\empty-games-prototype.rq'
$emptyGamesQuery = Get-Content -LiteralPath $emptyGamesQueryPath -Raw
$emptyGamesQuery = [regex]::Replace(
    $emptyGamesQuery,
    'WHERE\s*\{',
    "WHERE {`n  VALUES ?graph { <$graphIri> }",
    1
)
$emptyGamesResult = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $emptyGamesQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$emptyGameCandidates = @($emptyGamesResult.results.bindings)
if ($gamePk -eq '566279' -and $emptyGameCandidates.Count -ne 6) {
    throw "Empty Games prototype regression failed: expected 6 fixture candidates, got $($emptyGameCandidates.Count)."
}

& (Join-Path $PSScriptRoot 'test-query-index.ps1') -GamePk $gamePk -SkipBuild

Write-Host 'Offline manual vertical slice passed.'
Write-Host "Game: $gamePk"
Write-Host "Source/archive SHA-256: $inputHashBefore"
Write-Host "Graph: $graphIri"
Write-Host "Triples: $triples; plate appearances: $plateAppearances; pitches: $pitches; contextualized pitches: $contextualizedPitches"
Write-Host "Empty Games prototype candidates: $($emptyGameCandidates.Count)"
