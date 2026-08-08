[CmdletBinding()]
param(
    [string] $InputRoot,
    [datetime] $FromDate = [datetime]'1900-01-01',
    [datetime] $ThroughDate = [datetime]'2999-12-31',
    [ValidateRange(1, 8)][int] $ConcurrentImports = 3,
    [ValidateRange(1, 1440)][int] $TimeoutMinutes = 480,
    [switch] $NoWait
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

$defaultInputRoot = Join-Path $script:RepositoryRoot 'data\raw\samples'
if ([string]::IsNullOrWhiteSpace($InputRoot)) {
    $InputRoot = $defaultInputRoot
}
$inputRootPath = [System.IO.Path]::GetFullPath($InputRoot)
if (-not (Test-Path -LiteralPath $inputRootPath -PathType Container)) {
    throw "Corpus root was not found: $inputRootPath"
}
if ($FromDate.Date -gt $ThroughDate.Date) {
    throw 'FromDate must not be later than ThroughDate.'
}

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443) -or -not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    & (Join-Path $PSScriptRoot '..\infra\start-stack.ps1')
}
& (Join-Path $PSScriptRoot '..\infra\configure-nifi-foundation.ps1')
& (Join-Path $PSScriptRoot '..\infra\configure-nifi-games-manual.ps1') -Enable -ConcurrentImports $ConcurrentImports

$entriesByGame = @{}
$duplicateInputs = 0
foreach ($file in Get-ChildItem -LiteralPath $inputRootPath -Recurse -File -Filter '*.json' | Sort-Object FullName) {
    if ($file.BaseName -notmatch '^\d+$' -or $file.Directory.Name -notmatch '^\d{4}-\d{2}-\d{2}$') {
        continue
    }
    $date = [datetime]::ParseExact($file.Directory.Name, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    if ($date.Date -lt $FromDate.Date -or $date.Date -gt $ThroughDate.Date) {
        continue
    }
    $document = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    $gamePk = [string]$document.gamePk
    if ($gamePk -ne $file.BaseName -or $gamePk -notmatch '^\d+$') {
        throw "Filename/gamePk mismatch in $($file.FullName)"
    }
    if ([string]$document.gameData.status.abstractGameState -ne 'Final') {
        throw "Corpus submission is restricted to final games: $($file.FullName)"
    }
    $officialDate = [datetime]::ParseExact([string]$document.gameData.datetime.officialDate, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    if ($officialDate.Date -ne $date.Date) {
        throw "Official date does not match the corpus directory for game $gamePk."
    }
    $sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($entriesByGame.ContainsKey($gamePk)) {
        if ($entriesByGame[$gamePk].Sha256 -ne $sha256) {
            throw "Game $gamePk appears more than once with different bytes."
        }
        $duplicateInputs++
        continue
    }
    $entriesByGame[$gamePk] = [PSCustomObject]@{
        GamePk = $gamePk
        OfficialDate = $date.ToString('yyyy-MM-dd')
        SourcePath = $file.FullName
        Sha256 = $sha256
    }
}

$entries = @($entriesByGame.Values | Sort-Object OfficialDate, GamePk)
if ($entries.Count -eq 0) {
    throw 'No final game JSON files matched the requested corpus range.'
}

$startedAt = [DateTime]::UtcNow
$runId = $startedAt.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N')
$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$inbox = Join-Path $pipelineRoot 'inbox\games'
$submissionRoot = Join-Path $pipelineRoot 'manifests\submissions'
$submissionPath = Join-Path $submissionRoot "$runId.json"
[void](New-Item -ItemType Directory -Force -Path $inbox, $submissionRoot)

$submission = [ordered]@{
    artifactType = 'nifi-game-corpus-submission'
    runId = $runId
    submittedAtUtc = $startedAt.ToString('o')
    sourceRoot = $inputRootPath
    fromDate = $FromDate.ToString('yyyy-MM-dd')
    throughDate = $ThroughDate.ToString('yyyy-MM-dd')
    uniqueGameCount = $entries.Count
    duplicateInputCount = $duplicateInputs
    concurrentImports = $ConcurrentImports
    status = 'submitting'
    games = @($entries | ForEach-Object { [ordered]@{ gamePk = $_.GamePk; officialDate = $_.OfficialDate; sha256 = $_.Sha256; sourcePath = $_.SourcePath } })
}
$submission | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $submissionPath -Encoding UTF8

foreach ($entry in $entries) {
    $name = "$runId-$($entry.OfficialDate)-$($entry.GamePk).json"
    $partial = Join-Path $inbox ".$name.partial"
    $destination = Join-Path $inbox $name
    Copy-Item -LiteralPath $entry.SourcePath -Destination $partial
    if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Sha256) {
        Remove-Item -LiteralPath $partial -Force
        throw "Inbox copy hash mismatch for game $($entry.GamePk)."
    }
    Move-Item -LiteralPath $partial -Destination $destination
}

$submission.status = if ($NoWait) { 'submitted' } else { 'processing' }
$submission | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $submissionPath -Encoding UTF8
Write-Host "Submitted $($entries.Count) unique final games to the NiFi inbox ($duplicateInputs duplicate inputs suppressed)."
Write-Host "Submission manifest: $submissionPath"
if ($NoWait) {
    return
}
& (Join-Path $PSScriptRoot 'monitor-nifi-corpus-submission.ps1') -RunId $runId -TimeoutMinutes $TimeoutMinutes
