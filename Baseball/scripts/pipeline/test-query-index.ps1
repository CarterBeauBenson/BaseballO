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
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not running on port 3031.'
}
if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $GamePk
}

$sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
$indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
$gameIri = "https://baseballontology.org/data/game/$GamePk"
$queryEndpoint = 'http://127.0.0.1:3031/baseball-dev/query'

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
$xsd = 'http://www.w3.org/2001/XMLSchema#'

Assert-EquivalentRows -Name 'Game core dimensions' -Variables @('game', 'venue', 'gameStart') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${base}BaseballGame> ; <${cco}ont00001918> ?field ; <${obo}BFO_0000199>/<${obo}BFO_0000222> ?startInstant .
  ?timestamp a <${base}BaseballTimestampICE> ; <${cco}ont00001916> ?startInstant ; <${cco}ont00001767> ?gameStart .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
"@ -IndexPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${idx}GameFact> ; <${idx}venue> ?venue ; <${idx}gameStart> ?gameStart .
"@

Assert-EquivalentRows -Name 'Game dimensions' -Variables @('game', 'season', 'seasonPhase', 'venue') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${base}BaseballGame> ; <${cco}ont00001918> ?field ; <${obo}BFO_0000199>/<${obo}BFO_0000222> ?startInstant .
  ?timestamp a <${base}BaseballTimestampICE> ; <${cco}ont00001916> ?startInstant ; <${cco}ont00001767> ?gameStart .
  ?field a <${base}BaseballFieldSite> ; <${obo}BFO_0000171> ?venue .
  ?game <${obo}BFO_0000132> ?phase .
  ?phase a ?seasonPhase ; <${obo}BFO_0000132> ?seasonProcess .
  VALUES ?seasonPhase { <${base}BaseballPreseasonPhase> <${base}BaseballRegularSeasonPhase> <${base}BaseballPostseasonPhase> <${base}BaseballAllStarPhase> }
  BIND(<${xsd}integer>(STRAFTER(STR(?seasonProcess), "/data/season/")) AS ?season)
"@ -IndexPattern @"
  VALUES ?game { <$gameIri> }
  ?game a <${idx}GameFact> ; <${idx}season> ?season ; <${idx}seasonPhase> ?seasonPhase ; <${idx}venue> ?venue .
"@

Assert-EquivalentRows -Name 'Label fidelity' -Variables @('resource', 'label') -FullPattern @"
  ?resource <${rdfs}label> ?label .
"@ -IndexPattern @"
  ?resource <${rdfs}label> ?label .
"@

