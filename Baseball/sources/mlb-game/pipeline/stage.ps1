[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('rml', 'shacl', 'promote', 'materialize', 'cleanup', 'quarantine')]
    [string] $Action,
    [Parameter(Mandatory = $true)][ValidatePattern('^\d+$')][string] $GamePk,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{32}$')][string] $RunId,
    [string] $InputJson,
    [string] $ScheduleEvidencePath = 'none',
    [string] $FailureStage = 'unknown'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
Initialize-LocalLayout

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$transientRoot = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot 'transient\mlb-game'))
$rdfPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "rdf\game-$GamePk.ttl"))
$rmlManifestPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "manifests\game-$GamePk-rml.json"))
$indexManifestPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "manifests\game-$GamePk-query-index.json"))
$stageEvidenceRoot = Join-Path $pipelineRoot "evidence\mlb-game\$GamePk\$RunId"
$stageLogPath = Join-Path $stageEvidenceRoot "$Action.log"
[void](New-Item -ItemType Directory -Force -Path $stageEvidenceRoot)

function Resolve-TransientInput {
    if ([string]::IsNullOrWhiteSpace($InputJson)) {
        throw "Action $Action requires -InputJson."
    }
    $resolved = [System.IO.Path]::GetFullPath($InputJson)
    $prefix = $transientRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Input JSON is outside the MLB-game transient root: $resolved"
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "Transient MLB-game payload does not exist: $resolved"
    }
    return $resolved
}

function Read-GameDocument([string] $Path) {
    try {
        $document = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    }
    catch {
        throw "MLB-game payload is not valid JSON: $($_.Exception.Message)"
    }
    if ([string]$document.gamePk -ne $GamePk) {
        throw "Payload gamePk does not match the FlowFile identity: expected $GamePk."
    }
    if ([string]$document.gameData.status.abstractGameState -ne 'Final') {
        throw "Game $GamePk is not final and cannot enter the semantic pipeline."
    }
    return $document
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory = $true)][scriptblock] $Command,
        [Parameter(Mandatory = $true)][string] $FailureMessage
    )
    $priorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Command *> $stageLogPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $priorPreference
    }
    if ($exitCode -ne 0) {
        $tail = if (Test-Path -LiteralPath $stageLogPath) { (Get-Content -LiteralPath $stageLogPath -Tail 20) -join "`n" } else { '' }
        throw "$FailureMessage`n$tail"
    }
}

function Write-StageResult([hashtable] $Values) {
    $result = [ordered]@{
        artifactType = 'baseballo-mlb-game-stage-result'
        contractVersion = 1
        action = $Action
        gamePk = $GamePk
        pipelineRunId = $RunId
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
    }
    foreach ($entry in $Values.GetEnumerator()) {
        $result[$entry.Key] = $entry.Value
    }
    $evidencePath = Join-Path $stageEvidenceRoot "$Action.json"
    Write-AtomicJsonFile -Path $evidencePath -Value $result -Depth 16
    Write-Output ($result | ConvertTo-Json -Depth 16 -Compress)
}

