[CmdletBinding()]
param([int] $TimeoutSeconds = 60)

. (Join-Path $PSScriptRoot 'common.ps1')
$nifiCommand = Join-Path $script:NiFiHome 'bin\nifi.cmd'
if (-not (Test-Path -LiteralPath $nifiCommand -PathType Leaf)) {
    Write-Host 'NiFi is not installed; nothing to stop.'
    exit 0
}

Set-JavaEnvironment
& $nifiCommand stop
if ($LASTEXITCODE -ne 0) {
    throw 'NiFi stop command failed.'
}

if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port 8443 -Open $false -TimeoutSeconds $TimeoutSeconds)) {
    throw "NiFi did not stop within $TimeoutSeconds seconds."
}
Write-Host 'NiFi stopped.'
