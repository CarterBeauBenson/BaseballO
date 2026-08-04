[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
$applicationLog = Join-Path $script:NiFiHome 'logs\nifi-app.log'
if (-not (Test-Path -LiteralPath $applicationLog -PathType Leaf)) {
    throw 'NiFi has not written an application log. Start NiFi first.'
}

$credentialLines = Select-String -LiteralPath $applicationLog -Pattern 'Generated Username|Generated Password'
if ($credentialLines.Count -lt 2) {
    throw 'Generated credentials are no longer present in nifi-app.log. Reset the single-user credentials to choose a new login.'
}

$credentialLines | Select-Object -Last 2 | ForEach-Object {
    if ($_.Line -match 'Generated (Username|Password) \[(.+)\]') {
        Write-Host "$($matches[1]): $($matches[2])"
    }
}
