[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')

$javaInstalled = Test-Path -LiteralPath (Join-Path $script:JavaHome 'bin\java.exe') -PathType Leaf
$nifiInstalled = Test-Path -LiteralPath (Join-Path $script:NiFiHome 'bin\nifi.cmd') -PathType Leaf
$fusekiInstalled = Test-Path -LiteralPath (Join-Path $script:FusekiHome 'fuseki-server.jar') -PathType Leaf
$nifiListening = Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort
$fusekiListening = Test-TcpPort -HostName '127.0.0.1' -Port $script:FusekiPort
$fusekiOwned = Test-BaseballFusekiService

$nifiHttp = 'stopped'
if ($nifiListening) {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($null -ne $curl) {
        $nifiHttp = (& $curl.Source --silent --output NUL --write-out '%{http_code}' "$script:NiFiBaseUri/nifi/").Trim()
    }
    else {
        $nifiHttp = 'port open'
    }
}

$fusekiHttp = 'stopped'
if ($fusekiListening) {
    $fusekiHttp = if ($fusekiOwned) { 'dataset healthy' } else { 'foreign or unhealthy service' }
}

@(
    [PSCustomObject]@{ Component = 'Java 21'; Installed = $javaInstalled; Listening = '-'; HTTP = '-' },
    [PSCustomObject]@{ Component = "NiFi 2.10.0 :$($script:NiFiPort)"; Installed = $nifiInstalled; Listening = $nifiListening; HTTP = $nifiHttp },
    [PSCustomObject]@{ Component = "Fuseki 6.1.0 :$($script:FusekiPort)"; Installed = $fusekiInstalled; Listening = $fusekiListening; HTTP = $fusekiHttp }
) | Format-Table -AutoSize

Write-Host "Local root: $script:LocalRoot"
Write-Host "RDF storage: $script:RdfStorageMode"
if (-not $script:RdfStorageAvailable) {
    Write-Warning $script:RdfStorageError
}
Write-Host "TDB2 data: $(Join-Path $script:FusekiState 'databases\baseball-dev')"
