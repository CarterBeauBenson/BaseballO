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
import urllib.request
from contextlib import closing
from functools import lru_cache

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
RETAINED_CENSUS=module(HERE/'retained-census-admissions.py','retained_census_admissions')


def checked_marker(promotion):
    path=Path(promotion['promotionManifest'])
    if sha(path)!=promotion['promotionManifestSha256']: raise ValueError('Promotion marker changed')
    return read(path)


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()+COMPATIBILITY_PATH.read_bytes()
        +RETAINED_BATTING.fingerprint().encode()+PLAYER_PARTICIPATION.fingerprint().encode()
        +PA_RESOLUTION.fingerprint().encode()
        +(HERE/'existing-graph-admissions.py').read_bytes()+(HERE/'retained-census-admissions.py').read_bytes()).hexdigest()


def selection_repairs(record):
    legacy={'foulPitcherCompletion','runnerReviewCompletion','finalAwardSelection',
        'prePitchBatterChain','errorCountPrefixRepair','foulDefenseSelectionRepair'}
    return [entry for name,entry in reversed(list(record.items())) if isinstance(entry,dict)
        and (name in legacy or entry.get('previousRepair'))]


def code_equivalence(family,previous,current,*,_context=None):
    """Pinned compatible edits, not blanket acceptance of stale proofs.

    The regression compares both exact context revisions and the transitive
    call dependencies. Complete producer fingerprints include every other
    original dependency, SHACL template and validator. Unknown changes miss.
    """
    record=read(COMPATIBILITY_PATH)
    compound=record.get('compoundResultRepair',{})
    groundout=record.get('defensiveGroundoutRepair',{})
    context=_context or sha(ROOT/record['contextPath'])
    missing_result=record.get('missingCountResultHandling',{})
    if (family=='pitch-count' and current==missing_result.get('currentImplementationSha256')
            and context==missing_result.get('contextSha256')):
        prior=missing_result['previousImplementationSha256']
        reused=(dict(kind='unchanged-admission-census') if previous==prior else
            code_equivalence(family,previous,prior,_context=context))
        if reused is not None:
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),
                previousImplementationSha256=previous,currentImplementationSha256=current,
                compatibilityReason='missing result now records existing unknown-result rejection')
    for selection in selection_repairs(record):
        bridge=selection.get('families',{}).get(family)
        if (bridge and context==selection.get('currentContextSha256')
                and current==bridge['currentImplementationSha256']):
            prior=bridge['previousImplementationSha256']
            reused=(dict(kind=bridge['reuseKind']) if previous==prior else
                code_equivalence(family,previous,prior,_context=selection['previousContextSha256']))
            if reused is not None:
                if bridge['reuseKind']!='unchanged-proof-dependencies' and reused['kind'] in {'unchanged-proof-dependencies','unchanged-admission-census'}:
                    reused=dict(reused,kind=bridge['reuseKind'])
                return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),
                    previousImplementationSha256=previous,currentImplementationSha256=current,
                    selectionRepairDecision=selection['decision'])
    foul=record.get('foulPrefixRepair',{})
    bridge=foul.get('families',{}).get(family)
    if (bridge and context==foul.get('currentContextSha256')
            and current==bridge['currentImplementationSha256']):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind='unchanged-admission-census') if previous==prior else
            code_equivalence(family,previous,prior,_context=foul['previousContextSha256']))
        if reused is not None:
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),
                previousImplementationSha256=previous,currentImplementationSha256=current,
                foulPrefixDecision=foul['decision'])
    history=record.get('historySelectionRepair',{})
    bridge=history.get('families',{}).get(family)
    if (bridge and context==history.get('currentContextSha256')
            and current==bridge['currentImplementationSha256']):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind=bridge['reuseKind']) if previous==prior else
            code_equivalence(family,previous,prior,_context=history['previousContextSha256']))
        if reused is not None:
            if bridge['reuseKind']!='unchanged-proof-dependencies' and reused['kind']=='unchanged-proof-dependencies':
                reused=dict(reused,kind=bridge['reuseKind'])
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),
                previousImplementationSha256=previous,currentImplementationSha256=current,
                historySelectionRecord=history['implementationRecord'])
    bridge=groundout.get('families',{}).get(family)
    if (bridge and current==bridge['currentImplementationSha256'] and previous!=current
            and current!=bridge['previousImplementationSha256']
            and context==groundout.get('currentContextSha256')):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind='unchanged-proof-dependencies') if previous==prior
                else code_equivalence(family,previous,prior,_context=context))
        if reused is not None:
            if family=='defensive':reused=dict(reused,kind='prior-stricter-defensive-selection')
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),previousImplementationSha256=previous,
                currentImplementationSha256=current,defensiveSelectionDecision=groundout['decision'])
    bridge=compound.get('families',{}).get(family)
    if (bridge and current==bridge['currentImplementationSha256'] and previous!=current
            and context in {compound.get('currentContextSha256'),groundout.get('currentContextSha256')}):
        prior=bridge['previousImplementationSha256']
        if current!=prior:
            reused=(dict(kind='prior-stricter-compound-result' if family=='batting' else 'unchanged-proof-dependencies')
                    if previous in {prior,*bridge.get('previousImplementationSha256s',[])}
                    else code_equivalence(family,previous,prior,_context=context))
            if reused is not None:
                if family=='batting':reused=dict(reused,kind='prior-stricter-compound-result')
                return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),previousImplementationSha256=previous,
                    currentImplementationSha256=current,compoundResultDecision=compound['decision'])
    context_matches=lambda *values: context in set(values)|{compound.get('currentContextSha256'),groundout.get('currentContextSha256')}
    walk=record.get('intentionalWalkPrefix',{})
    bridge=walk.get('families',{}).get(family)
    if (bridge and bridge['previousImplementationSha256']!=current and current==bridge['currentImplementationSha256']
            and context_matches(walk['currentContextSha256'])):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind='prior-stricter-walk-selection' if family in {'pitch-count','runner-boundary'}
                     else 'unchanged-proof-dependencies') if previous==prior
                else code_equivalence(family,previous,prior,_context=context))
        if reused is not None:
            if family in {'pitch-count','runner-boundary'} and reused['kind']=='unchanged-proof-dependencies':
                reused=dict(reused,kind='prior-stricter-walk-selection')
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),previousImplementationSha256=previous,
                currentImplementationSha256=current,walkSelectionDecision=walk['decision'])
    isolation=record.get('zeroEpisodeIsolation',{})
    bridge=isolation.get('families',{}).get(family)
    if (bridge and current==bridge['currentImplementationSha256']
            and context_matches(isolation['currentContextSha256'],walk.get('currentContextSha256'))):
        prior=bridge['previousImplementationSha256']
        reused=(dict(kind='prior-stricter-history-selection' if family=='runner-boundary' else 'unchanged-proof-dependencies')
                if previous==prior else code_equivalence(family,previous,prior,_context=context))
        if reused is not None:
            return dict(reused,recordSha256=sha(COMPATIBILITY_PATH),previousImplementationSha256=previous,
                currentImplementationSha256=current,viaPreviousImplementationSha256=prior,
                historyIsolationDecision=isolation['decision'])
    entry=record['families'].get(family)
    if (entry and previous==entry['previousImplementationSha256']
            and current==entry['currentImplementationSha256']
            and context_matches(record['currentContextSha256'],isolation.get('currentContextSha256'),walk.get('currentContextSha256'))):
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


