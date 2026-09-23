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
import urllib.request
import uuid

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DECISION = 'archive/design-records/mlb-game-zero-episode-history-isolation/review.json'
PACKAGE = ROOT / Path(DECISION).parent
MAPPING = HERE.parent / 'mapping/mlb-game.rml.ttl'
MAPS = ('PersonalRunnerProcessMap', 'PersonalRunnerIntervalMap', 'PersonalRunnerMembershipMap')


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
sha = I.sha256_file
read = TX.read
atomic = TX.atomic_json


def select_history(manifest, case):
    original = manifest['runnerHistoryReconciliation']
    if original['inputSha256'] != case['inputSha256'] or original['sourceConsistency'] != 'consistent':
        raise ValueError('Q7 retained history belongs to another or inconsistent input')
    history = H.CONTEXT.isolate_zero_episode_histories(copy.deepcopy(original))
    previous = {h['lifetimeKey'] for h in original['histories']}
    selected = [h for h in history['histories'] if h['lifetimeKey'] not in previous]
    if not selected or any((int(h['inning']), h['half']) != (case['inning'], case['half']) for h in selected):
        raise ValueError('Q7 addition differs from the approved half-inning scope')
    if any(h.get('placement') or h.get('gameEndInstantIri') for h in selected):
        raise ValueError('Q7 named repairs require only the three personal-history maps')
    for expected in case['scoringCandidates']:
        if expected not in selected:
            raise ValueError('Q7 approved scoring history changed')
    keys = {h['lifetimeKey'] for h in selected}
    delta = dict(inputSha256=original['inputSha256'], histories=selected,
        episodeMembership=[e for e in history['episodeMembership'] if e['lifetimeKey'] in keys],
        placementAdjudications=[])
    return history, delta


def subset_mapping(game_pk, destination):
    """Slice existing map descriptions without authoring new predicates."""
    full = Graph().parse(MAPPING, format='turtle')
    selected = Graph()
    logical_source = URIRef('http://semweb.mmlab.be/ns/rml#logicalSource')
    for prefix, namespace in full.namespaces():
        selected.bind(prefix, namespace)
    for name in MAPS:
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


def revalidate(marker, manifest, history, rdf, evidence, java, classpath):
    """Recheck retained source contracts; never rerun acquisition or source mapping.

    Unchanged censuses keep their original producer identity. A separate receipt
    records this graph revalidation. Previously withheld populations stay so.
    """
    output_fields = {}
    with J.Session(rdf, java, classpath) as session:
        def validate(shape, report):
            conforms, graph, _ = session.validate_with_jena(data_path=rdf, shape_path=shape,
                java=java, classpath=classpath, max_heap='384m')
            graph.serialize(destination=report, format='turtle')
            return conforms

        shape = HERE.parent / 'shacl/authoritative.ttl'
        if not validate(shape, evidence / 'authoritative.report.ttl'):
            raise ValueError('Q7 resulting graph failed the existing authoritative SHACL')
        for field, value in marker.items():
            if not field.endswith('Admission'):
                continue
            prior = Path(value)
            if sha(prior) != marker[field + 'Sha256']:
                raise ValueError('Retained admission changed: ' + field)
            proof = read(prior)
            if (proof['sourceSha256'] != marker['rawSha256']
                    or proof['authoritativeRdfSha256'] != manifest['outputSha256']):
                raise ValueError('Retained admission does not describe the approved base')
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
                if not conforms:
                    raise ValueError('Q7 changed an existing admitted graph contract: ' + field)
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
    return output_fields


