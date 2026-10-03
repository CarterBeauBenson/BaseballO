"""Bounded NiFi discovery for H3's accepted additive history worker.

Start with a recorded history/boundary failure, preserve the exact source and
base identities, and let the unchanged context select the missing histories.
This is queue construction, not another semantic validator or game remapper.
"""
from pathlib import Path
import urllib.request

SCOPE='archive/design-records/metric-repair-scope-2026-09-30/answers.md'


def inventory_path(state):
    return state/'pipeline/control/mlb-game/history-discovery/inventory.json'


def inventory(owner,state):
    path=inventory_path(state)
    return owner.read(path) if path.is_file() else dict(games={})


def cases(owner,state):
    return [r['case'] for r in inventory(owner,state)['games'].values() if r.get('status')=='selected']


def source(owner,state,promotion,request_path):
    """The persisted request identifies the one game before any acquisition."""
    request=owner.read(request_path);pk=promotion['gamePk']
    if request.get('gamePk')!=pk or request.get('promotionManifestSha256')!=promotion['promotionManifestSha256']:
        raise ValueError('History acquisition request belongs to another game or promotion')
    directory=state/'pipeline/quarantine/mlb-game'/pk/('targeted-history-'+promotion['promotionManifestSha256'][:16])
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
    retained=evidence.retained_raw_witness(state,promotion)
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


def discover(owner,state,excluded,limit=25):
    """Inspect at most 25 receipts and prepare at most one source per tick."""
    data=inventory(owner,state);version=owner.fingerprint();inspected=0
    contract=owner.read(owner.SELECTION)
    if owner.sha(owner.ROOT/'scripts/pipeline/prepare-rml-context.py')!=contract['contextBuilderSha256']:
        raise ValueError('History discovery context differs from accepted H3')
    directories=sorted((state/'pipeline/evidence/nifi/game-promotion').glob('*'),
        key=lambda p:(data['games'].get(p.name,{}).get('status')!='failed',p.name))
    for directory in directories:
        pk=directory.name
        if not directory.is_dir() or not pk.isdecimal() or pk in excluded:continue
        markers=list(directory.glob('*.json'))
        if not markers:continue
        marker_path=max(markers,key=lambda p:(owner.read(p)['promotedAtUtc'],p.name))
        marker=owner.read(marker_path);identity=[owner.sha(marker_path),version]
        if data['games'].get(pk,{}).get('identity')==identity:continue
        inspected+=1;attempted_source=False
        record=dict(identity=identity,checkedAtUtc=owner.TX.now(),status='not-applicable')
        data['games'][pk]=record
        try:
            manifest_path=owner.I.retained_artifact(state,pk,marker['rmlManifestSha256'],Path(marker['rmlManifest']))
            if not manifest_path.is_file() or owner.sha(manifest_path)!=marker['rmlManifestSha256']:
                record['status']='retained-manifest-unavailable'
            else:
                manifest=owner.read(manifest_path);original=manifest.get('runnerHistoryReconciliation')
                if not original:record['status']='retained-history-census-unavailable'
                elif (original.get('sourceConsistency')=='consistent'
                        and (original.get('withheldHistories') or original.get('boundaryIssues'))):
                    promotion=owner.I.validated_promotion_record(state,marker_path,pk,owner.I.query_index_contract_admission())
                    request=dict(gamePk=pk,promotionManifestSha256=identity[0],rmlManifestSha256=marker['rmlManifestSha256'],
                        contextBuilderSha256=contract['contextBuilderSha256'],scopeDecision=SCOPE,
                        historyFailures=[dict(inning=r['inning'],half=r['half'],issues=r['issues'])
                            for r in original.get('withheldHistories',[])],boundaryIssues=original.get('boundaryIssues',[]))
                    request_key=owner.hashlib.sha256(owner.json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    request_path=inventory_path(state).parent/pk/(request_key+'.json')
                    if not request_path.is_file():owner.atomic(request_path,request)
                    elif owner.read(request_path)!=request:raise ValueError('Recorded history repair request changed')
                    attempted_source=True
                    witness=source(owner,state,promotion,request_path)
                    raw=Path(witness['path']).read_bytes()
                    history=owner.H.CONTEXT.personal_runner_histories(raw,previous=original)
                    previous={h['lifetimeKey'] for h in original['histories']}
                    selected=[h for h in history['histories'] if h['lifetimeKey'] not in previous]
                    case=dict(gamePk=pk,selectionRepair='H3',discovered=True,inputSha256=original['inputSha256'],
                        sourceSha256=witness['sha256'],sourceWitness=witness,promotionManifestSha256=identity[0],
                        selectedHistoryKeys=sorted(h['lifetimeKey'] for h in selected),
                        halves=[dict(inning=i,half=h) for i,h in sorted({(int(h['inning']),h['half']) for h in selected})],
                        repairRequest=str(request_path),repairRequestSha256=owner.sha(request_path))
                    if selected:owner.select_history(manifest,case,raw)
                    record.update(status='selected',case=case)
                    owner.atomic(inventory_path(state),data)
                    return pk
        except Exception as error:
            record.update(status='failed',error=str(error))
            # Preserve source and terminal evidence. An unrelated game still
            # gets its next bounded tick; never reacquire this failed input.
        owner.atomic(inventory_path(state),data)
        if attempted_source:return None
        if inspected>=limit:break
    return None
