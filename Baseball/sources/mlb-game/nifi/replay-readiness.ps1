# Source-local extension using provision.ps1's ordinary NiFi helpers.
function Install-ReplayReadiness {
    param([string] $GroupId, [switch] $Start)
    $flow = Get-GroupFlow -GroupId $GroupId
    $failure = @($flow.processors | Where-Object { $_.component.name -eq 'Record Quarantine Replay Control Failure' })
    if ($failure.Count -ne 1) { throw 'Replay failure destination is not unique.' }
    foreach ($lane in @(
        @{ Name='Plan'; Worker='Plan Quarantine Replay'; Edge='quarantine replay plan failed'; Y=-1160 },
        @{ Name='Remainder'; Worker='Emit Quarantine Remainder Retry'; Edge='quarantine remainder retry failed'; Y=-1760 }
    )) {
        $names = @($lane.Worker, "Route Quarantine $($lane.Name) Readiness", "Retry Quarantine $($lane.Name) SQL Readiness")
        $resume = @()
        foreach ($processor in @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -in $names })) {
            if ($processor.component.state -eq 'RUNNING') {
                $entity = Invoke-NiFi GET "/processors/$($processor.id)"
                Invoke-NiFi PUT "/processors/$($processor.id)/run-status" @{
                    revision=$entity.revision; state='STOPPED'; disconnectedNodeAcknowledged=$false
                } | Out-Null
                $resume += $processor.id
            }
        }
        $worker = @((Get-GroupFlow $GroupId).processors | Where-Object { $_.component.name -eq $lane.Worker })
        if ($worker.Count -ne 1) { throw 'Replay worker is not unique.' }
        # Stopping scheduling does not terminate an already-running command.
        # Its eventual success still uses the unchanged success connection.
        $gate = Ensure-Processor -GroupId $GroupId -Name $names[1] -Type 'org.apache.nifi.processors.standard.RouteOnAttribute' -X 640 -Y $lane.Y -AutoTerminate @() -Properties @{
            'Routing Strategy'='Route to Property name'; 'pending'="`${execution.status:equals('75')}"
        }
        $retry = Ensure-RetryProcessor -GroupId $GroupId -Stage "Quarantine $($lane.Name) SQL Readiness" -X 960 -Y $lane.Y -MaximumRetries 720 -SchedulingPeriod '0 sec'
        $edge = @((Get-GroupFlow $GroupId).connections | Where-Object { $_.component.name -eq $lane.Edge })
        if ($edge.Count -gt 1) { throw 'Replay failure connection is not unique.' }
        if ($edge.Count -eq 1 -and $edge[0].component.destination.id -ne $gate) {
            $current = Invoke-NiFi GET "/connections/$($edge[0].id)"
            if ($current.component.source.id -ne $worker[0].id -or $current.component.destination.id -ne $failure[0].id -or
                $current.status.aggregateSnapshot.flowFilesQueued -gt 0) { throw 'Cannot reroute occupied or unexpected replay failure connection.' }
            Invoke-NiFi PUT "/connections/$($current.id)" @{
                revision=$current.revision; component=@{id=$current.id; destination=@{id=$gate;groupId=$GroupId;type='PROCESSOR'}}
            } | Out-Null
        }
        Ensure-Connection $GroupId $lane.Edge $worker[0].id $gate @('nonzero status') | Out-Null
        Ensure-Connection $GroupId "quarantine $($lane.Name) dependency pending" $gate $retry @('pending') | Out-Null
        Ensure-Connection $GroupId "quarantine $($lane.Name) command failed" $gate $failure[0].id @('unmatched') | Out-Null
        $returnId = Ensure-Connection $GroupId "quarantine $($lane.Name) dependency retry" $retry $worker[0].id @('retry')
        $current = Invoke-NiFi GET "/connections/$returnId"
        Invoke-NiFi PUT "/connections/$returnId" @{
            revision=$current.revision; component=@{id=$returnId;backPressureObjectThreshold=0;backPressureDataSizeThreshold='0 B'}
        } | Out-Null
        Ensure-Connection $GroupId "quarantine $($lane.Name) dependency exhausted" $retry $failure[0].id @('retries_exceeded') | Out-Null
        if ($Start) { $resume += @($gate,$retry) }
        foreach ($id in $resume) {
            $entity = Invoke-NiFi GET "/processors/$id"
            Invoke-NiFi PUT "/processors/$id/run-status" @{
                revision=$entity.revision; state='RUNNING'; disconnectedNodeAcknowledged=$false
            } | Out-Null
        }
    }
}
