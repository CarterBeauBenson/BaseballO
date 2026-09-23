[CmdletBinding()]
param([Parameter(Mandatory = $true)][ValidatePattern('^\d+(,\d+)*$')][string] $GamePks)

# Submit bounded derived work without reconciling or restarting ingestion.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\..\scripts\infra\common.ps1')
$api = $script:NiFiApiUri
$root = Invoke-RestMethod "$api/flow/process-groups/root"
$baseball = @($root.processGroupFlow.flow.processGroups | Where-Object { $_.component.name -eq 'BaseballO' })
if ($baseball.Count -ne 1) { throw 'Expected one BaseballO process group.' }
$parent = Invoke-RestMethod "$api/flow/process-groups/$($baseball[0].id)"
$groups = @($parent.processGroupFlow.flow.processGroups | Where-Object { $_.component.name -eq $script:MlbGameProcessGroupName })
if ($groups.Count -ne 1) { throw 'Expected one owned MLB Game process group.' }
$groupId = $groups[0].id
$flow = Invoke-RestMethod "$api/flow/process-groups/$groupId"
$name = 'Repair Selected Query Indexes'
$existing = @($flow.processGroupFlow.flow.processors | Where-Object { $_.component.name -eq $name })
if ($existing.Count -gt 1) { throw 'Duplicate query-index repair processors.' }
if ($existing.Count -eq 0) {
    $types = Invoke-RestMethod "$api/flow/processor-types"
    $type = @($types.processorTypes | Where-Object { $_.type -eq 'org.apache.nifi.processors.standard.ExecuteProcess' })
    if ($type.Count -ne 1) { throw 'Expected one ExecuteProcess processor type.' }
    $body = @{ revision = @{ version = 0 }; component = @{
        name = $name; type = $type[0].type; bundle = $type[0].bundle
        position = @{ x = -400; y = -1760 }
    } } | ConvertTo-Json -Depth 10
    $entity = Invoke-RestMethod "$api/process-groups/$groupId/processors" -Method Post -ContentType 'application/json' -Body $body
}
else { $entity = Invoke-RestMethod "$api/processors/$($existing[0].id)" }
if ($entity.component.state -ne 'STOPPED' -or $entity.status.aggregateSnapshot.activeThreadCount -gt 0) {
    throw 'Query-index repair is already active.'
}
$worker = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\pipeline\repair-query-index.ps1'))
$body = @{ revision = $entity.revision; component = @{ id = $entity.id; config = @{
    schedulingStrategy = 'TIMER_DRIVEN'; schedulingPeriod = '365 days'; concurrentlySchedulableTaskCount = 1
    autoTerminatedRelationships = @('success')
    properties = @{
        'Command' = (Join-Path $PSHOME 'powershell.exe')
        'Command Arguments' = "-NoProfile;-NonInteractive;-ExecutionPolicy;Bypass;-File;$worker;-GamePks;$GamePks"
        'Argument Delimiter' = ';'; 'Redirect Error Stream' = 'true'
        'Working Directory' = $script:RepositoryRoot
    }
} } } | ConvertTo-Json -Depth 10
$entity = Invoke-RestMethod "$api/processors/$($entity.id)" -Method Put -ContentType 'application/json' -Body $body
$body = @{ revision = $entity.revision; state = 'RUN_ONCE'; disconnectedNodeAcknowledged = $false } | ConvertTo-Json
Invoke-RestMethod "$api/processors/$($entity.id)/run-status" -Method Put -ContentType 'application/json' -Body $body | Out-Null
Write-Output "Submitted NiFi query-index repair for games $GamePks; processor $($entity.id)."
