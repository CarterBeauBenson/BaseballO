[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $RdfFile,
    [Parameter(Mandatory = $true)][string] $GamePk
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')

if ($GamePk -notmatch '^\d+$') {
    throw "GamePk must contain only digits: $GamePk"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}
$rdfPath = [System.IO.Path]::GetFullPath($RdfFile)
if (-not (Test-Path -LiteralPath $rdfPath -PathType Leaf)) {
    throw "RDF file was not found: $rdfPath"
}

$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-generated-rdf.py'
& python $validatorPath $rdfPath $GamePk
if ($LASTEXITCODE -ne 0) {
    throw "Refusing to load invalid RDF for game $GamePk."
}

$graphIri = "https://w3id.org/baseball/graph/game/$GamePk"
$encodedGraph = [Uri]::EscapeDataString($graphIri)
$dataEndpoint = "http://127.0.0.1:3030/baseball-dev/data?graph=$encodedGraph"
Invoke-WebRequest -Uri $dataEndpoint -Method Put -ContentType 'text/turtle' -InFile $rdfPath -UseBasicParsing | Out-Null

$query = "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <$graphIri> { ?s ?p ?o } }"
$result = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
$count = [int64]$result.results.bindings[0].count.value
if ($count -le 0) {
    throw "Fuseki graph $graphIri is empty after PUT."
}

$gameIri = "https://baseballontology.org/data/game/$GamePk"
$ask = "ASK { GRAPH <$graphIri> { <$gameIri> a <https://baseballontology.org/BaseballGame> } }"
$askResult = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/baseball-dev/query' -Method Post -Body @{ query = $ask } -Headers @{ Accept = 'application/sparql-results+json' }
if ($askResult.boolean -ne $true) {
    throw "Expected BaseballGame assertion was not found in $graphIri."
}

Write-Host "Loaded graph: $graphIri"
Write-Host "Graph triples: $count"
