[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $GamePk,
    [switch] $SkipBuild,
    [switch] $SkipManifestCheck
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
if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $GamePk
}

$sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
$indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
$gameIri = "https://baseballontology.org/data/game/$GamePk"
$queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'

function Get-CanonicalRows {
    param(
        [Parameter(Mandatory = $true)][string] $GraphIri,
        [Parameter(Mandatory = $true)][string[]] $Variables,
        [Parameter(Mandatory = $true)][string] $Pattern
    )

    $selection = ($Variables | ForEach-Object { "?$_" }) -join ' '
    $query = "SELECT DISTINCT $selection WHERE { GRAPH <$GraphIri> { $Pattern } }"
    $result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
    $rows = foreach ($binding in @($result.results.bindings)) {
        $parts = foreach ($variable in $Variables) {
            $term = $binding.$variable
            if ($null -eq $term) {
                "$variable=<unbound>"
            }
            else {
                $datatypeProperty = $term.PSObject.Properties['datatype']
                $languageProperty = $term.PSObject.Properties['xml:lang']
                $datatype = if ($null -eq $datatypeProperty) { '' } else { [string]$datatypeProperty.Value }
                $language = if ($null -eq $languageProperty) { '' } else { [string]$languageProperty.Value }
                "$variable=$($term.type)|$datatype|$language|$($term.value)"
            }
        }
        $parts -join "`u{001F}"
    }
    return @($rows | Sort-Object -Unique)
}

function Assert-EquivalentRows {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string[]] $Variables,
        [Parameter(Mandatory = $true)][string] $FullPattern,
        [Parameter(Mandatory = $true)][string] $IndexPattern
    )

    $fullRows = @(Get-CanonicalRows -GraphIri $sourceGraph -Variables $Variables -Pattern $FullPattern)
    $indexRows = @(Get-CanonicalRows -GraphIri $indexGraph -Variables $Variables -Pattern $IndexPattern)
    $difference = @(Compare-Object -ReferenceObject $fullRows -DifferenceObject $indexRows)
    if ($difference.Count -ne 0) {
        $sample = ($difference | Select-Object -First 5 | Out-String).Trim()
        throw "$Name query-index equivalence failed: full=$($fullRows.Count); index=$($indexRows.Count)`n$sample"
    }
    Write-Host "$Name equivalence: $($fullRows.Count) rows"
}

$base = 'https://baseballontology.org/'
$cco = 'https://www.commoncoreontologies.org/'
$idx = 'https://w3id.org/baseball/query-index/'
$obo = 'http://purl.obolibrary.org/obo/'
$dcterms = 'http://purl.org/dc/terms/'
$rdfs = 'http://www.w3.org/2000/01/rdf-schema#'

Assert-EquivalentRows -Name 'Game dimensions' -Variables @('game', 'season', 'venue') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${base}BaseballGame> ; <${cco}ont00001918> ?field ; <${obo}BFO_0000199>/<${obo}BFO_0000222> ?startInstant .
  ?timestamp a <${base}BaseballTimestampICE> ; <${cco}ont00001916> ?startInstant ; <${cco}ont00001767> ?gameStart .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
  BIND(YEAR(?gameStart) AS ?season)
"@ -IndexPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${idx}GameFact> ; <${idx}season> ?season ; <${idx}venue> ?venue .
"@

Assert-EquivalentRows -Name 'Label fidelity' -Variables @('resource', 'label') -FullPattern @"
  ?resource <${rdfs}label> ?label .
"@ -IndexPattern @"
  ?resource <${rdfs}label> ?label .
"@

