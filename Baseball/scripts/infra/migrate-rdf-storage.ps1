[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $TargetRoot,
    [switch] $RemoveLocalAfterVerification,
    [ValidateRange(1, 32)][int] $CopyThreads = 8
)

. (Join-Path $PSScriptRoot 'common.ps1')

function Get-TreeInventory {
    param([Parameter(Mandatory = $true)][string] $Root)

    $resolvedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $items = @()
    foreach ($file in Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File -Force | Sort-Object FullName) {
        if ($file.Name -eq 'fuseki.pid') { continue }
        $relative = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\').Replace('\', '/')
        $items += [pscustomobject]@{
            RelativePath = $relative
            FullName = $file.FullName
            Length = [int64]$file.Length
        }
    }
    return @($items)
}

function Get-InventorySha256 {
    param([Parameter(Mandatory = $true)][object[]] $Inventory)

    $lines = [System.Collections.Generic.List[string]]::new()
    $position = 0
    foreach ($item in $Inventory) {
        $position++
        Write-Progress -Activity 'Verifying external RDF copy' -Status $item.RelativePath -PercentComplete (($position * 100) / [math]::Max(1, $Inventory.Count))
        $digest = $null
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            try {
                $hashResult = Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256 -ErrorAction Stop
                if ($null -ne $hashResult -and -not [string]::IsNullOrWhiteSpace([string]$hashResult.Hash)) {
                    $digest = ([string]$hashResult.Hash).ToLowerInvariant()
                    break
                }
            }
            catch {
                if ($attempt -eq 5) { throw }
            }
            Start-Sleep -Seconds 1
        }
        if ([string]::IsNullOrWhiteSpace($digest)) {
            throw "Could not hash copied RDF file after five attempts: $($item.FullName)"
        }
        $lines.Add("$($item.RelativePath)`t$($item.Length)`t$digest")
    }
    Write-Progress -Activity 'Verifying external RDF copy' -Completed
    $text = ($lines -join "`n") + "`n"
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($text)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($algorithm.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $algorithm.Dispose()
    }
}

if ($script:RdfStorageMode -eq 'external') {
    Assert-RdfStorageAvailable
    $configuredRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $script:FusekiState))
    $requestedRoot = [System.IO.Path]::GetFullPath($TargetRoot)
    if ($configuredRoot -ne $requestedRoot) {
        throw "RDF storage is already external at $configuredRoot; refusing to repoint it implicitly."
    }
    Write-Host "RDF storage is already configured at $configuredRoot."
    exit 0
}

$sourceFusekiState = [System.IO.Path]::GetFullPath($script:FusekiState)
$expectedLocalFusekiState = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'fuseki'))
if ($sourceFusekiState -ne $expectedLocalFusekiState) {
    throw "Refusing to migrate an unexpected Fuseki source path: $sourceFusekiState"
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceFusekiState 'databases\baseball-dev') -PathType Container)) {
    throw "The local TDB2 database was not found: $sourceFusekiState"
}

