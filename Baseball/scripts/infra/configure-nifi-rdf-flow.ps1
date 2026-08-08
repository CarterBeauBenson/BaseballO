[CmdletBinding()]
param(
    [switch] $Enable,
    [ValidateRange(1, 8)][int] $ConcurrentGames = 3
)

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

    function Remove-ObsoleteSkeleton([string] $GroupId) {
        $obsoleteNames = @(
            '10 Accept completed game JSON', '20 Run guarded RML mapping',
            '30 Validate generated RDF', '40 PUT complete game graph',
            '90 Quarantine failed artifact'
        )
        foreach ($processor in @(Get-Processors $GroupId | Where-Object { $_.component.name -in $obsoleteNames })) {
            if ([string]$processor.component.state -ne 'STOPPED') { [void](Set-State ([string]$processor.component.id) 'STOPPED') }
            $entity = Get-Processor ([string]$processor.component.id)
            Invoke-RestMethod -Uri "$baseUri/processors/$($processor.component.id)?version=$($entity.revision.version)" -Headers $headers -Method Delete | Out-Null
            Write-Host "Removed obsolete stopped skeleton processor: $($processor.component.name)"
        }
    }

    function Ensure-Processor([string] $GroupId, [hashtable] $Definition) {
        $existing = Get-Processors $GroupId | Where-Object { $_.component.name -eq $Definition.Name } | Select-Object -First 1
        $config = @{
            properties = $Definition.Properties; schedulingStrategy = 'TIMER_DRIVEN'; schedulingPeriod = $Definition.Period
            executionNode = 'ALL'; concurrentlySchedulableTaskCount = $Definition.Concurrent; autoTerminatedRelationships = $Definition.AutoTerminate
        }
        if ($null -eq $existing) {
            $body = @{ revision = @{ version = 0 }; component = @{
                name = $Definition.Name; type = $Definition.Type
                bundle = @{ group = 'org.apache.nifi'; artifact = $Definition.Artifact; version = $script:Versions.NiFi.Version }
                comments = $Definition.Comments; position = @{ x = $Definition.X; y = $Definition.Y }; state = 'STOPPED'; config = $config
            } }
            return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/processors" -Headers $headers -Method Post -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
        }
        if ([string]$existing.component.state -ne 'STOPPED') { [void](Set-State ([string]$existing.component.id) 'STOPPED'); $existing = Get-Processor ([string]$existing.component.id) }
        $body = @{ revision = @{ version = $existing.revision.version }; component = @{
            id = [string]$existing.component.id; name = $Definition.Name; comments = $Definition.Comments
            position = @{ x = $Definition.X; y = $Definition.Y }; config = $config
        } }
        return Invoke-RestMethod -Uri "$baseUri/processors/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 12)
    }

    function Ensure-Connection([string] $GroupId, [string] $Name, [string] $Source, [string] $Destination, [string] $Relationship) {
        $existing = Get-Connections $GroupId | Where-Object { $_.component.name -eq $Name } | Select-Object -First 1
        $component = @{
            name = $Name; source = @{ id = $Source; groupId = $GroupId; type = 'PROCESSOR' }
            destination = @{ id = $Destination; groupId = $GroupId; type = 'PROCESSOR' }
            selectedRelationships = @($Relationship); flowFileExpiration = '0 sec'; backPressureObjectThreshold = 100
            backPressureDataSizeThreshold = '1 GB'; prioritizers = @()
        }
        if ($null -eq $existing) {
            return Invoke-RestMethod -Uri "$baseUri/process-groups/$GroupId/connections" -Headers $headers -Method Post -ContentType 'application/json' -Body (@{ revision = @{ version = 0 }; component = $component } | ConvertTo-Json -Depth 10)
        }
        $component.id = [string]$existing.component.id
        return Invoke-RestMethod -Uri "$baseUri/connections/$($existing.component.id)" -Headers $headers -Method Put -ContentType 'application/json' -Body (@{ revision = @{ version = $existing.revision.version }; component = $component } | ConvertTo-Json -Depth 10)
    }

    $root = Invoke-RestMethod -Uri "$baseUri/flow/process-groups/root" -Headers $headers
    $baseballId = Find-Group ([string]$root.processGroupFlow.id) 'BaseballO - MLB Ingestion'
    $groupId = Find-Group $baseballId '90 Shared RDF Mapping and Load'
    Remove-ObsoleteSkeleton $groupId

    $inbox = Join-Path $script:StateRoot 'pipeline\inbox\rdf'
    $staging = Join-Path $script:StateRoot 'pipeline\staging\rdf-requests'
    $processorQuarantine = Join-Path $script:StateRoot 'pipeline\quarantine\nifi-rdf\processor-output'
    foreach ($directory in @($inbox, $staging, $processorQuarantine)) { [void](New-Item -ItemType Directory -Force -Path $directory) }
    $powerShell = Join-Path ([Environment]::SystemDirectory) 'WindowsPowerShell\v1.0\powershell.exe'
    $stageScript = Join-Path $script:RepositoryRoot 'scripts\pipeline\process-nifi-rdf-stage.ps1'
    $requestArgument = Join-Path $staging '${filename}'

    $definitions = @(
        @{ Key='Read'; Name='10 Read queued game work'; Type='org.apache.nifi.processors.standard.GetFile'; Artifact='nifi-standard-nar'; X=0; Y=0; Period='1 sec'; Concurrent=1; AutoTerminate=@(); Comments='Consumes compact work requests created only after byte-identical raw archival.'; Properties=@{ 'Input Directory'=$inbox; 'File Filter'='(?i)^.+\.json$'; 'Batch Size'='10'; 'Keep Source File'='false'; 'Recurse Subdirectories'='false'; 'Minimum File Age'='1 sec'; 'Ignore Hidden Files'='true' } },
        @{ Key='Name'; Name='12 Assign isolated request filename'; Type='org.apache.nifi.processors.attributes.UpdateAttribute'; Artifact='nifi-update-attribute-nar'; X=250; Y=0; Period='0 sec'; Concurrent=1; AutoTerminate=@(); Comments='Preserves the queue filename and assigns a collision-safe local work filename.'; Properties=@{ 'source.request.filename'='${filename}'; 'filename'='${uuid}.json' } },
        @{ Key='Stage'; Name='15 Stage semantic work request'; Type='org.apache.nifi.processors.standard.PutFile'; Artifact='nifi-standard-nar'; X=500; Y=0; Period='0 sec'; Concurrent=$ConcurrentGames; AutoTerminate=@(); Comments='Stages the request without changing the archived raw JSON.'; Properties=@{ 'Directory'=$staging; 'Conflict Resolution Strategy'='fail'; 'Create Missing Directories'='true' } }
    )
    $x = 750
    foreach ($stageName in @('assess','rml','validate','load','index','promote')) {
        $label = switch ($stageName) {
            'assess' { '20 Assess dependency freshness' }; 'rml' { '30 Run guarded RML mapping' }
            'validate' { '40 Validate authoritative RDF' }; 'load' { '50 PUT authoritative graph' }
            'index' { '60 Build and verify query index' }; 'promote' { '70 Promote current graph pair' }
        }
        $arguments = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$stageScript,'-Stage',$stageName,'-RequestJson',$requestArgument) -join ';'
        $definitions += @{ Key=$stageName; Name=$label; Type='org.apache.nifi.processors.standard.ExecuteStreamCommand'; Artifact='nifi-standard-nar'; X=$x; Y=0; Period='0 sec'; Concurrent=$ConcurrentGames; AutoTerminate=@('original'); Comments="Runs only the repository-owned $stageName stage and emits a compact evidence manifest."; Properties=@{
            'Command Path'=$powerShell; 'Command Arguments Strategy'='Command Arguments Property'; 'Command Arguments'=$arguments
            'Argument Delimiter'=';'; 'Ignore STDIN'='true'; 'Output MIME Type'='application/json'; 'Working Directory'=$script:RepositoryRoot; 'BASEBALLO_LOCAL_ROOT'=$script:LocalRoot
        } }
        $x += 300
    }
    $definitions += @(
        @{ Key='Success'; Name='80 Record promoted game'; Type='org.apache.nifi.processors.standard.LogAttribute'; Artifact='nifi-standard-nar'; X=$x; Y=0; Period='0 sec'; Concurrent=1; AutoTerminate=@('success'); Comments='Records the promotion manifest in NiFi provenance.'; Properties=@{} },
        @{ Key='Failure'; Name='90 Persist failed stage output'; Type='org.apache.nifi.processors.standard.PutFile'; Artifact='nifi-standard-nar'; X=1200; Y=350; Period='0 sec'; Concurrent=1; AutoTerminate=@('success','failure'); Comments='Persists processor output; the stage runner separately quarantines its request, evidence, and complete log.'; Properties=@{ 'Directory'=$processorQuarantine; 'Conflict Resolution Strategy'='fail'; 'Create Missing Directories'='true' } }
    )

    $processors = @{}
    foreach ($definition in $definitions) { $processors[$definition.Key] = Ensure-Processor $groupId $definition }
    $chain = @('Read','Name','Stage','assess','rml','validate','load','index','promote','Success')
    for ($i=0; $i -lt $chain.Count-1; $i++) {
        $relationship = if ($chain[$i] -in @('assess','rml','validate','load','index','promote')) { 'output stream' } else { 'success' }
        [void](Ensure-Connection $groupId "$($chain[$i]) to $($chain[$i+1])" $processors[$chain[$i]].component.id $processors[$chain[$i+1]].component.id $relationship)
    }
    [void](Ensure-Connection $groupId 'failed request staging' $processors.Stage.component.id $processors.Failure.component.id 'failure')
    foreach ($stageName in @('assess','rml','validate','load','index','promote')) {
        [void](Ensure-Connection $groupId "$stageName failure to quarantine" $processors[$stageName].component.id $processors.Failure.component.id 'nonzero status')
    }

    $deadline = (Get-Date).AddSeconds(30)
    do {
        $targets = @(Get-Processors $groupId | Where-Object { $_.component.name -in $definitions.Name })
        $invalid = @($targets | Where-Object { $_.component.validationStatus -ne 'VALID' })
        if ($invalid.Count -eq 0 -and $targets.Count -eq $definitions.Count) { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    if ($invalid.Count -ne 0 -or $targets.Count -ne $definitions.Count) {
        $details = $invalid | ForEach-Object { "$($_.component.name): $($_.component.validationErrors -join '; ')" }
        throw "NiFi RDF flow is invalid or incomplete: $($details -join ' | ')"
    }

    if ($Enable) {
        foreach ($key in @('Success','Failure','promote','index','load','validate','rml','assess','Stage','Name','Read')) { [void](Set-State ([string]$processors[$key].component.id) 'RUNNING') }
        Write-Host "NiFi shared RDF flow is running with at most $ConcurrentGames concurrent games."
    } else { Write-Host 'NiFi shared RDF flow is configured, connected, valid, and stopped.' }
}
finally { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $originalCallback }
