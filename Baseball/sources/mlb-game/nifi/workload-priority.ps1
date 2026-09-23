# Existing source entry lanes converge on the same accepted processing stages.
function Install-WorkloadPriority {
    param([string] $GroupId)
    $names = @('Name Transient Payload','RML','Source SHACL','Promote Graph Pair')
    $flow = Get-GroupFlow $GroupId
    $selected = @($flow.processors | Where-Object { $_.component.name -in $names })
    if ($selected.Count -ne 4) { throw 'Workload priority requires all four existing source stages.' }
    if (@($selected | Where-Object { $_.status.aggregateSnapshot.activeThreadCount -gt 0 }).Count) {
        throw 'The affected source stages are busy; leave their work intact and deploy at the next idle boundary.'
    }
    $resume = @()
    try {
        foreach ($p in $selected) {
            if ($p.component.state -eq 'RUNNING') {
                $entity = Invoke-NiFi GET "/processors/$($p.id)"
                Invoke-NiFi PUT "/processors/$($p.id)/run-status" @{
                    revision=$entity.revision;state='STOPPED';disconnectedNodeAcknowledged=$false
                } | Out-Null
                $resume += $p.id
                $deadline = [DateTime]::UtcNow.AddSeconds(5)
                do {
                    Start-Sleep -Milliseconds 250
                    $stopped = Invoke-NiFi GET "/processors/$($p.id)"
                    if ($stopped.component.state -eq 'STOPPED' -and $stopped.status.aggregateSnapshot.activeThreadCount -eq 0) { break }
                } while ([DateTime]::UtcNow -lt $deadline)
                if ($stopped.component.state -ne 'STOPPED' -or $stopped.status.aggregateSnapshot.activeThreadCount -gt 0) {
                    throw 'Source processor did not become idle for its priority update.'
                }
            }
        }
        $name = @($selected | Where-Object { $_.component.name -eq 'Name Transient Payload' })[0]
        $entity = Invoke-NiFi GET "/processors/$($name.id)"
        Invoke-NiFi PUT "/processors/$($name.id)" @{
            revision=$entity.revision;component=@{id=$name.id;config=@{properties=@{
                'priority'='${quarantine.replay.plan.path:isEmpty():not():ifElse(''10'',${request.kind:equals(''backfill''):ifElse(''20'',''0'')})}'
                'workload.lane'='${quarantine.replay.plan.path:isEmpty():not():ifElse(''repair'',${request.kind:equals(''backfill''):ifElse(''historical'',''current'')})}'
            }}}
        } | Out-Null
        foreach ($edge in @($flow.connections | Where-Object { $_.component.name -in @(
            '07 payload written','09 RML passed to SHACL','11 SHACL passed to promotion') })) {
            $entity = Invoke-NiFi GET "/connections/$($edge.id)"
            $component = $entity.component
            $component.prioritizers = @('org.apache.nifi.prioritizer.PriorityAttributePrioritizer',
                'org.apache.nifi.prioritizer.FirstInFirstOutPrioritizer')
            Invoke-NiFi PUT "/connections/$($edge.id)" @{revision=$entity.revision;component=$component} | Out-Null
        }
    } finally {
        foreach ($id in $resume) {
            $entity = Invoke-NiFi GET "/processors/$id"
            Invoke-NiFi PUT "/processors/$id/run-status" @{
                revision=$entity.revision;state='RUNNING';disconnectedNodeAcknowledged=$false
            } | Out-Null
        }
    }
}
