[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('context', 'rml', 'shacl', 'promote', 'emit', 'cleanup', 'quarantine')][string] $Action,
    [Parameter(Mandatory = $true)][string] $ContractPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{32}$')][string] $RunId,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]+$')][string] $ScopeKey,
    [string] $RequestScope,
    [string] $Season,
    [string] $PersonId,
    [string] $ResourceKind,
    [string] $InputOneKey,
    [string] $InputOnePath,
    [string] $InputTwoKey,
    [string] $InputTwoPath,
    [string] $FailureStage = 'unknown'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repositoryRoot 'scripts\infra\common.ps1')
Initialize-LocalLayout

$contractFile = [System.IO.Path]::GetFullPath($ContractPath)
$sourcesRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot 'sources')) + [System.IO.Path]::DirectorySeparatorChar
if (-not $contractFile.StartsWith($sourcesRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Source flow contract must reside inside Baseball/sources/.'
}
if (-not (Test-Path -LiteralPath $contractFile -PathType Leaf)) {
    throw "Source flow contract does not exist: $contractFile"
}
$contract = Get-Content -LiteralPath $contractFile -Raw | ConvertFrom-Json
if ([string]$contract.artifactType -ne 'baseballo-nifi-source-flow-contract' -or [int]$contract.contractVersion -ne 1) {
    throw "Unsupported source flow contract: $contractFile"
}
$moduleId = [string]$contract.sourceModule
if ($moduleId -notmatch '^[a-z0-9-]+$') {
    throw 'Source flow contract has an unsafe module identifier.'
}
$moduleRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "sources\$moduleId"))
$modulePrefix = $moduleRoot + [System.IO.Path]::DirectorySeparatorChar
if (-not $contractFile.StartsWith($modulePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Flow contract is not owned by its declared module $moduleId."
}
$eventContract = $contract.promotedGraphEvents
if (
    [int]$eventContract.contractVersion -ne 1 -or
    [string]$eventContract.emitter -ne 'scripts/pipeline/emit-promoted-graph-event.py' -or
    [string]$eventContract.outbox -ne 'pipeline/events/promoted-graphs' -or
    [string]$eventContract.delivery -ne 'immutable-idempotent-before-transient-cleanup'
) {
    throw "$moduleId promoted-graph event contract is invalid."
}

$shaclEngine = 'pyshacl'
$shaclJenaMaxHeap = '384m'
$runtimeExecutionProperty = $contract.PSObject.Properties['runtimeExecution']
if ($null -ne $runtimeExecutionProperty) {
    $sourceShaclProperty = $runtimeExecutionProperty.Value.PSObject.Properties['sourceShacl']
    if ($null -ne $sourceShaclProperty) {
        $engineProperty = $sourceShaclProperty.Value.PSObject.Properties['engine']
        if ($null -ne $engineProperty -and -not [string]::IsNullOrWhiteSpace([string]$engineProperty.Value)) {
            $shaclEngine = ([string]$engineProperty.Value).ToLowerInvariant()
        }
        $heapProperty = $sourceShaclProperty.Value.PSObject.Properties['jenaMaxHeap']
        if ($null -ne $heapProperty -and -not [string]::IsNullOrWhiteSpace([string]$heapProperty.Value)) {
            $shaclJenaMaxHeap = [string]$heapProperty.Value
        }
    }
}
if ($shaclEngine -notin @('pyshacl', 'jena')) {
    throw "$moduleId declares an unsupported source SHACL engine: $shaclEngine"
}
if ($shaclJenaMaxHeap -notmatch '^[1-9][0-9]*[mMgG]$') {
    throw "$moduleId declares an invalid Jena SHACL maximum heap: $shaclJenaMaxHeap"
}

$pipelineRoot = Join-Path $script:StateRoot 'pipeline'
$transientRoot = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "transient\$moduleId"))
$workRoot = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "work\$moduleId\$ScopeKey\$RunId"))
$rdfPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "rdf\$moduleId\$ScopeKey.ttl"))
$manifestPath = [System.IO.Path]::GetFullPath((Join-Path $pipelineRoot "manifests\$moduleId-$ScopeKey-rml.json"))
$contextPath = Join-Path $workRoot ([string]$contract.context.contextName)
$prepareManifestPath = Join-Path $workRoot 'prepare-manifest.json'
$evidenceRoot = Join-Path $pipelineRoot "evidence\$moduleId\$ScopeKey\$RunId"
$logPath = Join-Path $evidenceRoot "$Action.log"
foreach ($directory in @($transientRoot, $workRoot, (Split-Path -Parent $rdfPath), (Split-Path -Parent $manifestPath), $evidenceRoot)) {
    [void](New-Item -ItemType Directory -Force -Path $directory)
}

