[CmdletBinding()]
param(
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string] $Date,
    [ValidateRange(1, 14)][int] $LookbackDays = 3,
    [ValidateRange(0, 100)][int] $MaxGames = 0,
    [ValidatePattern('^\d+$')][string] $GamePk,
    [ValidateRange(1, 5)][int] $RetryCount = 3,
    [switch] $SkipRdfLoad,
    [switch] $ForceRdfLoad,
    [switch] $ExternalDataAccessApproved
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
if (-not $ExternalDataAccessApproved) {
    throw 'External game acquisition is parked pending an approved data-access source. Use the manual inbox or pass -ExternalDataAccessApproved only after that issue is resolved.'
}
Initialize-LocalLayout

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$workRoot = Join-Path $pipelineRoot 'work\acquisition'
$rawScheduleRoot = Join-Path $pipelineRoot 'raw\schedules'
$rawGameRoot = Join-Path $pipelineRoot 'raw\games'
$scheduleManifestRoot = Join-Path $pipelineRoot 'manifests\acquisition\schedules'
$gameManifestRoot = Join-Path $pipelineRoot 'manifests\acquisition\games'
$runManifestRoot = Join-Path $pipelineRoot 'manifests\runs\games'
$quarantineRoot = Join-Path $pipelineRoot 'quarantine\acquisition'
foreach ($directory in @($workRoot, $rawScheduleRoot, $rawGameRoot, $scheduleManifestRoot, $gameManifestRoot, $runManifestRoot, $quarantineRoot)) {
    [void](New-Item -ItemType Directory -Force -Path $directory)
}

$runId = [Guid]::NewGuid().ToString('N')
$runStartedAt = [DateTime]::UtcNow
$runStamp = $runStartedAt.ToString('yyyyMMddTHHmmssfffZ')
$runWork = Join-Path $workRoot $runId
[void](New-Item -ItemType Directory -Path $runWork)
$runQuarantined = $false

function Get-AcquisitionDates {
    if (-not [string]::IsNullOrWhiteSpace($Date)) {
        return @([DateTime]::ParseExact($Date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture))
    }

    $through = (Get-Date).Date.AddDays(-1)
    $dates = @()
    for ($offset = $LookbackDays - 1; $offset -ge 0; $offset--) {
        $dates += $through.AddDays(-$offset)
    }
    return $dates
}

function Invoke-JsonDownload {
    param(
        [Parameter(Mandatory = $true)][string] $Uri,
        [Parameter(Mandatory = $true)][string] $Destination
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        try {
            if (Test-Path -LiteralPath $Destination -PathType Leaf) {
                Remove-Item -LiteralPath $Destination -Force
            }
            $response = Invoke-WebRequest -Uri $Uri -Method Get -OutFile $Destination -PassThru -UseBasicParsing -TimeoutSec 60 -Headers @{
                Accept = 'application/json'
                'User-Agent' = 'BaseballO-local-pipeline/0.1'
            }
            if ([int]$response.StatusCode -ne 200) {
                throw "Unexpected HTTP status $($response.StatusCode) from $Uri"
            }
            if (-not (Test-Path -LiteralPath $Destination -PathType Leaf) -or (Get-Item -LiteralPath $Destination).Length -eq 0) {
                throw "MLB returned an empty response body from $Uri"
            }
            return $response
        }
        catch {
            $lastError = $_
            if ($attempt -lt $RetryCount) {
                Start-Sleep -Seconds ([math]::Pow(2, $attempt - 1))
            }
        }
    }
    throw "MLB request failed after $RetryCount attempts: $Uri`n$lastError"
}

function Save-ContentAddressedArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $TemporaryPath,
        [Parameter(Mandatory = $true)][string] $DestinationDirectory
    )

    [void](New-Item -ItemType Directory -Force -Path $DestinationDirectory)
    $hash = (Get-FileHash -LiteralPath $TemporaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $destination = Join-Path $DestinationDirectory "$hash.json"
    $archivedNew = $false
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $existingHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingHash -ne $hash) {
            throw "Content-addressed archive collision at $destination"
        }
        Remove-Item -LiteralPath $TemporaryPath -Force
    }
    else {
        Move-Item -LiteralPath $TemporaryPath -Destination $destination
        $archivedNew = $true
    }
    return [PSCustomObject]@{
        Path = $destination
        Sha256 = $hash
        ByteCount = (Get-Item -LiteralPath $destination).Length
        ArchivedNew = $archivedNew
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] $Value,
        [Parameter(Mandatory = $true)][string] $Path
    )

    [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path))
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-MediaType($Response) {
    $contentType = [string]$Response.Headers['Content-Type']
    if ([string]::IsNullOrWhiteSpace($contentType)) {
        return 'application/json'
    }
    return $contentType
}