Assert-EquivalentRows -Name 'Plate-appearance results' -Variables @('result', 'plateAppearance', 'player', 'outcomeClass', 'eventType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?result a <${base}BaseballInstitutionalProcess>, ?outcomeClass ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000117> ?adjudication .
  ?adjudication a <${base}BaseballAdjudicationAct> .
  ?batterAct a <${base}BatterAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  VALUES (?outcomeClass ?eventType) {
    (<${base}SingleProcess> "single") (<${base}DoubleProcess> "double") (<${base}TripleProcess> "triple") (<${base}HomeRunProcess> "home_run")
    (<${base}WalkProcess> "walk") (<${base}StrikeoutProcess> "strikeout") (<${base}HitByPitchProcess> "hit_by_pitch")
    (<${base}FieldersChoiceProcess> "fielders_choice") (<${base}ErrorProcess> "field_error") (<${base}SacrificeFlyProcess> "sac_fly")
    (<${base}SacrificeBuntProcess> "sac_bunt") (<${base}BattedBallOutProcess> "field_out") (<${base}ForceOutProcess> "force_out")
    (<${base}DoublePlayProcess> "double_play") (<${base}GroundedIntoDoublePlayProcess> "grounded_into_double_play")
    (<${base}BalkProcess> "balk") (<${base}InterferenceProcess> "catcher_interf")
  }
"@ -IndexPattern @"
  ?result a <${idx}PlateAppearanceResultFact> ; <${idx}plateAppearance> ?plateAppearance ; <${idx}agent> ?player ; <${idx}outcomeClass> ?outcomeClass ; <${idx}sourceEventType> ?eventType ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Hits' -Variables @('hit', 'player', 'hitClass', 'game', 'venue') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?hit a <${base}BaseballInstitutionalProcess>, ?hitClass ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000117> ?judgment ; <${cco}ont00001918> ?field .
  ?judgment a <${base}HitJudgmentAct> .
  ?batterAct a <${base}BatterAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
  VALUES ?hitClass { <${base}SingleProcess> <${base}DoubleProcess> <${base}TripleProcess> <${base}HomeRunProcess> }
"@ -IndexPattern @"
  ?hit a <${idx}HitFact> ; <${idx}agent> ?player ; <${idx}hitType> ?hitClass ; <${idx}game> ?game ; <${idx}venue> ?venue .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Pitches' -Variables @('pitch', 'player', 'plateAppearance', 'game', 'venue') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?pitch a <${base}PitchAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000063> ?motion ; <${cco}ont00001918> ?field .
  ?motion a <${base}PitchBallMotionProcess> .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
"@ -IndexPattern @"
  ?pitch a <${idx}PitchFact> ; <${idx}agent> ?player ; <${idx}plateAppearance> ?plateAppearance ; <${idx}game> ?game ; <${idx}venue> ?venue .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Pitch calls' -Variables @('call', 'pitch', 'player', 'callType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?pitch a <${base}PitchAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000063> ?motion .
  ?motion a <${base}PitchBallMotionProcess> .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?record a <${base}BaseballEventRecord> ; <${cco}ont00001808> ?pitch, ?call .
  ?call a ?callClass ; <${obo}BFO_0000117> ?judgment . ?judgment a ?judgmentClass .
  VALUES (?callClass ?judgmentClass ?callType) { (<${base}BallProcess> <${base}BallJudgmentAct> <${idx}Ball>) (<${base}StrikeProcess> <${base}StrikeJudgmentAct> <${idx}Strike>) (<${base}StrikeProcess> <${base}FoulTipJudgmentAct> <${idx}Strike>) }
"@ -IndexPattern @"
  ?call a <${idx}PitchCallFact> ; <${idx}pitch> ?pitch ; <${idx}agent> ?player ; <${idx}callType> ?callType ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Batting acts' -Variables @('battingAct', 'player', 'battingActClass', 'plateAppearance', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?battingAct a ?battingActClass ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000055> ?role .
  ?role a <${base}BatterRole> ; <${obo}BFO_0000197> ?player .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  VALUES ?battingActClass { <${base}SwingAct> <${base}BuntAct> }
"@ -IndexPattern @"
  ?battingAct a <${idx}BattingActFact> ; <${idx}agent> ?player ; <${idx}battingActType> ?battingActClass ; <${idx}plateAppearance> ?plateAppearance ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Contacts' -Variables @('contact', 'player', 'battedBall', 'plateAppearance', 'game', 'venue') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?battedBall a <${base}BattedBallMotionProcess> ; <${obo}BFO_0000132> ?plateAppearance ; <${cco}ont00001918> ?field .
  ?contact a <${base}BatBallContactProcess> ; <${obo}BFO_0000063> ?battedBall .
  ?battingAct a ?actClass ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000063> ?contact .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
  VALUES ?actClass { <${base}SwingAct> <${base}BuntAct> }
"@ -IndexPattern @"
  ?contact a <${idx}ContactFact> ; <${idx}agent> ?player ; <${idx}battedBall> ?battedBall ; <${idx}plateAppearance> ?plateAppearance ; <${idx}game> ?game ; <${idx}venue> ?venue .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Runner resolutions' -Variables @('resolution', 'player', 'resolutionClass', 'eventType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?record a <${base}BaseballEventRecord> ; <${cco}ont00001808> ?resolution ; <${dcterms}identifier> ?eventType .
  ?resolution a <${base}RunnerResolutionProcess>, ?resolutionClass ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000117> ?judgment .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?player a <${cco}ont00001262> .
  ?judgment a ?judgmentClass .
  VALUES (?resolutionClass ?judgmentClass) { (<${base}RunProcess> <${base}RunJudgmentAct>) (<${base}OutProcess> <${base}OutJudgmentAct>) (<${base}SafeProcess> <${base}SafeJudgmentAct>) }
"@ -IndexPattern @"
  ?resolution a <${idx}RunnerResolutionFact> ; <${idx}agent> ?player ; <${idx}resolutionClass> ?resolutionClass ; <${idx}sourceEventType> ?eventType ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Stolen bases' -Variables @('stolenBase', 'player', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?stolenBase a <${base}StolenBaseProcess> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000117> ?judgment .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?player a <${cco}ont00001262> .
  ?judgment a <${base}StolenBaseJudgmentAct> .
"@ -IndexPattern @"
  ?stolenBase a <${idx}StolenBaseFact> ; <${idx}agent> ?player ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

Assert-EquivalentRows -Name 'Game assignments' -Variables @('role', 'assignee', 'assignmentType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?role a ?roleClass ; <${obo}BFO_0000197> ?assignee ; <${obo}BFO_0000054> ?game .
  VALUES (?roleClass ?assignmentType) { (<${base}HomeTeamRole> <${idx}HomeTeam>) (<${base}AwayTeamRole> <${idx}AwayTeam>) (<${base}UmpireRole> <${idx}Umpire>) (<${base}OfficialScorerRole> <${idx}OfficialScorer>) }
"@ -IndexPattern @"
  ?role a <${idx}AssignmentFact> ; <${idx}assignee> ?assignee ; <${idx}assignmentType> ?assignmentType ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
"@

if (-not $SkipManifestCheck) {
    $manifestPath = Join-Path $script:StateRoot "pipeline\manifests\game-$GamePk-query-index.json"
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.contractSha256 -ne (Get-QueryIndexContractHash)) {
        throw 'Query-index manifest has a stale generation contract hash.'
    }
    if ([int64]$manifest.indexTripleCount -le 0 -or [int64]$manifest.indexTripleCount -ge [int64]$manifest.sourceTripleCount) {
        throw 'Query-index manifest does not describe a smaller non-empty graph.'
    }
    Write-Host "Source triples: $($manifest.sourceTripleCount); index triples: $($manifest.indexTripleCount)"
}

Write-Host 'Query-index equivalence suite passed.'
