[CmdletBinding()]
param(
    [string] $InputJson,
    [string] $OutputFile,
    [string] $ScheduleEvidencePath,
    [switch] $DeferShaclValidation
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

if ([string]::IsNullOrWhiteSpace($InputJson)) {
    $InputJson = Join-Path $script:RepositoryRoot 'data\raw\game-566279.json'
}
$inputPath = [System.IO.Path]::GetFullPath($InputJson)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "Input game JSON was not found: $inputPath"
}

$gameDocument = Get-Content -LiteralPath $inputPath -Raw | ConvertFrom-Json
$gamePk = [string]$gameDocument.gamePk
if ([string]::IsNullOrWhiteSpace($gamePk)) {
    throw 'Input JSON has no gamePk.'
}
if ($gamePk -notmatch '^\d+$') {
    throw "Input JSON has an unsafe gamePk value: $gamePk"
}
$venueId = [string]$gameDocument.gameData.venue.id
if ([string]::IsNullOrWhiteSpace($venueId) -or $venueId -notmatch '^\d+$') {
    throw "Game $gamePk has no safe numeric gameData.venue.id value."
}
$awayTeamId = [string]$gameDocument.gameData.teams.away.id
$homeTeamId = [string]$gameDocument.gameData.teams.home.id
if ($awayTeamId -notmatch '^\d+$' -or $homeTeamId -notmatch '^\d+$') {
    throw "Game $gamePk has no safe numeric away/home team identifier values."
}
$officialScorerId = [string]$gameDocument.gameData.officialScorer.id
if (-not [string]::IsNullOrWhiteSpace($officialScorerId) -and $officialScorerId -notmatch '^\d+$') {
    throw "Game $gamePk has an unsafe official scorer identifier: $officialScorerId"
}
$homePlateUmpire = @($gameDocument.liveData.boxscore.officials | Where-Object { $_.officialType -eq 'Home Plate' }) | Select-Object -First 1
$homePlateUmpireId = [string]$homePlateUmpire.official.id
if (-not [string]::IsNullOrWhiteSpace($homePlateUmpireId) -and $homePlateUmpireId -notmatch '^\d+$') {
    throw "Game $gamePk has an unsafe home-plate umpire identifier: $homePlateUmpireId"
}
if ([string]$gameDocument.gameData.status.abstractGameState -ne 'Final') {
    throw "Game $gamePk is not final; RML execution is restricted to completed games."
}
$resolvedScheduleEvidencePath = $null
if (-not [string]::IsNullOrWhiteSpace($ScheduleEvidencePath) -and $ScheduleEvidencePath -ne 'none') {
    $resolvedScheduleEvidencePath = [System.IO.Path]::GetFullPath($ScheduleEvidencePath)
    $scheduleEvidenceRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $script:StateRoot 'pipeline\control\mlb-game\schedule-evidence')
    )
    $scheduleEvidencePrefix = $scheduleEvidenceRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $resolvedScheduleEvidencePath.StartsWith($scheduleEvidencePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Schedule evidence is outside the MLB-game control root: $resolvedScheduleEvidencePath"
    }
    if (-not (Test-Path -LiteralPath $resolvedScheduleEvidencePath -PathType Leaf)) {
        throw "Schedule evidence does not exist: $resolvedScheduleEvidencePath"
    }
    $scheduleEvidenceDocument = Get-Content -LiteralPath $resolvedScheduleEvidencePath -Raw | ConvertFrom-Json
    if ([string]$scheduleEvidenceDocument.gamePk -ne $gamePk) {
        throw "Schedule evidence gamePk does not match game $gamePk."
    }
}
$expectedPlateAppearanceCount = @($gameDocument.liveData.plays.allPlays).Count
$expectedPlayerParticipantCount = @(
    @($gameDocument.liveData.boxscore.teams.away.players.PSObject.Properties) +
        @($gameDocument.liveData.boxscore.teams.home.players.PSObject.Properties) |
        ForEach-Object { [string]$_.Value.person.id } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
).Count
$expectedGameEndTime = [string]@($gameDocument.liveData.plays.allPlays)[-1].about.endTime
$expectedPitchCount = 0
$expectedBattingActCount = 0
$expectedContactCount = 0
$expectedRunnerRecordCount = 0
$expectedRunnerResolutionCount = 0
$passedBallEventIds = [System.Collections.Generic.HashSet[string]]::new()
$wildPitchEventIds = [System.Collections.Generic.HashSet[string]]::new()
$expectedUncaughtThirdStrikeCount = 0
foreach ($play in @($gameDocument.liveData.plays.allPlays)) {
    $expectedRunnerRecordCount += @($play.runners).Count
    $hasNullBatterStrikeout = $false
    $safeBatterClassificationTypes = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($runner in @($play.runners)) {
        if ($runner.movement.isOut -is [bool]) {
            $expectedRunnerResolutionCount++
        }
        $runnerEventType = [string]$runner.details.eventType
        if ($runnerEventType -in @('passed_ball', 'wild_pitch')) {
            $playIndex = [int]$runner.details.playIndex
            $classificationEvent = @($play.playEvents)[$playIndex]
            $classificationPlayId = ''
            if ($classificationEvent.PSObject.Properties.Name -contains 'playId') {
                $classificationPlayId = [string]$classificationEvent.playId
            }
            if ($classificationEvent.isPitch -ne $true -or [string]::IsNullOrWhiteSpace($classificationPlayId)) {
                $classificationPitchEvent = @(
                    $play.playEvents |
                        Where-Object {
                            $_.isPitch -eq $true -and
                            $_.index -le $playIndex -and
                            $_.PSObject.Properties.Name -contains 'playId' -and
                            -not [string]::IsNullOrWhiteSpace([string]$_.playId)
                        } |
                        Select-Object -Last 1
                )
                if ($classificationPitchEvent.Count -gt 0) {
                    $classificationPlayId = [string]$classificationPitchEvent[0].playId
                }
            }
            if ([string]::IsNullOrWhiteSpace($classificationPlayId)) {
                throw "Game $gamePk play $($play.about.atBatIndex) has a $runnerEventType row without a source playId."
            }
            if ($runnerEventType -eq 'passed_ball') {
                [void]$passedBallEventIds.Add($classificationPlayId)
            }
            else {
                [void]$wildPitchEventIds.Add($classificationPlayId)
            }
        }
        if (
            $runnerEventType -eq 'strikeout' -and
            [string]$runner.details.runner.id -eq [string]$play.matchup.batter.id -and
            $null -eq $runner.movement.isOut
        ) {
            $hasNullBatterStrikeout = $true
        }
        if (
            $runnerEventType -in @('passed_ball', 'wild_pitch') -and
            [string]$runner.details.runner.id -eq [string]$play.matchup.batter.id -and
            $runner.movement.isOut -eq $false -and
            [string]$runner.movement.end -eq '1B'
        ) {
            [void]$safeBatterClassificationTypes.Add($runnerEventType)
        }
    }
    if (
        [string]$play.result.eventType -eq 'strikeout' -and
        $hasNullBatterStrikeout -and
        $safeBatterClassificationTypes.Count -eq 1
    ) {
        $expectedUncaughtThirdStrikeCount++
    }
    foreach ($event in @($play.playEvents)) {
        if ($event.isPitch -eq $true) {
            $expectedPitchCount++
            $callCode = [string]$event.details.call.code
            $trajectory = ''
            if (
                $event.PSObject.Properties.Name -contains 'hitData' -and
                $null -ne $event.hitData -and
                $event.hitData.PSObject.Properties.Name -contains 'trajectory'
            ) {
                $trajectory = [string]$event.hitData.trajectory
            }
            $isBuntAttempt = (
                $callCode -in @('L', 'M', 'O') -or
                $trajectory -in @('bunt_grounder', 'bunt_popup', 'bunt_line_drive')
            )
            if ($isBuntAttempt -or $callCode -in @('S', 'W', 'F', 'T', 'X', 'D', 'E')) {
                $expectedBattingActCount++
            }
            if (
                $callCode -in @('F', 'T') -or
                (-not $isBuntAttempt -and $callCode -in @('X', 'D', 'E')) -or
                ($isBuntAttempt -and $callCode -ne 'M')
            ) {
                $expectedContactCount++
            }
        }
    }
}
if ($expectedPlateAppearanceCount -eq 0 -or $expectedPitchCount -eq 0) {
    throw "Game $gamePk has no canonical plate appearances or pitches."
}
if ([string]::IsNullOrWhiteSpace($expectedGameEndTime)) {
    throw "Game $gamePk has no final play end timestamp."
}

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$rdfDirectory = Join-Path $pipelineRoot 'rdf'
$manifestDirectory = Join-Path $pipelineRoot 'manifests'
$workDirectory = Join-Path $pipelineRoot 'work'
$quarantineDirectory = Join-Path $pipelineRoot 'quarantine\rml'
foreach ($directory in @($rdfDirectory, $manifestDirectory, $workDirectory, $quarantineDirectory)) {
    [void](New-Item -ItemType Directory -Force -Path $directory)
}

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $OutputFile = Join-Path $rdfDirectory "game-$gamePk.ttl"
}
$outputPath = [System.IO.Path]::GetFullPath($OutputFile)
[void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath))

