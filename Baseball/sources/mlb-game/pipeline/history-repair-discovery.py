"""Bounded NiFi discovery for H3's accepted additive history worker.

Start with a recorded history/boundary failure, preserve the exact source and
base identities, and let the unchanged context select the missing histories.
This is queue construction, not another semantic validator or game remapper.
"""
from pathlib import Path
import inspect
import urllib.request

SCOPE='archive/design-records/metric-repair-scope-2026-09-30/answers.md'


def inventory_path(state):
    return state/'pipeline/control/mlb-game/history-discovery/inventory.json'


def inventory(owner,state):
    path=inventory_path(state)
    return owner.read(path) if path.is_file() else dict(games={})


def cases(owner,state):
    return [r['case'] for r in inventory(owner,state)['games'].values() if r.get('status')=='selected']


def conflict_details(owner,raw,original,current):
    """Explain the existing context's refusal; make no new admission decision."""
    old={h['lifetimeKey']:h for h in original.get('histories',[])}
    new={h['lifetimeKey']:h for h in current.get('histories',[])}
    fields=('runnerId','inning','half','entryAnchor','terminationAnchor','terminal')
    changed=[dict(lifetimeKey=key,previous={f:row.get(f) for f in fields},
        current={f:new[key].get(f) for f in fields} if key in new else None)
        for key,row in old.items() if key not in new or any(row.get(f)!=new[key].get(f) for f in fields)]
    issues=[dict(inning=half['inning'],half=half['half'],issues=half['issues'])
        for half in current.get('withheldHistories',[])]
    indexes={int(i['atBatIndex']) for half in issues for i in half['issues']
        if type(i.get('atBatIndex')) is int or
        (isinstance(i.get('atBatIndex'),str) and i['atBatIndex'].isdecimal())}
    document=owner.json.loads(raw)
    plays=[dict(atBatIndex=p['atBatIndex'],description=p.get('result',{}).get('description'),
        postBases={k:v for k,v in p.get('matchup',{}).items() if k.startswith('postOn')},
        runners=p.get('runners',[])) for p in document['liveData']['plays']['allPlays']
        if p['atBatIndex'] in sorted(indexes)[:5]]
    return dict(kind='retained-history-conflict',priorInputSha256=original.get('inputSha256'),
        currentInputSha256=current.get('inputSha256'),priorSourceRevision=original.get('sourceRevision'),
        currentSourceRevision=current.get('sourceRevision'),changedHistories=changed,
        sourceConsistency=current.get('sourceConsistency'),sourceIssues=current.get('sourceIssues',[]),
        withheldHalves=issues,boundaryIssues=current.get('boundaryIssues',[]),
        sourcePlays=plays,omittedSourcePlayCount=max(0,len(indexes)-len(plays)),
        nextAction='Reconcile the retained source with existing identities before retrying; preserve promoted RDF.')


