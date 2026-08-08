[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9-]+$')][string] $RunId,
    [ValidateRange(1, 1440)][int] $TimeoutMinutes = 480
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$submissionPath = Join-Path $pipelineRoot "manifests\submissions\$RunId.json"
if (-not (Test-Path -LiteralPath $submissionPath -PathType Leaf)) {
    throw "NiFi corpus submission manifest was not found: $submissionPath"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443)) {
    throw 'NiFi is not running; refusing to report a stalled queue as active.'
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running; the NiFi import flow cannot complete.'
}

$submission = Get-Content -LiteralPath $submissionPath -Raw | ConvertFrom-Json
$entries = @($submission.games)
if ($entries.Count -ne [int]$submission.uniqueGameCount -or $entries.Count -eq 0) {
    throw 'Submission manifest game count is inconsistent.'
}
$startedAt = [datetime]$submission.submittedAtUtc
$mappingHash = (Get-FileHash -LiteralPath (Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl') -Algorithm SHA256).Hash.ToLowerInvariant()
$contextHash = (Get-FileHash -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\prepare-rml-context.py') -Algorithm SHA256).Hash.ToLowerInvariant()
$contractHash = Get-QueryIndexContractHash
$deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
$lastReported = -1

do {
    $newFailures = @(
        Get-ChildItem -LiteralPath (Join-Path $pipelineRoot 'quarantine\manual-inbox') -Directory -ErrorAction SilentlyContinue |
            Where-Object {
                $failurePath = Join-Path $_.FullName 'failure.json'
                if (-not (Test-Path -LiteralPath $failurePath -PathType Leaf)) {
                    return $false
                }
                try {
                    $failureDocument = Get-Content -LiteralPath $failurePath -Raw | ConvertFrom-Json
                    return [datetime]$failureDocument.failedAtUtc -ge $startedAt
                }
                catch {
                    return $false
                }
            }
    )
    if ($newFailures.Count -gt 0) {
        $failureText = @($newFailures | ForEach-Object {
            $failure = Join-Path $_.FullName 'failure.json'
            if (Test-Path -LiteralPath $failure) { Get-Content -LiteralPath $failure -Raw } else { $_.FullName }
        }) -join "`n"
        $submission.status = 'failed'
        $submission.completedAtUtc = [DateTime]::UtcNow.ToString('o')
        $submission | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $submissionPath -Encoding UTF8
        throw "NiFi quarantined a corpus item:`n$failureText"
    }

    $completed = 0
    foreach ($entry in $entries) {
        $rmlPath = Join-Path $pipelineRoot "manifests\game-$($entry.gamePk)-rml.json"
        $indexPath = Join-Path $pipelineRoot "manifests\game-$($entry.gamePk)-query-index.json"
        if (-not (Test-Path -LiteralPath $rmlPath) -or -not (Test-Path -LiteralPath $indexPath)) { continue }
        try {
            $rml = Get-Content -LiteralPath $rmlPath -Raw | ConvertFrom-Json
            $index = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
            if (
                [string]$rml.inputSha256 -eq [string]$entry.sha256 -and
                [string]$rml.mappingSha256 -eq $mappingHash -and
                [string]$rml.contextBuilderSha256 -eq $contextHash -and
                [string]$index.contractSha256 -eq $contractHash -and
                [string]$index.sourceRdfSha256 -eq [string]$rml.outputSha256
            ) {
                $completed++
            }
        }
        catch { continue }
    }
    if ($completed -ne $lastReported) {
        $inboxCount = @(Get-ChildItem -LiteralPath (Join-Path $pipelineRoot 'inbox\games') -File -ErrorAction SilentlyContinue).Count
        $stagingCount = @(Get-ChildItem -LiteralPath (Join-Path $pipelineRoot 'staging\manual-inbox') -File -ErrorAction SilentlyContinue).Count
        Write-Host "NiFi corpus progress: $completed/$($entries.Count) current graph pairs; inbox=$inboxCount; staging=$stagingCount."
        $lastReported = $completed
    }
    if ($completed -eq $entries.Count) { break }
    Start-Sleep -Seconds 10
} while ([DateTime]::UtcNow -lt $deadline)

if ($completed -ne $entries.Count) {
    $submission.status = 'timed-out'
    $submission.completedAtUtc = [DateTime]::UtcNow.ToString('o')
    $submission | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $submissionPath -Encoding UTF8
    throw "Timed out with $completed/$($entries.Count) current graph pairs."
}

$submission.status = 'completed'
$submission.completedAtUtc = [DateTime]::UtcNow.ToString('o')
$submission | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $submissionPath -Encoding UTF8
Write-Host "NiFi completed all $completed game imports."
