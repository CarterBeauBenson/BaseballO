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

$graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
$query = @"
SELECT (COUNT(*) AS ?triples)
WHERE { GRAPH <$graphIri> { ?subject ?predicate ?object } }
"@
$countResult = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
$triples = [int64]$countResult.results.bindings[0].triples.value

$typeQuery = @"
SELECT (COUNT(DISTINCT ?plateAppearance) AS ?plateAppearances)
       (COUNT(DISTINCT ?pitch) AS ?pitches)
WHERE {
  GRAPH <$graphIri> {
    OPTIONAL { ?plateAppearance a <https://baseballontology.org/PlateAppearance> }
    OPTIONAL { ?pitch a <https://baseballontology.org/PitchAct> }
  }
}
"@
$result = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $typeQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$binding = $result.results.bindings[0]
$plateAppearances = [int64]$binding.plateAppearances.value
$pitches = [int64]$binding.pitches.value
if ($triples -le 0 -or $plateAppearances -ne @($document.liveData.plays.allPlays).Count) {
    throw "Fuseki verification failed: triples=$triples; plateAppearances=$plateAppearances"
}

$emptyGamesQueryPath = Join-Path $script:RepositoryRoot 'sparql\empty-games-prototype.rq'
$emptyGamesQuery = Get-Content -LiteralPath $emptyGamesQueryPath -Raw
$emptyGamesResult = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $emptyGamesQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$emptyGameCandidates = @($emptyGamesResult.results.bindings)
if ($gamePk -eq '566279' -and $emptyGameCandidates.Count -ne 6) {
    throw "Empty Games prototype regression failed: expected 6 fixture candidates, got $($emptyGameCandidates.Count)."
}

Write-Host 'Offline manual vertical slice passed.'
Write-Host "Game: $gamePk"
Write-Host "Source/archive SHA-256: $inputHashBefore"
Write-Host "Graph: $graphIri"
Write-Host "Triples: $triples; plate appearances: $plateAppearances; pitches: $pitches"
Write-Host "Empty Games prototype candidates: $($emptyGameCandidates.Count)"
