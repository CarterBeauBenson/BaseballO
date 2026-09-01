[CmdletBinding()]
param([ValidateRange(30, 900)][int] $TimeoutSeconds = 300)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout

$launcher = Join-Path $script:NiFiHome 'bin\nifi.cmd'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "NiFi is not installed at $launcher. Run bootstrap.ps1 first."
}
Set-JavaEnvironment
$bootstrapConfig = Join-Path $script:NiFiHome 'conf\bootstrap.conf'
if (-not (Test-Path -LiteralPath $bootstrapConfig -PathType Leaf)) {
    throw "NiFi bootstrap configuration is missing: $bootstrapConfig"
}
Set-KeyValueProperty -Path $bootstrapConfig -Key 'java.arg.99' -Value '-Duser.timezone=America/New_York'
if (Test-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort) {
    Write-Host "NiFi is already listening at $script:NiFiBaseUri/nifi/."
    return
}

$arguments = '/d /s /c ""' + $launcher + '" start"'
[void](Start-Process -FilePath $env:ComSpec -ArgumentList $arguments -WorkingDirectory $script:NiFiHome -WindowStyle Hidden -PassThru)
if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port $script:NiFiPort -Open $true -TimeoutSeconds $TimeoutSeconds)) {
    throw "NiFi did not open port $script:NiFiPort within $TimeoutSeconds seconds."
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    try {
        $root = Invoke-RestMethod -Uri "$script:NiFiApiUri/flow/process-groups/root" -Method Get -TimeoutSec 10
        if (-not [string]::IsNullOrWhiteSpace([string]$root.processGroupFlow.id)) {
            Write-Host "NiFi started at $script:NiFiBaseUri/nifi/."
            return
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
} while ((Get-Date) -lt $deadline)
throw 'NiFi opened its port but its REST API did not become ready.'
