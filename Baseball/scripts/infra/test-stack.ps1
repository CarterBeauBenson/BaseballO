[CmdletBinding()]
param([switch] $WriteProbe)

. (Join-Path $PSScriptRoot 'common.ps1')

$java = Get-JavaExecutable
$previousErrorPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$javaVersionOutput = & $java -version 2>&1
$javaExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorPreference
if ($javaExitCode -ne 0) {
    throw 'The BaseballO Java runtime did not return its version.'
}
$javaVersion = ($javaVersionOutput | Select-Object -First 1).ToString()
if ($javaVersion -notmatch '21\.0\.12') {
    throw "Unexpected Java version: $javaVersion"
}
Write-Host "Java: $javaVersion"

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
    throw 'Fuseki is not listening on port 3031.'
}
$askResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:3031/baseball-dev/query' -Method Post -Body @{ query = 'ASK { }' } -Headers @{ Accept = 'application/sparql-results+json' }
if ($askResponse.boolean -ne $true) {
    throw 'Fuseki ASK health query did not return true.'
}
Write-Host 'Fuseki: query endpoint healthy.'

if ($WriteProbe) {
    $graph = 'urn:baseballo:infra:write-probe'
    $graphParameter = [Uri]::EscapeDataString($graph)
    $dataEndpoint = "http://127.0.0.1:3031/baseball-dev/data?graph=$graphParameter"
    $probe = '@prefix ex: <urn:baseballo:infra:> . ex:probe ex:status "ok" .'
    Invoke-RestMethod -Uri $dataEndpoint -Method Put -ContentType 'text/turtle' -Body $probe | Out-Null
    try {
        $query = "ASK { GRAPH <$graph> { <urn:baseballo:infra:probe> <urn:baseballo:infra:status> `"ok`" } }"
        $probeResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:3031/baseball-dev/query' -Method Post -Body @{ query = $query } -Headers @{ Accept = 'application/sparql-results+json' }
        if ($probeResponse.boolean -ne $true) {
            throw 'Fuseki write probe was not readable from its named graph.'
        }
        Write-Host 'Fuseki: named-graph write/read probe passed.'
    }
    finally {
        Invoke-RestMethod -Uri $dataEndpoint -Method Delete | Out-Null
    }
}

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    throw "NiFi is not listening on port $script:NiFiPort."
}
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if ($null -ne $curl) {
    $status = (& $curl.Source --silent --output NUL --write-out '%{http_code}' "$script:NiFiBaseUri/nifi/").Trim()
    if ($status -notin @('200', '302', '303')) {
        throw "NiFi returned unexpected HTTP status $status."
    }
    Write-Host "NiFi: HTTPS endpoint healthy (HTTP $status)."
}
else {
    Write-Host 'NiFi: HTTPS port is reachable (curl.exe unavailable for an HTTP probe).'
}

Write-Host 'BaseballO local stack checks passed.'
