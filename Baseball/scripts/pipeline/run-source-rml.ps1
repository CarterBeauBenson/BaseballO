[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-z0-9-]+$')][string] $ModuleId,
    [Parameter(Mandatory = $true)][string] $ContextJson,
    [Parameter(Mandatory = $true)][string] $MappingFile,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]+[.]json$')][string] $MappingContextName,
    [Parameter(Mandatory = $true)][string] $OutputFile,
    [Parameter(Mandatory = $true)][string] $ManifestFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$moduleRoot = [System.IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot "sources\$ModuleId"))
if (-not (Test-Path -LiteralPath $moduleRoot -PathType Container)) {
    throw "Unknown source module: $ModuleId"
}

$contextPath = [System.IO.Path]::GetFullPath($ContextJson)
$mappingPath = [System.IO.Path]::GetFullPath($MappingFile)
$outputPath = [System.IO.Path]::GetFullPath($OutputFile)
$manifestPath = [System.IO.Path]::GetFullPath($ManifestFile)
$modulePrefix = $moduleRoot + [System.IO.Path]::DirectorySeparatorChar
if (-not $mappingPath.StartsWith($modulePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "RML mapping must be owned by source module $ModuleId."
}
if (-not (Test-Path -LiteralPath $contextPath -PathType Leaf)) {
    throw "RML execution context does not exist: $contextPath"
}
if (-not (Test-Path -LiteralPath $mappingPath -PathType Leaf)) {
    throw "RML mapping does not exist: $mappingPath"
}

$contextHashBefore = (Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant()
$mappingHash = (Get-FileHash -LiteralPath $mappingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$workRoot = Join-Path $script:StateRoot "pipeline\work\$ModuleId"
[void](New-Item -ItemType Directory -Force -Path $workRoot)
$stage = Join-Path $workRoot ([Guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $stage)
$stageContext = Join-Path $stage $MappingContextName
$stageMapping = Join-Path $stage (Split-Path -Leaf $mappingPath)
$stageOutput = Join-Path $stage 'candidate.ttl'
$stageLog = Join-Path $stage 'rmlmapper.log'

try {
    & python (Join-Path $script:RepositoryRoot 'scripts\validate_semantic_change_control.py') '--runtime-admission' $ModuleId
    if ($LASTEXITCODE -ne 0) {
        throw "The $ModuleId semantic artifacts do not match their accepted runtime admission."
    }

    Copy-Item -LiteralPath $contextPath -Destination $stageContext
    Copy-Item -LiteralPath $mappingPath -Destination $stageMapping
    if ((Get-FileHash -LiteralPath $stageContext -Algorithm SHA256).Hash.ToLowerInvariant() -ne $contextHashBefore) {
        throw "The staged $ModuleId context is not byte-identical to its validated input."
    }

    $java = Get-JavaExecutable
    $mapper = Get-RMLMapperJar
    Push-Location $stage
    try {
        $priorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $mapperOutput = & $java '-Xmx2g' '-jar' $mapper '-m' $stageMapping '-o' $stageOutput '-s' 'turtle' '-b' "https://baseballontology.org/mapping/$ModuleId" '--strict' 2>&1
        $mapperExitCode = $LASTEXITCODE
        $ErrorActionPreference = $priorPreference
        $mapperOutput | Set-Content -LiteralPath $stageLog -Encoding UTF8
    }
    finally {
        Pop-Location
    }
    if ($mapperExitCode -ne 0) {
        $tail = (Get-Content -LiteralPath $stageLog -Tail 30) -join "`n"
        throw "RMLMapper failed for $ModuleId with exit code $mapperExitCode.`n$tail"
    }
    if (-not (Test-Path -LiteralPath $stageOutput -PathType Leaf) -or (Get-Item -LiteralPath $stageOutput).Length -eq 0) {
        throw "RMLMapper produced no RDF for $ModuleId."
    }
    if ((Get-FileHash -LiteralPath $contextPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $contextHashBefore) {
        throw "The $ModuleId execution context changed during RML execution."
    }

    [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath))
    Copy-Item -LiteralPath $stageOutput -Destination $outputPath -Force
    $manifest = [ordered]@{
        artifactType = 'baseballo-source-rml-run'
        contractVersion = 1
        sourceModule = $ModuleId
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        contextPath = $contextPath
        contextSha256 = $contextHashBefore
        mappingPath = $mappingPath
        mappingSha256 = $mappingHash
        rdfPath = $outputPath
        rdfSha256 = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash.ToLowerInvariant()
        shaclStatus = 'pending'
    }
    Write-AtomicJsonFile -Path $manifestPath -Value $manifest -Depth 12
    Write-Output ($manifest | ConvertTo-Json -Depth 12 -Compress)
}
finally {
    if (Test-Path -LiteralPath $stage -PathType Container) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