def add_game(state, game_pk, java, mapper, classpath):
    if read(ROOT / DECISION)['status'] != 'accepted':
        raise ValueError('Q7 decision is not accepted')
    case = next((c for c in read(PACKAGE / 'source-evidence.json')['cases'] if c['gamePk'] == game_pk), None)
    if case is None:
        raise ValueError('Game is outside the approved Q7 additions')
    store = TX.HttpGraphStore('http://127.0.0.1:3031/baseball-dev/data')
    TX.recover(store, state, game_pk)
    marker_root = state / 'pipeline/evidence/nifi/game-promotion' / game_pk
    marker_path = max(marker_root.glob('*.json'), key=lambda p: (read(p)['promotedAtUtc'], p.name))
    marker = read(marker_path)
    if marker.get('targetedAddition', {}).get('decision') == DECISION:
        EVENT.emit(state, marker_path)
        return dict(status='already-complete', promotionEvidence=str(marker_path), **marker['targetedAddition'])
    if sha(marker_path) != case['promotionManifestSha256']:
        raise ValueError('Q7 base promotion changed; preserve it and diagnose before retrying')
    I.validated_promotion_record(state, marker_path, game_pk, I.query_index_contract_admission())
    I.retain_game_artifacts(state, game_pk)
    prior_path = I.retained_artifact(state, game_pk, case['rmlManifestSha256'], Path(marker['rmlManifest']))
    if sha(prior_path) != case['rmlManifestSha256']:
        raise ValueError('Q7 retained mapping manifest changed')
    manifest = read(prior_path)
    if manifest['outputSha256'] != case['authoritativeRdfSha256']:
        raise ValueError('Q7 retained graph identity changed')
    history, delta_context = select_history(manifest, case)
    run = uuid.uuid4().hex
    evidence = state / 'pipeline/evidence/mlb-game' / game_pk / run
    evidence.mkdir(parents=True)
    context = evidence / 'game-context.json'
    atomic(context, dict(gamePk=int(game_pk), _baseballO=dict(runnerHistoryReconciliation=delta_context)))
    mapping = evidence / 'history.rml.ttl'
    subset_mapping(game_pk, mapping)
    delta_path = evidence / 'history-addition.ttl'
    command([java, '-Xmx512m', '-jar', mapper, '-m', mapping, '-o', delta_path,
        '-s', 'turtle', '-b', manifest['mappingBaseIri'], '--strict'], evidence, evidence / 'rml.log')
    delta = Graph().parse(delta_path, format='turtle')
    V.verify(json.loads(context.read_text()), delta)
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
    if len(combined) == len(base):
        raise ValueError('Q7 base marker does not match an already-added history')
    rdf = evidence / 'authoritative-with-addition.nt'
    combined.serialize(destination=rdf, format='nt')
    V.verify(dict(gamePk=int(game_pk), _baseballO=dict(runnerHistoryReconciliation=history)), combined)
    proof_fields = revalidate(marker, manifest, history, rdf, evidence, java, classpath)
    addition = dict(decision=DECISION, basePromotionSha256=sha(marker_path),
        baseRmlManifestSha256=sha(prior_path), baseRdfSha256=manifest['outputSha256'],
        baseExportSha256=TX.sha_bytes(base_bytes),
        deltaPath=str(delta_path), deltaSha256=sha(delta_path),
        effectiveMappingSha256=sha(mapping), executionContextSha256=sha(context),
        contextBuilderSha256=sha(ROOT / 'scripts/pipeline/prepare-rml-context.py'),
        addedHistories=len(delta_context['histories']), addedTriples=len(combined) - len(base),
        baseTripleCount=len(base), resultingTripleCount=len(combined),
        mutation='additive-graph-store-post', acquiredInputs=0)
    promoted = marker_root / (run + '.json')
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
    EVENT.emit(state, promoted)
    return dict(status='complete', promotionEvidence=str(promoted), **addition)


def tick(state, game_pk, java, mapper, classpath):
    control = state / 'pipeline/control/mlb-game/history-addition' / (game_pk + '.json')
    version = hashlib.sha256(Path(__file__).read_bytes() +
        (ROOT / 'scripts/pipeline/prepare-rml-context.py').read_bytes()).hexdigest()
    previous = read(control) if control.exists() else {}
    if previous.get('status') in {'complete', 'already-complete'}:
        return previous
    if previous.get('implementationSha256') == version and previous.get('attempts', 0) >= 2:
        return previous
    result = dict(gamePk=game_pk, implementationSha256=version, checkedAtUtc=TX.now(),
        attempts=previous.get('attempts', 0) + 1 if previous.get('implementationSha256') == version else 1)
    try:
        result.update(add_game(state, game_pk, java, mapper, classpath))
    except Exception as error:
        result.update(status='failed', error=str(error))
    atomic(control, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state-root', 'java', 'mapper', 'jena-classpath'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--game-pk', choices=('822846', '824467'), required=True)
    args = parser.parse_args()
    result = tick(args.state_root, args.game_pk, args.java, args.mapper, args.jena_classpath)
    print(json.dumps(result))
    raise SystemExit(result['status'] == 'failed')
