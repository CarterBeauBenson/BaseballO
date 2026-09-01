[CmdletBinding()]
param([ValidateRange(15, 300)][int] $TimeoutSeconds = 120)

. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort)) {
    Write-Host 'NiFi is already stopped.'
    return
}
$launcher = Join-Path $script:NiFiHome 'bin\nifi.cmd'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "NiFi launcher was not found at $launcher."
}

Set-JavaEnvironment
$arguments = '/d /s /c ""' + $launcher + '" stop"'
$process = Start-Process -FilePath $env:ComSpec -ArgumentList $arguments -WorkingDirectory $script:NiFiHome -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) {
    throw "NiFi stop command exited with code $($process.ExitCode)."
}
if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort -Open $false -TimeoutSeconds $TimeoutSeconds)) {
    throw "NiFi did not close port $script:NiFiPort within $TimeoutSeconds seconds."
}
Write-Host 'NiFi stopped.'
