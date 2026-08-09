[CmdletBinding()]
param([switch] $Enable)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-LocalLayout
if (-not (Test-TcpPort -HostName '127.0.0.1' -Port 8443)) { throw 'NiFi is not running on port 8443.' }

$appLog = Join-Path $script:NiFiHome 'logs\nifi-app.log'
$credentialLines = Select-String -LiteralPath $appLog -Pattern 'Generated Username|Generated Password' | Select-Object -Last 2
$usernameLine = $credentialLines | Where-Object { $_.Line -match 'Generated Username' } | Select-Object -First 1
$passwordLine = $credentialLines | Where-Object { $_.Line -match 'Generated Password' } | Select-Object -First 1
if ($null -eq $usernameLine -or $null -eq $passwordLine) { throw 'Generated NiFi credentials were not found.' }
$username = $usernameLine.Line -replace '^.*Generated Username \[([^]]+)\].*$', '$1'
$password = $passwordLine.Line -replace '^.*Generated Password \[([^]]+)\].*$', '$1'
$baseUri = 'https://127.0.0.1:8443/nifi-api'
$originalCallback = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

try {
    $token = Invoke-RestMethod -Uri "$baseUri/access/token" -Method Post -ContentType 'application/x-www-form-urlencoded' -Body @{ username = $username; password = $password }
    $headers = @{ Authorization = "Bearer $token" }
    function Get-Groups([string] $ParentId) { return @((Invoke-RestMethod -Uri "$baseUri/process-groups/$ParentId/process-groups" -Headers $headers).processGroups) }
    function Find-Group([string] $ParentId, [string] $Name) {
        $group = Get-Groups $ParentId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        if ($null -eq $group) { throw "Required NiFi process group is missing: $Name" }
        return [string]$group.component.id
    }
    function Get-Processors([string] $GroupId) { return @((Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers).processors) }
    function Get-Processor([string] $Id) { return Invoke-RestMethod -Uri "$baseUri/processors/$Id" -Headers $headers }
    function Set-State([string] $Id, [string] $State) {
        $entity = Get-Processor $Id
        return Invoke-RestMethod -Uri "$baseUri/processors/$Id/run-status" -Headers $headers -Method Put -ContentType 'application/json' -Body (@{ revision = @{ version = $entity.revision.version }; state = $State } | ConvertTo-Json -Depth 5)
    }
    function Get-Connections([string] $GroupId) { return @((Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers).connections) }
    function Ensure-Processor([string] $GroupId, [hashtable] $Definition) {
        $existing = Get-Processors $GroupId | Where-Object { $_.component.name -eq $Definition.Name } | Select-Object -First 1
        $config = @{ properties=$Definition.Properties; schedulingStrategy='TIMER_DRIVEN'; schedulingPeriod=$Definition.Period; executionNode='ALL'; concurrentlySchedulableTaskCount=1; autoTerminatedRelationships=$Definition.AutoTerminate }
        if ($null -eq $existing) {
            $body = @{ revision=@{version=0}; component=@{ name=$Definition.Name; type=$Definition.Type; bundle=@{group='org.apache.nifi';artifact=$Definition.Artifact;version=$script:Versions.NiFi.Version}; comments=$Definition.Comments; position=@{x=$Definition.X;y=$Definition.Y}; state='STOPPED'; config=$config } }
            return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
        }
        if ([string]$existing.component.state -ne 'STOPPED') { [void](Set-State ([string]$existing.component.id) 'STOPPED'); $existing = Get-Processor ([string]$existing.component.id) }
        $body = @{ revision=@{version=$existing.revision.version}; component=@{id=[string]$existing.component.id;name=$Definition.Name;comments=$Definition.Comments;position=@{x=$Definition.X;y=$Definition.Y};config=$config} }
        return Invoke-RestMethod -Uri "$baseUri/processors/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
    }
    function Ensure-Connection([string] $GroupId, [string] $Name, [string] $Source, [string] $Destination, [string] $Relationship) {
        $existing = Get-Connections $GroupId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        $component = @{name=$Name;source=@{id=$Source;groupId=$GroupId;type='PROCESSOR'};destination=@{id=$Destination;groupId=$GroupId;type='PROCESSOR'};selectedRelationships=@($Relationship);flowFileExpiration='0 sec';backPressureObjectThreshold=100;backPressureDataSizeThreshold='1 GB';prioritizers=@()}
        if ($null -eq $existing) { return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Post -ContentType 'application/json' -Body (@{revision=@{version=0};component=$component}|ConvertTo-Json -Depth 10) }
        $component.id = [string]$existing.component.id
        return Invoke-RestMethod -Uri "$baseUri/connections/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body (@{revision=@{version=$existing.revision.version};component=$component}|ConvertTo-Json -Depth 10)
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers
    $baseballId = Find-Group ([string]$root.processGroupFlow.id) 'BaseballO - MLB Ingestion'
    $groupId = Find-Group $baseballId '91 Repeatable Validation and Evidence'
    $triggerInbox = Join-Path $script:StateRoot 'pipeline\inbox\corpus-completion'
    $auditInbox = Join-Path $script:StateRoot 'pipeline\inbox\corpus-audits'
    $auditStaging = Join-Path $script:StateRoot 'pipeline\staging\corpus-audits'
    $processorQuarantine = Join-Path $script:StateRoot 'pipeline\quarantine\nifi-corpus-audit\processor-output'
    foreach ($directory in @($triggerInbox,$auditInbox,$auditStaging,$processorQuarantine)) { [void](New-Item -ItemType Directory -Force -Path $directory) }
    $python = (Get-Command python -ErrorAction Stop).Source
    $queueScript = Join-Path $script:RepositoryRoot 'scripts\pipeline\queue-ready-corpus-audits.py'
    $stageScript = Join-Path $script:RepositoryRoot 'scripts\pipeline\process-nifi-corpus-stage.py'
    $requestPath = Join-Path $auditStaging '${filename}'
    $powerShell = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'

    $definitions = @(
        @{Key='Trigger';Name='30 Read game promotion events';Type='org.apache.nifi.processors.standard.GetFile';Artifact='nifi-standard-nar';X=0;Y=1450;Period='1 sec';AutoTerminate=@();Comments='Consumes local promotion events and checks only explicitly audit-enabled corpus submissions.';Properties=@{'Input Directory'=$triggerInbox;'File Filter'='(?i)^.+\.json$';'Batch Size'='10';'Keep Source File'='false';'Recurse Subdirectories'='false';'Minimum File Age'='1 sec';'Ignore Hidden Files'='true'}},
        @{Key='Assess';Name='32 Queue ready corpus audits';Type='org.apache.nifi.processors.standard.ExecuteStreamCommand';Artifact='nifi-standard-nar';X=300;Y=1450;Period='0 sec';AutoTerminate=@('original');Comments='Queues one audit request only after every game in an audit-enabled submission has a matching fail-closed promotion marker.';Properties=@{'Command Path'=$python;'Command Arguments Strategy'='Command Arguments Property';'Command Arguments'=(@('-u',$queueScript,'--state-root',$script:StateRoot)-join ';');'Argument Delimiter'=';';'Ignore STDIN'='true';'Output MIME Type'='application/json';'Working Directory'=$script:RepositoryRoot}},
        @{Key='Read';Name='40 Read ready corpus audit';Type='org.apache.nifi.processors.standard.GetFile';Artifact='nifi-standard-nar';X=0;Y=1700;Period='1 sec';AutoTerminate=@();Comments='Consumes durable corpus audit requests created by successful promotion events.';Properties=@{'Input Directory'=$auditInbox;'File Filter'='(?i)^.+\.json$';'Batch Size'='1';'Keep Source File'='false';'Recurse Subdirectories'='false';'Minimum File Age'='1 sec';'Ignore Hidden Files'='true'}},
        @{Key='Stage';Name='42 Stage corpus audit request';Type='org.apache.nifi.processors.standard.PutFile';Artifact='nifi-standard-nar';X=300;Y=1700;Period='0 sec';AutoTerminate=@();Comments='Persists the request while the event-driven audit chain updates its evidence references.';Properties=@{'Directory'=$auditStaging;'Conflict Resolution Strategy'='fail';'Create Missing Directories'='true'}}
    )
    $x=600
    foreach ($stage in @('canned','advanced','equivalence','benchmark','complete')) {
        $label = switch ($stage) {'canned'{'44 Audit canned queries'};'advanced'{'46 Audit advanced queries'};'equivalence'{'48 Verify graph equivalence'};'benchmark'{'50 Generate benchmark evidence'};'complete'{'52 Complete corpus promotion'}}
        $arguments = @('-u',$stageScript,'--stage',$stage,'--request',$requestPath,'--state-root',$script:StateRoot) -join ';'
        $definitions += @{Key=$stage;Name=$label;Type='org.apache.nifi.processors.standard.ExecuteStreamCommand';Artifact='nifi-standard-nar';X=$x;Y=1700;Period='0 sec';AutoTerminate=@('original');Comments="Runs the repository-owned $stage corpus stage with durable evidence and quarantine.";Properties=@{'Command Path'=$python;'Command Arguments Strategy'='Command Arguments Property';'Command Arguments'=$arguments;'Argument Delimiter'=';';'Ignore STDIN'='true';'Output MIME Type'='application/json';'Working Directory'=$script:RepositoryRoot;'BASEBALLO_LOCAL_ROOT'=$script:LocalRoot;'BASEBALLO_POWERSHELL'=$powerShell}}
        $x+=280
    }
    $definitions += @(
        @{Key='Success';Name='78 Record corpus orchestration evidence';Type='org.apache.nifi.processors.standard.LogAttribute';Artifact='nifi-standard-nar';X=$x;Y=1700;Period='0 sec';AutoTerminate=@('success');Comments='Records readiness checks and completed corpus audit evidence in NiFi provenance.';Properties=@{}},
        @{Key='Failure';Name='98 Persist failed corpus orchestration output';Type='org.apache.nifi.processors.standard.PutFile';Artifact='nifi-standard-nar';X=1200;Y=2050;Period='0 sec';AutoTerminate=@('success','failure');Comments='Persists command output; stage code separately quarantines the request, evidence, and complete log.';Properties=@{'Directory'=$processorQuarantine;'Conflict Resolution Strategy'='replace';'Create Missing Directories'='true'}}
    )
    $processors=@{}; foreach($definition in $definitions){$processors[$definition.Key]=Ensure-Processor $groupId $definition}
    [void](Ensure-Connection $groupId 'promotion event to corpus readiness' $processors.Trigger.component.id $processors.Assess.component.id 'success')
    [void](Ensure-Connection $groupId 'corpus readiness evidence' $processors.Assess.component.id $processors.Success.component.id 'output stream')
    [void](Ensure-Connection $groupId 'corpus readiness failure' $processors.Assess.component.id $processors.Failure.component.id 'nonzero status')
    $chain=@('Read','Stage','canned','advanced','equivalence','benchmark','complete','Success')
    for($index=0;$index -lt $chain.Count-1;$index++){$relationship=if($chain[$index] -in @('canned','advanced','equivalence','benchmark','complete')){'output stream'}else{'success'};[void](Ensure-Connection $groupId "corpus $($chain[$index]) to $($chain[$index+1])" $processors[$chain[$index]].component.id $processors[$chain[$index+1]].component.id $relationship)}
    [void](Ensure-Connection $groupId 'failed corpus request staging' $processors.Stage.component.id $processors.Failure.component.id 'failure')
    foreach($stage in @('canned','advanced','equivalence','benchmark','complete')){[void](Ensure-Connection $groupId "corpus $stage failure" $processors[$stage].component.id $processors.Failure.component.id 'nonzero status')}

    $deadline=(Get-Date).AddSeconds(30);do{$targets=@(Get-Processors $groupId|Where-Object{$_.component.name -in $definitions.Name});$invalid=@($targets|Where-Object{$_.component.validationStatus -ne 'VALID'});if($invalid.Count -eq 0 -and $targets.Count -eq $definitions.Count){break};Start-Sleep -Milliseconds 500}while((Get-Date)-lt $deadline)
    if($invalid.Count -ne 0 -or $targets.Count -ne $definitions.Count){$details=$invalid|ForEach-Object{"$($_.component.name): $($_.component.validationErrors -join '; ')"};throw "NiFi corpus audit flow is invalid or incomplete: $($details -join ' | ')"}
    if($Enable){foreach($key in @('Success','Failure','complete','benchmark','equivalence','advanced','canned','Stage','Read','Assess','Trigger')){[void](Set-State ([string]$processors[$key].component.id) 'RUNNING')};Write-Host 'NiFi promotion-driven corpus audits are running.'}else{Write-Host 'NiFi promotion-driven corpus audits are configured, connected, valid, and stopped.'}
}
finally { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCallback }
