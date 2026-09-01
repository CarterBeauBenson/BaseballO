[CmdletBinding()]
param([int] $TimeoutSeconds = 120)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

if (Test-TcpPort -HostName '127.0.0.1' -Port $script:FusekiPort) {
    if (Test-BaseballFusekiService) {
        Write-Host "BaseballO Fuseki is already listening at $($script:FusekiBaseUri)/."
        exit 0
    }
    throw "Port $($script:FusekiPort) is occupied by a service that is not the BaseballO Fuseki dataset."
}

$java = Get-JavaExecutable
$jar = Join-Path $script:FusekiHome 'fuseki-server.jar'
$config = Join-Path $script:FusekiState 'configuration\baseball-dev.ttl'
$logDirectory = Join-Path $script:FusekiState 'logs'
$pidFile = Join-Path $script:FusekiState 'fuseki.pid'

if (-not (Test-Path -LiteralPath $jar -PathType Leaf)) {
    throw "Fuseki is not installed at $jar. Run scripts\infra\bootstrap.ps1 first."
}
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw "Fuseki configuration is missing at $config. Run scripts\infra\bootstrap.ps1 first."
}
[void](New-Item -ItemType Directory -Force -Path $logDirectory)

$oldFusekiBase = $env:FUSEKI_BASE
$oldFusekiHome = $env:FUSEKI_HOME
$env:FUSEKI_BASE = $script:FusekiState
$env:FUSEKI_HOME = $script:FusekiHome
try {
    $arguments = @(
        '-Xms256m',
        '-Xmx1g',
        '-jar',
        "`"$jar`"",
        '--localhost',
        "--port=$($script:FusekiPort)"
    )
    $process = Start-Process -FilePath $java -ArgumentList $arguments -WorkingDirectory $script:FusekiState -RedirectStandardOutput (Join-Path $logDirectory 'stdout.log') -RedirectStandardError (Join-Path $logDirectory 'stderr.log') -PassThru -WindowStyle Hidden
    Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII -NoNewline
}
finally {
    $env:FUSEKI_BASE = $oldFusekiBase
    $env:FUSEKI_HOME = $oldFusekiHome
}

if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port $script:FusekiPort -Open $true -TimeoutSeconds $TimeoutSeconds)) {
    throw "Fuseki did not become ready within $TimeoutSeconds seconds. Check $logDirectory."
}

if (-not (Test-BaseballFusekiService)) {
    throw "A listener opened port $($script:FusekiPort), but the BaseballO dataset health check failed."
}

Write-Host "BaseballO Fuseki is ready at $($script:FusekiBaseUri)/."