def source(owner,state,promotion,request_path):
    """The persisted request identifies the one game before any acquisition."""
    request=owner.read(request_path);pk=promotion['gamePk']
    if request.get('gamePk')!=pk or request.get('promotionManifestSha256')!=promotion['promotionManifestSha256']:
        raise ValueError('History acquisition request belongs to another game or promotion')
    recovery=request.get('recoverRetainedSourceSha256')
    if recovery and (not isinstance(recovery,str) or len(recovery)!=64
            or any(c not in '0123456789abcdef' for c in recovery)):
        raise ValueError('History recovery requires an exact source hash')
    suffix=('-recovery-'+recovery[:12]) if recovery else ''
    directory=state/'pipeline/quarantine/mlb-game'/pk/('targeted-history-'+promotion['promotionManifestSha256'][:16]+suffix)
    path=directory/'input.json';receipt=directory/'acquisition.json';intent=directory/'acquisition-intent.json'
    if receipt.is_file():
        witness=owner.read(receipt)
        # A new approved selector needs a new repair request, not new source
        # bytes. Keep the acquisition's original request and hash unchanged.
        acquired_request=Path(witness.get('acquisitionRequest',''))
        request_root=(inventory_path(state).parent/pk).resolve()
        if (witness.get('gamePk')!=pk or witness.get('path')!=str(path)
                or acquired_request.resolve().parent!=request_root
                or not acquired_request.is_file()
                or owner.sha(acquired_request)!=witness.get('acquisitionRequestSha256')
                or not path.is_file() or owner.sha(path)!=witness['sha256']):
            raise ValueError('Discovered history input differs from its acquisition receipt')
        original_request=owner.read(acquired_request)
        scope=lambda value:{k:v for k,v in value.items() if k!='contextBuilderSha256'}
        if scope(original_request)!=scope(request):
            raise ValueError('Retained history acquisition belongs to a different repair scope')
        return witness
    evidence=owner.module(owner.HERE/'admission-evidence.py','history_discovery_evidence')
    retained=None if recovery else evidence.retained_raw_witness(state,promotion)
    url=f'https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live'
    origin=(owner.read(intent) if intent.is_file() else dict(
        kind='retained-response-copy' if retained else 'targeted-reacquisition',
        **(dict(copiedFrom=retained) if retained else {})))
    if not intent.is_file():owner.atomic(intent,origin)
    if path.is_file():raw=path.read_bytes()  # Recover an interrupted receipt write.
    elif origin.get('copiedFrom'):
        retained=origin['copiedFrom'];raw=Path(retained['path']).read_bytes()
        if owner.hashlib.sha256(raw).hexdigest()!=retained['sha256']:
            raise ValueError('Retained history response changed before its copy')
    else:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/json'}),timeout=60) as response:
            raw=response.read()
    if str(owner.json.loads(raw).get('gamePk'))!=pk:raise ValueError('History source game identity differs')
    directory.mkdir(parents=True,exist_ok=True)
    if not path.is_file():
        pending=directory/'input.pending';pending.write_bytes(raw);pending.replace(path)
    witness=dict(gamePk=pk,path=str(path),sha256=owner.sha(path),**origin,
        acquisitionRequest=str(request_path),acquisitionRequestSha256=owner.sha(request_path),
        scopeDecision=SCOPE,url=url,acquiredAtUtc=owner.TX.now())
    owner.atomic(receipt,witness)
    return witness


def fingerprint(owner):
    """Inspection depends on selection, not reporting or the execution queue."""
    proof_inputs=('admission-evidence.py','runner-boundary-admission.py','batting-admission.py',
        'reconcile-metric-source.py',
        'existing-graph-admissions.py','retained-census-admissions.py','context-proof-compatibility.json')
    return owner.hashlib.sha256(inspect.getsource(inspect_record).encode()+
        inspect.getsource(boundary_admission).encode()+
        inspect.getsource(owner.select_history).encode()+
        b''.join((owner.HERE/name).read_bytes() for name in proof_inputs)+
        (owner.ROOT/'scripts/pipeline/validate-shacl.py').read_bytes()+
        (owner.HERE.parent/'shacl/runner-boundary-admission.ttl').read_bytes()+
        (owner.ROOT/'scripts/pipeline/prepare-rml-context.py').read_bytes()).hexdigest()


def boundary_admission(owner,state,marker_path):
    """Reuse the owning full-history/boundary proof, never infer coverage."""
    evidence=owner.module(owner.HERE/'admission-evidence.py','history_discovery_admission')
    adapter=evidence.module(owner.HERE/'runner-boundary-admission.py','history_discovery_boundary')
    promotion=owner.I.validated_promotion_record(state,marker_path,marker_path.parent.name,
        owner.I.query_index_contract_admission())
    proof=evidence.load(adapter,state,promotion,'runner-boundary')
    if proof.get('status')!='admitted':return None
    return dict(proofSha256=proof['proofSha256'],implementationSha256=proof['implementationSha256'],
        **({'implementationReuse':proof['implementationReuse']} if proof.get('implementationReuse') else {}))


