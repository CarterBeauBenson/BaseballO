[CmdletBinding()]
param([Parameter(Mandatory = $true)][ValidatePattern('^\d+(,\d+)*$')][string] $GamePks)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
. (Join-Path $PSScriptRoot 'game-lock.ps1')
Initialize-LocalLayout

$pipeline = Join-Path $script:StateRoot 'pipeline'
$inventory = Join-Path $script:RepositoryRoot 'scripts\pipeline\game_promotion_inventory.py'
$builder = Join-Path $script:RepositoryRoot 'scripts\pipeline\build-query-index.ps1'
$reconciler = Join-Path $PSScriptRoot 'reconcile-promotion-evidence.py'
$runRoot = Join-Path $pipeline ('evidence\nifi\query-index-repair\' + [Guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $runRoot -Force)
$result = [ordered]@{ gamePks = @($GamePks.Split(',')); repairedGames = @(); status = 'running'; startedAtUtc = [DateTime]::UtcNow.ToString('o') }
$resultPath = Join-Path $runRoot 'result.json'
$result | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8

try {
    foreach ($gamePk in $result.gamePks) {
        $gameLock = Enter-MlbGameLock -StateRoot $script:StateRoot -GamePk $gamePk
        try {
            $work = Join-Path $runRoot $gamePk
            [void](New-Item -ItemType Directory -Path $work -Force)
            $rmlPath = Join-Path $pipeline "manifests\game-$gamePk-rml.json"
            $rml = Get-Content -LiteralPath $rmlPath -Raw | ConvertFrom-Json
            $rmlSha = (Get-FileHash -LiteralPath $rmlPath -Algorithm SHA256).Hash.ToLowerInvariant()
            $sourceGraph = "https://w3id.org/baseball/graph/game/$gamePk"
            if ([string]$rml.gamePk -ne $gamePk -or $rml.graphIri -ne $sourceGraph -or $rml.shaclStatus -ne 'validated') {
                throw "Game $gamePk has no validated authoritative RML manifest."
            }
            $anchors = @(Get-ChildItem (Join-Path $pipeline "evidence\nifi\game-promotion\$gamePk") -Filter '*.json' | ForEach-Object {
                $marker = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
                if ($marker.rmlManifestSha256 -eq $rmlSha -and $marker.rawSha256 -eq $rml.inputSha256) { $marker }
            })
            if ($anchors.Count -eq 0) { throw "Game $gamePk has no immutable promotion anchor for this RDF." }
            & python -B $inventory --state-root $script:StateRoot --retain-game-artifacts $gamePk
            if ($LASTEXITCODE -ne 0) { throw 'Unable to retain published artifacts.' }

            $sourceFile = Join-Path $work 'source.nt'
            $indexBackup = Join-Path $work 'previous-index.nt'
            $indexEndpoint = 'http://127.0.0.1:3031/baseball-dev/data?graph=' + [Uri]::EscapeDataString("https://w3id.org/baseball/graph/query-index/game/$gamePk")
            $sourceEndpoint = 'http://127.0.0.1:3031/baseball-dev/data?graph=' + [Uri]::EscapeDataString($sourceGraph)
            Invoke-WebRequest -Uri $sourceEndpoint -Headers @{ Accept = 'application/n-triples' } -OutFile $sourceFile -UseBasicParsing | Out-Null
            Invoke-WebRequest -Uri $indexEndpoint -Headers @{ Accept = 'application/n-triples' } -OutFile $indexBackup -UseBasicParsing | Out-Null
            $manifestPath = Join-Path $pipeline "manifests\game-$gamePk-query-index.json"
            $indexPath = Join-Path $pipeline "query-index\game-$gamePk.nt"
            Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $work 'previous-manifest.json')
            Copy-Item -LiteralPath $indexPath -Destination (Join-Path $work 'previous-artifact.nt')
            try {
                & $builder -GamePk $gamePk -SourceRdfFile $sourceFile -SourceRdfSha256 ([string]$rml.outputSha256) *> (Join-Path $work 'build.log')
                & python -B $reconciler --state-root $script:StateRoot --game-pk $gamePk *> (Join-Path $work 'reconcile.log')
                if ($LASTEXITCODE -ne 0) { throw "Game $gamePk evidence reconciliation failed." }
            }
            catch {
                $writer = Enter-FusekiWriteLock
                try {
                    # Roll back only this derived graph and its mutable artifacts.
                    Invoke-WebRequest -Uri $indexEndpoint -Method Put -ContentType 'application/n-triples' -InFile $indexBackup -UseBasicParsing | Out-Null
                    Copy-Item -LiteralPath (Join-Path $work 'previous-manifest.json') -Destination $manifestPath -Force
                    Copy-Item -LiteralPath (Join-Path $work 'previous-artifact.nt') -Destination $indexPath -Force
                }
                finally { Exit-FusekiWriteLock -LockHandle $writer }
                throw
            }
            # These exports are temporary build inputs, not a second RDF corpus.
            Remove-Item -LiteralPath $sourceFile, $indexBackup, (Join-Path $work 'previous-artifact.nt')
            $result.repairedGames += $gamePk
            $result | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
        }
        finally { $gameLock.Dispose() }
    }
    $result.status = 'completed'
}
catch {
    $result.status = 'failed'
    $result['error'] = [string]$_
    throw
}
finally {
    $result['finishedAtUtc'] = [DateTime]::UtcNow.ToString('o')
    $result | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
    Write-Output "Query-index repair evidence: $resultPath"
}
