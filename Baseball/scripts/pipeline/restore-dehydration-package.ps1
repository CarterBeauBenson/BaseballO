[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $PackageDirectory,
    [switch] $Load
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$packageRoot = [System.IO.Path]::GetFullPath($PackageDirectory)
$manifestPath = Join-Path $packageRoot 'manifest.json'
$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-dehydration-package.py'
& python $validatorPath $packageRoot
if ($LASTEXITCODE -ne 0) {
    throw "Refusing to restore an invalid dehydration package: $packageRoot"
}
if (-not $Load) {
    Write-Host 'Package validation passed. Use -Load to replace the two named graphs.'
    return
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$sourceGraph = [string]$manifest.authoritativeGraph.graphIri
$indexGraph = [string]$manifest.queryIndexGraph.graphIri
$sourcePath = Join-Path $packageRoot (([string]$manifest.authoritativeGraph.path) -replace '/', [System.IO.Path]::DirectorySeparatorChar)
$indexPath = Join-Path $packageRoot (([string]$manifest.queryIndexGraph.path) -replace '/', [System.IO.Path]::DirectorySeparatorChar)
$sourceEndpoint = "http://127.0.0.1:3030/baseball-dev/data?graph=$([Uri]::EscapeDataString($sourceGraph))"
$indexEndpoint = "http://127.0.0.1:3030/baseball-dev/data?graph=$([Uri]::EscapeDataString($indexGraph))"

# Remove the disposable graph first. If either authoritative or index loading
# fails, an old shortcut graph cannot remain visible beside new source data.
try {
    Invoke-WebRequest -Uri $indexEndpoint -Method Delete -UseBasicParsing | Out-Null
}
catch {
    # Absence is already the desired pre-load state.
}
Invoke-WebRequest -Uri $sourceEndpoint -Method Put -ContentType 'text/turtle' -InFile $sourcePath -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri $indexEndpoint -Method Put -ContentType 'application/n-triples' -InFile $indexPath -UseBasicParsing | Out-Null

$queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
$countQuery = "SELECT ?sourceTriples ?indexTriples WHERE { { SELECT (COUNT(*) AS ?sourceTriples) WHERE { GRAPH <$sourceGraph> { ?s ?p ?o } } } { SELECT (COUNT(*) AS ?indexTriples) WHERE { GRAPH <$indexGraph> { ?s ?p ?o } } } }"
$result = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $countQuery } -Headers @{ Accept = 'application/sparql-results+json' }
$sourceCount = [int64]$result.results.bindings[0].sourceTriples.value
$indexCount = [int64]$result.results.bindings[0].indexTriples.value
if ($sourceCount -ne [int64]$manifest.authoritativeGraph.tripleCount -or $indexCount -ne [int64]$manifest.queryIndexGraph.tripleCount) {
    throw "Restored graph counts differ from the package: source=$sourceCount; index=$indexCount"
}

$gamePk = [string]$manifest.gamePk
$metadataAsk = "ASK { GRAPH <$sourceGraph> { <https://baseballontology.org/data/game/$gamePk> a <https://baseballontology.org/BaseballGame> } GRAPH <$indexGraph> { <https://w3id.org/baseball/query-index-build/game/$gamePk> a <https://w3id.org/baseball/query-index/QueryIndex> ; <https://w3id.org/baseball/query-index/sourceGraph> <$sourceGraph> } }"
$metadata = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $metadataAsk } -Headers @{ Accept = 'application/sparql-results+json' }
if ($metadata.boolean -ne $true) {
    throw 'Restored graphs failed the expected game/index metadata assertion.'
}

Write-Host "Restored authoritative graph: $sourceGraph ($sourceCount triples)"
Write-Host "Restored query-index graph: $indexGraph ($indexCount triples)"
