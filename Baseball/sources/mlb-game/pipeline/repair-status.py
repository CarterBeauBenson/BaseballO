"""Source-owned NiFi observations of existing work, never an ingestion gate.

Read terminal evidence and discovery coverage. Do not run RML, query RDF,
acquire inputs, decide semantics, retry work, or change another checkpoint.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
QUEUES=('defensive-addition','history-addition','foul-addition','award-addition',
        'runner-addition','compound-addition','admission-evidence')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(value):
    return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=Z|[+-])',r'\1',value).replace('Z','+00:00'))


def foul_source_excerpt(state,pk,record):
    witness=record.get('sourceWitness',{});source=Path(witness['path']).resolve()
    roots=(state/'pipeline/quarantine/mlb-game'/pk,HERE.parents[2]/'data/raw')
    if not any(source.is_relative_to(root.resolve()) for root in roots):
        raise ValueError('Diagnostic source is outside its retained input roots')
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=witness['sha256']:
        raise ValueError('Diagnostic source differs from the repair witness')
    document=json.loads(raw)
    if str(document['gamePk'])!=pk:raise ValueError('Diagnostic source belongs to another game')
    selected=record.get('unresolvedFouls') or record.get('case',{}).get('selected',[])
    indexes=sorted({int(r['atBatIndex']) for r in selected})[:5]
    return [dict(atBatIndex=p['atBatIndex'],description=p.get('result',{}).get('description'),
        events=[{key:e[key] for key in ('index','playId','type','isPitch','details','count','reviewDetails')
                 if key in e} for e in p.get('playEvents',[])])
        for p in document['liveData']['plays']['allPlays'] if p['atBatIndex'] in indexes]


def observe(state,owner):
    control=state/'pipeline/control/mlb-game';issues=[];errors=[];queues={};records={}

    def load(path,default=None):
        try:return read(path)
        except (OSError,ValueError) as error:
            errors.append(dict(path=str(path),error=str(error)));return default

    def issue(kind,pk,record,path):
        keys=('status','error','checkedAtUtc','attempts','failureAttempts','sourceWitness',
              'repairRequest','repairRequestSha256','unresolvedFouls','diagnostics','familyFailures')
        item=dict(kind=kind,gamePk=pk,evidence=str(path),
            **{key:record[key] for key in keys if key in record})
        if (kind=='foul-addition' and record.get('sourceWitness')
                and (record.get('unresolvedFouls') or record.get('case',{}).get('selected'))):
            try:item['sourcePlays']=foul_source_excerpt(state,pk,record)
            except (KeyError,OSError,ValueError) as error:item['diagnosticError']=str(error)
        issues.append(item)

    for kind in QUEUES:
        rows={}
        for path in (control/kind).glob('*.json'):
            if not path.stem.isdecimal():continue
            row=load(path)
            if not isinstance(row,dict):continue
            rows[path.stem]=row
            if row.get('status') in {'failed','partial','retry-exhausted'} or row.get('familyFailures'):
                issue(kind,path.stem,row,path)
        records[kind]=rows
        queues[kind]=dict(Counter(row.get('status','missing-status') for row in rows.values()))

    inventory_path=control/'history-discovery/inventory.json'
    discovery=(load(inventory_path,{}) if inventory_path.is_file() else {}).get('games',{})
    fixed={case['gamePk'] for case in owner.cases()};version=owner.DISCOVERY.fingerprint(owner)
    latest={};uninspected=[];stale=[];eligible=0;missing_promotion=[]
    for directory in (state/'pipeline/evidence/nifi/game-promotion').glob('*'):
        if not directory.is_dir() or not directory.name.isdecimal():continue
        candidates=[]
        for path in directory.glob('*.json'):
            marker=load(path)
            if isinstance(marker,dict) and marker.get('promotedAtUtc'):
                candidates.append((marker['promotedAtUtc'],path.name,path))
        if not candidates:
            missing_promotion.append(directory.name);continue
        _,_,path=max(candidates);pk=directory.name
        try:latest[pk]=dict(path=str(path),sha256=digest(path),promotedAtUtc=read(path)['promotedAtUtc'])
        except (OSError,ValueError) as error:
            errors.append(dict(path=str(path),error=str(error)));continue
        if pk in fixed:continue
        eligible+=1;record=discovery.get(pk)
        if record is None:uninspected.append(pk)
        elif record.get('identity')!=[latest[pk]['sha256'],version]:stale.append(pk)

    selected_complete=0;selected_pending=[]
    for pk,record in discovery.items():
        if record.get('status')=='failed':issue('history-discovery',pk,record,inventory_path)
        if record.get('status')!='selected':continue
        case=record['case'];previous=records['history-addition'].get(pk,{})
        # Invoke the worker's own request/source/selection completion rule.
        if owner.completed_case(previous,case):selected_complete+=1
        else:selected_pending.append(pk)
    fixed_pending=sorted({case['gamePk'] for case in owner.cases()
        if not owner.completed_case(records['history-addition'].get(case['gamePk'],{}),case)})

    defensive_path=control/'defensive-addition/inventory.json'
    defensive=load(defensive_path,{}) if defensive_path.is_file() else {}
    unresolved=sorted({row['gamePk'] for row in defensive.get('inputs',{}).values()
        if row.get('status')=='unresolved-source'})
    unavailable=sorted(pk for pk,row in discovery.items() if row.get('status','').startswith('retained-')
        and row['status'].endswith('-unavailable'))
    quarantine_pending=[];quarantine_superseded=0
    for directory in (state/'pipeline/quarantine/rml').glob('game-*'):
        match=re.fullmatch(r'game-(\d+)-(\d{8}T\d{6}Z)',directory.name)
        if not directory.is_dir() or not match:continue
        pk,when=match.groups()
        failed=datetime.strptime(when,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        try:later=pk in latest and timestamp(latest[pk]['promotedAtUtc'])>failed
        except ValueError as error:
            errors.append(dict(path=latest[pk]['path'],error=str(error)));later=False
        if later:quarantine_superseded+=1
        else:quarantine_pending.append(dict(gamePk=pk,path=str(directory)))

    active=sum(n for counts in queues.values() for status,n in counts.items()
        if status in {'running','finalizing'} or status.startswith('waiting-'))
    awaiting_source=sorted(pk for pk,r in discovery.items() if r.get('status')=='awaiting-source')
    pending=len(uninspected)+len(stale)+len(selected_pending)+len(fixed_pending)+len(awaiting_source)+active
    coverage=dict(unresolvedDefensiveSources=unresolved,unavailableHistoryEvidence=unavailable,
        defensiveSourceEvidence=[dict(sourcePath=path,**{key:row[key] for key in
            ('gamePk','sha256','error','sourceIssues','sourceRevision') if key in row})
            for path,row in sorted(defensive.get('inputs',{}).items()) if row.get('status')=='unresolved-source'])
    attention=bool(issues or errors or unresolved or unavailable or quarantine_pending or missing_promotion)
    return dict(artifactType='baseballo-mlb-game-repair-status',checkedAtUtc=owner.TX.now(),
        status='attention-required' if attention else 'inspection-in-progress' if pending else
            'recorded-work-clear' if latest else 'no-promotion-evidence',
        recordedWorkClear=bool(latest) and not attention and pending==0,promotedGames=len(latest),queues=queues,
        historyDiscovery=dict(eligiblePromotedGames=eligible,inspectionImplementationSha256=version,
            statuses=dict(Counter(r.get('status','missing-status') for r in discovery.values())),
            uninspectedGames=sorted(uninspected),outdatedInspections=sorted(stale),
            awaitingSource=awaiting_source,
            selectedCompleted=selected_complete,selectedPending=sorted(selected_pending),fixedPending=fixed_pending),
        coverageLimits=coverage,issues=issues,observationErrors=errors,
        promotionDirectoriesWithoutMarker=missing_promotion,
        rmlQuarantine=dict(historicalWithLaterPromotion=quarantine_superseded,
            withoutLaterPromotion=quarantine_pending),
        actionPolicy='Existing NiFi owners execute bounded retries. Source or identity conflicts remain blocked; this report never changes their status.')


def publish(state,owner):
    report=observe(state,owner)
    path=state/'pipeline/control/mlb-game/repair-status.json';owner.atomic(path,report)
    discovery=report['historyDiscovery']
    return dict(status=report['status'],recordedWorkClear=report['recordedWorkClear'],report=str(path),
        issueCount=len(report['issues']),observationErrors=len(report['observationErrors']),
        uninspectedGames=len(discovery['uninspectedGames']),outdatedInspections=len(discovery['outdatedInspections']),
        selectedPending=len(discovery['selectedPending']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,required=True);args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('repair_status_owner',HERE/'targeted-history-addition.py')
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    print(json.dumps(publish(args.state_root,owner)))
