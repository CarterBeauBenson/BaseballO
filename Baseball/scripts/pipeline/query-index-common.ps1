function Get-QueryIndexImplementationFiles {
    $componentRoot = Join-Path $script:RepositoryRoot 'sparql\query-index\components'
    $files = @(
        Get-ChildItem -LiteralPath $componentRoot -Filter '*.rq' -File | Sort-Object Name
    )
    $files += @(
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\compile-query-index.py')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\build-query-index.ps1')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\infra\canonical-text.ps1')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\query-index-common.ps1')
        Get-Item -LiteralPath (Join-Path $script:RepositoryRoot 'scripts\pipeline\test-query-index.ps1')
    )
    return @($files | Sort-Object FullName)
}

function Get-QueryIndexImplementationHash {
    $repositoryPrefix = [System.IO.Path]::GetFullPath($script:RepositoryRoot).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $lines = foreach ($file in Get-QueryIndexImplementationFiles) {
        $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
        if (-not $fullPath.StartsWith($repositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Query-index implementation file is outside the repository: $fullPath"
        }
        $relativePath = $fullPath.Substring($repositoryPrefix.Length) -replace '\\', '/'
        $fileHash = Get-CanonicalTextSha256 -Path $file.FullName
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

# Deprecated compatibility alias. This value fingerprints the exact generator
# implementation for provenance/reproducibility only; it is not a semantic
# admission key. New callers must use Get-QueryIndexImplementationHash.
function Get-QueryIndexContractHash {
    return Get-QueryIndexImplementationHash
}

function Get-QueryIndexSemanticAdmission {
    $routingPath = Join-Path $script:RepositoryRoot 'sparql\query-index\operational-query-routing.json'
    $contractPath = Join-Path $script:RepositoryRoot 'sparql\query-index\semantic-contract.json'
    if (-not (Test-Path -LiteralPath $routingPath -PathType Leaf) -or -not (Test-Path -LiteralPath $contractPath -PathType Leaf)) {
        throw 'Query-index semantic routing or contract is missing.'
    }
    $routing = Get-Content -LiteralPath $routingPath -Raw | ConvertFrom-Json
    $contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
    $contractSha256 = Get-CanonicalTextSha256 -Path $contractPath
    $relativeContractPath = 'sparql/query-index/semantic-contract.json'
    if (
        [string]$contract.artifactType -ne 'baseball-query-index-semantic-contract' -or
        [int]$contract.contractVersion -ne 1 -or
        [string]$contract.semanticContractId -notmatch '^baseball-query-index-v[1-9][0-9]*$' -or
        [string]$routing.artifactType -ne 'baseball-reviewed-query-routing' -or
        [int]$routing.routingVersion -ne 2 -or
        [string]$routing.semanticAdmission.contractId -ne [string]$contract.semanticContractId -or
        [string]$routing.semanticAdmission.contract -ne $relativeContractPath -or
        [string]$routing.semanticAdmission.contractTextSha256 -ne $contractSha256
    ) {
        throw 'Operational routing does not admit the exact query-index semantic contract.'
    }
    return [PSCustomObject]@{
        ContractId = [string]$contract.semanticContractId
        ContractPath = $relativeContractPath
        ContractSha256 = $contractSha256
        Contract = $contract
        Routing = $routing
        RoutingPath = $routingPath
    }
}

function Get-QueryIndexLegacyManifestBridge {
    $admission = Get-QueryIndexSemanticAdmission
    $bridge = $admission.Routing.legacyManifestBridge
    $fixedHashes = @($bridge.fixedImplementationSha256)
    if (
        $null -eq $bridge -or
        [int]$bridge.bridgeVersion -ne 1 -or
        [string]$bridge.status -ne 'reviewed-fixed' -or
        [bool]$bridge.appliesOnlyWhenSemanticFieldsAbsent -ne $true -or
        [string]$bridge.legacyImplementationField -ne 'contractSha256' -or
        [string]$bridge.semanticContractId -ne $admission.ContractId -or
        [string]$bridge.semanticContractSha256 -ne $admission.ContractSha256 -or
        $fixedHashes.Count -ne 5 -or
        @($fixedHashes | Sort-Object -Unique).Count -ne 5 -or
        @($fixedHashes | Where-Object { [string]$_ -notmatch '^[0-9a-f]{64}$' }).Count -gt 0 -or
        [string]::IsNullOrWhiteSpace([string]$bridge.compatibilityReview) -or
        [string]::IsNullOrWhiteSpace([string]$bridge.requiredOutputValidation)
    ) {
        throw 'Operational routing has no valid fixed reviewed legacy-manifest bridge.'
    }
    return [PSCustomObject]@{
        SemanticAdmission = $admission
        FixedImplementationSha256 = @($fixedHashes)
        Value = $bridge
    }
}

function Resolve-QueryIndexManifestAdmission {
    param([Parameter(Mandatory = $true)] $Manifest)

    if (
        [string]$Manifest.artifactType -ne 'baseball-query-index-build' -or
        [int]$Manifest.contractVersion -ne 1
    ) {
        throw 'Unsupported query-index manifest envelope.'
    }
    $admission = Get-QueryIndexSemanticAdmission
    $propertyNames = @($Manifest.PSObject.Properties.Name)
    $semanticFields = @('semanticContractId', 'semanticContractSha256')
    $presentSemanticFields = @($semanticFields | Where-Object { $_ -in $propertyNames })
    if ($presentSemanticFields.Count -gt 0 -and $presentSemanticFields.Count -ne $semanticFields.Count) {
        throw 'Query-index manifest has a partial semantic-contract identity.'
    }

    if ($presentSemanticFields.Count -eq $semanticFields.Count) {
        if (
            [string]$Manifest.semanticContractId -ne $admission.ContractId -or
            [string]$Manifest.semanticContractSha256 -ne $admission.ContractSha256 -or
            ('semanticContractPath' -in $propertyNames -and [string]$Manifest.semanticContractPath -ne $admission.ContractPath)
        ) {
            throw 'Query-index manifest does not match the admitted semantic contract.'
        }
        if (
            'implementationSha256' -notin $propertyNames -or
            [string]$Manifest.implementationSha256 -notmatch '^[0-9a-f]{64}$' -or
            [string]$Manifest.implementationFingerprintAlgorithm -ne 'query-index-generation-file-set-v1' -or
            ('contractSha256' -in $propertyNames -and [string]$Manifest.contractSha256 -ne [string]$Manifest.implementationSha256)
        ) {
            throw 'Query-index manifest has invalid implementation provenance.'
        }
        return [PSCustomObject]@{
            Mode = 'semantic-contract'
            SemanticContractId = $admission.ContractId
            SemanticContractSha256 = $admission.ContractSha256
            ImplementationSha256 = [string]$Manifest.implementationSha256
        }
    }

    if ('semanticContractPath' -in $propertyNames -or 'implementationSha256' -in $propertyNames) {
        throw 'Query-index manifest cannot mix legacy and separated contract fields.'
    }
    $bridge = Get-QueryIndexLegacyManifestBridge
    $legacyImplementationSha256 = [string]$Manifest.contractSha256
    if ($legacyImplementationSha256 -notin $bridge.FixedImplementationSha256) {
        throw 'Legacy query-index implementation fingerprint is not in the fixed reviewed bridge.'
    }
    return [PSCustomObject]@{
        Mode = 'reviewed-legacy-bridge'
        SemanticContractId = $admission.ContractId
        SemanticContractSha256 = $admission.ContractSha256
        ImplementationSha256 = $legacyImplementationSha256
    }
}
