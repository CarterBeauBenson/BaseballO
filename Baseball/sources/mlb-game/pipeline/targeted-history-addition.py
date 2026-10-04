"""NiFi-owned Q7 addition from retained source evidence, never a game remap.

Reuse three existing RML maps and the source's SHACL profiles. The authoritative
write is an additive Graph Store POST. The existing graph-pair transaction owns
crash recovery; only the affected game's derived query index is replaced.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace
import urllib.request
import uuid

import rdflib
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

# This stage exports an existing graph, not new source values. RDF term
# identity includes lexical forms; preserve Z, integer spelling, and so on.
rdflib.NORMALIZE_LITERALS = False

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DECISION = 'archive/design-records/mlb-game-zero-episode-history-isolation/review.json'
PACKAGE = ROOT / Path(DECISION).parent
MAPPING = HERE.parent / 'mapping/mlb-game.rml.ttl'
MAPS = ('PersonalRunnerProcessMap', 'PersonalRunnerIntervalMap', 'PersonalRunnerMembershipMap')
COMPLETION = HERE / 'history-completion-candidates.json'
SELECTION = HERE / 'history-selection-candidates.json'
SUCCESS = {'complete', 'already-complete', 'already-present', 'evidence-refreshed'}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


TX = module(ROOT / 'scripts/pipeline/graph-pair-transaction.py', 'q7_transaction')
I = module(ROOT / 'scripts/pipeline/game_promotion_inventory.py', 'q7_inventory')
H = module(HERE / 'runner-history-admission.py', 'q7_history')
V = module(HERE / 'verify-runner-history-serialization.py', 'q7_serialization')
J = module(ROOT / 'scripts/pipeline/jena_session.py', 'q7_jena')
EVENT = module(ROOT / 'scripts/pipeline/emit-promoted-graph-event.py', 'q7_event')
DISCOVERY = module(HERE / 'history-repair-discovery.py', 'history_repair_discovery')
MEMORY = module(ROOT / 'scripts/pipeline/process_state.py', 'history_memory')
LOCK = module(ROOT / 'scripts/pipeline/process_lock.py', 'history_lock')
sha = I.sha256_file
read = TX.read
atomic = TX.atomic_json


def select_history(manifest, case, raw=None):
    original = manifest['runnerHistoryReconciliation']
    inputs={case['inputSha256'],case.get('sourceSha256',case['inputSha256'])}
    if original['inputSha256'] not in inputs or original['sourceConsistency'] != 'consistent':
        raise ValueError('Q7 retained history belongs to another or inconsistent input')
    if case.get('selectionRepair') in {'H2','H3'}:
        if raw is None or hashlib.sha256(raw).hexdigest() != case.get('sourceSha256',case['inputSha256']):
            raise ValueError('History repair requires the exact inventoried response')
        history = H.CONTEXT.personal_runner_histories(raw, previous=original)
    else:
        history = H.CONTEXT.isolate_zero_episode_histories(copy.deepcopy(original))
    previous = {h['lifetimeKey'] for h in original['histories']}
    # A later additive promotion may already contain some of this exact named
    # selection. Retain its scope and compare mapped triples with the live base
    # below; membership in a newer manifest is not a mapping failure.
    if 'selectedHistoryKeys' in case:
        named=set(case['selectedHistoryKeys'])
        selected=[h for h in history['histories'] if h['lifetimeKey'] in named]
    else:
        selected=[h for h in history['histories'] if h['lifetimeKey'] not in previous]
    halves = {(int(h['inning']), h['half']) for h in case.get('halves', [case])}
    if 'selectedHistoryKeys' in case and {h['lifetimeKey'] for h in selected} != set(case['selectedHistoryKeys']):
        raise ValueError('Q7 completion differs from the inventoried histories')
    if not selected or any((int(h['inning']), h['half']) not in halves for h in selected):
        raise ValueError('Q7 addition differs from the approved half-inning scope')
    if case.get('selectionRepair') != 'H3' and any(h.get('placement') or h.get('gameEndInstantIri') for h in selected):
        raise ValueError('Q7 named repairs require only the three personal-history maps')
    for expected in case.get('scoringCandidates', []):
        if expected not in selected:
            raise ValueError('Q7 approved scoring history changed')
    keys = {h['lifetimeKey'] for h in selected}
    delta = dict(inputSha256=history['inputSha256'], histories=selected,
        episodeMembership=[e for e in history['episodeMembership'] if e['lifetimeKey'] in keys],
        placementAdjudications=[r for r in history.get('placementAdjudications',[]) if r['lifetimeKey'] in keys])
    return history, delta


def history_maps(delta_context):
    maps=list(MAPS)
    if delta_context['placementAdjudications']:
        maps.extend('RunnerPlacement'+name+'Map' for name in ('Judgment','Membership','Decision','Base','BaseIdentifier','Rule','Record'))
    if any(h.get('gameEndInstantIri') for h in delta_context['histories']):
        maps.append('PersonalRunnerGameEndIntervalMap')
    return tuple(maps)


def subset_mapping(game_pk, destination, maps=MAPS):
    """Slice existing map descriptions without authoring new predicates."""
    full = Graph().parse(MAPPING, format='turtle')
    selected = Graph()
    logical_source = URIRef('http://semweb.mmlab.be/ns/rml#logicalSource')
    for prefix, namespace in full.namespaces():
        selected.bind(prefix, namespace)
    for name in maps:
        matches = [s for s in set(full.subjects()) if str(s).endswith('#' + name)]
        if len(matches) != 1:
            raise ValueError('Existing RML map is not unique: ' + name)
        pending, visited = [matches[0]], set()
        while pending:
            subject = pending.pop()
            if subject in visited:
                continue
            visited.add(subject)
            for s, p, o in full.triples((subject, None, None)):
                value = Literal(str(o).replace('{$.gamePk}', game_pk), datatype=o.datatype, lang=o.language) if isinstance(o, Literal) else o
                selected.add((s, p, value))
                if isinstance(o, BNode) or p == logical_source:
                    pending.append(o)
    selected.serialize(destination=destination, format='turtle')


def command(args, cwd, log):
    with log.open('wb') as output:
        result = subprocess.run([str(a) for a in args], cwd=cwd, stdout=output,
            stderr=subprocess.STDOUT, timeout=1200)
    if result.returncode:
        raise RuntimeError('Stage failed; see ' + str(log))


def retain_source_binding(proof, marker, field):
    """Keep D1's separately evidenced source attached through later additions.

    The caller first verifies the exact proof hash in the current promotion.
    A targeted defensive census can use a different retained response from
    the game's original ingest. Its original receipt binds both identities;
    neither hash is rewritten to pretend the responses were identical.
    """
    if proof.get('sourceSha256') == marker['rawSha256']:
        return
    receipt = proof.get('sourceRevalidation', proof.get('graphRevalidation', {}))
    if (field in {'runnerHistoryAdmission','runnerResolutionAdmission'}
            and receipt.get('decision') == 'archive/design-records/metric-source-c1-operation-2026-09-14/review.json'
            and receipt.get('mode') == 'current-history-source-census'
            and receipt.get('promotionSourceSha256') == marker['rawSha256']
            and receipt.get('sourceSha256') == proof.get('sourceSha256')
            and receipt.get('originalProofSha256')):
        proof['sourceRevalidation'] = dict(receipt)
        return
    if (field != 'defensiveAdmission'
            or receipt.get('decision') != 'archive/design-records/mlb-game-defensive-acts/review.json'
            or receipt.get('mode') != 'current-defensive-source-census'
            or receipt.get('promotionSourceSha256') != marker['rawSha256']):
        raise ValueError('Retained admission belongs to an unbound source: ' + field)
    if not receipt.get('originalProofSha256'):
        # The first D1 proof has no predecessor. Its owning promotion binds
        # the separately retained input; preserve that actual first proof as
        # the origin for subsequent additions instead of requiring a fiction.
        addition=marker.get('targetedAddition',{});witness=addition.get('sourceWitness',{})
        prior=Path(marker.get(field,''))
        if (addition.get('decision')!=receipt['decision']
                or proof.get('gamePk')!=marker.get('gamePk') or not proof.get('gamePk')
                or witness.get('gamePk')!=marker['gamePk']
                or witness.get('sha256')!=proof.get('sourceSha256')
                or not prior.is_file() or sha(prior)!=marker.get(field+'Sha256')
                or read(prior)!=proof):
            raise ValueError('Retained admission belongs to an unbound source: ' + field)
        receipt=dict(receipt,originalProofSha256=sha(prior),
            originalProofKind='first-defensive-admission',sourceWitness=witness)
    proof['sourceRevalidation'] = dict(receipt)


def unchanged_unrelated_resolution_issues(previous, current, selected_histories):
    """Route an existing source rejection without turning it into an admission."""
    selected_pas={str(e['atBatIndex']) for h in selected_histories or [] for e in h.get('episodes',[])}
    issues=current.get('issues',[])
    return bool(selected_pas and previous.get('status')==current.get('status')=='withheld'
        and previous.get('sourceReconciled') is False and current.get('sourceReconciled') is False
        and issues and previous.get('issues')==issues
        and all(i.get('atBatIndex') is not None and str(i['atBatIndex']) not in selected_pas for i in issues))


def revalidate(marker, manifest, history, rdf, evidence, java, classpath, delta=None, source_raw=None,
               selected_histories=None):
    """Recheck retained source contracts; never rerun acquisition or source mapping.

    Unchanged censuses keep their original producer identity. A separate receipt
    records this graph revalidation. Previously withheld populations stay so.
    """
    output_fields = {}
    with J.Session(rdf, java, classpath, max_heap='384m') as session:
        def validate(shape, report):
            conforms, graph, _ = session.validate_with_jena(data_path=rdf, shape_path=shape,
                java=java, classpath=classpath, max_heap='384m')
            graph.serialize(destination=report, format='turtle')
            return conforms

        shape = HERE.parent / 'shacl/authoritative.ttl'
        if delta is not None:
            # Reuse the existing additive worker's target scoping. The shapes
            # still query the complete base plus addition, including dependencies.
            addition = module(HERE / 'targeted-award-addition.py', 'q7_scoped_shapes')
            shape = evidence / 'authoritative-scoped.shapes.ttl'
            addition.authoritative_scope(Graph().parse(rdf), set(delta.subjects()) | set(delta.objects())).serialize(
                destination=shape, format='turtle')
        if not validate(shape, evidence / 'authoritative.report.ttl'):
            raise ValueError('Q7 resulting graph failed the existing authoritative SHACL')
        for field, value in marker.items():
            if not field.endswith('Admission'):
                continue
            prior = Path(value)
            if sha(prior) != marker[field + 'Sha256']:
                raise ValueError('Retained admission changed: ' + field)
            proof = read(prior)
            retain_source_binding(proof, marker, field)
            if proof['authoritativeRdfSha256'] != manifest['outputSha256']:
                raise ValueError('Retained admission does not describe the approved base')
            if source_raw is not None and field in {'runnerHistoryAdmission', 'runnerResolutionAdmission'}:
                # These source censuses actually change in H2. Generate them
                # anew below; never stamp the old withheld result as current.
                continue
            target = evidence / prior.name
            for suffix, key in (('.source.json', 'sourceCensusSha256'),
                                ('.shapes.ttl', 'shapeSha256'), ('.report.ttl', 'reportSha256')):
                if key in proof:
                    source = prior.with_suffix(suffix)
                    if sha(source) != proof[key]:
                        raise ValueError('Retained admission artifact changed: ' + key)
                    target.with_suffix(suffix).write_bytes(source.read_bytes())
            if field == 'runnerHistoryAdmission':
                census_path = target.with_suffix('.source.json')
                census = read(census_path)
                census['history'] = history
                census['retainedSourceEvidence'] = dict(originalCensusSha256=proof['sourceCensusSha256'],
                    rmlManifestSha256=marker['rmlManifestSha256'], decision=DECISION)
                atomic(census_path, census)
                target.with_suffix('.shapes.ttl').write_text(H.shape_text(census), encoding='utf-8', newline='\n')
                proof.update(selectedHistories=len(history['histories']),
                    sourceCensusSha256=sha(census_path),
                    shapeSha256=sha(target.with_suffix('.shapes.ttl')))
            if 'shapeSha256' in proof:
                conforms = validate(target.with_suffix('.shapes.ttl'), target.with_suffix('.report.ttl'))
                if not conforms and (field == 'runnerHistoryAdmission' or proof.get('graphConforms') is True):
                    raise ValueError('Q7 changed an existing admitted graph contract: ' + field)
                proof['graphConforms'] = conforms
                proof['reportSha256'] = sha(target.with_suffix('.report.ttl'))
            proof.update(authoritativeRdfSha256=sha(rdf),
                graphRevalidation=dict(decision=DECISION, originalProofSha256=sha(prior),
                    implementationSha256=sha(Path(__file__)), checkedAtUtc=TX.now(),
                    mode='q7-retained-history-selection' if field == 'runnerHistoryAdmission'
                         else 'unchanged-source-census',
                    graphChecked='shapeSha256' in proof))
            # Source-level rejection is still a rejection, including when no
            # shape was generated. Do not turn partial histories into a full
            # half-inning or game population approval.
            atomic(target, proof)
            output_fields[field] = str(target)
            output_fields[field + 'Sha256'] = sha(target)
    if source_raw is not None:
        resolution = module(HERE / 'runner-resolution-admission.py', 'h2_resolution')
        for field, adapter, filename in (('runnerHistoryAdmission', H, 'runner-history-admission.json'),
                                        ('runnerResolutionAdmission', resolution, 'runner-resolution-admission.json')):
            output = evidence / filename
            proof = adapter.prove(raw=source_raw, game_pk=marker['gamePk'], rdf_path=rdf,
                                  output=output, java=java, classpath=classpath)
            if not proof.get('graphConforms'):
                prior=Path(marker.get(field,''))
                if (field!='runnerResolutionAdmission' or not prior.is_file()
                        or sha(prior)!=marker.get(field+'Sha256')
                        or not unchanged_unrelated_resolution_issues(read(prior),proof,selected_histories)):
                    raise ValueError('H2 current source census failed graph conformance: ' + field)
                # Authoritative and selected-history SHACL passed above. This
                # unchanged source rejection is outside that selected scope;
                # keep the full runner-resolution population withheld.
                proof['partialRepairIsolation']=dict(originalProofSha256=sha(prior),
                    selectedPlateAppearances=sorted({str(e['atBatIndex'])
                        for h in selected_histories for e in h['episodes']}),
                    reason='unchanged-source-issues-outside-selected-histories')
                atomic(output,proof)
            if proof.get('sourceSha256') != marker['rawSha256']:
                proof['sourceRevalidation'] = dict(
                    decision='archive/design-records/metric-source-c1-operation-2026-09-14/review.json',
                    mode='current-history-source-census',promotionSourceSha256=marker['rawSha256'],
                    sourceSha256=proof['sourceSha256'],originalProofSha256=marker[field+'Sha256'])
                atomic(output,proof)
            output_fields[field] = str(output)
            output_fields[field + 'Sha256'] = sha(output)
    return output_fields


def acquire_selection_source(state, case):
    """Use only inventoried responses; copy immutable samples before execution."""
    inventory = read(SELECTION)
    if sha(ROOT / 'scripts/pipeline/prepare-rml-context.py') != inventory['contextBuilderSha256']:
        raise ValueError('H2 context differs from the prepared repair')
    game_pk = case['gamePk']
    if case.get('discovered'):
        witness=case['sourceWitness'];source=Path(witness['path'])
        owner=(state/'pipeline/quarantine/mlb-game'/game_pk).resolve()
        if (source.name!='input.json' or source.parent.parent.resolve()!=owner
                or not source.parent.name.startswith('targeted-history-')
                or not source.is_file() or sha(source)!=case['sourceSha256']
                or witness['sha256']!=case['sourceSha256']
                or sha(Path(case['repairRequest']))!=case['repairRequestSha256']):
            raise ValueError('Discovered history witness differs from its recorded scope')
        return witness
    directory = state / 'pipeline/quarantine/mlb-game' / game_pk / 'targeted-h2'
    source = directory / 'input.json'; receipt = directory / 'acquisition.json'
    if receipt.is_file():
        witness = read(receipt)
        if not source.is_file() or sha(source) != witness['sha256'] or witness['sha256'] != case.get('sourceSha256',case['inputSha256']):
            raise ValueError('H2 retained response differs from its receipt')
        return witness
    directory.mkdir(parents=True, exist_ok=True)
    url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    if not source.is_file() and case.get('retainedSource'):
        retained=(ROOT/case['retainedSource']).resolve()
        if not retained.is_relative_to((ROOT/'data/raw').resolve()):
            raise ValueError('History repair witness escapes immutable source samples')
        if sha(retained) != case['sourceSha256']:
            raise ValueError('History repair retained source changed')
        source.write_bytes(retained.read_bytes())
    if not source.is_file():
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=60) as response:
            raw = response.read()
        source.write_bytes(raw)
    # Keep a changed response quarantined with its true hash. Do not retry by
    # overwriting it or reinterpret its rows against the old episode identities.
    witness = dict(kind='retained-response-copy' if case.get('retainedSource') else 'targeted-reacquisition', gamePk=game_pk, path=str(source), sha256=sha(source),
        url=url, acquiredAtUtc=TX.now(), scopeDecision=inventory['scopeDecision'],
        implementationRecord=inventory['implementationRecord'])
    atomic(receipt, witness)
    if witness['sha256'] != case.get('sourceSha256',case['inputSha256']) or str(read(source).get('gamePk')) != game_pk:
        raise ValueError('H2 response differs from the original hash-bound input; retained for diagnosis')
    return witness


def finish_selection(state,case,promoted,java,classpath):
    """Resume post-promotion evidence/cleanup after interruption without another add."""
    marker=read(promoted);witness=marker.get('targetedAddition',{}).get('sourceWitness')
    if not witness:
        EVENT.emit(state,promoted);return
    game_pk=case['gamePk'];source=Path(witness['path'])
    owned=(Path(case['sourceWitness']['path']) if case.get('discovered') else
           state/'pipeline/quarantine/mlb-game'/game_pk/'targeted-h2/input.json')
    owner=(state/'pipeline/quarantine/mlb-game'/game_pk).resolve()
    if owned.name!='input.json' or owned.parent.parent.resolve()!=owner:
        raise ValueError('History repair cleanup escapes its source game')
    if source.resolve()!=owned.resolve():raise ValueError('History repair cleanup escapes its owned input')
    evidence=state/'pipeline/evidence/mlb-game'/game_pk/marker['pipelineRunId']
    cleanup=evidence/'cleanup.json'
    if cleanup.is_file():
        receipt=read(cleanup)
        if receipt.get('sourceWitness')!=witness or receipt.get('promotionEvidence')!=str(promoted):
            raise ValueError('History repair retirement receipt changed')
        if source.is_file():
            if sha(source)!=witness['sha256']:raise ValueError('History repair cleanup input changed')
            source.unlink()
        receipt.update(rawRetiredAfterPromotion=True)
        atomic(cleanup,receipt)
        EVENT.emit(state,promoted);return
    if not source.is_file() or sha(source)!=witness['sha256']:
        raise ValueError('History repair source missing or changed before successful retirement')
    if case.get('selectionRepair')=='H3':
        admission=module(HERE/'admission-evidence.py','history_evidence_refresh')
        promotion=I.validated_promotion_record(state,promoted,game_pk,I.query_index_contract_admission())
        admission.refresh_existing_graph(state,promotion,witness,java,classpath,'http://127.0.0.1:3031/baseball-dev/query')
    # Write the receipt before deletion so an interruption cannot lose cleanup provenance.
    receipt=dict(sourceWitness=witness,retirementAuthorizedAtUtc=TX.now(),promotionEvidence=str(promoted))
    atomic(cleanup,receipt)
    source.unlink()
    atomic(cleanup,dict(receipt,rawRetiredAfterPromotion=True,completedAtUtc=TX.now()))
    EVENT.emit(state,promoted)


def add_game(state, game_pk, java, mapper, classpath):
    if read(ROOT / DECISION)['status'] != 'accepted':
        raise ValueError('Q7 decision is not accepted')
    case = next((c for c in cases(state) if c['gamePk'] == game_pk), None)
    if case is None:
        raise ValueError('Game is outside the approved Q7 additions')
    decision = ('archive/design-records/metric-source-c1-operation-2026-09-14/review.json'
                if case.get('selectionRepair') in {'H2','H3'} else DECISION)
    if read(ROOT / decision)['status'] != 'accepted':
        raise ValueError('Personal-history contract is not accepted')
    store = TX.HttpGraphStore('http://127.0.0.1:3031/baseball-dev/data')
    TX.recover(store, state, game_pk)
    marker_root = state / 'pipeline/evidence/nifi/game-promotion' / game_pk
    marker_path = max(marker_root.glob('*.json'), key=lambda p: (read(p)['promotedAtUtc'], p.name))
    marker = read(marker_path)
    promotion=I.validated_promotion_record(state, marker_path, game_pk, I.query_index_contract_admission())
    admission=None
    evidence_only=case.get('discovered') and not case['selectedHistoryKeys']
    if evidence_only:
        admission=module(HERE/'admission-evidence.py','discovered_history_evidence')
    needs_memory=not evidence_only or admission.existing_graph_refresh_needed(state,promotion)
    available=MEMORY.available_memory()
    if needs_memory and available is not None and available<1024*1024*1024:
        return dict(status='waiting-for-memory',availableMemoryBytes=available,rdfChanged=False)
    if (marker.get('targetedAddition', {}).get('decision') == decision
            and ('selectedHistoryKeys' not in case or marker['targetedAddition'].get('selectedHistoryKeys') == case['selectedHistoryKeys'])
            and (not case.get('selectionRepair') or marker['targetedAddition'].get('sourceWitness',{}).get('sha256')
                 ==case.get('sourceSha256',case['inputSha256']))):
        finish_selection(state,case,marker_path,java,classpath)
        return dict(status='already-complete', promotionEvidence=str(marker_path), **marker['targetedAddition'])
    I.retain_game_artifacts(state, game_pk)
    # The approved scope is the exact selected histories, not an obsolete base
    # snapshot. Preserve a later valid promotion and reconcile against its census.
    prior_path = I.retained_artifact(state, game_pk, marker['rmlManifestSha256'], Path(marker['rmlManifest']))
    if sha(prior_path) != marker['rmlManifestSha256']:
        raise ValueError('Q7 retained mapping manifest changed')
    manifest = read(prior_path)
    witness = acquire_selection_source(state, case) if case.get('selectionRepair') in {'H2','H3'} else None
    raw = Path(witness['path']).read_bytes() if witness else None
    if case.get('discovered') and not case['selectedHistoryKeys']:
        # The current selector found no missing histories. Recheck the existing
        # graph through its owner; do not manufacture a delta or remap the game.
        outcomes=admission.refresh_existing_graph(state,promotion,witness,java,classpath,
            'http://127.0.0.1:3031/baseball-dev/query')
        history_evidence={}
        if case.get('legacyHistoryEvidence'):
            adapter=admission.module(HERE/'runner-boundary-admission.py','legacy_history_boundary')
            proof=admission.load(adapter,state,promotion,'runner-boundary')
            history_evidence['historyEvidence']={k:proof[k] for k in
                ('status','issues','proofSha256','implementationSha256') if k in proof}
        EVENT.emit(state,marker_path)
        return dict(status='evidence-refreshed',rdfChanged=False,addedHistories=0,selectedHistoryKeys=[],
            sourceWitness=witness,admissionOutcomes={family:status for _,family,status in outcomes},**history_evidence)
    history, delta_context = select_history(manifest, case, raw)
    run = uuid.uuid4().hex
    evidence = state / 'pipeline/evidence/mlb-game' / game_pk / run
    evidence.mkdir(parents=True)
    context = evidence / 'game-context.json'
    atomic(context, dict(gamePk=int(game_pk), _baseballO=dict(runnerHistoryReconciliation=delta_context)))
    mapping = evidence / 'history.rml.ttl'
    subset_mapping(game_pk,mapping,history_maps(delta_context))
    delta_path = evidence / 'history-addition.ttl'
    command([java, '-Xmx256m', '-jar', mapper, '-m', mapping, '-o', delta_path,
        '-s', 'turtle', '-b', manifest['mappingBaseIri'], '--strict'], evidence, evidence / 'rml.log')
    delta = Graph().parse(delta_path, format='turtle')
    V.verify(read(context), delta)
    if not delta:
        raise ValueError('History RML selection produced no triples')
    base_bytes = store.get(marker['authoritativeGraph'])
    if base_bytes is None:
        raise ValueError('Q7 base graph is missing')
    base = TX.nt_graph(base_bytes)
    if len(base) != marker['authoritativeTripleCount']:
        raise ValueError('Q7 live graph count differs from its current promotion')
    prior_rdf = Path(manifest['outputPath'])
    if prior_rdf.is_file() and sha(prior_rdf) == manifest['outputSha256'] and not isomorphic(base, Graph().parse(prior_rdf)):
        raise ValueError('Q7 live graph differs from its retained promoted RDF')
    combined = base + delta
    V.verify(dict(gamePk=int(game_pk), _baseballO=dict(runnerHistoryReconciliation=history)), combined)
    if len(combined) == len(base):
        EVENT.emit(state,marker_path)
        return dict(status='already-present',promotionEvidence=str(marker_path),rdfChanged=False,
            addedHistories=0,addedTriples=0,selectedHistoryKeys=sorted(h['lifetimeKey'] for h in delta_context['histories']))
    rdf = evidence / 'authoritative-with-addition.nt'
    combined.serialize(destination=rdf, format='nt')
    proof_fields = revalidate(marker, manifest, history, rdf, evidence, java, classpath,
                              delta=delta if 'selectedHistoryKeys' in case else None, source_raw=raw,
                              selected_histories=delta_context['histories'])
    addition = dict(decision=decision, basePromotionSha256=sha(marker_path),
        inventoriedBasePromotionSha256=case['promotionManifestSha256'],
        baseRmlManifestSha256=sha(prior_path), baseRdfSha256=manifest['outputSha256'],
        baseExportSha256=TX.sha_bytes(base_bytes),
        deltaPath=str(delta_path), deltaSha256=sha(delta_path),
        effectiveMappingSha256=sha(mapping), executionContextSha256=sha(context),
        contextBuilderSha256=sha(ROOT / 'scripts/pipeline/prepare-rml-context.py'),
        addedHistories=len(delta_context['histories']), addedTriples=len(combined) - len(base),
        baseTripleCount=len(base), resultingTripleCount=len(combined),
        mutation='additive-graph-store-post', acquiredInputs=int(witness is not None and witness['kind']=='targeted-reacquisition'))
    if 'selectedHistoryKeys' in case:
        inventory = SELECTION if witness else COMPLETION
        addition.update(scopeDecision=read(inventory)['scopeDecision'],
                        repairInventorySha256=sha(inventory), selectedHistoryKeys=case['selectedHistoryKeys'])
    if witness:
        addition.update(selectionRepair=case['selectionRepair'], sourceWitness=witness)
    if case.get('discovered'):
        addition.update(repairRequest=case['repairRequest'],repairRequestSha256=case['repairRequestSha256'])
    promoted = marker_root / (run + '.json')
    latest = max(marker_root.glob('*.json'), key=lambda p: (read(p)['promotedAtUtc'], p.name))
    if latest != marker_path or sha(marker_path) != addition['basePromotionSha256']:
        raise ValueError('History repair promotion changed during preparation')
    TX.prepare(store, state, game_pk, run)
    try:
        # Reuse source-game locking and the existing recovery snapshots. No
        # authoritative PUT or delete occurs on the successful repair path.
        request = urllib.request.Request(store._url(marker['authoritativeGraph']),
            data=delta.serialize(format='nt', encoding='utf-8'), method='POST',
            headers={'Content-Type': 'application/n-triples'})
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError('Q7 additive graph write failed')
        if not isomorphic(TX.nt_graph(store.get(marker['authoritativeGraph'])), combined):
            raise ValueError('Q7 addition did not preserve the exact base plus delta')
        command(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            ROOT / 'scripts/pipeline/build-query-index.ps1', '-GamePk', game_pk,
            '-SourceRdfFile', rdf, '-SourceRdfSha256', sha(rdf)], ROOT, evidence / 'query-index.log')
        updated = dict(manifest, artifactType='baseballo-rml-targeted-addition-manifest',
            mappingExecution='retained-base-plus-targeted-delta', baseRmlManifest=str(prior_path),
            targetedAddition=addition, runnerHistoryReconciliation=history,
            outputPath=str(rdf), outputSha256=sha(rdf), serialization='ntriples',
            shaclValidatedAtUtc=TX.now(), completedAtUtc=TX.now())
        atomic(Path(marker['rmlManifest']), updated)
        index = read(Path(marker['queryIndexManifest']))
        I.retain_game_artifacts(state, game_pk)
        next_marker = dict(marker, pipelineRunId=run, transactionRunId=run, promotedAtUtc=TX.now(),
            authoritativeTripleCount=len(combined), queryIndexTripleCount=index['indexTripleCount'],
            rmlManifestSha256=sha(Path(marker['rmlManifest'])),
            queryIndexManifestSha256=sha(Path(marker['queryIndexManifest'])),
            targetedAddition=addition, **proof_fields)
        # Validate the ordinary publication contract before publishing it.
        candidate = evidence / 'promotion.json'
        atomic(candidate, next_marker)
        I.validated_promotion_record(state, candidate, game_pk, I.query_index_contract_admission())
        atomic(promoted, next_marker)
        TX.commit(state, game_pk, run)
    except BaseException:
        if not promoted.is_file():
            TX.restore(store, state, game_pk, run, 'targeted-history-addition-failed')
        raise
    finish_selection(state,case,promoted,java,classpath)
    return dict(status='complete', promotionEvidence=str(promoted), **addition)


def completed_case(previous,case):
    if previous.get('status') not in SUCCESS:return False
    if case.get('selectionRepair') and previous.get('selectedHistoryKeys')!=case.get('selectedHistoryKeys'):return False
    return not case.get('discovered') or (previous.get('repairRequestSha256')==case['repairRequestSha256']
        and previous.get('sourceSha256')==case['sourceSha256'])


def same_attempt(previous,case,version):
    return (previous.get('implementationSha256')==version
        and (not case.get('discovered') or (previous.get('repairRequestSha256')==case['repairRequestSha256']
             and previous.get('sourceSha256')==case['sourceSha256'])))


def tick(state, game_pk, java, mapper, classpath):
    control = state / 'pipeline/control/mlb-game/history-addition' / (game_pk + '.json')
    version = fingerprint()
    previous = read(control) if control.exists() else {}
    case=next(c for c in cases(state) if c['gamePk']==game_pk)
    if completed_case(previous,case):
        return previous
    same=same_attempt(previous,case,version)
    if same and previous.get('attempts', 0) >= 2:
        return previous
    result = dict(gamePk=game_pk, implementationSha256=version, checkedAtUtc=TX.now(),
        attempts=previous.get('attempts', 0) + 1 if same else 1)
    if case.get('discovered'):
        result.update(repairRequest=case['repairRequest'],repairRequestSha256=case['repairRequestSha256'],
                      sourceSha256=case['sourceSha256'])
    try:
        result.update(add_game(state, game_pk, java, mapper, classpath))
    except Exception as error:
        result.update(status='failed', error=str(error))
    if result['status']=='waiting-for-memory':result['attempts']-=1
    atomic(control, result)
    return result


def cases(state=None):
    selection = [dict(case, selectionRepair=case.get('selectionRepair','H2')) for case in read(SELECTION)['cases']] if SELECTION.is_file() else []
    fixed=selection + read(PACKAGE / 'source-evidence.json')['cases'] + read(COMPLETION)['cases']
    return fixed + (DISCOVERY.cases(SimpleNamespace(**globals()),state) if state is not None else [])


def fingerprint():
    # Failed evidence-only retries depend on admission code as well as the
    # mapper. Completed cases remain completed; this never requests a remap.
    evidence_code=b''.join(p.read_bytes() for p in sorted(HERE.glob('*-admission.py')))
    return hashlib.sha256(Path(__file__).read_bytes() + COMPLETION.read_bytes() +
        (SELECTION.read_bytes() if SELECTION.is_file() else b'') +
        (ROOT / 'scripts/pipeline/prepare-rml-context.py').read_bytes() +
        (HERE/'history-repair-discovery.py').read_bytes() + evidence_code +
        (HERE/'admission-evidence.py').read_bytes() +
        (HERE/'existing-graph-admissions.py').read_bytes()).hexdigest()


def next_case(state,skip=()):
    version = fingerprint()
    for case in cases(state):
        if case['gamePk'] in skip:continue
        path = state / 'pipeline/control/mlb-game/history-addition' / (case['gamePk'] + '.json')
        previous = read(path) if path.is_file() else {}
        if completed_case(previous,case):
            continue
        if same_attempt(previous,case,version) and previous.get('attempts', 0) >= 2:
            continue
        return case['gamePk']
    return DISCOVERY.discover(SimpleNamespace(**globals()),state,{c['gamePk'] for c in cases()}|set(skip))


def drain(state,java,mapper,classpath,limit=10,seconds=45):
    """One serial, bounded NiFi tick; no waiting loop and no concurrent JVMs."""
    started=time.monotonic();outcomes=[];deferred=set()
    for _ in range(limit):
        pk=next_case(state,deferred)
        if pk is None:break
        try:
            with LOCK.exclusive(state/'pipeline/work/mlb-game-locks'/(pk+'.lock')):
                result=tick(state,pk,java,mapper,classpath)
        except (BlockingIOError,PermissionError):
            result=dict(gamePk=pk,status='waiting-for-game')
        outcomes.append(result)
        if result['status'] in {'waiting-for-memory','waiting-for-game'}:deferred.add(pk)
        if time.monotonic()-started>=seconds:break
    summary=dict(status='processed' if outcomes else 'unchanged',processedGames=len(outcomes),
        outcomes={status:sum(r['status']==status for r in outcomes) for status in sorted({r['status'] for r in outcomes})})
    atomic(state/'pipeline/control/mlb-game/history-addition/latest.json',summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--next', action='store_true')
    parser.add_argument('--drain', action='store_true')
    for name in ('java', 'mapper', 'jena-classpath'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--game-pk')
    args = parser.parse_args()
    if args.next:
        print(json.dumps(next_case(args.state_root)))
        raise SystemExit(0)
    if args.drain:
        if not all((args.java,args.mapper,args.jena_classpath)):
            parser.error('Drain requires Java, mapper and Jena classpath')
        print(json.dumps(drain(args.state_root,args.java,args.mapper,args.jena_classpath)))
        raise SystemExit(0)
    if not all((args.java, args.mapper, args.jena_classpath, args.game_pk)):
        parser.error('Execution requires game, Java, mapper and Jena classpath')
    result = tick(args.state_root, args.game_pk, args.java, args.mapper, args.jena_classpath)
    print(json.dumps(result))
    raise SystemExit(result['status'] == 'failed')