switch ($Action) {
    'rml' {
        $inputPath = Resolve-TransientInput
        [void](Read-GameDocument -Path $inputPath)
        $rmlScript = Join-Path $repositoryRoot 'scripts\pipeline\run-rml.ps1'
        Invoke-LoggedCommand -FailureMessage "RML failed for game $GamePk." -Command {
            & $rmlScript -InputJson $inputPath -OutputFile $rdfPath -ScheduleEvidencePath $ScheduleEvidencePath -DeferShaclValidation
        }
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf) -or -not (Test-Path -LiteralPath $rmlManifestPath -PathType Leaf)) {
            throw "RML did not produce its RDF and manifest for game $GamePk."
        }
        Write-StageResult @{
            inputSha256 = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
            rdfPath = $rdfPath
            rdfSha256 = (Get-FileHash -LiteralPath $rdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
            rmlManifest = $rmlManifestPath
        }
    }
    'shacl' {
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf) -or -not (Test-Path -LiteralPath $rmlManifestPath -PathType Leaf)) {
            throw "RDF or RML manifest is missing for game $GamePk."
        }
        $validator = Join-Path $repositoryRoot 'scripts\pipeline\validate-shacl.py'
        Invoke-LoggedCommand -FailureMessage "Authoritative SHACL failed for game $GamePk." -Command {
            & python $validator '--profile' 'authoritative' '--data' $rdfPath
        }
        $manifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
        if ([string]$manifest.gamePk -ne $GamePk) {
            throw "RML manifest game identity differs from $GamePk."
        }
        $shapePath = Join-Path $repositoryRoot 'sources\mlb-game\shacl\authoritative.ttl'
        $manifest.shaclStatus = 'validated'
        $manifest.shaclValidatedAtUtc = [DateTime]::UtcNow.ToString('o')
        $manifest.shaclShapeSha256 = (Get-FileHash -LiteralPath $shapePath -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifest.shaclValidatorSha256 = (Get-FileHash -LiteralPath $validator -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-AtomicJsonFile -Path $rmlManifestPath -Value $manifest -Depth 16
        Write-StageResult @{
            rdfPath = $rdfPath
            shaclProfile = 'authoritative'
            conforms = $true
            rmlManifest = $rmlManifestPath
        }
    }
    'promote' {
        $inputPath = Resolve-TransientInput
        [void](Read-GameDocument -Path $inputPath)
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf)) {
            throw "Validated RDF is missing for game $GamePk."
        }
        $rmlManifest = Get-Content -LiteralPath $rmlManifestPath -Raw | ConvertFrom-Json
        if ([string]$rmlManifest.shaclStatus -ne 'validated') {
            throw "Game $GamePk has not passed authoritative SHACL."
        }
        $transactionRunId = [Guid]::NewGuid().ToString('N')
        $transaction = Join-Path $repositoryRoot 'scripts\pipeline\graph-pair-transaction.py'
        $load = Join-Path $repositoryRoot 'scripts\pipeline\load-game-graph.ps1'
        $index = Join-Path $repositoryRoot 'scripts\pipeline\build-query-index.ps1'
        $prepared = $false
        try {
            Invoke-LoggedCommand -FailureMessage "Could not prepare graph-pair transaction for game $GamePk." -Command {
                & python $transaction '--state-root' $script:StateRoot '--game-pk' $GamePk '--run-id' $transactionRunId '--action' 'prepare'
            }
            $prepared = $true
            Invoke-LoggedCommand -FailureMessage "Authoritative graph load failed for game $GamePk." -Command {
                & $load -RdfFile $rdfPath -GamePk $GamePk
            }
            Invoke-LoggedCommand -FailureMessage "Query-index build failed for game $GamePk." -Command {
                & $index -GamePk $GamePk
            }

            $queryEndpoint = "$($script:FusekiDatasetUri)/query"
            $sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
            $indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
            $countQuery = "SELECT ?sourceCount ?indexCount WHERE { { SELECT (COUNT(*) AS ?sourceCount) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } } } { SELECT (COUNT(*) AS ?indexCount) WHERE { GRAPH <$indexGraph> { ?is ?ip ?io } } } }"
            $counts = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $countQuery } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 120
            $binding = @($counts.results.bindings)[0]
            $sourceCount = [int64]$binding.sourceCount.value
            $indexCount = [int64]$binding.indexCount.value
            if ($sourceCount -le 0 -or $indexCount -le 0) {
                throw "Promoted graph pair has an empty member for game $GamePk."
            }
            if (-not (Test-Path -LiteralPath $indexManifestPath -PathType Leaf)) {
                throw "Query-index manifest is missing for game $GamePk."
            }
            $promotionRoot = Join-Path $pipelineRoot "evidence\nifi\game-promotion\$GamePk"
            $promotionPath = Join-Path $promotionRoot "$transactionRunId.json"
            $promotion = [ordered]@{
                artifactType = 'baseball-nifi-game-promotion'
                contractVersion = 1
                gamePk = $GamePk
                pipelineRunId = $RunId
                transactionRunId = $transactionRunId
                promotedAtUtc = [DateTime]::UtcNow.ToString('o')
                rawSha256 = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
                authoritativeGraph = $sourceGraph
                authoritativeTripleCount = $sourceCount
                queryIndexGraph = $indexGraph
                queryIndexTripleCount = $indexCount
                rmlManifest = $rmlManifestPath
                rmlManifestSha256 = (Get-FileHash -LiteralPath $rmlManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
                queryIndexManifest = $indexManifestPath
                queryIndexManifestSha256 = (Get-FileHash -LiteralPath $indexManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
            }
            Write-AtomicJsonFile -Path $promotionPath -Value $promotion -Depth 16
            Invoke-LoggedCommand -FailureMessage "Could not commit graph-pair transaction for game $GamePk." -Command {
                & python $transaction '--state-root' $script:StateRoot '--game-pk' $GamePk '--run-id' $transactionRunId '--action' 'commit'
            }
            Write-StageResult @{
                transactionRunId = $transactionRunId
                promotionEvidence = $promotionPath
                authoritativeGraph = $sourceGraph
                authoritativeTripleCount = $sourceCount
                queryIndexGraph = $indexGraph
                queryIndexTripleCount = $indexCount
            }
        }
        catch {
            if ($prepared) {
                try {
                    & python $transaction '--state-root' $script:StateRoot '--game-pk' $GamePk '--run-id' $transactionRunId '--action' 'restore' '--reason' 'promotion-stage-failure' *> $null
                }
                catch {
                    throw "Promotion failed and graph-pair restoration also failed for game $GamePk."
                }
            }
            throw
        }
    }
    'materialize' {
        $materializer = Join-Path $repositoryRoot 'scripts\pipeline\materialize-serving-layer.py'
        Invoke-LoggedCommand -FailureMessage "Serving materialization failed after game $GamePk." -Command {
            & python $materializer '--state-root' $script:StateRoot '--retain-builds' '3'
        }
        $pointerPath = Join-Path $script:StateRoot 'serving\current.json'
        if (-not (Test-Path -LiteralPath $pointerPath -PathType Leaf)) {
            throw 'Serving materialization produced no promoted pointer.'
        }
        $pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json
        Write-StageResult @{
            servingPointer = $pointerPath
            databasePath = [string]$pointer.databasePath
            corpusFingerprint = [string]$pointer.corpusFingerprint
            gameCount = [int]$pointer.gameCount
        }
    }
    'cleanup' {
        $inputPath = Resolve-TransientInput
        $inputSha256 = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
        Remove-Item -LiteralPath $inputPath -Force
        $rdfRemoved = $false
        if (Test-Path -LiteralPath $rdfPath -PathType Leaf) {
            Remove-Item -LiteralPath $rdfPath -Force
            $rdfRemoved = $true
        }
        Write-StageResult @{
            deletedTransientPayload = $inputPath
            inputSha256 = $inputSha256
            deletedSerializedRdf = $rdfRemoved
            authoritativeRdfRemainsInGraphStore = $true
        }
    }
    'quarantine' {
        $quarantineRoot = Join-Path $pipelineRoot "quarantine\mlb-game\$GamePk\$RunId"
        [void](New-Item -ItemType Directory -Force -Path $quarantineRoot)
        $retainedInput = $null
        if (-not [string]::IsNullOrWhiteSpace($InputJson)) {
            $candidate = [System.IO.Path]::GetFullPath($InputJson)
            if ($candidate.StartsWith($transientRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                $retainedInput = Join-Path $quarantineRoot 'input.json'
                Move-Item -LiteralPath $candidate -Destination $retainedInput -Force
            }
        }
        $failure = [ordered]@{
            artifactType = 'baseballo-mlb-game-quarantine'
            contractVersion = 1
            gamePk = $GamePk
            pipelineRunId = $RunId
            failedStage = $FailureStage
            quarantinedAtUtc = [DateTime]::UtcNow.ToString('o')
            retainedInput = $retainedInput
        }
        $failurePath = Join-Path $quarantineRoot 'failure.json'
        Write-AtomicJsonFile -Path $failurePath -Value $failure -Depth 12
        Write-Output ($failure | ConvertTo-Json -Depth 12 -Compress)
    }
}
