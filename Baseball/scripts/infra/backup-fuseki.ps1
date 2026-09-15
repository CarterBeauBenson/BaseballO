[CmdletBinding()]
param(
    [ValidateSet('Submit', 'Complete', 'Verify')][string] $Action = 'Submit',
    [string] $Job
)

. (Join-Path $PSScriptRoot 'common.ps1')

$component = Join-Path $script:RepositoryRoot 'scripts\pipeline\rdf-recovery.py'
$recoveryRoot = Join-Path $script:StateRoot 'recovery'
$arguments = @($component, '--root', $recoveryRoot, $Action.ToLowerInvariant())
if ($Action -eq 'Submit') {
    if ($Job) { throw 'A new submission cannot reuse a job identity.' }
    $arguments += @('--server', $script:FusekiBaseUri, '--dataset', 'baseball-dev', '--backups', (Join-Path $script:FusekiState 'backups'))
}
else {
    if (-not $Job) { throw 'Complete and Verify require the submitted Job identity.' }
    $arguments += @('--job', $Job)
}
& python @arguments
if ($LASTEXITCODE -ne 0) { throw "RDF recovery stage $Action failed. Inspect its job evidence." }
# Complete returns pending without sleeping when Fuseki is still working.
# NiFi owns requeue, retry and scheduling; this wrapper is not a scheduler.
