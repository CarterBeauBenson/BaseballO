[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('assess', 'rml', 'validate', 'load', 'index', 'promote')][string] $Stage,
    [Parameter(Mandatory = $true)][string] $RequestJson
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
. (Join-Path $PSScriptRoot 'query-index-common.ps1')
Initialize-LocalLayout

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$requestPath = [System.IO.Path]::GetFullPath($RequestJson)
$requestRoot = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot 'staging\rdf-requests'))
if (-not $requestPath.StartsWith($requestRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing a NiFi RDF request outside $requestRoot`: $requestPath"
}
if (-not (Test-Path -LiteralPath $requestPath -PathType Leaf)) {
    throw "NiFi RDF work request was not found: $requestPath"
}

function Write-AtomicJson {
    param([Parameter(Mandatory = $true)][string] $Path, [Parameter(Mandatory = $true)] $Value)
    $temporary = "$Path.$([Guid]::NewGuid().ToString('N')).partial"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temporary, (($Value | ConvertTo-Json -Depth 16) + "`n"), $utf8)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Assert-PathWithin {
    param([string] $Path, [string] $Root, [string] $Label)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $resolvedRoot = [System.IO.Path]::GetFullPath($Root)
    if (-not $resolvedPath.StartsWith($resolvedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label is outside its allowed root: $resolvedPath"
    }
    return $resolvedPath
}

function Acquire-GameLock {
    param([string] $GamePk, [string] $RunId, [int] $TimeoutMinutes = 20)
    $lockRoot = Join-Path $pipelineRoot 'work\game-locks'
    [void](New-Item -ItemType Directory -Force -Path $lockRoot)
    $lockPath = Join-Path $lockRoot "game-$GamePk.lock"
    $deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
    do {
        try {
            $stream = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            try {
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($RunId)
                $stream.Write($bytes, 0, $bytes.Length)
            }
            finally { $stream.Dispose() }
            return $lockPath
        }
        catch [System.IO.IOException] {
            try {
                if ((Get-Content -LiteralPath $lockPath -Raw -ErrorAction Stop).Trim() -eq $RunId) { return $lockPath }
            }
            catch { }
            Start-Sleep -Seconds 2
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Timed out waiting for the active NiFi lock for game $GamePk."
}

function Release-GameLock {
    param($Request, [string] $RunId)
    if (-not ($Request.PSObject.Properties.Name -contains 'lockPath')) { return }
    $lockPath = [string]$Request.lockPath
    if ([string]::IsNullOrWhiteSpace($lockPath) -or -not (Test-Path -LiteralPath $lockPath -PathType Leaf)) { return }
    $expectedRoot = Join-Path $pipelineRoot 'work\game-locks'
    [void](Assert-PathWithin -Path $lockPath -Root $expectedRoot -Label 'Game lock path')
    try {
        if ((Get-Content -LiteralPath $lockPath -Raw).Trim() -eq $RunId) { Remove-Item -LiteralPath $lockPath -Force }
    }
    catch { }
}

function Get-CurrentGraphState {
    param([string] $GamePk, [string] $RawPath, [string] $RawSha256)
    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
        return [PSCustomObject]@{ Current = $false; Reason = 'fuseki-unavailable' }
    }
    $rmlPath = Join-Path $pipelineRoot "manifests\game-$GamePk-rml.json"
    $indexPath = Join-Path $pipelineRoot "manifests\game-$GamePk-query-index.json"
    if (-not (Test-Path -LiteralPath $rmlPath -PathType Leaf) -or -not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        return [PSCustomObject]@{ Current = $false; Reason = 'missing-build-manifest' }
    }
    try {
        $rml = Get-Content -LiteralPath $rmlPath -Raw | ConvertFrom-Json
        $index = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
        $mappingPath = Join-Path $script:RepositoryRoot 'mappings\direct\mlb-direct.rml.ttl'
        $contextPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\prepare-rml-context.py'
        $mappingHash = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $contextHash = (Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if (
            [string]$rml.inputPath -ne $RawPath -or
            [string]$rml.inputSha256 -ne $RawSha256 -or
            [string]$rml.mappingSha256 -ne $mappingHash -or
            [string]$rml.contextBuilderSha256 -ne $contextHash -or
            [string]$rml.mapperVersion -ne [string]$script:Versions.RMLMapper.Version
        ) {
            return [PSCustomObject]@{ Current = $false; Reason = 'stale-rml-contract' }
        }
        if ($rml.PSObject.Properties.Name -contains 'shaclStatus' -and [string]$rml.shaclStatus -ne 'validated') {
            return [PSCustomObject]@{ Current = $false; Reason = 'authoritative-shacl-not-validated' }
        }
        $rdfPath = [System.IO.Path]::GetFullPath([string]$rml.outputPath)
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf) -or (Get-FileHash -LiteralPath $rdfPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$rml.outputSha256) {
            return [PSCustomObject]@{ Current = $false; Reason = 'stale-authoritative-rdf' }
        }
        $sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
        $indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
        if (
            [string]$index.contractSha256 -ne (Get-QueryIndexContractHash) -or
            [string]$index.sourceGraph -ne $sourceGraph -or
            [string]$index.indexGraph -ne $indexGraph -or
            [string]$index.sourceRdfSha256 -ne [string]$rml.outputSha256
        ) {
            return [PSCustomObject]@{ Current = $false; Reason = 'stale-index-contract' }
        }
        $localIndexPath = [System.IO.Path]::GetFullPath([string]$index.indexPath)
        if (-not (Test-Path -LiteralPath $localIndexPath -PathType Leaf) -or (Get-FileHash -LiteralPath $localIndexPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$index.indexSha256) {
            return [PSCustomObject]@{ Current = $false; Reason = 'stale-index-artifact' }
        }
        $gameIri = "https://baseballontology.org/data/game/$GamePk"
        $indexResource = "https://w3id.org/baseball/query-index-build/game/$GamePk"
        $query = "SELECT ?sourceCount ?indexCount WHERE { { SELECT (COUNT(*) AS ?sourceCount) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } } } { SELECT (COUNT(*) AS ?indexCount) WHERE { GRAPH <$indexGraph> { ?is ?ip ?io } } } FILTER EXISTS { GRAPH <$sourceGraph> { <$gameIri> a <https://baseballontology.org/BaseballGame> } } FILTER EXISTS { GRAPH <$indexGraph> { <$indexResource> a <https://w3id.org/baseball/query-index/QueryIndex> ; <https://w3id.org/baseball/query-index/sourceGraph> <$sourceGraph> } } }"
        $result = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
        if (@($result.results.bindings).Count -ne 1) {
            return [PSCustomObject]@{ Current = $false; Reason = 'missing-loaded-graph-assertions' }
        }
        $sourceCount = [int64]$result.results.bindings[0].sourceCount.value
        $indexCount = [int64]$result.results.bindings[0].indexCount.value
        if ($sourceCount -ne [int64]$index.sourceTripleCount -or $indexCount -ne [int64]$index.indexTripleCount) {
            return [PSCustomObject]@{ Current = $false; Reason = 'loaded-graph-count-mismatch' }
        }
        return [PSCustomObject]@{ Current = $true; Reason = 'current'; SourceTripleCount = $sourceCount; IndexTripleCount = $indexCount; RmlManifest = $rmlPath; IndexManifest = $indexPath }
    }
    catch {
        return [PSCustomObject]@{ Current = $false; Reason = "current-state-check-failed: $($_.Exception.Message)" }
    }
}

$request = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json
if ([string]$request.artifactType -ne 'baseball-nifi-game-work-request' -or [int]$request.contractVersion -ne 1) {
    throw 'Unsupported NiFi RDF work request contract.'
}
$gamePk = [string]$request.gamePk
$runId = [string]$request.pipelineRunId
if ($gamePk -notmatch '^\d+$' -or $runId -notmatch '^[A-Za-z0-9-]+$') {
    throw 'NiFi RDF work request has an unsafe gamePk or run identifier.'
}
$rawPath = Assert-PathWithin -Path ([string]$request.rawPath) -Root (Join-Path $pipelineRoot 'raw\games') -Label 'Raw path'
$importManifestPath = Assert-PathWithin -Path ([string]$request.importManifestPath) -Root (Join-Path $pipelineRoot 'manifests\imports\games') -Label 'Import manifest path'
$evidenceRoot = Join-Path $pipelineRoot "evidence\nifi\game-processing\$gamePk"
$quarantineRoot = Join-Path $pipelineRoot "quarantine\nifi-rdf\$gamePk\$runId\$Stage"
[void](New-Item -ItemType Directory -Force -Path $evidenceRoot)
$manifestPath = Join-Path $evidenceRoot "$runId-$Stage.json"
$logPath = Join-Path $evidenceRoot "$runId-$Stage.log"
$startedAt = [DateTime]::UtcNow
$requestHashBefore = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$logText = ''
$rawHash = $null
$stageResult = [ordered]@{}
$promotionPath = $null
$promotion = $null

try {
    if (-not (Test-Path -LiteralPath $rawPath -PathType Leaf) -or -not (Test-Path -LiteralPath $importManifestPath -PathType Leaf)) {
        throw 'NiFi RDF work request references a missing raw file or import manifest.'
    }
    $rawHash = (Get-FileHash -LiteralPath $rawPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($rawHash -ne [string]$request.rawSha256) {
        throw 'NiFi RDF work request raw hash does not match the immutable archive.'
    }
    switch ($Stage) {
        'assess' {
            $lockPath = Acquire-GameLock -GamePk $gamePk -RunId $runId
            $request | Add-Member -NotePropertyName lockPath -NotePropertyValue $lockPath -Force
            $current = Get-CurrentGraphState -GamePk $gamePk -RawPath $rawPath -RawSha256 $rawHash
            $request.action = if ($request.forceRdfLoad -eq $true -or -not $current.Current) { 'rebuild' } else { 'current' }
            $stageResult.action = [string]$request.action
            $stageResult.reason = if ($request.forceRdfLoad -eq $true) { 'forced-rdf-load' } else { [string]$current.Reason }
        }
        'rml' {
            if ([string]$request.action -eq 'rebuild') {
                $logText = (& (Join-Path $PSScriptRoot 'run-rml.ps1') -InputJson $rawPath -DeferShaclValidation *>&1 | Out-String)
            }
            $rmlManifest = Join-Path $pipelineRoot "manifests\game-$gamePk-rml.json"
            if (-not (Test-Path -LiteralPath $rmlManifest -PathType Leaf)) { throw 'RML stage produced no manifest.' }
            $stageResult.rmlManifest = $rmlManifest
            $stageResult.execution = if ([string]$request.action -eq 'rebuild') { 'executed' } else { 'skipped-current' }
        }
        'validate' {
            if ([string]$request.action -eq 'rebuild') {
                $rmlManifestPath = Join-Path $pipelineRoot "manifests\game-$gamePk-rml.json"
                $rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
                $rdfPath = Join-Path $pipelineRoot "rdf\game-$gamePk.ttl"
                $validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-generated-rdf.py'
                $shaclPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-shacl.py'
                $validationOutput = & python $validatorPath $rdfPath $gamePk *>&1
                if ($LASTEXITCODE -ne 0) { throw "Generated RDF validation failed for game $gamePk." }
                $shaclOutput = & python $shaclPath '--profile' 'authoritative' '--data' $rdfPath *>&1
                if ($LASTEXITCODE -ne 0) { throw "Authoritative SHACL validation failed for game $gamePk." }
                $logText = (@($validationOutput) + @($shaclOutput) | Out-String)
                $rmlManifest.shaclStatus = 'validated'
                $rmlManifest.shaclValidatedAtUtc = [DateTime]::UtcNow.ToString('o')
                Write-AtomicJson -Path $rmlManifestPath -Value $rmlManifest
            }
            $stageResult.execution = if ([string]$request.action -eq 'rebuild') { 'executed' } else { 'skipped-current' }
            $stageResult.profile = 'authoritative'
        }
        'load' {
            if ([string]$request.action -eq 'rebuild') {
                $rdfPath = Join-Path $pipelineRoot "rdf\game-$gamePk.ttl"
                $logText = (& (Join-Path $PSScriptRoot 'load-game-graph.ps1') -RdfFile $rdfPath -GamePk $gamePk *>&1 | Out-String)
            }
            $stageResult.execution = if ([string]$request.action -eq 'rebuild') { 'executed' } else { 'skipped-current' }
            $stageResult.graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
        }
        'index' {
            if ([string]$request.action -eq 'rebuild') {
                $logText = (& (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $gamePk *>&1 | Out-String)
            }
            $stageResult.execution = if ([string]$request.action -eq 'rebuild') { 'executed' } else { 'skipped-current' }
            $stageResult.indexGraphIri = "https://w3id.org/baseball/graph/query-index/game/$gamePk"
        }
        'promote' {
            $current = Get-CurrentGraphState -GamePk $gamePk -RawPath $rawPath -RawSha256 $rawHash
            if (-not $current.Current) { throw "Promotion refused: $($current.Reason)" }
            $importManifest = Get-Content -LiteralPath $importManifestPath -Raw | ConvertFrom-Json
            $importManifest.status = if ([string]$request.action -eq 'current') { 'unchanged-current-graph' } else { 'loaded' }
            $importManifest.completedAtUtc = [DateTime]::UtcNow.ToString('o')
            $importManifest.graphIri = "https://w3id.org/baseball/graph/game/$gamePk"
            Write-AtomicJson -Path $importManifestPath -Value $importManifest
            $promotionPath = Join-Path $pipelineRoot "evidence\nifi\game-promotion\$gamePk\$runId.json"
            [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $promotionPath))
            $promotion = [ordered]@{
                artifactType = 'baseball-nifi-game-promotion'
                contractVersion = 1
                pipelineRunId = $runId
                gamePk = $gamePk
                promotedAtUtc = [DateTime]::UtcNow.ToString('o')
                action = [string]$request.action
                rawPath = $rawPath
                rawSha256 = $rawHash
                authoritativeGraph = "https://w3id.org/baseball/graph/game/$gamePk"
                authoritativeTripleCount = [int64]$current.SourceTripleCount
                queryIndexGraph = "https://w3id.org/baseball/graph/query-index/game/$gamePk"
                queryIndexTripleCount = [int64]$current.IndexTripleCount
                rmlManifest = [string]$current.RmlManifest
                rmlManifestSha256 = (Get-FileHash -LiteralPath ([string]$current.RmlManifest) -Algorithm SHA256).Hash.ToLowerInvariant()
                queryIndexManifest = [string]$current.IndexManifest
                queryIndexManifestSha256 = (Get-FileHash -LiteralPath ([string]$current.IndexManifest) -Algorithm SHA256).Hash.ToLowerInvariant()
                importManifest = $importManifestPath
            }
            $stageResult.promotionManifest = $promotionPath
            $stageResult.authoritativeTripleCount = [int64]$current.SourceTripleCount
            $stageResult.queryIndexTripleCount = [int64]$current.IndexTripleCount
        }
    }

    $stageRecord = [PSCustomObject]@{
        status = 'succeeded'
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        result = [PSCustomObject]$stageResult
    }
    if ($null -eq $request.stages) { $request | Add-Member -NotePropertyName stages -NotePropertyValue ([PSCustomObject]@{}) -Force }
    $request.stages | Add-Member -NotePropertyName $Stage -NotePropertyValue $stageRecord -Force
    Write-AtomicJson -Path $requestPath -Value $request
    $requestHashAfter = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText($logPath, $logText, (New-Object System.Text.UTF8Encoding($false)))
    $manifest = [ordered]@{
        artifactType = 'baseball-nifi-game-stage-evidence'
        contractVersion = 1
        pipelineRunId = $runId
        gamePk = $gamePk
        stage = $Stage
        status = 'succeeded'
        startedAtUtc = $startedAt.ToString('o')
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        requestPath = $requestPath
        requestSha256Before = $requestHashBefore
        requestSha256After = $requestHashAfter
        rawSha256 = $rawHash
        result = [PSCustomObject]$stageResult
        logPath = $logPath
        logSha256 = (Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    Write-AtomicJson -Path $manifestPath -Value $manifest
    if ($Stage -eq 'promote') {
        # This is the final fail-closed promotion marker. No graph pair is
        # current for this request until all request and stage evidence exists.
        Write-AtomicJson -Path $promotionPath -Value $promotion
        Release-GameLock -Request $request -RunId $runId
        try { Remove-Item -LiteralPath $requestPath -Force } catch { }
    }
    $manifest | ConvertTo-Json -Depth 12 -Compress
}
catch {
    Release-GameLock -Request $request -RunId $runId
    [void](New-Item -ItemType Directory -Force -Path $quarantineRoot)
    [System.IO.File]::WriteAllText($logPath, ($logText + "`n" + $_.Exception.ToString()), (New-Object System.Text.UTF8Encoding($false)))
    $failure = [ordered]@{
        artifactType = 'baseball-nifi-game-stage-evidence'
        contractVersion = 1
        pipelineRunId = $runId
        gamePk = $gamePk
        stage = $Stage
        status = 'failed'
        startedAtUtc = $startedAt.ToString('o')
        failedAtUtc = [DateTime]::UtcNow.ToString('o')
        error = $_.Exception.Message
        requestPath = $requestPath
        requestSha256 = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        rawPath = $rawPath
        rawSha256 = $rawHash
        quarantinePath = $quarantineRoot
    }
    Write-AtomicJson -Path $manifestPath -Value $failure
    Copy-Item -LiteralPath $requestPath -Destination (Join-Path $quarantineRoot 'request.json') -Force
    Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $quarantineRoot 'manifest.json') -Force
    Copy-Item -LiteralPath $logPath -Destination (Join-Path $quarantineRoot 'stage.log') -Force
    throw "NiFi RDF stage $Stage failed; evidence is quarantined at $quarantineRoot`n$($_.Exception.Message)"
}
