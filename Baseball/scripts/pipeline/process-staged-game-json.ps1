[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $InputJson,
    [string] $SourceFileNameBase64
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$inputPath = [System.IO.Path]::GetFullPath($InputJson)
$stagingRoot = Join-Path $script:StateRoot 'pipeline\staging\manual-inbox'
$resolvedStagingRoot = [System.IO.Path]::GetFullPath($stagingRoot) + [System.IO.Path]::DirectorySeparatorChar
if (-not $inputPath.StartsWith($resolvedStagingRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to process a NiFi staging path outside $stagingRoot`: $inputPath"
}
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "NiFi staged game JSON was not found: $inputPath"
}

try {
    $archiveScript = Join-Path $PSScriptRoot 'archive-and-queue-game-json.py'
    $archiveArguments = @('--input', $inputPath, '--state-root', $script:StateRoot)
    if (-not [string]::IsNullOrWhiteSpace($SourceFileNameBase64)) {
        try { $sourceFileName = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($SourceFileNameBase64)) }
        catch { throw 'NiFi supplied an invalid Base64 source filename.' }
        $archiveArguments += @('--source-filename', $sourceFileName)
    }
    & python $archiveScript @archiveArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'The NiFi archive-and-queue stage failed.'
    }
    Remove-Item -LiteralPath $inputPath -Force
}
catch {
    $quarantineRoot = Join-Path $script:StateRoot 'pipeline\quarantine\manual-inbox'
    $quarantine = Join-Path $quarantineRoot ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Force -Path $quarantine)
    if (Test-Path -LiteralPath $inputPath -PathType Leaf) {
        Move-Item -LiteralPath $inputPath -Destination (Join-Path $quarantine 'input.json')
    }
    [PSCustomObject]@{
        pipeline = 'nifi-game-json-manual-inbox'
        failedAtUtc = [DateTime]::UtcNow.ToString('o')
        error = $_.Exception.Message
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $quarantine 'failure.json') -Encoding UTF8
    throw "NiFi staged-file processing failed; artifacts are quarantined at $quarantine`n$($_.Exception.Message)"
}
