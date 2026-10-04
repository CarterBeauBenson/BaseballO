function New-MlbRmlExecutionSnapshot {
    param([string]$RepositoryRoot, [string]$Stage)
    $artifacts = [ordered]@{}
    $paths = @(
        'scripts/pipeline/prepare-rml-context.py',
        'sources/mlb-game/pipeline/reconcile-metric-source.py',
        'sources/mlb-game/pipeline/graph-source-scope.py',
        'sources/mlb-game/mapping/mlb-game.rml.ttl',
        'governance/semantic-freeze.json'
    )
    foreach ($relative in $paths) {
        $source = Join-Path $RepositoryRoot $relative
        $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        $copy = Join-Path (Join-Path $Stage 'implementation') $relative
        [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $copy))
        Copy-Item -LiteralPath $source -Destination $copy
        if ((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) {
            throw "RML implementation changed while staging: $relative"
        }
        $artifacts[$relative] = [pscustomobject]@{ path=$source; stagedPath=$copy; sha256=$hash }
    }
    return $artifacts
}

function Assert-MlbRmlExecutionSnapshot {
    param($Snapshot)
    foreach ($entry in $Snapshot.GetEnumerator()) {
        foreach ($path in @($entry.Value.path, $entry.Value.stagedPath)) {
            if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value.sha256) {
                throw "RML implementation changed during execution: $($entry.Key)"
            }
        }
    }
}
