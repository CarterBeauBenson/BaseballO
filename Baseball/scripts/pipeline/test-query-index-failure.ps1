[CmdletBinding()]
param(
    [string] $GamePk = '566279'
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

if ($GamePk -notmatch '^\d+$') {
    throw "GamePk must contain only digits: $GamePk"
}
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}

$fixturePath = Join-Path $script:RepositoryRoot "data\raw\game-$GamePk.json"
if (-not (Test-Path -LiteralPath $fixturePath -PathType Leaf)) {
    throw "Failure test fixture is missing: $fixturePath"
}
$fixtureHashBefore = (Get-FileHash -LiteralPath $fixturePath -Algorithm SHA256).Hash.ToLowerInvariant()
$testRoot = Join-Path $script:StateRoot ("pipeline\failure-tests\query-index-" + [Guid]::NewGuid().ToString('N'))
$componentRoot = Join-Path $testRoot 'components'
[void](New-Item -ItemType Directory -Force -Path $componentRoot)
Copy-Item -Path (Join-Path $script:RepositoryRoot 'sparql\query-index\components\*.rq') -Destination $componentRoot

$expectedFailure = $false
try {
    $brokenComponent = Join-Path $componentRoot '00-index-metadata.rq'
    [System.IO.File]::WriteAllText($brokenComponent, "THIS IS DELIBERATELY INVALID SPARQL`n", [System.Text.UTF8Encoding]::new($false))
    try {
        & (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $GamePk -ComponentRoot $componentRoot
    }
    catch {
        $expectedFailure = $true
        Write-Host "Observed expected component failure: $($_.Exception.Message)"
    }
    if (-not $expectedFailure) {
        throw 'The malformed query-index component unexpectedly succeeded.'
    }

    $sourceGraph = "https://w3id.org/baseball/graph/game/$GamePk"
    $indexGraph = "https://w3id.org/baseball/graph/query-index/game/$GamePk"
    $queryEndpoint = 'http://127.0.0.1:3030/baseball-dev/query'
    $stateAsk = "SELECT ?sourcePresent ?indexPresent WHERE { BIND(EXISTS { GRAPH <$sourceGraph> { <https://baseballontology.org/data/game/$GamePk> a <https://baseballontology.org/BaseballGame> } } AS ?sourcePresent) BIND(EXISTS { GRAPH <$indexGraph> { ?s ?p ?o } } AS ?indexPresent) }"
    $state = Invoke-RestMethod -Uri $queryEndpoint -Method Post -Body @{ query = $stateAsk } -Headers @{ Accept = 'application/sparql-results+json' }
    $binding = $state.results.bindings[0]
    if ([string]$binding.sourcePresent.value -ne 'true') {
        throw 'Authoritative graph disappeared during query-index failure injection.'
    }
    if ([string]$binding.indexPresent.value -ne 'false') {
        throw 'Failed query-index build left a derived graph visible.'
    }

    & (Join-Path $PSScriptRoot 'build-query-index.ps1') -GamePk $GamePk
    & (Join-Path $PSScriptRoot 'test-query-index.ps1') -GamePk $GamePk -SkipBuild

    $fixtureHashAfter = (Get-FileHash -LiteralPath $fixturePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($fixtureHashAfter -ne $fixtureHashBefore) {
        throw 'Query-index failure test changed the checked-in raw fixture.'
    }
    Write-Host 'Query-index failure and stale-graph regression passed.'
}
finally {
    if (Test-Path -LiteralPath $testRoot -PathType Container) {
        $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
        $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'pipeline\failure-tests'))
        if (-not $resolvedTestRoot.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove an unexpected failure-test path: $resolvedTestRoot"
        }
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
