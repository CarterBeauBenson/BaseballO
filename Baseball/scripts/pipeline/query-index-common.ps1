function Get-QueryIndexContractFiles {
    $componentRoot = Join-Path $script:RepositoryRoot 'sparql\query-index\components'
    $files = @(
        Get-ChildItem -LiteralPath $componentRoot -Filter '*.rq' -File | Sort-Object Name
    )
    $files += @(
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\compile-query-index.py')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\build-query-index.ps1')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\query-index-common.ps1')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\test-query-index.ps1')
    )
    return @($files | Sort-Object FullName)
}

function Get-QueryIndexContractHash {
    $repositoryPrefix = [System.IO.Path]::GetFullPath($script:RepositoryRoot).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $lines = foreach ($file in Get-QueryIndexContractFiles) {
        $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
        if (-not $fullPath.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Query-index contract file is outside the repository: $fullPath"
        }
        $relativePath = $fullPath.Substring($repositoryPrefix.Length) -replace '\\', '/'
        $fileHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$relativePath=$fileHash"
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($sha256.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $sha256.Dispose()
    }
}
