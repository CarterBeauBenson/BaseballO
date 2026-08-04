[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $PackageDirectory
)

. (Join-Path $PSScriptRoot '..\infra\common.ps1')
Initialize-LocalLayout

$packageRoot = [System.IO.Path]::GetFullPath($PackageDirectory)
$validatorPath = Join-Path $script:RepositoryRoot 'scripts\pipeline\validate-dehydration-package.py'
& python $validatorPath $packageRoot
if ($LASTEXITCODE -ne 0) {
    throw 'The source package must validate before the tamper test.'
}

$testRoot = Join-Path $script:StateRoot ("pipeline\package-tests\tamper-" + [Guid]::NewGuid().ToString('N'))
$tamperedRoot = Join-Path $testRoot 'package'
[void](New-Item -ItemType Directory -Force -Path $testRoot)
try {
    Copy-Item -LiteralPath $packageRoot -Destination $tamperedRoot -Recurse
    $manifest = Get-Content -LiteralPath (Join-Path $tamperedRoot 'manifest.json') -Raw | ConvertFrom-Json
    $rawPath = Join-Path $tamperedRoot (([string]$manifest.rawSource.path) -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    [System.IO.File]::AppendAllText($rawPath, " `n", [System.Text.UTF8Encoding]::new($false))

    $previousErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & python $validatorPath $tamperedRoot *> $null
        $tamperedExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorPreference
    }
    if ($tamperedExitCode -eq 0) {
        throw 'Package validator accepted deliberately modified raw bytes.'
    }

    & python $validatorPath $packageRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Tamper test changed the original package.'
    }
    Write-Host 'Dehydration package tamper regression passed.'
}
finally {
    if (Test-Path -LiteralPath $testRoot -PathType Container) {
        $resolvedTestRoot = [System.IO.Path]::GetFullPath($testRoot)
        $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $script:StateRoot 'pipeline\package-tests'))
        if (-not $resolvedTestRoot.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove an unexpected package-test path: $resolvedTestRoot"
        }
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
