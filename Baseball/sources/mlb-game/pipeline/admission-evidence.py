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


def checked_marker(promotion):
    path=Path(promotion['promotionManifest'])
    if sha(path)!=promotion['promotionManifestSha256']: raise ValueError('Promotion marker changed')
    return read(path)


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+COMPATIBILITY_PATH.read_bytes()).hexdigest()


def code_equivalence(family,previous,current):
    """Pinned compatible edits, not blanket acceptance of stale proofs.

    The regression compares both exact context revisions and the transitive
    call dependencies. Complete producer fingerprints include every other
    original dependency, SHACL template and validator. Unknown changes miss.
    """
    record=read(COMPATIBILITY_PATH)
    entry=record['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']
            and sha(ROOT/record['contextPath'])==record['currentContextSha256']):
        return dict(kind='unchanged-proof-dependencies',recordSha256=sha(COMPATIBILITY_PATH),
            previousImplementationSha256=previous,currentImplementationSha256=current)
    entry=record['priorClockIsolation']['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']):
        return dict(kind='prior-stricter-clock-check',recordSha256=sha(COMPATIBILITY_PATH),
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
    if reuse['kind']=='prior-stricter-clock-check' and proof.get('status')!='admitted': return None
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
    if reuse['kind']=='prior-stricter-clock-check':
        census=read(path.with_suffix('.source.json'))
        # Old admitted proofs required every source issue, including reversed
        # clocks, to be absent. T1 separates clocks without adding an issue
        # predicate; these exact positive proofs retain the same SHACL contract.
        if (census.get('status')!='reconciled' or census.get('issues')!=[]
                or census.get('sourceSha256')!=promotion['rawSha256']
                or census.get('gamePk')!=promotion['gamePk']):
            raise ValueError('Prior clock proof lacks its reconciled source census')
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
    proof=refreshed(state,promotion,family,adapter.fingerprint())
    if proof is not None:
        checked_marker(promotion)
        return proof
    proof=compatible_proof(state,promotion,family,adapter.fingerprint())
    if proof is not None: return proof
    return adapter.promoted_admission(state,promotion)


def refresh_game(state,promotion,java,classpath):
    marker=checked_marker(promotion)
    adapters={family:module(HERE/(family+'-admission.py'),'refresh_'+family.replace('-','_')) for family in FIELDS}
    versions={family:adapter.fingerprint() for family,adapter in adapters.items()}
    diagnostics={family:diagnostic(state,promotion,family,versions[family]) for family in FIELDS}
    pending=[family for family in FIELDS if diagnostics[family]['evidenceState'] not in {'current','implementation-compatible'}
        and refreshed(state,promotion,family,versions[family]) is None]
    result=dict(gamePk=promotion['gamePk'],promotionManifestSha256=promotion['promotionManifestSha256'],
        diagnostics=diagnostics,refreshed=[],rdfChanged=False)
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


def tick(state,java,classpath,limit=100):
    control=Path(state)/'pipeline/control/mlb-game/admission-evidence'
    versions={family:module(HERE/(family+'-admission.py'),'version_'+family.replace('-','_')).fingerprint() for family in FIELDS}
    version=hashlib.sha256(json.dumps(versions,sort_keys=True).encode()+fingerprint().encode()).hexdigest()
    outcomes=[]
    for directory in sorted((Path(state)/'pipeline/evidence/nifi/game-promotion').glob('*')):
        if not directory.is_dir() or not directory.name.isdigit(): continue
        candidates=[(read(path).get('promotedAtUtc',''),path.name,path) for path in directory.glob('*.json')]
        if not candidates: continue
        path=max(candidates)[2];marker=read(path);marker_sha=sha(path)
        destination=control/(directory.name+'.json')
        previous=read(destination) if destination.is_file() else {}
        if (previous.get('promotionManifestSha256')==marker_sha and previous.get('implementationSetSha256')==version
                and previous.get('status') not in {'waiting-for-memory','failed'}):
            continue
        if previous.get('status')=='failed' and previous.get('implementationSetSha256')==version and previous.get('attempts',0)>=2:
            continue
        result=dict(gamePk=directory.name,promotionManifestSha256=marker_sha,implementationSetSha256=version,
            checkedAtUtc=datetime.now(timezone.utc).isoformat(),rdfChanged=False,attempts=previous.get('attempts',0)+1)
        try:
            if marker.get('artifactType')!='baseball-nifi-game-promotion' or str(marker.get('gamePk'))!=directory.name:
                raise ValueError('Unexpected source promotion marker')
            rml_path=retained_manifest(state,marker,directory.name)
            if not rml_path.is_file() or sha(rml_path)!=marker.get('rmlManifestSha256'):
                result.update(status='retained-manifest-unavailable')
            else:
                manifest=read(rml_path)
                promotion=dict(gamePk=directory.name,promotionManifest=str(path),promotionManifestSha256=marker_sha,
                    rawSha256=marker['rawSha256'],authoritativeGraph=marker['authoritativeGraph'],
                    authoritativeRdfSha256=manifest['outputSha256'])
                result.update(refresh_game(state,promotion,java,classpath))
        except (OSError,ValueError,RuntimeError) as error:
            result.update(status='failed',error=str(error))
        atomic(destination,result);outcomes.append(result)
        # Bound JVM work to one game, while inexpensive diagnostics can advance.
        if result.get('refreshed') or len(outcomes)>=limit: break
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
    args=parser.parse_args()
    print(json.dumps(tick(args.state_root,args.java,args.jena_classpath)))