$inputs = [ordered]@{}
foreach ($pair in @(
    @($InputOneKey, $InputOnePath),
    @($InputTwoKey, $InputTwoPath)
)) {
    $key = [string]$pair[0]
    $path = [string]$pair[1]
    if ([string]::IsNullOrWhiteSpace($key) -and [string]::IsNullOrWhiteSpace($path)) {
        continue
    }
    if ($key -notmatch '^[a-z0-9-]+$' -or [string]::IsNullOrWhiteSpace($path)) {
        throw 'Source-stage input key/path pairs must be complete and safe.'
    }
    $resolved = [System.IO.Path]::GetFullPath($path)
    $prefix = $transientRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Input $key is outside the $moduleId transient root: $resolved"
    }
    $inputs[$key] = $resolved
}

function Invoke-LoggedCommand {
    param([Parameter(Mandatory = $true)][scriptblock] $Command, [Parameter(Mandatory = $true)][string] $FailureMessage)
    $priorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Command *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $priorPreference
    }
    if ($exitCode -ne 0) {
        $tail = if (Test-Path -LiteralPath $logPath) { (Get-Content -LiteralPath $logPath -Tail 30) -join "`n" } else { '' }
        throw "$FailureMessage`n$tail"
    }
}

function Write-StageResult([hashtable] $Values) {
    $result = [ordered]@{
        artifactType = 'baseballo-source-stage-result'
        contractVersion = 1
        sourceModule = $moduleId
        scopeKey = $ScopeKey
        pipelineRunId = $RunId
        action = $Action
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
    }
    foreach ($entry in $Values.GetEnumerator()) {
        $result[$entry.Key] = $entry.Value
    }
    $evidencePath = Join-Path $evidenceRoot "$Action.json"
    Write-AtomicJsonFile -Path $evidencePath -Value $result -Depth 16
    Write-Output ($result | ConvertTo-Json -Depth 16 -Compress)
}