def prior_versions(kind,current):
    """Exact retained proofs whose existing checks W1 does not invalidate.

    Keep their original producer and outcomes. A new promotion gets new paths
    and must be checked again; this is never approval of W1's missing facts.
    """
    if kind=='players' and current==PLAYER_PARTICIPATION.fingerprint():
        # Only the interpretation of unrelated run-total diagnostics changed.
        # Keep original B1 graph reports; the owner retries affected negatives.
        previous=PLAYER_PARTICIPATION.PREVIOUS_RUN_SCOPE_IMPLEMENTATION
        return [previous,*prior_versions(kind,previous)]
    if kind=='pa' and current==PLAYER_PARTICIPATION.PA.fingerprint():
        previous=PLAYER_PARTICIPATION.PA.PREVIOUS_SOURCE_SELECTION
        return [previous,*prior_versions(kind,previous)]
    record=read(COMPATIBILITY_PATH)
    for selection in selection_repairs(record):
        entry=selection.get('derivedProofs',{}).get(kind,{})
        if (entry.get('currentImplementationSha256')==current
                and sha(ROOT/record['contextPath'])==selection.get('currentContextSha256')):
            return entry['previousImplementationSha256s']
    foul=record.get('foulPrefixRepair',{})
    entry=foul.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==foul.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    history=record.get('historySelectionRepair',{})
    entry=history.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==history.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    selection=record.get('retainedCompoundExpectations',{})
    entry=selection.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==selection.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    walk=record.get('defensiveGroundoutRepair',{})
    entry=walk.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==walk.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    walk=record.get('compoundResultRepair',{})
    entry=walk.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==walk.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    walk=record.get('intentionalWalkPrefix',{})
    entry=walk.get('derivedProofs',{}).get(kind,{})
    if (entry.get('currentImplementationSha256')==current
            and sha(ROOT/record['contextPath'])==walk.get('currentContextSha256')):
        return entry['previousImplementationSha256s']
    return []