$mappingPath = Join-Path $script:RepositoryRoot 'sources\mlb-game\mapping\mlb-game.rml.ttl'
$mappingValidatorPath = Join-Path $script:RepositoryRoot 'sources\mlb-game\mapping\validate_mlb_game_mapping.py'
$contextBuilderPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\prepare-rml-context.py'
$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-generated-rdf.py'
$shaclValidatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-shacl.py'
$authoritativeShapePath = Join-Path $script:RepositoryRoot 'sources\mlb-game\shacl\authoritative.ttl'
$semanticAdmissionValidatorPath = Join-Path $script:RepositoryRoot 'scripts\validate_semantic_change_control.py'
$semanticFreezePath = Join-Path $script:RepositoryRoot 'governance\semantic-freeze.json'
$java = Get-JavaExecutable
$mapper = Get-RMLMapperJar
$mappingBaseIri = 'https://baseballontology.org/mapping/mlb-direct'
$inputHashBefore = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$mappingHash = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$stage = Join-Path $workDirectory ("rml-$gamePk-" + [Guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $stage)
$stageInput = Join-Path $stage 'game.json'
$stageContext = Join-Path $stage 'game-context.json'
$stageMapping = Join-Path $stage 'mlb-game.rml.ttl'
$stageOutput = Join-Path $stage "game-$gamePk.ttl"
$stageLog = Join-Path $stage 'rmlmapper.log'
$gamePkTemplateReference = '{$.gamePk}'
$venueTemplateReference = '{$.gameData.venue.id}'
$awayTeamTemplateReference = '{$.gameData.teams.away.id}'
$homeTeamTemplateReference = '{$.gameData.teams.home.id}'
$officialScorerTemplateReference = '{$.gameData.officialScorer.id}'
$homePlateUmpireTemplateReference = '{$.homePlateUmpire.id}'

try {
    & python $semanticAdmissionValidatorPath '--runtime-admission' 'mlb-game'
    if ($LASTEXITCODE -ne 0) {
        throw "The MLB game semantic artifacts do not match their frozen runtime admission."
    }

    & python $mappingValidatorPath $inputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Direct mapping preflight validation failed for game $gamePk."
    }

    Copy-Item -LiteralPath $inputPath -Destination $stageInput
    $stagedInputHash = (Get-FileHash -LiteralPath $stageInput -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($stagedInputHash -ne $inputHashBefore) {
        throw 'The staged game JSON is not byte-identical to the acquired input.'
    }

    # RMLMapper evaluates a nested JSONPath record without access to its play
    # ancestors and does not expand parent array references as a multi-value
    # join. Generate an isolated execution-only copy that adds ancestor IDs to
    # pitch records. The staged and authoritative raw JSON remain byte-identical.
    $contextArguments = @($contextBuilderPath, $stageInput, $stageContext)
    if ($null -ne $resolvedScheduleEvidencePath) {
        $contextArguments += @('--schedule-evidence', $resolvedScheduleEvidencePath)
    }
    & python @contextArguments
    if ($LASTEXITCODE -ne 0) {
        throw "RML execution-context generation failed for game $gamePk."
    }
    if (-not (Test-Path -LiteralPath $stageContext -PathType Leaf)) {
        throw "RML execution-context generation produced no file for game $gamePk."
    }
    $contextHash = (Get-FileHash -LiteralPath $stageContext -Algorithm SHA256).Hash.ToLowerInvariant()

    # RML references are evaluated relative to the current JSONPath iterator. The
    # The reusable mapping marks guarded root identifiers explicitly; materialize only
    # the isolated mapping copy so nested records retain deterministic game-scoped
    # IRIs without adding helper fields to the authoritative MLB JSON.
    $mappingText = Get-Content -LiteralPath $mappingPath -Raw
    $gamePkReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($gamePkTemplateReference))).Count
    $venueReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($venueTemplateReference))).Count
    $awayTeamReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($awayTeamTemplateReference))).Count
    $homeTeamReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($homeTeamTemplateReference))).Count
    $officialScorerReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($officialScorerTemplateReference))).Count
    $homePlateUmpireReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($homePlateUmpireTemplateReference))).Count
    $absoluteReferenceCount = ([regex]::Matches($mappingText, '\{\$\.')).Count
    if ($gamePkReferenceCount -eq 0 -or $venueReferenceCount -eq 0 -or $awayTeamReferenceCount -eq 0 -or $homeTeamReferenceCount -eq 0) {
        throw 'The mapping does not contain the expected root identifier template references.'
    }
    $recognizedReferenceCount = $gamePkReferenceCount + $venueReferenceCount + $awayTeamReferenceCount + $homeTeamReferenceCount + $officialScorerReferenceCount + $homePlateUmpireReferenceCount
    if ($absoluteReferenceCount -ne $recognizedReferenceCount) {
        throw 'The mapping contains an unrecognized absolute JSONPath template reference.'
    }
    $materializedMapping = $mappingText.Replace($gamePkTemplateReference, $gamePk)
    $materializedMapping = $materializedMapping.Replace($venueTemplateReference, $venueId)
    $materializedMapping = $materializedMapping.Replace($awayTeamTemplateReference, $awayTeamId)
    $materializedMapping = $materializedMapping.Replace($homeTeamTemplateReference, $homeTeamId)
    if ([string]::IsNullOrWhiteSpace($officialScorerId)) {
        $materializedMapping = [regex]::Replace(
            $materializedMapping,
            "(?m)^.*$([regex]::Escape($officialScorerTemplateReference)).*(?:\r?\n)?",
            ''
        )
    }
    else {
        $materializedMapping = $materializedMapping.Replace($officialScorerTemplateReference, $officialScorerId)
    }
    if ([string]::IsNullOrWhiteSpace($homePlateUmpireId)) {
        $materializedMapping = [regex]::Replace(
            $materializedMapping,
            "(?m)^.*$([regex]::Escape($homePlateUmpireTemplateReference)).*(?:\r?\n)?",
            ''
        )
    }
    else {
        $materializedMapping = $materializedMapping.Replace($homePlateUmpireTemplateReference, $homePlateUmpireId)
    }
    if ($materializedMapping.Contains('{$.')) {
        throw 'The staged mapping still contains an absolute JSONPath template reference.'
    }
    Set-Content -LiteralPath $stageMapping -Value $materializedMapping -Encoding UTF8
    $effectiveMappingHash = (Get-FileHash -LiteralPath $stageMapping -Algorithm SHA256).Hash.ToLowerInvariant()

    Push-Location $stage
    try {
        $previousErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $mapperOutput = & $java '-Xmx2g' '-jar' $mapper '-m' $stageMapping '-o' $stageOutput '-s' 'turtle' '-b' $mappingBaseIri '--strict' 2>&1
        $mapperExitCode = $LASTEXITCODE
        $ErrorActionPreference = $previousErrorPreference
        $mapperOutput | Set-Content -LiteralPath $stageLog -Encoding UTF8
    }
    finally {
        Pop-Location
    }
    if ($mapperExitCode -ne 0) {
        throw "RMLMapper failed for game $gamePk with exit code $mapperExitCode."
    }
    if (-not (Test-Path -LiteralPath $stageOutput -PathType Leaf) -or (Get-Item -LiteralPath $stageOutput).Length -eq 0) {
        throw "RMLMapper produced no RDF for game $gamePk."
    }

    & python $validatorPath $stageOutput $gamePk '--expected-player-participants' $expectedPlayerParticipantCount '--expected-plate-appearances' $expectedPlateAppearanceCount '--expected-batter-acts' $expectedPlateAppearanceCount '--expected-pitches' $expectedPitchCount '--expected-batting-acts' $expectedBattingActCount '--expected-contacts' $expectedContactCount '--expected-runner-records' $expectedRunnerRecordCount '--expected-runner-resolutions' $expectedRunnerResolutionCount '--expected-pitch-ball-control-failures' 0 '--expected-passed-balls' $passedBallEventIds.Count '--expected-wild-pitches' $wildPitchEventIds.Count '--expected-uncaught-third-strikes' $expectedUncaughtThirdStrikeCount '--expected-game-end' $expectedGameEndTime
    if ($LASTEXITCODE -ne 0) {
        throw "Generated RDF validation failed for game $gamePk."
    }

    if (-not $DeferShaclValidation) {
        & python $shaclValidatorPath '--profile' 'authoritative' '--data' $stageOutput
        if ($LASTEXITCODE -ne 0) {
            throw "Authoritative SHACL validation failed for game $gamePk."
        }
    }

    Copy-Item -LiteralPath $stageOutput -Destination $outputPath -Force
    $outputHash = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $inputHashAfter = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($inputHashAfter -ne $inputHashBefore) {
        throw 'The authoritative input JSON changed during RML execution.'
    }

    $manifestPath = Join-Path $manifestDirectory "game-$gamePk-rml.json"
    [PSCustomObject]@{
        gamePk = $gamePk
        graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
        inputPath = $inputPath
        inputSha256 = $inputHashBefore
        mappingPath = $mappingPath
        mappingSha256 = $mappingHash
        semanticFreezePath = $semanticFreezePath
        semanticFreezeSha256 = (Get-FileHash -LiteralPath $semanticFreezePath -Algorithm SHA256).Hash.ToLowerInvariant()
        semanticAdmission = 'mlb-game:frozen-known-debt'
        effectiveMappingSha256 = $effectiveMappingHash
        contextBuilderPath = $contextBuilderPath
        contextBuilderSha256 = (Get-FileHash -LiteralPath $contextBuilderPath -Algorithm SHA256).Hash.ToLowerInvariant()
        executionContextSha256 = $contextHash
        scheduleEvidencePath = $resolvedScheduleEvidencePath
        scheduleEvidenceSha256 = if ($null -eq $resolvedScheduleEvidencePath) { $null } else { (Get-FileHash -LiteralPath $resolvedScheduleEvidencePath -Algorithm SHA256).Hash.ToLowerInvariant() }
        materializedRootReferences = [ordered]@{
            gamePk = $gamePkReferenceCount
            venueId = $venueReferenceCount
            awayTeamId = $awayTeamReferenceCount
            homeTeamId = $homeTeamReferenceCount
            officialScorerId = $officialScorerReferenceCount
            homePlateUmpireId = $homePlateUmpireReferenceCount
        }
        mappingBaseIri = $mappingBaseIri
        mapperVersion = $script:Versions.RMLMapper.Version
        serialization = 'turtle'
        sourceCounts = [ordered]@{
            playerParticipants = $expectedPlayerParticipantCount
            plateAppearances = $expectedPlateAppearanceCount
            batterActs = $expectedPlateAppearanceCount
            pitches = $expectedPitchCount
            battingActs = $expectedBattingActCount
            contacts = $expectedContactCount
            runnerRecords = $expectedRunnerRecordCount
            runnerResolutions = $expectedRunnerResolutionCount
            pitchBallControlFailures = 0
            passedBalls = $passedBallEventIds.Count
            wildPitches = $wildPitchEventIds.Count
            uncaughtThirdStrikes = $expectedUncaughtThirdStrikeCount
        }
        outputPath = $outputPath
        outputSha256 = $outputHash
        shaclStatus = if ($DeferShaclValidation) { 'deferred-to-nifi' } else { 'validated' }
        shaclValidatedAtUtc = if ($DeferShaclValidation) { $null } else { [DateTime]::UtcNow.ToString('o') }
        shaclProfile = 'authoritative'
        shaclShapePath = $authoritativeShapePath
        shaclShapeSha256 = (Get-FileHash -LiteralPath $authoritativeShapePath -Algorithm SHA256).Hash.ToLowerInvariant()
        shaclValidatorSha256 = (Get-FileHash -LiteralPath $shaclValidatorPath -Algorithm SHA256).Hash.ToLowerInvariant()
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Write-Host "RML output: $outputPath"
    Write-Host "RML manifest: $manifestPath"
}
catch {
    $quarantine = Join-Path $quarantineDirectory ("game-$gamePk-" + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
    if (Test-Path -LiteralPath $stage -PathType Container) {
        Move-Item -LiteralPath $stage -Destination $quarantine
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $stage -PathType Container) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
