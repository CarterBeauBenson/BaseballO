function Get-CanonicalTextSha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $raw = [System.IO.File]::ReadAllBytes($fullPath)
    $hasUtf8Bom = (
        $raw.Length -ge 3 -and
        $raw[0] -eq 0xEF -and
        $raw[1] -eq 0xBB -and
        $raw[2] -eq 0xBF
    )
    $text = [System.IO.File]::ReadAllText($fullPath)
    # ReadAllText consumes a UTF-8 BOM, while Python's utf-8 decoder retains
    # U+FEFF. Restore it as canonical content so both implementations hash the
    # same tracked text on LF and CRLF checkouts.
    if ($hasUtf8Bom -and ($text.Length -eq 0 -or [int]$text[0] -ne 0xFEFF)) {
        $text = [char]0xFEFF + $text
    }
    $canonical = $text.Replace("`r`n", "`n").Replace("`r", "`n")
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($canonical)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($algorithm.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    }
    finally {
        $algorithm.Dispose()
    }
}
