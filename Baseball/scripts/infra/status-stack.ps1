[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')

$javaInstalled = Test-Path -LiteralPath (Join-Path $script:JavaHome 'bin\java.exe') -PathType Leaf
$nifiInstalled = Test-Path -LiteralPath (Join-Path $script:NiFiHome 'bin\nifi.cmd') -PathType Leaf
$fusekiInstalled = Test-Path -LiteralPath (Join-Path $script:FusekiHome 'fuseki-server.jar') -PathType Leaf
$nifiListening = Test-TcpPort -HostName '127.0.0.1' -Port 8443
$fusekiListening = Test-TcpPort -HostName '127.0.0.1' -Port 3030

$nifiHttp = 'stopped'
if ($nifiListening) {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($null -ne $curl) {
        $nifiHttp = (& $curl.Source --silent --insecure --output NUL --write-out '%{http_code}' 'https://127.0.0.1:8443/nifi/').Trim()
    }
    else {
        $nifiHttp = 'port open'
    }
}

$fusekiHttp = 'stopped'
if ($fusekiListening) {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:3030/$/ping' -UseBasicParsing
        $fusekiHttp = [string]$response.StatusCode
    }
    catch {
        $fusekiHttp = 'port open; ping failed'
    }
}

@(
    [PSCustomObject]@{ Component = 'Java 21'; Installed = $javaInstalled; Listening = '-'; HTTP = '-' },
    [PSCustomObject]@{ Component = 'NiFi 2.10.0'; Installed = $nifiInstalled; Listening = $nifiListening; HTTP = $nifiHttp },
    [PSCustomObject]@{ Component = 'Fuseki 6.1.0'; Installed = $fusekiInstalled; Listening = $fusekiListening; HTTP = $fusekiHttp }
) | Format-Table -AutoSize

Write-Host "Local root: $script:LocalRoot"
Write-Host "TDB2 data: $(Join-Path $script:FusekiState 'databases\baseball-dev')"
