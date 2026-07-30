[CmdletBinding()]
param([int] $TimeoutSeconds = 120)

. (Join-Path $PSScriptRoot 'common.ps1')

if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 3030)) {
    throw 'Fuseki is not running on port 3030.'
}

$request = Invoke-RestMethod -Uri 'http://127.0.0.1:3030/$/backup/baseball-dev' -Method Post
$taskId = [string]$request.taskId
if ([string]::IsNullOrWhiteSpace($taskId)) {
    throw 'Fuseki did not return a backup task identifier.'
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 1
    $task = Invoke-RestMethod -Uri "http://127.0.0.1:3030/`$/tasks/$taskId" -Method Get
    if ($null -ne $task -and $null -ne $task.finished) {
        if ($task.success -ne $true) {
            throw "Fuseki backup task $taskId failed."
        }
        $backup = Get-ChildItem (Join-Path $script:FusekiState 'backups') -Filter 'baseball-dev_*.nq.gz' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($null -eq $backup) {
            throw 'Fuseki reported a successful backup but no backup file was found.'
        }
        Write-Host "Fuseki backup completed: $($backup.FullName)"
        exit 0
    }
} while ((Get-Date) -lt $deadline)

throw "Fuseki backup task $taskId did not finish within $TimeoutSeconds seconds."
