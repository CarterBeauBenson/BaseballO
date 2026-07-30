[CmdletBinding()]
param(
    [string] $InputJson,
    [string] $OutputFile
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
if ([string]$gameDocument.gameData.status.abstractGameState -ne 'Final') {
    throw "Game $gamePk is not final; RML execution is restricted to completed games."
}
$expectedPlateAppearanceCount = @($gameDocument.liveData.plays.allPlays).Count
$expectedPitchCount = 0
foreach ($play in @($gameDocument.liveData.plays.allPlays)) {
    foreach ($event in @($play.playEvents)) {
        if ($event.isPitch -eq $true) {
            $expectedPitchCount++
        }
    }
}
if ($expectedPlateAppearanceCount -eq 0 -or $expectedPitchCount -eq 0) {
    throw "Game $gamePk has no canonical plate appearances or pitches."
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

$mappingPath = Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl'
$mappingValidatorPath = Join-Path $script:RepositoryRoot 'mappings\direct\validate_direct_mapping.py'
$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-generated-rdf.py'
$java = Get-JavaExecutable
$mapper = Get-RMLMapperJar
$mappingBaseIri = 'https://baseballontology.org/mapping/mlb-direct'
$inputHashBefore = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
$mappingHash = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$stage = Join-Path $workDirectory ("rml-$gamePk-" + [Guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $stage)
$stageInput = Join-Path $stage 'game.json'
$stageMapping = Join-Path $stage 'mlb-direct.rml.ttl'
$stageOutput = Join-Path $stage "game-$gamePk.ttl"
$stageLog = Join-Path $stage 'rmlmapper.log'
$gamePkTemplateReference = '{$.gamePk}'
$venueTemplateReference = '{$.gameData.venue.id}'
$awayTeamTemplateReference = '{$.gameData.teams.away.id}'
$homeTeamTemplateReference = '{$.gameData.teams.home.id}'

try {
    & python $mappingValidatorPath $inputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Direct mapping preflight validation failed for game $gamePk."
    }

    Copy-Item -LiteralPath $inputPath -Destination $stageInput
    $stagedInputHash = (Get-FileHash -LiteralPath $stageInput -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($stagedInputHash -ne $inputHashBefore) {
        throw 'The staged game JSON is not byte-identical to the acquired input.'
    }

    # RML references are evaluated relative to the current JSONPath iterator. The
    # reusable mapping marks four root identifiers explicitly; materialize only
    # the isolated mapping copy so nested records retain deterministic game-scoped
    # IRIs without adding helper fields to the authoritative MLB JSON.
    $mappingText = Get-Content -LiteralPath $mappingPath -Raw
    $gamePkReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($gamePkTemplateReference))).Count
    $venueReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($venueTemplateReference))).Count
    $awayTeamReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($awayTeamTemplateReference))).Count
    $homeTeamReferenceCount = ([regex]::Matches($mappingText, [regex]::Escape($homeTeamTemplateReference))).Count
    $absoluteReferenceCount = ([regex]::Matches($mappingText, '\{\$\.')).Count
    if ($gamePkReferenceCount -eq 0 -or $venueReferenceCount -eq 0 -or $awayTeamReferenceCount -eq 0 -or $homeTeamReferenceCount -eq 0) {
        throw 'The mapping does not contain the expected root identifier template references.'
    }
    $recognizedReferenceCount = $gamePkReferenceCount + $venueReferenceCount + $awayTeamReferenceCount + $homeTeamReferenceCount
    if ($absoluteReferenceCount -ne $recognizedReferenceCount) {
        throw 'The mapping contains an unrecognized absolute JSONPath template reference.'
    }
    $materializedMapping = $mappingText.Replace($gamePkTemplateReference, $gamePk)
    $materializedMapping = $materializedMapping.Replace($venueTemplateReference, $venueId)
    $materializedMapping = $materializedMapping.Replace($awayTeamTemplateReference, $awayTeamId)
    $materializedMapping = $materializedMapping.Replace($homeTeamTemplateReference, $homeTeamId)
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

    & python $validatorPath $stageOutput $gamePk '--expected-plate-appearances' $expectedPlateAppearanceCount '--expected-batter-acts' $expectedPlateAppearanceCount '--expected-pitches' $expectedPitchCount
    if ($LASTEXITCODE -ne 0) {
        throw "Generated RDF validation failed for game $gamePk."
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
        effectiveMappingSha256 = $effectiveMappingHash
        materializedRootReferences = [ordered]@{
            gamePk = $gamePkReferenceCount
            venueId = $venueReferenceCount
            awayTeamId = $awayTeamReferenceCount
            homeTeamId = $homeTeamReferenceCount
        }
        mappingBaseIri = $mappingBaseIri
        mapperVersion = $script:Versions.RMLMapper.Version
        serialization = 'turtle'
        sourceCounts = [ordered]@{
            plateAppearances = $expectedPlateAppearanceCount
            batterActs = $expectedPlateAppearanceCount
            pitches = $expectedPitchCount
        }
        outputPath = $outputPath
        outputSha256 = $outputHash
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