function Test-GameGraphCurrent {
    param(
        [Parameter(Mandatory = $true)][string] $GamePkValue,
        [Parameter(Mandatory = $true)][string] $InputSha256
    )

    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
        return $false
    }
    $rmlManifestPath = Join-Path $pipelineRoot "manifests\game-$GamePkValue-rml.json"
    if (-not (Test-Path -LiteralPath $rmlManifestPath -PathType Leaf)) {
        return $false
    }
    try {
        $rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
        $currentMappingHash = (Get-FileHash -LiteralPath (Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl') -Algorithm SHA256).Hash.ToLowerInvariant()
        if ([string]$rmlManifest.inputSha256 -ne $InputSha256 -or [string]$rmlManifest.mappingSha256 -ne $currentMappingHash -or [string]$rmlManifest.mapperVersion -ne [string]$script:Versions.RMLMapper.Version) {
            return $false
        }
    }
    catch {
        return $false
    }
    $graphIri = "https://w3id.org/baseball/graph/game/$GamePkValue"
    $gameIri = "https://baseballontology.org/data/game/$GamePkValue"
    $query = "ASK { GRAPH <$graphIri> { <$gameIri> a <https://baseballontology.org/BaseballGame> } }"
    try {
        $result = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
        return $result.boolean -eq $true
    }
    catch {
        return $false
    }
}

$dates = @()
$dateStrings = @()
$scheduleResults = @()
$candidateGames = @{}
$gameResults = @()
$runManifestPath = Join-Path $runManifestRoot "$runStamp-$runId.json"

try {
    $dates = @(Get-AcquisitionDates)
    $dateStrings = @($dates | ForEach-Object { $_.ToString('yyyy-MM-dd') })
    foreach ($dateString in $dateStrings) {
        $scheduleUri = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=$dateString"
        $scheduleTemp = Join-Path $runWork "schedule-$dateString.json.partial"
        $retrievedAt = [DateTime]::UtcNow
        $response = Invoke-JsonDownload -Uri $scheduleUri -Destination $scheduleTemp
        try {
            $schedule = Get-Content -LiteralPath $scheduleTemp -Raw | ConvertFrom-Json
        }
        catch {
            throw "MLB schedule response for $dateString is not valid JSON: $_"
        }
        $archive = Save-ContentAddressedArtifact -TemporaryPath $scheduleTemp -DestinationDirectory (Join-Path $rawScheduleRoot $dateString)
        $scheduleManifestPath = Join-Path (Join-Path $scheduleManifestRoot $dateString) "$runStamp-$runId.json"
        $scheduleManifest = [ordered]@{
            artifactType = 'mlb-schedule'
            scheduleDate = $dateString
            sourceUrl = $scheduleUri
            httpStatus = [int]$response.StatusCode
            retrievedAtUtc = $retrievedAt.ToString('o')
            contentSha256 = $archive.Sha256
            byteCount = $archive.ByteCount
            mediaType = Get-MediaType $response
            pipelineRunId = $runId
            rawPath = $archive.Path
            archivedNew = $archive.ArchivedNew
        }
        Write-JsonFile -Value $scheduleManifest -Path $scheduleManifestPath

        $games = @($schedule.dates | ForEach-Object { $_.games })
        $scheduleResults += [PSCustomObject]@{
            Date = $dateString
            Games = $games.Count
            FinalGames = @($games | Where-Object { $_.status.abstractGameState -eq 'Final' }).Count
            RawPath = $archive.Path
            ArchivedNew = $archive.ArchivedNew
        }
        foreach ($game in $games) {
            $candidateGamePk = [string]$game.gamePk
            if ($candidateGamePk -notmatch '^\d+$') {
                throw "Schedule $dateString contains an unsafe gamePk value: $candidateGamePk"
            }
            if (-not [string]::IsNullOrWhiteSpace($GamePk) -and $candidateGamePk -ne $GamePk) {
                continue
            }
            if ($game.status.abstractGameState -eq 'Final') {
                $candidateGames[$candidateGamePk] = [PSCustomObject]@{
                    GamePk = $candidateGamePk
                    ScheduleDate = $dateString
                    Season = [string]$game.season
                    DetailedState = [string]$game.status.detailedState
                }
            }
        }
    }

    $selectedGames = @($candidateGames.Values | Sort-Object ScheduleDate, GamePk)
    if ($MaxGames -gt 0) {
        $selectedGames = @($selectedGames | Select-Object -First $MaxGames)
    }

    foreach ($candidate in $selectedGames) {
        $gamePkValue = [string]$candidate.GamePk
        $gameUri = "https://statsapi.mlb.com/api/v1.1/game/$gamePkValue/feed/live"
        $gameTemp = Join-Path $runWork "game-$gamePkValue.json.partial"
        $retrievedAt = [DateTime]::UtcNow
        $gameArchivePath = $null
        $gameArchivedNew = $false
        try {
            $response = Invoke-JsonDownload -Uri $gameUri -Destination $gameTemp
            try {
                $feed = Get-Content -LiteralPath $gameTemp -Raw | ConvertFrom-Json
            }
            catch {
                throw "MLB feed/live response for game $gamePkValue is not valid JSON: $_"
            }
            if ([string]$feed.gamePk -ne $gamePkValue) {
                throw "MLB feed/live identity mismatch: requested $gamePkValue, received $($feed.gamePk)"
            }
            $season = [string]$feed.gameData.game.season
            if ($season -notmatch '^\d{4}$') {
                $season = [string]$candidate.Season
            }
            if ($season -notmatch '^\d{4}$') {
                throw "Game $gamePkValue has no safe four-digit season value."
            }

            $archiveDirectory = Join-Path (Join-Path $rawGameRoot $season) $gamePkValue
            $archive = Save-ContentAddressedArtifact -TemporaryPath $gameTemp -DestinationDirectory $archiveDirectory
            $gameArchivePath = $archive.Path
            $gameArchivedNew = $archive.ArchivedNew
            $gameManifestPath = Join-Path (Join-Path (Join-Path $gameManifestRoot $season) $gamePkValue) "$runStamp-$runId.json"
            $gameManifest = [ordered]@{
                artifactType = 'mlb-feed-live'
                gamePk = $gamePkValue
                season = $season
                scheduleDate = $candidate.ScheduleDate
                scheduledDetailedState = $candidate.DetailedState
                feedAbstractGameState = [string]$feed.gameData.status.abstractGameState
                feedDetailedState = [string]$feed.gameData.status.detailedState
                sourceUrl = $gameUri
                httpStatus = [int]$response.StatusCode
                retrievedAtUtc = $retrievedAt.ToString('o')
                contentSha256 = $archive.Sha256
                byteCount = $archive.ByteCount
                mediaType = Get-MediaType $response
                pipelineRunId = $runId
                rawPath = $archive.Path
                archivedNew = $archive.ArchivedNew
            }
            Write-JsonFile -Value $gameManifest -Path $gameManifestPath

            if ([string]$feed.gameData.status.abstractGameState -ne 'Final') {
                $gameResults += [PSCustomObject]@{
                    GamePk = $gamePkValue
                    Status = 'deferred-not-final'
                    RawPath = $archive.Path
                    ArchivedNew = $archive.ArchivedNew
                    Error = $null
                }
                continue
            }

            if ($SkipRdfLoad) {
                $gameResults += [PSCustomObject]@{
                    GamePk = $gamePkValue
                    Status = 'archived-only'
                    RawPath = $archive.Path
                    ArchivedNew = $archive.ArchivedNew
                    Error = $null
                }
                continue
            }

            if (-not $ForceRdfLoad -and -not $archive.ArchivedNew -and (Test-GameGraphCurrent -GamePkValue $gamePkValue -InputSha256 $archive.Sha256)) {
                $gameResults += [PSCustomObject]@{
                    GamePk = $gamePkValue
                    Status = 'unchanged-current-graph'
                    RawPath = $archive.Path
                    ArchivedNew = $archive.ArchivedNew
                    GraphIri = "https://w3id.org/baseball/graph/game/$gamePkValue"
                    Error = $null
                }
                continue
            }

            & (Join-Path $PSScriptRoot 'run-rml.ps1') -InputJson $archive.Path
            if ($LASTEXITCODE -ne 0) {
                throw "RML execution failed for game $gamePkValue."
            }
            $rdfPath = Join-Path $pipelineRoot "rdf\game-$gamePkValue.ttl"
            & (Join-Path $PSScriptRoot 'load-game-graph.ps1') -RdfFile $rdfPath -GamePk $gamePkValue
            if ($LASTEXITCODE -ne 0) {
                throw "Fuseki graph load failed for game $gamePkValue."
            }
            $gameResults += [PSCustomObject]@{
                GamePk = $gamePkValue
                Status = 'loaded'
                RawPath = $archive.Path
                ArchivedNew = $archive.ArchivedNew
                GraphIri = "https://w3id.org/baseball/graph/game/$gamePkValue"
                Error = $null
            }
        }
        catch {
            $gameResults += [PSCustomObject]@{
                GamePk = $gamePkValue
                Status = 'failed'
                RawPath = $gameArchivePath
                ArchivedNew = $gameArchivedNew
                Error = $_.Exception.Message
            }
            Write-Warning "Game $gamePkValue failed: $($_.Exception.Message)"
        }
    }

    $failedGames = @($gameResults | Where-Object Status -eq 'failed')
    $summary = [ordered]@{
        pipeline = 'games-daily'
        pipelineRunId = $runId
        startedAtUtc = $runStartedAt.ToString('o')
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        requestedDates = $dateStrings
        gameFilter = if ([string]::IsNullOrWhiteSpace($GamePk)) { $null } else { $GamePk }
        maxGames = $MaxGames
        skipRdfLoad = [bool]$SkipRdfLoad
        forceRdfLoad = [bool]$ForceRdfLoad
        schedules = $scheduleResults
        finalCandidates = $candidateGames.Count
        selectedGames = $selectedGames.Count
        loadedGames = @($gameResults | Where-Object Status -eq 'loaded').Count
        archivedOnlyGames = @($gameResults | Where-Object Status -eq 'archived-only').Count
        unchangedCurrentGraphGames = @($gameResults | Where-Object Status -eq 'unchanged-current-graph').Count
        deferredGames = @($gameResults | Where-Object Status -eq 'deferred-not-final').Count
        failedGames = $failedGames.Count
        games = $gameResults
    }
    Write-JsonFile -Value $summary -Path $runManifestPath

    Write-Host "Daily game run manifest: $runManifestPath"
    Write-Host "Final candidates: $($candidateGames.Count); selected: $($selectedGames.Count); loaded: $($summary.loadedGames); failed: $($failedGames.Count)"
    if ($failedGames.Count -gt 0) {
        throw "$($failedGames.Count) completed game(s) failed acquisition, mapping, or loading."
    }
}
catch {
    $failurePath = Join-Path $runWork 'failure.json'
    Write-JsonFile -Value ([ordered]@{
        pipelineRunId = $runId
        failedAtUtc = [DateTime]::UtcNow.ToString('o')
        error = $_.Exception.Message
        runManifestPath = if (Test-Path -LiteralPath $runManifestPath) { $runManifestPath } else { $null }
    }) -Path $failurePath
    $quarantine = Join-Path $quarantineRoot "$runStamp-$runId"
    Move-Item -LiteralPath $runWork -Destination $quarantine
    $runQuarantined = $true
    Write-Error "Daily game acquisition failed; run artifacts quarantined at $quarantine`n$($_.Exception.Message)"
}
finally {
    if (-not $runQuarantined -and (Test-Path -LiteralPath $runWork -PathType Container)) {
        $resolvedWork = [System.IO.Path]::GetFullPath($runWork)
        $resolvedRoot = [System.IO.Path]::GetFullPath($workRoot) + [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedWork.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove work directory outside acquisition root: $resolvedWork"
        }
        Remove-Item -LiteralPath $resolvedWork -Recurse -Force
    }
}
