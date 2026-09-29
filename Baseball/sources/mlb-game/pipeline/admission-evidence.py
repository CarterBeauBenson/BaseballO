"""Evidence-only maintenance over exact retained inputs and promoted RDF.

This never acquires source data, executes RML, changes a graph or changes a
promotion marker. Previously withheld proofs stay distinguishable from absent
proofs and implementation drift. Refreshed proofs retain the original promotion.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import os
import argparse
from datetime import datetime, timezone
from types import SimpleNamespace
import sqlite3
import time
from contextlib import closing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
COMPATIBILITY_PATH=HERE/'context-proof-compatibility.json'
FIELDS={'batting':'battingAdmission','scoring-run':'scoringRunAdmission',
    'runner-resolution':'runnerResolutionAdmission','pitch-count':'pitchCountAdmission',
    'runner-boundary':'runnerBoundaryAdmission','defensive':'defensiveAdmission'}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno());tmp=Path(stream.name)
    try: os.replace(tmp,path)
    finally: tmp.unlink(missing_ok=True)


RETAINED_BATTING=module(HERE/'retained-batting-evidence.py','retained_batting_evidence')
PLAYER_PARTICIPATION=module(HERE/'player-participation-admission.py','player_participation_evidence')
EXISTING_GRAPH=module(HERE/'existing-graph-admissions.py','existing_graph_admissions')
PA_RESOLUTION=module(HERE/'pa-resolution-admission.py','pa_resolution_evidence')


def checked_marker(promotion):
    path=Path(promotion['promotionManifest'])
    if sha(path)!=promotion['promotionManifestSha256']: raise ValueError('Promotion marker changed')
    return read(path)


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+COMPATIBILITY_PATH.read_bytes()
        +RETAINED_BATTING.fingerprint().encode()+PLAYER_PARTICIPATION.fingerprint().encode()
        +PA_RESOLUTION.fingerprint().encode()
        +(HERE/'existing-graph-admissions.py').read_bytes()).hexdigest()


def code_equivalence(family,previous,current):
    """Pinned compatible edits, not blanket acceptance of stale proofs.

    The regression compares both exact context revisions and the transitive
    call dependencies. Complete producer fingerprints include every other
    original dependency, SHACL template and validator. Unknown changes miss.
    """
    record=read(COMPATIBILITY_PATH)
    isolation=record.get('zeroEpisodeIsolation',{})
    bridge=isolation.get('families',{}).get(family)
    if (bridge and current==bridge['currentImplementationSha256']
            and sha(ROOT/record['contextPath'])==isolation['currentContextSha256']):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind='prior-stricter-history-selection' if family=='runner-boundary' else 'unchanged-proof-dependencies')
                if previous==prior else code_equivalence(family,previous,prior))
        if reused is not None:
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),previousImplementationSha256=previous,
                currentImplementationSha256=current,viaPreviousImplementationSha256=prior,
                historyIsolationDecision=isolation['decision'])
    entry=record['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']
            and sha(ROOT/record['contextPath']) in {record['currentContextSha256'],isolation.get('currentContextSha256')}):
        return dict(kind='unchanged-proof-dependencies',recordSha256=sha(COMPATIBILITY_PATH),
            previousImplementationSha256=previous,currentImplementationSha256=current)
    entry=record['priorClockIsolation']['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']):
        return dict(kind='prior-stricter-clock-check',recordSha256=sha(COMPATIBILITY_PATH),
            previousImplementationSha256=previous,currentImplementationSha256=current)
    entry=record['priorPinchHitterIsolation']['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']):
        return dict(kind='prior-stricter-pinch-hitter-check',recordSha256=sha(COMPATIBILITY_PATH),
            previousImplementationSha256=previous,currentImplementationSha256=current)
    return None


def compatible_proof(state,promotion,family,implementation):
    marker=checked_marker(promotion);field=FIELDS[family];path=Path(marker.get(field,''))
    if not path.is_file(): return None
    if not path.resolve().is_relative_to((Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Proof escaped its owning source game')
    if sha(path)!=marker.get(field+'Sha256'): raise ValueError('Retained proof changed')
    proof=read(path)
    reuse=code_equivalence(family,proof.get('implementationSha256'),implementation)
    if reuse is None: return None
    positive_only=reuse['kind'] in {'prior-stricter-clock-check','prior-stricter-pinch-hitter-check','prior-stricter-history-selection'}
    if positive_only and proof.get('status')!='admitted': return None
    expected=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
        gamePk=promotion['gamePk'],sourceSha256=promotion['rawSha256'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],graph=promotion['authoritativeGraph'])
    if any(proof.get(key)!=value for key,value in expected.items()): return None
    required=('sourceReconciled','graphConforms','sourceCensusSha256','shapeSha256','reportSha256')
    if family=='defensive': required+=('populationComplete',)
    if proof.get('status')=='admitted' and not all(proof.get(key) for key in required):
        raise ValueError('Admitted proof lacks its retained conformance evidence')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if key in proof and sha(path.with_suffix(suffix))!=proof[key]:
            raise ValueError('Retained validation artifact changed: '+key)
    if positive_only:
        census=read(path.with_suffix('.source.json'))
        # These exact older implementations rejected the newly isolated cases.
        # Their successful source censuses retain the same SHACL expectations.
        # Withheld proofs cannot use this implication in the other direction.
        if (census.get('status')!='reconciled' or census.get('issues')!=[]
                or census.get('sourceSha256')!=promotion['rawSha256']
                or census.get('gamePk')!=promotion['gamePk']):
            raise ValueError('Prior proof lacks its reconciled source census')
    # Keep the original status, issues AND producer fingerprint. This is code
    # reuse provenance, not a newly issued source/SHACL proof.
    return {**proof,'proofSha256':sha(path),'implementationReuse':reuse}


def retained_manifest(state,marker,game_pk):
    inventory=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','admission_retained_artifacts')
    return inventory.retained_artifact(Path(state),game_pk,marker['rmlManifestSha256'],Path(marker['rmlManifest']))


def diagnostic(state,promotion,family,implementation):
    marker=checked_marker(promotion);field=FIELDS[family]
    path=Path(marker.get(field,''))
    if not path.is_file(): return dict(evidenceState='missing',family=family)
    owner=Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']
    if not path.resolve().is_relative_to(owner.resolve()): raise ValueError('Proof escaped its owning source game')
    if sha(path)!=marker.get(field+'Sha256'): raise ValueError('Retained proof changed')
    proof=read(path)
    same=(proof.get('gamePk')==promotion['gamePk'] and proof.get('sourceSha256')==promotion['rawSha256']
        and proof.get('authoritativeRdfSha256')==promotion['authoritativeRdfSha256'])
    current=proof.get('implementationSha256')==implementation
    reuse=compatible_proof(state,promotion,family,implementation) if same and not current else None
    return dict(family=family,evidenceState='promotion-mismatch' if not same else 'current' if current else
            'implementation-compatible' if reuse is not None else 'implementation-stale',
        previousStatus=proof.get('status'),previousIssues=proof.get('issues',[]),
        recordedImplementationSha256=proof.get('implementationSha256'),requiredImplementationSha256=implementation)


def refresh_path(state,promotion,family,implementation):
    return Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']/'admission-refresh'/(
        promotion['promotionManifestSha256']+'-'+implementation)/f'{family}.json'


def refreshed(state,promotion,family,implementation):
    path=refresh_path(state,promotion,family,implementation)
    receipt=path.with_suffix('.receipt.json')
    if not receipt.is_file(): return None
    record=read(receipt)
    if record.get('promotionManifestSha256')!=promotion['promotionManifestSha256'] or record.get('proofSha256')!=sha(path):
        raise ValueError('Refreshed admission receipt changed')
    proof=read(path)
    expected=dict(artifactType='baseballo-'+family+'-admission',contractVersion=1,
        gamePk=promotion['gamePk'],sourceSha256=promotion['rawSha256'],
        authoritativeRdfSha256=promotion['authoritativeRdfSha256'],implementationSha256=implementation,
        graph=promotion['authoritativeGraph'])
    if any(proof.get(k)!=v for k,v in expected.items()): raise ValueError('Refreshed admission belongs to different inputs')
    if proof.get('status')=='admitted' and not all(proof.get(k) for k in
            ('sourceReconciled','graphConforms','sourceCensusSha256','shapeSha256','reportSha256')):
        raise ValueError('Admitted refresh lacks its existing conformance evidence')
    for suffix,key in (('.source.json','sourceCensusSha256'),('.shapes.ttl','shapeSha256'),('.report.ttl','reportSha256')):
        if key in proof and sha(path.with_suffix(suffix))!=proof[key]: raise ValueError('Refreshed validation artifact changed')
    return {**proof,'proofSha256':record['proofSha256']}


def load(adapter,state,promotion,family):
    independent=EXISTING_GRAPH.load(SimpleNamespace(**globals()),state,promotion,family,adapter)
    if independent is not None and independent.get('status')=='admitted':return independent
    # A failed later witness cannot suppress a separately valid original proof.
    def select(proof):return proof if proof.get('status')=='admitted' else independent or proof
    if family=='batting':
        proof=RETAINED_BATTING.load(SimpleNamespace(**globals()),state,promotion)
        if proof is not None:
            checked_marker(promotion)
            return select(proof)
    proof=refreshed(state,promotion,family,adapter.fingerprint())
    if proof is not None:
        checked_marker(promotion)
        return select(proof)
    proof=compatible_proof(state,promotion,family,adapter.fingerprint())
    if proof is not None: return select(proof)
    return select(adapter.promoted_admission(state,promotion))


def player_admission(state,promotion):
    api=SimpleNamespace(**globals())
    individual=PLAYER_PARTICIPATION.load(api,state,promotion)
    resolution=PA_RESOLUTION.load(api,state,promotion)
    return dict(individual or {},paResolutions=resolution) if resolution else individual


def refresh_game(state,promotion,java,classpath,endpoint='http://127.0.0.1:3031/baseball-dev/query'):
    marker=checked_marker(promotion)
    adapters={family:module(HERE/(family+'-admission.py'),'refresh_'+family.replace('-','_')) for family in FIELDS}
    versions={family:adapter.fingerprint() for family,adapter in adapters.items()}
    diagnostics={family:diagnostic(state,promotion,family,versions[family]) for family in FIELDS}
    pending=[family for family in FIELDS if diagnostics[family]['evidenceState'] not in {'current','implementation-compatible'}
        and refreshed(state,promotion,family,versions[family]) is None]
    result=dict(gamePk=promotion['gamePk'],promotionManifestSha256=promotion['promotionManifestSha256'],
        diagnostics=diagnostics,refreshed=[],rdfChanged=False)
    api=SimpleNamespace(**globals())
    batting=load(adapters['batting'],state,promotion,'batting')
    boundary=load(adapters['runner-boundary'],state,promotion,'runner-boundary')
    individual=PLAYER_PARTICIPATION.load(api,state,promotion)
    if ((batting.get('status')!='admitted' or boundary.get('status')!='admitted')
            and (individual is None or individual.get('implementationSha256')!=PLAYER_PARTICIPATION.fingerprint())):
        retained=PLAYER_PARTICIPATION.retained_source(api,state,promotion)
        if retained is not None:
            memory=module(ROOT/'scripts/pipeline/process_state.py','participation_memory').available_memory()
            if memory is not None and memory<1024*1024*1024:
                return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
            proof=PLAYER_PARTICIPATION.prove(api,state,promotion,retained,java,classpath,endpoint)
            return dict(result,status='partial-refreshed',refreshed=['player-participation'],
                rosterComplete=proof['rosterComplete'],admittedPlayers=sum(p['status']=='admitted' for p in proof['players']))
    if RETAINED_BATTING.load(api,state,promotion) is None:
        api=SimpleNamespace(**globals())
        retained=RETAINED_BATTING.source_census(api,state,promotion)
        if retained is not None:
            memory=module(ROOT/'scripts/pipeline/process_state.py','retained_batting_memory').available_memory()
            # One bounded graph and the existing 384 MiB Jena heap. Retain
            # over 600 MiB outside that heap rather than applying the larger
            # multi-profile/raw-input refresh reservation to this stage.
            if memory is not None and memory<1024*1024*1024:
                return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
            proof=RETAINED_BATTING.prove(api,state,promotion,retained,java,classpath,endpoint)
            return dict(result,status='refreshed',refreshed=['batting'],battingStatus=proof['status'])
    resolution=load(adapters['runner-resolution'],state,promotion,'runner-resolution')
    if resolution.get('status')!='admitted' and PA_RESOLUTION.load(api,state,promotion) is None:
        retained=PA_RESOLUTION.retained_source(api,state,promotion)
        if retained is not None:
            memory=module(ROOT/'scripts/pipeline/process_state.py','pa_resolution_memory').available_memory()
            if memory is not None and memory<1024*1024*1024:
                return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
            proof=PA_RESOLUTION.prove(api,state,promotion,retained,java,classpath,endpoint)
            return dict(result,status='refreshed',refreshed=['pa-runner-resolution'],
                admittedResolutionPAs=sum(p['status']=='admitted' for p in proof['plateAppearances']))
    if not pending: return dict(result,status='current')
    manifest_path=retained_manifest(state,marker,promotion['gamePk'])
    if not manifest_path.is_file() or sha(manifest_path)!=marker.get('rmlManifestSha256'):
        return dict(result,status='retained-manifest-unavailable')
    manifest=read(manifest_path);rdf=Path(manifest.get('outputPath',''))
    if not rdf.is_file() or sha(rdf)!=promotion['authoritativeRdfSha256']:
        return dict(result,status='retained-rdf-unavailable')
    candidates=[Path(manifest.get('inputPath','')),
        *sorted((Path(state)/'pipeline/quarantine/mlb-game'/promotion['gamePk']).glob('*/input.json'))]
    source=next((p for p in candidates if p.is_file() and sha(p)==promotion['rawSha256']),None)
    if source is None: return dict(result,status='exact-source-input-retired')
    raw=source.read_bytes()
    memory=module(ROOT/'scripts/pipeline/process_state.py','admission_memory').available_memory()
    if memory is not None and memory<1536*1024*1024:
        return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
    session_module=module(ROOT/'scripts/pipeline/jena_session.py','refresh_jena_session')
    with session_module.Session(rdf,java,classpath) as session:
        for family in pending:
            producer=adapters[family];owner=getattr(producer,'B',producer);original=owner.module
            owner.module=lambda path,name,loader=original: session if Path(path).name=='validate-shacl.py' else loader(path,name)
            output=refresh_path(state,promotion,family,versions[family])
            producer.prove(raw=raw,game_pk=promotion['gamePk'],rdf_path=rdf,output=output,java=java,classpath=classpath)
            if source.read_bytes()!=raw or sha(rdf)!=promotion['authoritativeRdfSha256']:
                raise ValueError('Evidence refresh inputs changed')
            checked_marker(promotion)
            atomic(output.with_suffix('.receipt.json'),dict(artifactType='baseballo-admission-evidence-refresh',
                promotionManifestSha256=promotion['promotionManifestSha256'],proofSha256=sha(output),
                refreshedAtUtc=datetime.now(timezone.utc).isoformat(),rdfChanged=False))
            result['refreshed'].append(family)
    return dict(result,status='refreshed')


def dashboard_game_priorities(state):
    """Repair missing season qualification before unrelated maintenance.

    SQL identifies the backlog; existing source-owned checks still decide
    admission. A completed individual check is not retried merely because
    another player in that game remains withheld.
    """
    pointer=Path(state)/'serving/dashboard-current.json'
    if not pointer.is_file():return {}
    database=Path(read(pointer)['databasePath'])
    if not database.resolve().is_relative_to((Path(state)/'serving/dashboard/builds').resolve()):
        raise ValueError('Dashboard priority database escaped its owner')
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as connection:
        player_version=PLAYER_PARTICIPATION.fingerprint()
        priority={r[0]:2 for r in connection.execute("SELECT game_pk FROM game_dimension WHERE game_set='regular_season' "
            "AND season=(SELECT max(season) FROM game_dimension WHERE game_set='regular_season')")}
        for pk,batting,individual in connection.execute('''SELECT g.game_pk,
                json_extract(b.proof_json,'$.status'),json_extract(a.proof_json,'$.implementationSha256')
                FROM game_dimension g LEFT JOIN metric_suite_admission b USING(graph_iri)
                LEFT JOIN dashboard_player_admission a USING(graph_iri)
                WHERE g.game_set='regular_season' '''):
            if pk in priority and batting!='admitted' and individual!=player_version:priority[pk]=1
        for pk, in connection.execute("SELECT game_pk FROM game_dimension g LEFT JOIN dashboard_player_game p USING(graph_iri) "
                "WHERE game_set='regular_season' GROUP BY g.graph_iri HAVING MAX(COALESCE(p.roster_complete,0))=0"):
            if pk in priority:priority[pk]=0
        return priority


def tick(state,java,classpath,limit=100,endpoint='http://127.0.0.1:3031/baseball-dev/query'):
    control=Path(state)/'pipeline/control/mlb-game/admission-evidence'
    versions={family:module(HERE/(family+'-admission.py'),'version_'+family.replace('-','_')).fingerprint() for family in FIELDS}
    version=hashlib.sha256(json.dumps(versions,sort_keys=True).encode()+fingerprint().encode()).hexdigest()
    outcomes=[];started=time.monotonic();refreshed_games=0
    priority=dashboard_game_priorities(state)
    for directory in sorted((Path(state)/'pipeline/evidence/nifi/game-promotion').glob('*'),
            key=lambda p:(priority.get(p.name,3),p.name)):
        if not directory.is_dir() or not directory.name.isdigit(): continue
        candidates=[(read(path).get('promotedAtUtc',''),path.name,path) for path in directory.glob('*.json')]
        if not candidates: continue
        path=max(candidates)[2];marker=read(path);marker_sha=sha(path)
        destination=control/(directory.name+'.json')
        previous=read(destination) if destination.is_file() else {}
        if (previous.get('promotionManifestSha256')==marker_sha and previous.get('implementationSetSha256')==version
                and previous.get('status') not in {'waiting-for-memory','failed','partial-refreshed'}):
            continue
        if previous.get('status')=='failed' and previous.get('implementationSetSha256')==version and previous.get('attempts',0)>=2:
            continue
        result=dict(gamePk=directory.name,promotionManifestSha256=marker_sha,implementationSetSha256=version,
            checkedAtUtc=datetime.now(timezone.utc).isoformat(),rdfChanged=False,
            attempts=(previous.get('attempts',0) if previous.get('implementationSetSha256')==version else 0)+1)
        try:
            if marker.get('artifactType')!='baseball-nifi-game-promotion' or str(marker.get('gamePk'))!=directory.name:
                raise ValueError('Unexpected source promotion marker')
            inventory=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','admission_inventory')
            promotion=inventory.validated_promotion_record(Path(state),path,directory.name,inventory.query_index_contract_admission())
            result.update(refresh_game(state,promotion,java,classpath,endpoint))
        except (OSError,ValueError,RuntimeError) as error:
            result.update(status='failed',error=str(error))
        atomic(destination,result);outcomes.append(result)
        # Serial, bounded games share the existing one-minute owner schedule.
        # Finish the current game, then yield; no parallel JVM/heap accumulation.
        refreshed_games+=bool(result.get('refreshed'))
        if result.get('status')=='failed' or refreshed_games>=10 or time.monotonic()-started>=45 or len(outcomes)>=limit: break
    summary=dict(status='processed' if outcomes else 'unchanged',processedGames=len(outcomes),
        refreshedGames=sum(bool(r.get('refreshed')) for r in outcomes),
        outcomes={s:sum(r['status']==s for r in outcomes) for s in sorted({r['status'] for r in outcomes})})
    summary['proofOutcomes']={}
    for result in outcomes:
        for family,diagnosis in result.get('diagnostics',{}).items():
            counts=summary['proofOutcomes'].setdefault(family,{})
            key=diagnosis['evidenceState']+':'+str(diagnosis.get('previousStatus','unknown'))
            counts[key]=counts.get(key,0)+1
    atomic(control/'latest.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ('state-root','java','jena-classpath'): parser.add_argument('--'+key,required=True,type=Path)
    parser.add_argument('--endpoint',default='http://127.0.0.1:3031/baseball-dev/query')
    args=parser.parse_args()
    print(json.dumps(tick(args.state_root,args.java,args.jena_classpath,endpoint=args.endpoint)))