def compatible_proof(state,promotion,family,implementation):
    marker=checked_marker(promotion);field=FIELDS[family];path=Path(marker.get(field,''))
    if not path.is_file(): return None
    if not path.resolve().is_relative_to((Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']).resolve()):
        raise ValueError('Proof escaped its owning source game')
    if sha(path)!=marker.get(field+'Sha256'): raise ValueError('Retained proof changed')
    proof=read(path)
    reuse=code_equivalence(family,proof.get('implementationSha256'),implementation)
    if reuse is None: return None
    positive_only=reuse['kind'] in {'prior-stricter-clock-check','prior-stricter-pinch-hitter-check','prior-stricter-history-selection','prior-stricter-walk-selection','prior-stricter-compound-result','prior-stricter-defensive-selection'}
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
        if reuse['kind']=='prior-stricter-compound-result' and any(
                row.get('eventType')=='strikeout_double_play' for row in census.get('members',[])):
            return None  # The changed classification needs its own current check.
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
    retained=RETAINED_CENSUS.load(SimpleNamespace(**globals()),state,promotion,family,adapter)
    if retained is not None and (independent is None or independent.get('status')!='admitted'):independent=retained
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
    bridge=read(COMPATIBILITY_PATH).get('intentionalWalkPrefix',{}).get('families',{}).get(family,{})
    prior=bridge.get('previousImplementationSha256')
    reuse=code_equivalence(family,prior,adapter.fingerprint()) if prior and prior!=adapter.fingerprint() else None
    if reuse:
        proof=refreshed(state,promotion,family,prior)
        if proof is not None and (reuse['kind'] in {'unchanged-proof-dependencies','unchanged-admission-census'} or proof.get('status')=='admitted'):
            checked_marker(promotion)
            return select(dict(proof,implementationReuse=reuse))
    proof=compatible_proof(state,promotion,family,adapter.fingerprint())
    if proof is not None: return select(proof)
    return select(adapter.promoted_admission(state,promotion))


def player_admission(state,promotion):
    api=SimpleNamespace(**globals())
    individual=PLAYER_PARTICIPATION.load(api,state,promotion)
    resolution=PA_RESOLUTION.load(api,state,promotion)
    return dict(individual or {},paResolutions=resolution) if resolution else individual


@lru_cache(maxsize=1)
def retained_sample_paths():
    result={}
    for path in sorted((ROOT/'data/raw').rglob('*.json')):
        if path.stem.isdecimal():result.setdefault(path.stem,[]).append(path)
    return result


def retained_raw_witness(state,promotion):
    """A retained response is an independent witness, never a new acquisition."""
    paths=[*sorted((Path(state)/'pipeline/quarantine/mlb-game'/promotion['gamePk']).glob('*/input.json')),
           *retained_sample_paths().get(promotion['gamePk'],[])]
    candidates=[dict(kind='retained-source-response',path=str(path),sha256=sha(path)) for path in paths]
    return min(candidates,key=lambda row:(row['sha256']!=promotion['rawSha256'],row['path'])) if candidates else None


def existing_graph_refresh_needed(state,promotion):
    """Use the existing proof loaders before reserving another graph/JVM.

    This is the same skip condition as EXISTING_GRAPH.validate; current
    conclusive negative results stay negative and need no repeated execution.
    """
    api=SimpleNamespace(**globals())
    for family in EXISTING_GRAPH.SHORT:
        adapter=module(HERE/(family+'-admission.py'),'pending_'+family.replace('-','_'))
        if (load(adapter,state,promotion,family).get('status')!='admitted'
                and EXISTING_GRAPH.load(api,state,promotion,family,adapter) is None):
            return True
    return False


def refresh_existing_graph(state,promotion,witness,java,classpath,endpoint):
    """Run the existing six profiles without requiring a retired RDF export.

    The independent-check producer retains its unchanged fingerprints and
    source/graph provenance. Original proofs are not edited or upgraded.
    """
    inventory=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','independent_refresh_inventory')
    marker_path=Path(promotion['promotionManifest'])
    def current():
        latest=max(marker_path.parent.glob('*.json'),key=lambda p:(read(p).get('promotedAtUtc',''),p.name))
        if latest!=marker_path or sha(latest)!=promotion['promotionManifestSha256']:
            raise ValueError('Promotion changed during existing-graph refresh')
        record=inventory.validated_promotion_record(Path(state),latest,promotion['gamePk'],inventory.query_index_contract_admission())
        if any(record[k]!=promotion[k] for k in ('rawSha256','authoritativeRdfSha256','authoritativeGraph','authoritativeTripleCount')):
            raise ValueError('Existing-graph refresh belongs to another promotion')
        return record
    record=current()
    if witness.get('kind')!='retained-census-set':
        if sha(Path(witness['path']))!=witness['sha256']:
            raise ValueError('Retained source response changed')
        if not existing_graph_refresh_needed(state,promotion):return []
    query='CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <'+record['authoritativeGraph']+'> { ?s ?p ?o } }'
    request=urllib.request.Request(endpoint,data=query.encode(),headers={
        'Content-Type':'application/sparql-query','Accept':'text/turtle'})
    jena=module(ROOT/'scripts/pipeline/jena_session.py','independent_refresh_jena')
    api=SimpleNamespace(**globals())
    with tempfile.TemporaryDirectory(prefix='admission-existing-graph-') as temporary:
        rdf=Path(temporary)/'graph.ttl'
        with urllib.request.urlopen(request,timeout=120) as response,rdf.open('wb') as stream:
            size=0
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>128*1024*1024:raise ValueError('Single-game admission graph exceeds its read bound')
                stream.write(chunk)
        with jena.Session(rdf,java,classpath) as session:
            if session.data_count!=record['authoritativeTripleCount']:
                raise ValueError('Existing graph count differs from its promotion')
            validator=RETAINED_CENSUS if witness.get('kind')=='retained-census-set' else EXISTING_GRAPH
            payload=witness['families'] if validator is RETAINED_CENSUS else witness
            results=validator.validate(api,state,promotion,payload,rdf,session,java,classpath)
    current()
    EXISTING_GRAPH.commit(api,promotion,results)
    return results


def corrected_player_source(api,state,promotion,individual):
    """Feed an already reconciled B1 census into the existing player check.

    A whole-game B1 graph failure can coexist with a resolved source issue for
    one player. Reuse that source reconciliation, not the whole-game admission
    outcome. The unchanged player SHACL still decides each player's result.
    """
    if not individual or not any(i.get('code')=='OFFENSIVE_REPLACEMENT_WITHIN_TURN'
            for person in individual.get('players',[]) for i in person.get('issues',[])):
        return None
    proof=RETAINED_BATTING.load(api,state,promotion)
    if proof is None:return None
    source_path=refresh_path(state,promotion,'batting',proof['implementationSha256']).with_suffix('.source.json')
    source_sha=sha(source_path)
    if source_sha!=proof.get('sourceCensusSha256'):
        raise ValueError('Reconciled batting census changed before player validation')
    if individual.get('retainedSourceEvidence',{}).get('sha256')==source_sha:
        return None  # This exact source has already reached the player check.
    source=read(source_path)
    return PLAYER_PARTICIPATION.compound_expectations(source),dict(
        kind='retained-b1-census',path=str(source_path),sha256=source_sha,
        battingRepairProofSha256=proof['proofSha256'])


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
    corrected=(corrected_player_source(api,state,promotion,individual)
               if batting.get('status')!='admitted' else None)
    if ((batting.get('status')!='admitted' or boundary.get('status')!='admitted')
            and (individual is None or individual.get('implementationSha256') not in
                 [PLAYER_PARTICIPATION.fingerprint(),*prior_versions('players',PLAYER_PARTICIPATION.fingerprint())]
                 or PLAYER_PARTICIPATION.PA.needs_overlap_refresh((individual or {}).get('paBoundaries'))
                 or PLAYER_PARTICIPATION.PA.needs_source_refresh(api,state,promotion,(individual or {}).get('paBoundaries'))
                 or PLAYER_PARTICIPATION.needs_compound_refresh(individual)
                 or corrected is not None)):
        retained=corrected or PLAYER_PARTICIPATION.retained_source(api,state,promotion)
        if retained is not None:
            checkpoint=Path(state)/'pipeline/control/mlb-game/admission-evidence'/(promotion['gamePk']+'.json')
            prior=read(checkpoint) if checkpoint.is_file() else {}
            failure=prior.get('familyFailures',{}).get('player-participation',{})
            identity=dict(promotionManifestSha256=promotion['promotionManifestSha256'],
                implementationSha256=PLAYER_PARTICIPATION.fingerprint(),sourceWitness=retained[1])
            roster_error='A complete unambiguous roster is required'
            if not (failure.get('error')==roster_error and all(failure.get(k)==v for k,v in identity.items())):
                memory=module(ROOT/'scripts/pipeline/process_state.py','participation_memory').available_memory()
                if memory is not None and memory<1024*1024*1024:
                    return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
                try:
                    proof=PLAYER_PARTICIPATION.prove(api,state,promotion,retained,java,classpath,endpoint)
                except ValueError as error:
                    if str(error)!=roster_error:raise
                    failure=dict(identity,error=str(error),checkedAtUtc=datetime.now(timezone.utc).isoformat())
                else:
                    return dict(result,status='partial-refreshed',refreshed=['player-participation'],
                        rosterComplete=proof['rosterComplete'],admittedPlayers=sum(p['status']=='admitted' for p in proof['players']))
            # Preserve the owner's refusal, bound to its exact inputs. It is
            # not an admission proof and cannot suppress independent families.
            result['familyFailures']={'player-participation':failure}
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
    # Independently checking the other profiles must not depend on whether a
    # player's batting check happened to need a raw witness. A completed check
    # (including a withheld one) needs no retry for the same graph and producer.
    unchecked=[family for family,adapter in adapters.items()
        if load(adapter,state,promotion,family).get('status')!='admitted'
        and EXISTING_GRAPH.load(api,state,promotion,family,adapter) is None
        and RETAINED_CENSUS.load(api,state,promotion,family,adapter) is None]
    if not unchecked:return dict(result,status='partial' if result.get('familyFailures') else 'current')
    witness=retained_raw_witness(state,promotion)
    if witness is None:
        censuses={family:value for family in unchecked
                  if (value:=RETAINED_CENSUS.source(api,state,promotion,family,adapters[family])) is not None}
        if censuses:witness=dict(kind='retained-census-set',families=censuses)
    if witness is not None:
        memory=module(ROOT/'scripts/pipeline/process_state.py','independent_refresh_memory').available_memory()
        if memory is not None and memory<1024*1024*1024:
            return dict(result,status='waiting-for-memory',availableMemoryBytes=memory)
        checked=refresh_existing_graph(state,promotion,witness,java,classpath,endpoint)
        return dict(result,status='refreshed',refreshed=[family for _,family,_ in checked],
            existingGraphOutcomes={family:status for _,family,status in checked})
    if not pending: return dict(result,status='partial' if result.get('familyFailures') else 'current')
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
        player_versions={player_version,*prior_versions('players',player_version)}
        priority={r[0]:3 for r in connection.execute("SELECT game_pk FROM game_dimension WHERE game_set='regular_season' "
            "AND season=(SELECT max(season) FROM game_dimension WHERE game_set='regular_season')")}
        for pk,batting,individual,substitution in connection.execute('''SELECT g.game_pk,
                json_extract(b.proof_json,'$.status'),json_extract(a.proof_json,'$.implementationSha256'),
                instr(a.proof_json,'OFFENSIVE_REPLACEMENT_WITHIN_TURN')>0
                FROM game_dimension g LEFT JOIN metric_suite_admission b USING(graph_iri)
                LEFT JOIN dashboard_player_admission a USING(graph_iri)
                WHERE g.game_set='regular_season' '''):
            if pk in priority and batting!='admitted' and (individual not in player_versions or substitution):priority[pk]=1
        for pk, in connection.execute('''SELECT g.game_pk FROM game_dimension g
                JOIN metric_suite_runner_resolution_admission r USING(graph_iri)
                WHERE g.game_set='regular_season' AND json_extract(r.proof_json,'$.status')!='admitted' '''):
            if pk in priority:priority[pk]=min(priority[pk],2)
        for pk, in connection.execute("SELECT game_pk FROM game_dimension g LEFT JOIN dashboard_player_game p USING(graph_iri) "
                "WHERE game_set='regular_season' GROUP BY g.graph_iri HAVING MAX(COALESCE(p.roster_complete,0))=0"):
            if pk in priority:priority[pk]=0
        return priority


def preserve_interrupted_refresh(state,promotion,previous):
    """Retain a damaged receipt/proof set before the owner validates anew.

    Only the recorded receipt mismatch for this promotion enters recovery.
    Nothing here admits a proof or changes source bytes, semantic pins or RDF.
    The NiFi wrapper holds the same lease as targeted repair evidence writers.
    """
    if (previous.get('error')!='Existing graph admission receipt changed'
            or previous.get('promotionManifestSha256')!=promotion['promotionManifestSha256']):
        return []
    owner=(Path(state)/'pipeline/evidence/mlb-game'/promotion['gamePk']/'admission-refresh').resolve()
    recovered=[]
    for directory in sorted(owner.glob(promotion['promotionManifestSha256']+'-*')):
        if not directory.is_dir() or directory.resolve().parent!=owner:
            raise ValueError('Interrupted admission evidence escapes its game')
        mismatches=[]
        for receipt in directory.glob('*.receipt.json'):
            proof=receipt.with_name(receipt.name.replace('.receipt.json','.json'))
            record=read(receipt);actual=sha(proof) if proof.is_file() else None
            if (record.get('promotionManifestSha256')!=promotion['promotionManifestSha256']
                    or record.get('proofSha256')!=actual):
                mismatches.append(dict(receipt=receipt.name,expectedProofSha256=record.get('proofSha256'),
                                       actualProofSha256=actual))
        if not mismatches:continue
        files={p.name:sha(p) for p in directory.iterdir() if p.is_file()}
        identity=hashlib.sha256(json.dumps(dict(directory=directory.name,files=files),sort_keys=True).encode()).hexdigest()
        destination=owner/'interrupted'/identity
        if not destination.resolve().is_relative_to(owner) or destination.exists():
            raise ValueError('Interrupted admission archive already exists or escapes its owner')
        # Write the recovery intent first. The directory rename preserves all
        # original bytes atomically, including the mismatched receipt itself.
        atomic(destination.with_suffix('.json'),dict(originalDirectory=str(directory),
            preservedDirectory=str(destination),promotionManifestSha256=promotion['promotionManifestSha256'],
            files=files,mismatches=mismatches,rdfChanged=False))
        directory.rename(destination)
        recovered.append(str(destination))
    return recovered


def tick(state,java,classpath,limit=100,endpoint='http://127.0.0.1:3031/baseball-dev/query'):
    excluded=module(HERE/'work_scope.py','admission_work_scope').excluded_games(state)
    control=Path(state)/'pipeline/control/mlb-game/admission-evidence'
    versions={family:module(HERE/(family+'-admission.py'),'version_'+family.replace('-','_')).fingerprint() for family in FIELDS}
    version=hashlib.sha256(json.dumps(versions,sort_keys=True).encode()+fingerprint().encode()).hexdigest()
    outcomes=[];started=time.monotonic();refreshed_games=0
    priority=dashboard_game_priorities(state)
    # A previous failure gets its bounded retry before successful maintenance
    # is revisited after an engineering fingerprint change.
    failed={p.stem for p in control.glob('*.json') if read(p).get('status')=='failed'}
    for directory in sorted((Path(state)/'pipeline/evidence/nifi/game-promotion').glob('*'),
            key=lambda p:(p.name not in failed,priority.get(p.name,3),p.name)):
        if not directory.is_dir() or not directory.name.isdigit() or directory.name in excluded: continue
        candidates=[(read(path).get('promotedAtUtc',''),path.name,path) for path in directory.glob('*.json')]
        if not candidates: continue
        path=max(candidates)[2];marker=read(path);marker_sha=sha(path)
        destination=control/(directory.name+'.json')
        previous=read(destination) if destination.is_file() else {}
        same_input=(previous.get('promotionManifestSha256')==marker_sha
                    and previous.get('implementationSetSha256')==version)
        # A successful stage can supply the next stage's retained census.
        # Revisit it on the next bounded tick; only current/unavailable results
        # finish this input. The stage loaders reuse already completed checks.
        if same_input and previous.get('status') not in {'waiting-for-memory','failed','partial-refreshed','refreshed'}:
            continue
        failures=previous.get('failureAttempts',previous.get('attempts',0) if previous.get('status')=='failed' else 0) if same_input else 0
        if failures>=2:
            continue
        result=dict(gamePk=directory.name,promotionManifestSha256=marker_sha,implementationSetSha256=version,
            checkedAtUtc=datetime.now(timezone.utc).isoformat(),rdfChanged=False,
            attempts=(previous.get('attempts',0) if same_input else 0)+1,failureAttempts=failures)
        try:
            if marker.get('artifactType')!='baseball-nifi-game-promotion' or str(marker.get('gamePk'))!=directory.name:
                raise ValueError('Unexpected source promotion marker')
            inventory=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','admission_inventory')
            promotion=inventory.validated_promotion_record(Path(state),path,directory.name,inventory.query_index_contract_admission())
            preserved=preserve_interrupted_refresh(state,promotion,previous)
            if preserved:result['preservedInterruptedEvidence']=preserved
            result.update(refresh_game(state,promotion,java,classpath,endpoint))
            if result['status']!='waiting-for-memory':result['failureAttempts']=0
        except (OSError,ValueError,RuntimeError) as error:
            result.update(status='failed',error=str(error),failureAttempts=failures+1)
        atomic(destination,result);outcomes.append(result)
        # Serial, bounded games share the existing one-minute owner schedule.
        # Finish the current game, then yield; no parallel JVM/heap accumulation.
        refreshed_games+=bool(result.get('refreshed'))
        # Below the smallest existing JVM reservation, inspecting another game
        # cannot start validation. Yield to NiFi instead of repeatedly loading
        # and hashing dozens of games only to defer them all. The larger
        # raw-input refresh reservation can still defer while a smaller check
        # later in the queue makes progress.
        if (result.get('status')=='waiting-for-memory'
                and result.get('availableMemoryBytes',1024*1024*1024)<1024*1024*1024):break
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