$targetRootPath = [System.IO.Path]::GetFullPath($TargetRoot).TrimEnd('\')
$targetDriveRoot = [System.IO.Path]::GetPathRoot($targetRootPath)
if (
    [string]::IsNullOrWhiteSpace($targetDriveRoot) -or
    $targetRootPath -eq $targetDriveRoot.TrimEnd('\') -or
    $targetRootPath.StartsWith($script:LocalRoot, [System.StringComparison]::OrdinalIgnoreCase)
) {
    throw "TargetRoot must be a dedicated absolute directory outside the BaseballO local root."
}
if ($targetDriveRoot -notmatch '^[A-Za-z]:\\$') {
    throw 'External RDF storage currently requires a mounted Windows drive-letter volume.'
}
$driveLetter = $targetDriveRoot.Substring(0, 1)
$volume = Get-Volume -DriveLetter $driveLetter -ErrorAction Stop
$partition = Get-Partition -DriveLetter $driveLetter -ErrorAction Stop
$disk = $partition | Get-Disk -ErrorAction Stop
$sourceInventory = Get-TreeInventory -Root $sourceFusekiState
$sourceBytes = [int64](($sourceInventory | Measure-Object Length -Sum).Sum)
if ($sourceInventory.Count -eq 0 -or $sourceBytes -le 0) {
    throw 'The local Fuseki state contains no files to migrate.'
}
if ([int64]$volume.SizeRemaining -lt ($sourceBytes + 5GB)) {
    throw "The target volume lacks the required free space plus a 5 GiB safety margin."
}

$markerPath = Join-Path $targetRootPath '.baseballo-rdf-storage.json'
$targetFusekiState = Join-Path $targetRootPath 'fuseki'

if (Test-Path -LiteralPath $targetFusekiState) {
    throw "The target Fuseki directory already exists; refusing to merge stores: $targetFusekiState"
}
if (Test-Path -LiteralPath $markerPath -PathType Leaf) {
    throw "The target already has a BaseballO RDF marker; use its matching local configuration instead of overwriting it."
}

[void](New-Item -ItemType Directory -Force -Path $targetRootPath)
$existingStagingRoots = @(
    Get-ChildItem -LiteralPath $targetRootPath -Directory -Force |
        Where-Object { $_.Name -match '^\.migration-(?<migrationId>\d{8}T\d{9}Z-(?<storageId>[0-9a-f]{32}))$' }
)
if ($existingStagingRoots.Count -gt 1) {
    throw "Multiple incomplete RDF migrations exist under $targetRootPath; refusing to choose one implicitly."
}
if ($existingStagingRoots.Count -eq 1) {
    $stagingRoot = $existingStagingRoots[0].FullName
    if ($existingStagingRoots[0].Name -notmatch '^\.migration-(?<migrationId>\d{8}T\d{9}Z-(?<storageId>[0-9a-f]{32}))$') {
        throw "Incomplete RDF migration has an invalid name: $stagingRoot"
    }
    $migrationId = $Matches.migrationId
    $storageId = $Matches.storageId
    $stagingFusekiState = Join-Path $stagingRoot 'fuseki'
    Write-Host "Resuming verified copy from incomplete migration $migrationId."
}
else {
    $storageId = [Guid]::NewGuid().ToString('N')
    $migrationId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + $storageId
    $stagingRoot = Join-Path $targetRootPath ".migration-$migrationId"
    $stagingFusekiState = Join-Path $stagingRoot 'fuseki'
}
[void](New-Item -ItemType Directory -Force -Path $stagingFusekiState)
$marker = [ordered]@{
    artifactType = 'baseballo-external-rdf-storage-marker'
    contractVersion = 1
    storageId = $storageId
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
    volume = [ordered]@{
        driveLetter = $driveLetter
        label = [string]$volume.FileSystemLabel
        fileSystem = [string]$volume.FileSystem
        diskFriendlyName = [string]$disk.FriendlyName
        diskSerialNumber = ([string]$disk.SerialNumber).Trim()
    }
}

$nifiWasRunning = Test-TcpPort -HostName '127.0.0.1' -Port 8443
$fusekiWasRunning = Test-BaseballFusekiService
$storageConfigWritten = $false
$externalStoreCommitted = $false

try {
    if ($nifiWasRunning) {
        & (Join-Path $PSScriptRoot 'stop-nifi.ps1') -TimeoutSeconds 120
    }
    if ($fusekiWasRunning) {
        & (Join-Path $PSScriptRoot 'stop-fuseki.ps1') -TimeoutSeconds 60
    }

    Write-Host ("Copying {0:N2} GiB of stopped Fuseki state to {1}." -f ($sourceBytes / 1GB), $stagingFusekiState)
    & robocopy.exe $sourceFusekiState $stagingFusekiState /E /COPY:DAT /DCOPY:DAT /FFT /R:2 /W:2 "/MT:$CopyThreads" /XF fuseki.pid /NFL /NDL /NP
    $robocopyExitCode = $LASTEXITCODE
    if ($robocopyExitCode -gt 7) {
        throw "RDF storage copy failed with robocopy exit code $robocopyExitCode."
    }

    $targetInventory = Get-TreeInventory -Root $stagingFusekiState
    if ($sourceInventory.Count -ne $targetInventory.Count) {
        throw "RDF copy file count mismatch: source=$($sourceInventory.Count), target=$($targetInventory.Count)."
    }
    $targetByPath = @{}
    foreach ($item in $targetInventory) { $targetByPath[$item.RelativePath] = $item }
    foreach ($sourceItem in $sourceInventory) {
        $targetItem = $targetByPath[$sourceItem.RelativePath]
        if ($null -eq $targetItem -or $targetItem.Length -ne $sourceItem.Length) {
            throw "RDF copy differs in path or size: $($sourceItem.RelativePath)"
        }
    }

    Write-Host 'Computing source and target SHA-256 inventories before promotion.'
    $sourceTreeSha256 = Get-InventorySha256 -Inventory $sourceInventory
    $targetTreeSha256 = Get-InventorySha256 -Inventory $targetInventory
    if ($sourceTreeSha256 -ne $targetTreeSha256) {
        throw 'RDF copy SHA-256 inventory mismatch.'
    }

    Move-Item -LiteralPath $stagingFusekiState -Destination $targetFusekiState
    if ((Get-ChildItem -LiteralPath $stagingRoot -Force | Measure-Object).Count -eq 0) {
        Remove-Item -LiteralPath $stagingRoot -Force
    }
    $evidencePath = Join-Path $targetRootPath "migration-$migrationId.json"
    Write-AtomicJsonFile -Path $evidencePath -Value ([ordered]@{
        artifactType = 'baseballo-rdf-storage-migration'
        contractVersion = 1
        migrationId = $migrationId
        storageId = $storageId
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        source = $sourceFusekiState
        target = $targetFusekiState
        fileCount = $sourceInventory.Count
        byteCount = $sourceBytes
        inventorySha256 = $sourceTreeSha256
        localCopyRemovalRequested = [bool]$RemoveLocalAfterVerification
    }) -Depth 6
    Write-AtomicJsonFile -Path $markerPath -Value $marker -Depth 6

    Write-AtomicJsonFile -Path $script:StorageConfigPath -Value ([ordered]@{
        artifactType = 'baseballo-local-storage-config'
        contractVersion = 1
        rdfStorage = [ordered]@{
            mode = 'external'
            root = $targetRootPath
            markerId = $storageId
            volumeLabel = [string]$volume.FileSystemLabel
            diskSerialNumber = ([string]$disk.SerialNumber).Trim()
        }
    }) -Depth 6
    $storageConfigWritten = $true

    & (Join-Path $PSScriptRoot 'start-fuseki.ps1') -TimeoutSeconds 180
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:3031/baseball-dev/query' -Method Post -Body @{ query = 'ASK { }' } -Headers @{ Accept = 'application/sparql-results+json' } -TimeoutSec 10
    if ($health.boolean -ne $true) {
        throw 'External Fuseki store failed its ASK health query.'
    }
    $externalStoreCommitted = $true

    if ($RemoveLocalAfterVerification) {
        $resolvedSource = [System.IO.Path]::GetFullPath($sourceFusekiState)
        if ($resolvedSource -ne $expectedLocalFusekiState -or -not $resolvedSource.StartsWith($script:StateRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected local Fuseki path: $resolvedSource"
        }
        Remove-Item -LiteralPath $resolvedSource -Recurse -Force
        Write-Host "Removed the verified local Fuseki copy: $resolvedSource"
    }

    if ($nifiWasRunning) {
        & (Join-Path $PSScriptRoot 'start-nifi.ps1') -TimeoutSeconds 600
    }

    Write-Host "External RDF storage is active: $targetFusekiState"
    Write-Host "Migration evidence: $evidencePath"
}
catch {
    $failure = $_
    if (-not $externalStoreCommitted -and $storageConfigWritten -and (Test-Path -LiteralPath $script:StorageConfigPath -PathType Leaf)) {
        Remove-Item -LiteralPath $script:StorageConfigPath -Force
    }
    if (-not $externalStoreCommitted -and $fusekiWasRunning -and -not (Test-TcpPort -HostName '127.0.0.1' -Port 3031)) {
        try { & (Join-Path $PSScriptRoot 'start-fuseki.ps1') -TimeoutSeconds 180 } catch { Write-Warning "Could not restore local Fuseki automatically: $($_.Exception.Message)" }
    }
    if ($nifiWasRunning -and -not (Test-TcpPort -HostName '127.0.0.1' -Port 8443)) {
        try { & (Join-Path $PSScriptRoot 'start-nifi.ps1') -TimeoutSeconds 600 } catch { Write-Warning "Could not restore NiFi automatically: $($_.Exception.Message)" }
    }
    throw $failure
}
