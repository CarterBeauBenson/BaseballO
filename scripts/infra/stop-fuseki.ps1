[CmdletBinding()]
param([int] $TimeoutSeconds = 30)

. (Join-Path $PSScriptRoot 'common.ps1')
$pidFile = Join-Path $script:FusekiState 'fuseki.pid'

if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
    Write-Host 'Fuseki PID file is absent; nothing to stop.'
    exit 0
}

$fusekiPid = [int](Get-Content -LiteralPath $pidFile -Raw)
$process = Get-Process -Id $fusekiPid -ErrorAction SilentlyContinue
if ($null -eq $process) {
    Remove-Item -LiteralPath $pidFile -Force
    Write-Host 'Fuseki process is already stopped.'
    exit 0
}

$expectedJava = [System.IO.Path]::GetFullPath((Get-JavaExecutable))
$actualExecutable = [System.IO.Path]::GetFullPath($process.Path)
if ($actualExecutable -ne $expectedJava) {
    throw "Refusing to stop PID $fusekiPid because it is not the BaseballO Java runtime."
}
$processDetails = Get-CimInstance Win32_Process -Filter "ProcessId = $fusekiPid"
if ($null -eq $processDetails -or $processDetails.CommandLine -notlike '*fuseki-server.jar*') {
    throw "Refusing to stop PID $fusekiPid because its command line is not the BaseballO Fuseki server."
}

Stop-Process -Id $fusekiPid
if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port 3030 -Open $false -TimeoutSeconds $TimeoutSeconds)) {
    throw "Fuseki did not stop within $TimeoutSeconds seconds."
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host 'Fuseki stopped.'
