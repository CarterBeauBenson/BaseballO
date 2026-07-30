[CmdletBinding()]
param([int] $TimeoutSeconds = 600)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

if (Test-TcpPort -HostName '127.0.0.1' -Port 8443) {
    Write-Host 'NiFi is already listening at https://127.0.0.1:8443/nifi/.'
    exit 0
}

[void](Get-JavaExecutable)
$nifiCommand = Join-Path $script:NiFiHome 'bin\nifi.cmd'
if (-not (Test-Path -LiteralPath $nifiCommand -PathType Leaf)) {
    throw "NiFi is not installed at $nifiCommand. Run scripts\infra\bootstrap.ps1 first."
}

Set-JavaEnvironment
& $nifiCommand start
if ($LASTEXITCODE -ne 0) {
    throw 'NiFi start command failed.'
}

if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port 8443 -Open $true -TimeoutSeconds $TimeoutSeconds)) {
    throw "NiFi did not become ready within $TimeoutSeconds seconds. Check $script:NiFiHome\logs\nifi-app.log."
}

Write-Host 'NiFi is ready at https://127.0.0.1:8443/nifi/.'
Write-Host 'Use scripts\infra\show-nifi-credentials.ps1 to display the local login.'
