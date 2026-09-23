[CmdletBinding()]
param([switch] $Operations)

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

if ($Operations) {
    # Read existing owner records once. This command never launches, retries,
    # validates or repairs a pipeline stage.
    if ($nifiListening) {
        try {
            $api = "$script:NiFiBaseUri/nifi-api"
            $rootFlow = Invoke-RestMethod "$api/flow/process-groups/root" -TimeoutSec 5
            $baseball = @($rootFlow.processGroupFlow.flow.processGroups | Where-Object { $_.component.name -eq 'BaseballO' })
            if ($baseball.Count -eq 1) {
                $flow = Invoke-RestMethod "$api/flow/process-groups/$($baseball[0].id)" -TimeoutSec 5
                $flow.processGroupFlow.flow.processGroups | ForEach-Object {
                    [PSCustomObject]@{
                        Group = $_.component.name
                        Queued = $_.status.aggregateSnapshot.flowFilesQueued
                        ActiveThreads = $_.status.aggregateSnapshot.activeThreadCount
                    }
                } | Sort-Object Group | Format-Table -AutoSize
            }
        }
        catch { Write-Warning "NiFi operational snapshot unavailable: $($_.Exception.Message)" }
    }
    foreach ($relative in @('serving\authority\current.json', 'serving\current.json',
            'serving\dashboard-current.json', 'serving\dashboard\progress.json',
            'pipeline\control\mlb-game\admission-evidence\latest.json', 'recovery\current.json')) {
        $path = Join-Path $script:StateRoot $relative
        Write-Host $relative
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            try {
                $record = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
                $summary = [ordered]@{}
                foreach ($name in @('status', 'phase', 'buildId', 'promotedAtUtc', 'gameCount', 'completedGames',
                        'totalGames', 'sourceGraphCount', 'resultRowCount', 'processedGames', 'refreshedGames', 'outcomes')) {
                    if ($null -ne $record.PSObject.Properties[$name]) { $summary[$name] = $record.$name }
                }
                $summary | ConvertTo-Json -Depth 4
            }
            catch { Write-Warning "Owner record unavailable: $($_.Exception.Message)" }
        }
        else { Write-Host 'No owner record published yet.' }
    }
    Get-ChildItem -LiteralPath (Join-Path $script:StateRoot 'serving\builds') -Filter '*.progress.json' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1 | ForEach-Object {
            Write-Host "Latest report progress: $($_.FullName)"
            Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json |
                Select-Object status, phase, buildId, processId, completedGames, totalGames | Format-List
        }
}
