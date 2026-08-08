[CmdletBinding()]
param(
    [string] $InputJson,
    [ValidateRange(1, 30)][int] $TimeoutMinutes = 10
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout
if ([string]::IsNullOrWhiteSpace($InputJson)) { $InputJson = Join-Path $script:RepositoryRoot 'data\raw\game-566279.json' }
$inputPath = [System.IO.Path]::GetFullPath($InputJson)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) { throw "NiFi parity fixture was not found: $inputPath" }
$inputHash = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443) -or -not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    & (Join-Path $PSScriptRoot '..\infra\start-stack.ps1')
}
& (Join-Path $PSScriptRoot '..\infra\configure-nifi-foundation.ps1')
& (Join-Path $PSScriptRoot '..\infra\configure-nifi-rdf-flow.ps1') -Enable -ConcurrentGames 1

$archiver = Join-Path $PSScriptRoot 'archive-and-queue-game-json.py'
$archiveOutput = @(& python $archiver '--input' $inputPath '--state-root' $script:StateRoot '--force-rdf-load')
if ($LASTEXITCODE -ne 0 -or $archiveOutput.Count -eq 0) { throw 'Could not queue the forced NiFi parity request.' }
$archive = $archiveOutput[-1] | ConvertFrom-Json
$runId = [string]$archive.pipelineRunId
$gamePk = [string]$archive.gamePk
if ($runId -notmatch '^[A-Za-z0-9-]+$' -or $gamePk -notmatch '^\d+$') { throw 'Archive stage returned unsafe identifiers.' }

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$promotionPath = Join-Path $pipelineRoot "evidence\nifi\game-promotion\$gamePk\$runId.json"
$quarantinePath = Join-Path $pipelineRoot "quarantine\nifi-rdf\$gamePk\$runId"
$deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
do {
    if (Test-Path -LiteralPath $quarantinePath -PathType Container) {
        $failures = Get-ChildItem -LiteralPath $quarantinePath -Filter 'manifest.json' -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }
        throw "NiFi RDF parity run was quarantined:`n$($failures -join "`n")"
    }
    if (Test-Path -LiteralPath $promotionPath -PathType Leaf) { break }
    Start-Sleep -Seconds 2
} while ([DateTime]::UtcNow -lt $deadline)
if (-not (Test-Path -LiteralPath $promotionPath -PathType Leaf)) { throw "Timed out waiting for NiFi RDF promotion: $runId" }

$promotion = Get-Content -LiteralPath $promotionPath -Raw | ConvertFrom-Json
if ([string]$promotion.action -ne 'rebuild' -or [int64]$promotion.authoritativeTripleCount -le 0 -or [int64]$promotion.queryIndexTripleCount -le 0) {
    throw 'NiFi RDF promotion manifest does not describe a complete forced rebuild.'
}
$stageRoot = Join-Path $pipelineRoot "evidence\nifi\game-processing\$gamePk"
$expectedStages = @('assess','rml','validate','load','index','promote')
foreach ($stage in $expectedStages) {
    $manifestPath = Join-Path $stageRoot "$runId-$stage.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Missing NiFi stage evidence: $stage" }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.status -ne 'succeeded') { throw "NiFi stage did not succeed: $stage" }
}
if (Test-Path -LiteralPath ([string]$archive.semanticWorkRequest)) { throw 'NiFi left the queued request behind after promotion.' }
if (@(Get-ChildItem -LiteralPath (Join-Path $pipelineRoot 'staging\rdf-requests') -Filter "*$runId*" -File -ErrorAction SilentlyContinue).Count -ne 0) { throw 'NiFi left the staged request behind after promotion.' }
$lockPath = Join-Path $pipelineRoot "work\game-locks\game-$gamePk.lock"
if (Test-Path -LiteralPath $lockPath) { throw 'NiFi left the per-game concurrency lock behind after promotion.' }
if ((Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $inputHash) { throw 'NiFi parity run changed its source fixture.' }

& (Join-Path $PSScriptRoot 'test-query-index.ps1') -GamePk $gamePk -SkipBuild
Write-Host "NiFi RDF flow parity passed for game ${gamePk}: $($promotion.authoritativeTripleCount) authoritative triples; $($promotion.queryIndexTripleCount) index triples; six stage manifests."
Write-Host "Promotion evidence: $promotionPath"