Assert-EquivalentRows -Name 'Plate appearances' -Variables @('plateAppearance', 'player', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?batterAct a <${base}BatterAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
"@ -IndexPattern @"
  ?plateAppearance a <${idx}PlateAppearanceFact> ; <${idx}agent> ?player ; <${idx}game> ?game .
  VALUES ?game { <$gameIri> }
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

Assert-EquivalentRows -Name 'Current pitch classifications' -Variables @('pitch', 'category', 'pitchType') -FullPattern @"
  ?pitch a <${base}PitchAct> ; <${cco}ont00001914> ?category .
  VALUES (?category ?pitchType) {
    (<${base}FourSeamFastballPitchTypeICE> <${base}FourSeamFastballPitchAct>) (<${base}SinkerPitchTypeICE> <${base}SinkerPitchAct>)
    (<${base}CutterPitchTypeICE> <${base}CutterPitchAct>) (<${base}SliderPitchTypeICE> <${base}SliderPitchAct>)
    (<${base}SweeperPitchTypeICE> <${base}SweeperPitchAct>) (<${base}SlurvePitchTypeICE> <${base}SlurvePitchAct>)
    (<${base}CurveballPitchTypeICE> <${base}CurveballPitchAct>) (<${base}KnuckleCurvePitchTypeICE> <${base}KnuckleCurvePitchAct>)
    (<${base}SlowCurvePitchTypeICE> <${base}SlowCurvePitchAct>) (<${base}ChangeupPitchTypeICE> <${base}ChangeupPitchAct>)
    (<${base}SplitterPitchTypeICE> <${base}SplitterPitchAct>) (<${base}ForkballPitchTypeICE> <${base}ForkballPitchAct>)
    (<${base}ScrewballPitchTypeICE> <${base}ScrewballPitchAct>) (<${base}KnuckleballPitchTypeICE> <${base}KnuckleballPitchAct>)
    (<${base}EephusPitchTypeICE> <${base}EephusPitchAct>)
  }
"@ -IndexPattern @"
  ?pitch a <${idx}PitchFact>, ?pitchType ; <${idx}nominalCategory> ?category ; <${idx}pitchType> ?pitchType .
  VALUES ?pitchType {
    <${base}FourSeamFastballPitchAct> <${base}SinkerPitchAct> <${base}CutterPitchAct> <${base}SliderPitchAct> <${base}SweeperPitchAct>
    <${base}SlurvePitchAct> <${base}CurveballPitchAct> <${base}KnuckleCurvePitchAct> <${base}SlowCurvePitchAct> <${base}ChangeupPitchAct>
    <${base}SplitterPitchAct> <${base}ForkballPitchAct> <${base}ScrewballPitchAct> <${base}KnuckleballPitchAct> <${base}EephusPitchAct>
  }
"@

Assert-EquivalentRows -Name 'Pitch calls' -Variables @('call', 'pitch', 'player', 'callType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?pitch a <${base}PitchAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000063> ?motion .
  ?motion a <${base}PitchBallMotionProcess> .
  ?player a <${cco}ont00001262> .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?record a <${base}BaseballEventRecord> ; <${cco}ont00001808> ?pitch .
  BIND(IRI(CONCAT(STR(?pitch), "/call-fact")) AS ?call)
  { ?record <${cco}ont00001808> ?evidence . ?evidence a <${base}BallProcess> . BIND(<${idx}Ball> AS ?callType) }
  UNION { ?record <${cco}ont00001808> ?evidence . ?evidence a <${base}StrikeCallAct> . BIND(<${idx}CalledStrike> AS ?callType) }
  UNION {
    ?record <${cco}ont00001808> ?evidence, ?battingAct . ?evidence a <${base}StrikeProcess> .
    ?battingAct a ?battingActClass . VALUES ?battingActClass { <${base}SwingAct> <${base}BuntAct> }
    FILTER NOT EXISTS { ?record <${cco}ont00001808> ?foulBall . ?foulBall a <${base}FoulBallProcess> }
    FILTER NOT EXISTS { ?record <${cco}ont00001808> ?foulTip . ?foulTip a <${base}FoulTipProcess> }
    FILTER NOT EXISTS { ?record <${cco}ont00001808> ?fairBall . ?fairBall a <${base}FairBallProcess> }
    BIND(<${idx}SwingingStrike> AS ?callType)
  }
  UNION { ?record <${cco}ont00001808> ?evidence . ?evidence a ?foulType . VALUES ?foulType { <${base}FoulBallProcess> <${base}FoulTipProcess> } BIND(<${idx}Foul> AS ?callType) }
  UNION { ?record <${cco}ont00001808> ?evidence . ?evidence a <${base}FairBallProcess> . BIND(<${idx}InPlay> AS ?callType) }
  UNION {
    ?evidence a <${base}HitByPitchProcess> ; <${obo}BFO_0000132> ?plateAppearance .
    ?pitch <${obo}BFO_0000199>/<${obo}BFO_0000224> ?pitchEndInstant .
    ?pitchEndTimestamp a <${base}BaseballTimestampICE> ; <${cco}ont00001916> ?pitchEndInstant ; <${cco}ont00001767> ?pitchEnd .
    FILTER NOT EXISTS {
      ?laterPitch a <${base}PitchAct> ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000199>/<${obo}BFO_0000224> ?laterPitchEndInstant .
      ?laterPitchEndTimestamp a <${base}BaseballTimestampICE> ; <${cco}ont00001916> ?laterPitchEndInstant ; <${cco}ont00001767> ?laterPitchEnd .
      FILTER (?laterPitchEnd > ?pitchEnd)
    }
    BIND(<${idx}HitByPitch> AS ?callType)
  }
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

Assert-EquivalentRows -Name 'Current batted-ball trajectories' -Variables @('contact', 'battedBall', 'category', 'trajectoryType') -FullPattern @"
  ?contact a <${base}BatBallContactProcess> ; <${obo}BFO_0000063> ?battedBall .
  ?battedBall a <${base}BattedBallMotionProcess> ; <${cco}ont00001914> ?category .
  VALUES (?category ?trajectoryType) {
    (<${base}GroundBallTrajectoryICE> <${base}GroundBallMotionProcess>)
    (<${base}LineDriveTrajectoryICE> <${base}LineDriveMotionProcess>)
    (<${base}FlyBallTrajectoryICE> <${base}FlyBallMotionProcess>)
    (<${base}PopUpTrajectoryICE> <${base}PopUpMotionProcess>)
  }
"@ -IndexPattern @"
  ?contact a <${idx}ContactFact> ; <${idx}battedBall> ?battedBall ; <${idx}nominalCategory> ?category ; <${idx}trajectoryType> ?trajectoryType .
  ?battedBall a ?trajectoryType .
  VALUES ?trajectoryType { <${base}GroundBallMotionProcess> <${base}LineDriveMotionProcess> <${base}FlyBallMotionProcess> <${base}PopUpMotionProcess> }
"@

Assert-EquivalentRows -Name 'Runner resolutions' -Variables @('resolution', 'player', 'resolutionClass', 'eventType', 'game') -FullPattern @"
  VALUES ?game { <$gameIri> }
  ?record a <${base}BaseballEventRecord> ; <${cco}ont00001808> ?resolution .
  ?resolution a <${base}RunnerResolutionProcess>, ?resolutionClass ; <${obo}BFO_0000132> ?plateAppearance ; <${obo}BFO_0000057> ?player ; <${obo}BFO_0000117> ?judgment .
  ?plateAppearance a <${base}PlateAppearance> ; <${obo}BFO_0000132>/<${obo}BFO_0000132>/<${obo}BFO_0000132> ?game .
  ?player a <${cco}ont00001262> .
  ?judgment a ?judgmentClass .
  VALUES (?resolutionClass ?judgmentClass) { (<${base}RunProcess> <${base}RunJudgmentAct>) (<${base}OutProcess> <${base}OutJudgmentAct>) (<${base}SafeProcess> <${base}SafeJudgmentAct>) }
  OPTIONAL {
    ?record <${cco}ont00001808> ?specificResolution . ?specificResolution a ?specificResolutionClass .
    VALUES (?specificResolutionClass ?specificEventType) {
      (<${base}StolenBaseProcess> "stolen_base") (<${base}PassedBallProcess> "passed_ball")
      (<${base}WildPitchProcess> "wild_pitch") (<${base}UncaughtThirdStrikeProcess> "uncaught_third_strike")
    }
  }
  BIND(COALESCE(?specificEventType, IF(?resolutionClass = <${base}RunProcess>, "run", IF(?resolutionClass = <${base}OutProcess>, "out", "safe"))) AS ?eventType)
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
    $manifestAdmission = Resolve-QueryIndexManifestAdmission -Manifest $manifest
    $expectedIndexPath = [System.IO.Path]::GetFullPath(
        (Join-Path $script:StateRoot "pipeline\query-index\game-$GamePk.nt")
    )
    $manifestIndexPath = [System.IO.Path]::GetFullPath([string]$manifest.indexPath)
    if (
        [string]$manifest.sourceGraph -ne $sourceGraph -or
        [string]$manifest.indexGraph -ne $indexGraph -or
        [string]$manifest.indexResource -ne "https://w3id.org/baseball/query-index-build/game/$GamePk" -or
        $manifestIndexPath -ne $expectedIndexPath -or
        -not (Test-Path -LiteralPath $expectedIndexPath -PathType Leaf) -or
        (Get-FileHash -LiteralPath $expectedIndexPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$manifest.indexSha256
    ) {
        throw 'Query-index manifest output identity or artifact hash is invalid.'
    }
    if ([int64]$manifest.indexTripleCount -le 0 -or [int64]$manifest.indexTripleCount -ge [int64]$manifest.sourceTripleCount) {
        throw 'Query-index manifest does not describe a smaller non-empty graph.'
    }
    Write-Host "Semantic contract: $($manifestAdmission.SemanticContractId) ($($manifestAdmission.Mode)); implementation provenance: $($manifestAdmission.ImplementationSha256)"
    Write-Host "Source triples: $($manifest.sourceTripleCount); index triples: $($manifest.indexTripleCount)"
}

Write-Host 'Query-index equivalence suite passed.'
