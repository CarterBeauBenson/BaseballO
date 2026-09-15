[CmdletBinding()]
param([switch] $Remove)

. (Join-Path $PSScriptRoot 'common.ps1')
$taskName = 'BaseballO Local Services'
$taskPath = '\'
$owner = 'BaseballO local service supervision v1'
$runner = Join-Path $PSScriptRoot 'ensure-local-services.ps1'
$existing = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
if ($null -ne $existing -and $existing.Description -ne $owner) {
    throw 'A task with this name exists and is not owned by this installer.'
}
if ($Remove) {
    if ($null -ne $existing) { Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false }
    Write-Output 'Local service supervision removed; existing services remain running.'
    return
}
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) { throw 'Service supervision runner is missing.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') -WorkingDirectory $script:RepositoryRoot `
    -Argument ('-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '"')
$logon = New-ScheduledTaskTrigger -AtLogOn -User $identity
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $action -Trigger @($logon, $repeat) `
    -Principal $principal -Settings $settings -Description $owner -Force | Out-Null
Write-Output 'Installed local supervision at logon and every five minutes while signed in. No password stored.'