function Resolve-ModuleArtifact([string] $RelativePath) {
    $resolved = [System.IO.Path]::GetFullPath((Join-Path $moduleRoot $RelativePath))
    if (-not $resolved.StartsWith($modulePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Source contract artifact escapes module ${moduleId}: $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "Source contract artifact does not exist: $resolved"
    }
    return $resolved
}

function Require-Inputs {
    foreach ($acquisition in @($contract.acquisitions)) {
        $key = [string]$acquisition.key
        if (-not $inputs.Contains($key)) {
            throw "Action $Action requires transient input $key."
        }
        if (-not (Test-Path -LiteralPath $inputs[$key] -PathType Leaf)) {
            throw "Transient input $key does not exist: $($inputs[$key])"
        }
    }
}

function Expand-ContextArgument([string] $Argument) {
    $tokens = [ordered]@{
        '{context}' = $contextPath
        '{prepare.manifest}' = $prepareManifestPath
        '{request.scope}' = $RequestScope
        '{scope.key}' = $ScopeKey
        '{season}' = $Season
        '{person.id}' = $PersonId
        '{resource.kind}' = $ResourceKind
    }
    foreach ($entry in $inputs.GetEnumerator()) {
        $tokens["{input.$($entry.Key)}"] = [string]$entry.Value
        if (Test-Path -LiteralPath $entry.Value -PathType Leaf) {
            $tokens["{input.$($entry.Key).sha256}"] = (Get-FileHash -LiteralPath $entry.Value -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    if (-not $tokens.Contains($Argument)) {
        return $Argument
    }
    $value = [string]$tokens[$Argument]
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required context token $Argument has no value."
    }
    return $value
}

switch ($Action) {
    'context' {
        Require-Inputs
        $builder = Resolve-ModuleArtifact ([string]$contract.context.builder)
        $arguments = @($contract.context.arguments | ForEach-Object { Expand-ContextArgument ([string]$_) })
        Invoke-LoggedCommand -FailureMessage "$moduleId input/context validation failed." -Command {
            & python $builder @arguments
        }
        if (-not (Test-Path -LiteralPath $contextPath -PathType Leaf)) {
            throw "$moduleId context builder produced no execution context."
        }
        $inputEvidence = [ordered]@{}
        foreach ($entry in $inputs.GetEnumerator()) {
            $inputEvidence[$entry.Key] = [ordered]@{
                path = $entry.Value
                sha256 = (Get-FileHash -LiteralPath $entry.Value -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
        Write-StageResult @{
            inputs = $inputEvidence
            contextPath = $contextPath
            contextSha256 = (Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    'rml' {
        if (-not (Test-Path -LiteralPath $contextPath -PathType Leaf)) {
            throw "$moduleId execution context is missing."
        }
        $runner = Join-Path $repositoryRoot 'scripts\pipeline\run-source-rml.ps1'
        $mapping = Resolve-ModuleArtifact ([string]$contract.mapping)
        Invoke-LoggedCommand -FailureMessage "$moduleId RML failed." -Command {
            & $runner -ModuleId $moduleId -ContextJson $contextPath -MappingFile $mapping -MappingContextName ([string]$contract.context.contextName) -OutputFile $rdfPath -ManifestFile $manifestPath
        }
        Write-StageResult @{
            rdfPath = $rdfPath
            rdfSha256 = (Get-FileHash -LiteralPath $rdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
            rmlManifest = $manifestPath
        }
    }
    'shacl' {
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf) -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            throw "$moduleId RDF or RML manifest is missing."
        }
        $shape = Resolve-ModuleArtifact ([string]$contract.shacl)
        $report = Join-Path $evidenceRoot 'shacl-report.json'
        $validator = Join-Path $repositoryRoot 'scripts\pipeline\validate-shacl.py'
        $validatorArguments = @(
            $validator,
            '--shape-file', $shape,
            '--data', $rdfPath,
            '--report-json', $report,
            '--engine', $shaclEngine
        )
        if ($shaclEngine -eq 'jena') {
            $validatorArguments += @(
                '--java', (Get-JavaExecutable),
                '--jena-classpath', (Join-Path $script:FusekiHome 'fuseki-server.jar'),
                '--jena-max-heap', $shaclJenaMaxHeap
            )
        }
        Invoke-LoggedCommand -FailureMessage "$moduleId source SHACL failed." -Command {
            & python @validatorArguments
        }
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $manifest | Add-Member -NotePropertyName 'shaclStatus' -NotePropertyValue 'validated' -Force
        $manifest | Add-Member -NotePropertyName 'shaclValidatedAtUtc' -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
        $manifest | Add-Member -NotePropertyName 'shaclShapeSha256' -NotePropertyValue ((Get-FileHash -LiteralPath $shape -Algorithm SHA256).Hash.ToLowerInvariant()) -Force
        $manifest | Add-Member -NotePropertyName 'shaclEngine' -NotePropertyValue $shaclEngine -Force
        $manifest | Add-Member -NotePropertyName 'shaclValidatorSha256' -NotePropertyValue ((Get-FileHash -LiteralPath $validator -Algorithm SHA256).Hash.ToLowerInvariant()) -Force
        Write-AtomicJsonFile -Path $manifestPath -Value $manifest -Depth 16
        Write-StageResult @{
            conforms = $true
            shaclEngine = $shaclEngine
            shaclReport = $report
            shaclShape = $shape
        }
    }
    'promote' {
        if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf) -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            throw "$moduleId validated RDF is missing."
        }
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        if ([string]$manifest.shaclStatus -ne 'validated') {
            throw "$moduleId RDF has not passed source SHACL."
        }
        $graphIri = ([string]$contract.authoritativeGraphTemplate).Replace('{scope.key}', $ScopeKey)
        $catalog = Get-Content -LiteralPath (Join-Path $repositoryRoot 'sources\source-modules.json') -Raw | ConvertFrom-Json
        $module = @($catalog.modules | Where-Object { $_.id -eq $moduleId })
        if ($module.Count -ne 1 -or -not (@($module[0].authoritativeGraphPrefixes) | Where-Object { $graphIri.StartsWith([string]$_, [System.StringComparison]::Ordinal) })) {
            throw "$moduleId graph IRI is outside its registered authoritative namespace: $graphIri"
        }
        $dataUri = "$($script:FusekiDatasetUri)/data?graph=$([Uri]::EscapeDataString($graphIri))"
        $backupPath = Join-Path $workRoot 'previous-graph.ttl'
        $priorExists = $false
        $lock = Enter-FusekiWriteLock
        try {
            $ask = "ASK { GRAPH <$graphIri> { ?s ?p ?o } }"
            $prior = Invoke-RestMethod -Uri "$($script:FusekiDatasetUri)/query" -Method Post -Body @{ query = $ask } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 60
            $priorExists = $prior.boolean -eq $true
            if ($priorExists) {
                Invoke-WebRequest -Uri $dataUri -Method Get -Headers @{ Accept = 'text/turtle' } -OutFile $backupPath -TimeoutSec 120 -UseBasicParsing | Out-Null
            }
            try {
                Invoke-WebRequest -Uri $dataUri -Method Put -InFile $rdfPath -ContentType 'text/turtle; charset=utf-8' -TimeoutSec 600 -UseBasicParsing | Out-Null
                $countQuery = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$graphIri> { ?s ?p ?o } }"
                $countResult = Invoke-RestMethod -Uri "$($script:FusekiDatasetUri)/query" -Method Post -Body @{ query = $countQuery } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 120
                $tripleCount = [int64]@($countResult.results.bindings)[0].count.value
                if ($tripleCount -le 0) {
                    throw "$moduleId promoted an empty authoritative graph."
                }
            }
            catch {
                if ($priorExists -and (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
                    Invoke-WebRequest -Uri $dataUri -Method Put -InFile $backupPath -ContentType 'text/turtle; charset=utf-8' -TimeoutSec 600 -UseBasicParsing | Out-Null
                }
                else {
                    try { Invoke-WebRequest -Uri $dataUri -Method Delete -TimeoutSec 120 -UseBasicParsing | Out-Null } catch { }
                }
                throw
            }
        }
        finally {
            Exit-FusekiWriteLock -LockHandle $lock
        }
        $promotionPath = Join-Path $evidenceRoot 'promotion.json'
        $promotion = [ordered]@{
            artifactType = 'baseballo-source-graph-promotion'
            contractVersion = 1
            sourceModule = $moduleId
            scopeKey = $ScopeKey
            pipelineRunId = $RunId
            promotedAtUtc = [DateTime]::UtcNow.ToString('o')
            authoritativeGraph = $graphIri
            tripleCount = $tripleCount
            rdfSha256 = (Get-FileHash -LiteralPath $rdfPath -Algorithm SHA256).Hash.ToLowerInvariant()
            replacedPriorGraph = $priorExists
        }
        Write-AtomicJsonFile -Path $promotionPath -Value $promotion -Depth 12
        Write-StageResult @{
            authoritativeGraph = $graphIri
            tripleCount = $tripleCount
            promotionEvidence = $promotionPath
        }
    }
    'emit' {
        $promotionPath = Join-Path $evidenceRoot 'promotion.json'
        if (-not (Test-Path -LiteralPath $promotionPath -PathType Leaf)) {
            throw "$moduleId promotion evidence is missing; no downstream event can be emitted."
        }
        $emitter = Join-Path $repositoryRoot ([string]$eventContract.emitter)
        $resultPath = Join-Path $evidenceRoot 'promoted-graph-event-emission.json'
        Invoke-LoggedCommand -FailureMessage "$moduleId promoted-graph event emission failed." -Command {
            & python $emitter '--state-root' $script:StateRoot '--promotion-evidence' $promotionPath '--result-json' $resultPath
        }
        $emission = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        if ([string]$emission.status -notin @('created', 'already-present')) {
            throw "$moduleId promoted-graph event was not durably emitted."
        }
        Write-StageResult @{
            promotedGraphEvent = [string]$emission.eventPath
            promotedGraphEventSha256 = [string]$emission.eventSha256
            promotedGraphEventId = [string]$emission.eventId
        }
    }
    'cleanup' {
        $deleted = @()
        foreach ($path in @($inputs.Values) + @($contextPath, $prepareManifestPath, $rdfPath)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$path) -and (Test-Path -LiteralPath $path -PathType Leaf)) {
                Remove-Item -LiteralPath $path -Force
                $deleted += [string]$path
            }
        }
        Write-StageResult @{
            deletedTransientArtifacts = $deleted
            authoritativeRdfRemainsInGraphStore = $true
        }
    }
    'quarantine' {
        $quarantineRoot = Join-Path $pipelineRoot "quarantine\$moduleId\$ScopeKey\$RunId"
        [void](New-Item -ItemType Directory -Force -Path $quarantineRoot)
        $retained = @()
        foreach ($entry in $inputs.GetEnumerator()) {
            if (Test-Path -LiteralPath $entry.Value -PathType Leaf) {
                $destination = Join-Path $quarantineRoot (Split-Path -Leaf $entry.Value)
                Move-Item -LiteralPath $entry.Value -Destination $destination -Force
                $retained += [ordered]@{
                    key = $entry.Key
                    path = $destination
                    sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
                }
            }
        }
        Write-StageResult @{
            failureStage = $FailureStage
            retainedInputs = $retained
            retryExhausted = $true
        }
    }
}
