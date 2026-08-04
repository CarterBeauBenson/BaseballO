[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$routingPath = Join-Path $script:RepositoryRoot 'sparql\query-index\operational-query-routing.json'
$runnerPath = Join-Path $PSScriptRoot 'run-reviewed-query.ps1'
$routing = Get-Content -LiteralPath $routingPath -Raw | ConvertFrom-Json
$results = @()

foreach ($route in @($routing.routes)) {
    $arguments = @{
        Name = [string]$route.name
        Layer = 'Auto'
        VerifyEquivalent = ([string]$route.autoLayer -eq 'indexed')
    }
    $json = & $runnerPath @arguments
    $result = $json | ConvertFrom-Json
    if ([string]$result.selectedLayer -ne [string]$route.autoLayer) {
        throw "$($route.name) selected $($result.selectedLayer), expected $($route.autoLayer). Fallback: $($result.fallbackReason)"
    }
    if ([int]$result.rowCount -le 0) {
        throw "$($route.name) returned no rows."
    }
    if ([string]$route.autoLayer -eq 'indexed' -and $result.equivalenceVerified -ne $true) {
        throw "$($route.name) did not verify indexed/authoritative equivalence."
    }
    $results += [PSCustomObject]@{
        Name = [string]$route.name
        Layer = [string]$result.selectedLayer
        Rows = [int]$result.rowCount
        Milliseconds = [double]$result.durationMilliseconds
    }
}

$results | Format-Table -AutoSize
Write-Host "Reviewed-query routing passed: $($results.Count) routes; $(@($results | Where-Object Layer -eq 'indexed').Count) indexed; $(@($results | Where-Object Layer -eq 'authoritative').Count) authoritative."

$originalLocalRoot = $env:BASEBALLO_LOCAL_ROOT
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "baseballo-routing-$([Guid]::NewGuid().ToString('N'))"
try {
    $env:BASEBALLO_LOCAL_ROOT = $temporaryRoot
    $fallbackJson = & $runnerPath -Name 'hits-by-player-and-venue' -Layer Auto
    $fallbackResult = $fallbackJson | ConvertFrom-Json
    if ([string]$fallbackResult.selectedLayer -ne 'authoritative' -or [string]::IsNullOrWhiteSpace([string]$fallbackResult.fallbackReason)) {
        throw 'Auto mode did not fall back to authoritative execution when current manifests were unavailable.'
    }

    $indexedFailedClosed = $false
    try {
        & $runnerPath -Name 'hits-by-player-and-venue' -Layer Indexed | Out-Null
    }
    catch {
        if ($_.Exception.Message -notmatch '^Indexed execution refused: missing query-index manifest') {
            throw
        }
        $indexedFailedClosed = $true
    }
    if (-not $indexedFailedClosed) {
        throw 'Explicit Indexed mode did not fail closed when current manifests were unavailable.'
    }
    Write-Host 'Reviewed-query failure policy passed: Auto fell back; explicit Indexed failed closed.'
}
finally {
    if ($null -eq $originalLocalRoot) {
        Remove-Item Env:BASEBALLO_LOCAL_ROOT -ErrorAction SilentlyContinue
    }
    else {
        $env:BASEBALLO_LOCAL_ROOT = $originalLocalRoot
    }
    if (Test-Path -LiteralPath $temporaryRoot -PathType Container) {
        $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
        $allowedTemporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        ) + [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedTemporaryRoot.StartsWith($allowedTemporaryRoot + 'baseballo-routing-', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected routing-test path: $resolvedTemporaryRoot"
        }
        Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force
    }
}
