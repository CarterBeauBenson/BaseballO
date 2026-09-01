[CmdletBinding()]
param(
    [switch] $NoBrowser,
    [switch] $SkipNiFi,
    [int] $TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$explorerUri = 'http://127.0.0.1:4173/'
$explorerStatusUri = "${explorerUri}api/status"
$webRoot = Join-Path $script:RepositoryRoot 'web'
$explorerState = Join-Path $script:StateRoot 'explorer'
$logDirectory = Join-Path $explorerState 'logs'
$pidFile = Join-Path $explorerState 'explorer.pid'
$startedExplorerProcess = $null

function Invoke-StartupScript {
    param([Parameter(Mandatory = $true)][string] $Path)

    $powershell = Join-Path $PSHOME 'powershell.exe'
    & $powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File $Path
    if ($LASTEXITCODE -ne 0) {
        throw "Startup script failed: $Path"
    }
}

function Get-ExplorerStatus {
    try {
        $status = Invoke-RestMethod -Uri $explorerStatusUri -Method Get -TimeoutSec 5
        if ($status.connected -eq $true) {
            return $status
        }
        return $null
    }
    catch {
        return $null
    }
}

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string] $Value)

    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $hash = $algorithm.ComputeHash($bytes)
        return -join ($hash | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-ExplorerSourceFingerprint {
    $paths = @(
        (Join-Path $webRoot 'server.mjs'),
        (Join-Path $webRoot 'query-builder\analytics-query-builder.js'),
        (Join-Path $webRoot 'query-builder\derived-metric-query-builder.js'),
        (Join-Path $webRoot 'query-builder\empty-games-query-builder.js')
    )
    $hashes = foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Explorer runtime source is missing: $path"
        }
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return Get-StringSha256 -Value ($hashes -join "`n")
}

function Get-ExplorerListenerProcessId {
    try {
        $connection = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 4173 -State Listen -ErrorAction Stop |
            Select-Object -First 1
        if ($null -ne $connection) {
            return [int]$connection.OwningProcess
        }
    }
    catch {
        # netstat is the compatibility path on hosts where the TCP cmdlets are restricted.
    }
    $netstat = Join-Path $env:SystemRoot 'System32\netstat.exe'
    foreach ($line in & $netstat -ano -p tcp) {
        if ($line -match '^\s*TCP\s+127\.0\.0\.1:4173\s+\S+\s+LISTENING\s+(\d+)\s*$') {
            return [int]$Matches[1]
        }
    }
    throw 'Could not identify the process listening on Explorer port 4173.'
}

function Stop-StaleExplorer {
    param([Parameter(Mandatory = $true)] $Status)

    $processIdProperty = $Status.PSObject.Properties['processId']
    $listenerPid = if ($null -ne $processIdProperty) {
        [int]$processIdProperty.Value
    }
    else {
        Get-ExplorerListenerProcessId
    }
    $process = Get-Process -Id $listenerPid -ErrorAction Stop
    if ($process.ProcessName -ne 'node') {
        throw "Refusing to stop non-Node process $listenerPid on Explorer port 4173."
    }
    Stop-Process -Id $listenerPid
    if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port 4173 -Open $false -TimeoutSeconds $TimeoutSeconds)) {
        throw "Stale Explorer process $listenerPid did not release port 4173."
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

function Show-LaunchFailure {
    param([Parameter(Mandatory = $true)][string] $Message)

    if ($NoBrowser) {
        return
    }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show(
            "BaseballO could not start.`n`n$Message`n`nExplorer logs: $logDirectory",
            'BaseballO Explorer',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
    }
    catch {
        # The original error is still written to the PowerShell error stream.
    }
}

try {
    Initialize-LocalLayout
    [void](New-Item -ItemType Directory -Force -Path $logDirectory)

    Invoke-StartupScript -Path (Join-Path $PSScriptRoot 'start-fuseki.ps1')
    if (-not $SkipNiFi) {
        Invoke-StartupScript -Path (Join-Path $PSScriptRoot 'start-nifi.ps1')
    }

    if (Test-TcpPort -HostName '127.0.0.1' -Port 4173) {
        $status = Get-ExplorerStatus
        if ($null -eq $status) {
            throw 'Port 4173 is occupied, but it is not a healthy BaseballO Explorer.'
        }
        $expectedFingerprint = Get-ExplorerSourceFingerprint
        $serviceProperty = $status.PSObject.Properties['service']
        $fingerprintProperty = $status.PSObject.Properties['explorerSourceFingerprint']
        if ($null -ne $serviceProperty -and
            $null -ne $fingerprintProperty -and
            $serviceProperty.Value -eq 'baseballo-explorer' -and
            $fingerprintProperty.Value -eq $expectedFingerprint) {
            Write-Host "BaseballO Explorer is already current at $explorerUri"
        }
        else {
            Write-Host 'The running BaseballO Explorer is stale; restarting only its Node process.'
            Stop-StaleExplorer -Status $status
        }
    }

    if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 4173)) {
        $node = Get-Command node.exe -ErrorAction Stop
        $startedExplorerProcess = Start-Process `
            -FilePath $node.Source `
            -ArgumentList @('server.mjs') `
            -WorkingDirectory $webRoot `
            -RedirectStandardOutput (Join-Path $logDirectory 'stdout.log') `
            -RedirectStandardError (Join-Path $logDirectory 'stderr.log') `
            -PassThru `
            -WindowStyle Hidden
        Set-Content -LiteralPath $pidFile -Value $startedExplorerProcess.Id -Encoding ASCII -NoNewline

        if (-not (Wait-TcpPort -HostName '127.0.0.1' -Port 4173 -Open $true -TimeoutSeconds $TimeoutSeconds)) {
            throw "The Explorer did not open port 4173 within $TimeoutSeconds seconds."
        }
        if ($null -eq (Get-ExplorerStatus)) {
            throw 'The Explorer opened its port, but its BaseballO health check failed.'
        }
        Write-Host "BaseballO Explorer is ready at $explorerUri"
    }

    if (-not $NoBrowser) {
        Start-Process $explorerUri
    }
}
catch {
    if ($null -ne $startedExplorerProcess -and -not $startedExplorerProcess.HasExited) {
        Stop-Process -Id $startedExplorerProcess.Id -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }
    Show-LaunchFailure -Message $_.Exception.Message
    Write-Error $_
    exit 1
}