def inspect_record(owner,state,marker_path,contract,previous):
    """Read retained metadata and name the repair; never prepare source/RDF."""
    marker=owner.read(marker_path);pk=marker_path.parent.name
    record=dict(identity=[owner.sha(marker_path),fingerprint(owner)],
        checkedAtUtc=owner.TX.now(),status='not-applicable')
    proof=boundary_admission(owner,state,marker_path)
    if proof is not None:
        if previous.get('status')=='selected' and previous.get('case'):
            # Preserve the exact selected job so interrupted finalization or
            # transient-input cleanup can finish through its original owner.
            return {**previous,**record,'status':'selected','boundaryAdmission':proof}
        return dict(record,reason='existing-boundary-admission',boundaryAdmission=proof)
    manifest_path=owner.I.retained_artifact(state,pk,marker['rmlManifestSha256'],Path(marker['rmlManifest']))
    if not manifest_path.is_file() or owner.sha(manifest_path)!=marker['rmlManifestSha256']:
        return dict(record,status='retained-manifest-unavailable')
    original=owner.read(manifest_path).get('runnerHistoryReconciliation')
    if not original:return dict(record,status='retained-history-census-unavailable')
    if not (original.get('sourceConsistency')=='consistent'
            and (original.get('withheldHistories') or original.get('boundaryIssues'))):return record
    request=dict(gamePk=pk,promotionManifestSha256=record['identity'][0],
        rmlManifestSha256=marker['rmlManifestSha256'],contextBuilderSha256=contract['contextBuilderSha256'],
        scopeDecision=SCOPE,historyFailures=[dict(inning=r['inning'],half=r['half'],issues=r['issues'])
            for r in original.get('withheldHistories',[])],boundaryIssues=original.get('boundaryIssues',[]))
    request_key=owner.hashlib.sha256(owner.json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    request_path=inventory_path(state).parent/pk/(request_key+'.json')
    if not request_path.is_file():owner.atomic(request_path,request)
    elif owner.read(request_path)!=request:raise ValueError('Recorded history repair request changed')
    request_sha=owner.sha(request_path)
    # A source-recovery attempt keeps the same semantic scope and original
    # request. Do not replace it with the conflicted retained witness again.
    if previous.get('sourceRecovery') and previous.get('repairRequest'):
        retry=Path(previous['repairRequest'])
        if (retry.is_file() and owner.sha(retry)==previous.get('repairRequestSha256')
                and {k:v for k,v in owner.read(retry).items() if k!='recoverRetainedSourceSha256'}==request):
            return {**previous,'identity':record['identity'],'checkedAtUtc':record['checkedAtUtc']}
    # Reinspection of metadata must not recreate an already selected request,
    # whose transient source may have been retired after successful promotion.
    if (previous.get('status')=='selected'
            and previous.get('case',{}).get('repairRequestSha256')==request_sha):
        return {**previous,**record,'status':'selected'}
    if (previous.get('status')=='failed' and previous.get('repairRequestSha256')==request_sha
            and previous.get('diagnostics',{}).get('kind')=='retained-history-conflict'):
        return {**previous,**record,'status':'failed'}
    return dict(record,status='awaiting-source',promotionManifest=str(marker_path),
        repairRequest=str(request_path),repairRequestSha256=request_sha,
        queuedAtUtc=previous.get('queuedAtUtc',owner.TX.now()))


def inspect_promotions(owner,state,excluded,limit=100):
    """Bounded metadata progress even while selected jobs wait for execution."""
    data=inventory(owner,state);version=fingerprint(owner);inspected=0
    contract=owner.read(owner.SELECTION)
    if owner.sha(owner.ROOT/'scripts/pipeline/prepare-rml-context.py')!=contract['contextBuilderSha256']:
        raise ValueError('History discovery context differs from accepted H3')
    directories=sorted((state/'pipeline/evidence/nifi/game-promotion').glob('*'),
        key=lambda p:(p.name in data['games'],p.name))
    for directory in directories:
        pk=directory.name
        if not directory.is_dir() or not pk.isdecimal() or pk in excluded:continue
        markers=list(directory.glob('*.json'))
        if not markers:continue
        marker_path=max(markers,key=lambda p:(owner.read(p)['promotedAtUtc'],p.name))
        identity=[owner.sha(marker_path),version]
        if data['games'].get(pk,{}).get('identity')==identity:continue
        inspected+=1
        try:
            data['games'][pk]=inspect_record(owner,state,marker_path,contract,data['games'].get(pk,{}))
        except Exception as error:
            data['games'][pk]=dict(identity=identity,checkedAtUtc=owner.TX.now(),status='failed',error=str(error))
        if inspected>=limit:break
    if inspected:owner.atomic(inventory_path(state),data)
    return dict(inspectedGames=inspected,awaitingSource=sum(r.get('status')=='awaiting-source' for r in data['games'].values()))


def discover(owner,state,excluded,limit=25):
    """Prepare one queued source; inspection is also called independently."""
    inspect_promotions(owner,state,excluded,limit)
    data=inventory(owner,state)
    def recoverable(record):
        return (record.get('status')=='failed' and not record.get('sourceRecovery')
            and record.get('diagnostics',{}).get('kind')=='retained-history-conflict'
            and record.get('sourceWitness',{}).get('kind')=='retained-response-copy')
    pending=sorted(((pk,r) for pk,r in data['games'].items()
        if pk not in excluded and (r.get('status')=='awaiting-source' or recoverable(r))),
        key=lambda item:(not recoverable(item[1]),item[1].get('queuedAtUtc',item[1]['checkedAtUtc']),item[0]))
    version=fingerprint(owner)
    for pk,record in pending:
        if record['identity'][1]!=version and not recoverable(record):continue
        history=None;original=None;raw=None
        try:
            marker_path=Path(record.get('promotionManifest',''))
            if not marker_path.is_file():
                markers=list((state/'pipeline/evidence/nifi/game-promotion'/pk).glob('*.json'))
                marker_path=next(p for p in markers if owner.sha(p)==record['identity'][0])
            latest=max(marker_path.parent.glob('*.json'),key=lambda p:(owner.read(p)['promotedAtUtc'],p.name))
            if latest!=marker_path or owner.sha(marker_path)!=record['identity'][0]:
                continue  # The next metadata pass selects the new promotion.
            marker=owner.read(marker_path)
            promotion=owner.I.validated_promotion_record(state,marker_path,pk,owner.I.query_index_contract_admission())
            manifest_path=owner.I.retained_artifact(state,pk,marker['rmlManifestSha256'],Path(marker['rmlManifest']))
            if owner.sha(manifest_path)!=marker['rmlManifestSha256']:raise ValueError('Retained history manifest changed')
            manifest=owner.read(manifest_path);original=manifest['runnerHistoryReconciliation']
            request_path=Path(record['repairRequest'])
            if owner.sha(request_path)!=record['repairRequestSha256']:raise ValueError('Recorded history repair request changed')
            if recoverable(record):
                prior_request=request_path
                request=dict(owner.read(prior_request),recoverRetainedSourceSha256=record['sourceWitness']['sha256'])
                key=owner.hashlib.sha256(owner.json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                request_path=prior_request.parent/(key+'.json')
                if not request_path.is_file():owner.atomic(request_path,request)
                elif owner.read(request_path)!=request:raise ValueError('History recovery request changed')
                record.update(sourceRecovery=dict(originalRequest=str(prior_request),
                    originalRequestSha256=record['repairRequestSha256'],conflictedWitness=record['sourceWitness'],
                    reason=record['error'],diagnostics=record['diagnostics']),
                    repairRequest=str(request_path),repairRequestSha256=owner.sha(request_path),
                    identity=[record['identity'][0],version],status='awaiting-source',
                    queuedAtUtc=owner.TX.now(),promotionManifest=str(marker_path))
                recovery_path=request_path.with_suffix('.recovery.json')
                if not recovery_path.is_file():owner.atomic(recovery_path,record['sourceRecovery'])
                elif owner.read(recovery_path)!=record['sourceRecovery']:raise ValueError('History recovery evidence changed')
                owner.atomic(inventory_path(state),data)  # Named scope precedes the one new acquisition.
            witness=source(owner,state,promotion,request_path)
            record.update(sourceWitness=witness,identity=[record['identity'][0],version])
            raw=Path(witness['path']).read_bytes()
            history=owner.H.CONTEXT.personal_runner_histories(raw)
            owner.H.CONTEXT.verify_runner_history_correction(history,original)
            previous={h['lifetimeKey'] for h in original['histories']}
            selected=[h for h in history['histories'] if h['lifetimeKey'] not in previous]
            case=dict(gamePk=pk,selectionRepair='H3',discovered=True,inputSha256=original['inputSha256'],
                sourceSha256=witness['sha256'],sourceWitness=witness,promotionManifestSha256=record['identity'][0],
                selectedHistoryKeys=sorted(h['lifetimeKey'] for h in selected),
                halves=[dict(inning=i,half=h) for i,h in sorted({(int(h['inning']),h['half']) for h in selected})],
                repairRequest=str(request_path),repairRequestSha256=owner.sha(request_path))
            if selected:owner.select_history(manifest,case,raw)
            record.update(status='selected',case=case,checkedAtUtc=owner.TX.now())
            for key in ('error','diagnostics','diagnosticError'):record.pop(key,None)
            owner.atomic(inventory_path(state),data)
            return pk
        except Exception as error:
            record.update(status='failed',error=str(error))
            if history is not None:
                try:record['diagnostics']=conflict_details(owner,raw,original,history)
                except Exception as diagnostic_error:record['diagnosticError']=str(diagnostic_error)
            # Preserve source and terminal evidence. An unrelated game still
            # gets its next bounded tick; never reacquire this failed input.
        owner.atomic(inventory_path(state),data)
        return None
    return None


if __name__=='__main__':
    import argparse
    import importlib.util
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('history_inspection_owner',Path(__file__).with_name('targeted-history-addition.py'))
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    print(owner.json.dumps(inspect_promotions(owner,args.state_root,{c['gamePk'] for c in owner.cases()})))
