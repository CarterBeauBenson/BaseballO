"""T1 source-bound SHACL for clock isolation, before graph promotion.

The source supplies expected measurements and conflict diagnostics only. It
does not repair clock values or supply metric results. Graph constraints live
in the owning module's generated SHACL profile.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from rdflib import Graph, Literal, XSD

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('clock_support', HERE / 'batting-admission.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
CONTEXT = B.module(ROOT / 'scripts/pipeline/prepare-rml-context.py', 'clock_context')
SHAPE = HERE.parent / 'shacl/clock-admission.ttl'


def fingerprint():
    paths = [Path(__file__), SHAPE, HERE / 'batting-admission.py', HERE / 'reconcile-metric-source.py',
             ROOT / 'scripts/pipeline/prepare-rml-context.py', ROOT / 'scripts/pipeline/validate-shacl.py']
    return B.sha('\n'.join(p.relative_to(ROOT).as_posix() + ':' + B.sha(p.read_bytes()) for p in paths).encode())


def census(raw, game_pk):
    doc = json.loads(raw)
    source = B.SOURCE.reconcile(raw, game_pk)
    game = B.BASE + 'data/game/' + B.identity(int(game_pk))
    expected, withheld, processes = [], [], []

    def boundary(process, side, value, conflict=False):
        row = dict(timestamp=process + '/timestamp/' + side,
                   instant=process + '/temporal-instant/' + side, process=process, side=side)
        (withheld if conflict else expected).append(dict(row, value=value))

    def pair(record, process, kind):
        conflict = CONTEXT.clock_pair_conflicted(record)
        processes.append(dict(process=process, kind=kind))
        for side in ('start', 'end'):
            boundary(process, side, record.get(side + 'Time'), conflict)

    plays = doc['liveData']['plays']['allPlays']
    boundary(game, 'start', doc.get('gameData', {}).get('gameInfo', {}).get('firstPitch'))
    terminal = [p for p in plays if p.get('result', {}).get('eventType') not in CONTEXT.ADMINISTRATIVE_EVENT_TYPES
                and (p.get('playEvents') or p.get('runners') or p.get('about', {}).get('isComplete') is True)
                and isinstance(p.get('about', {}).get('endTime'), str)]
    if not terminal:
        raise ValueError('No terminal baseball event for clock census')
    boundary(game, 'end', terminal[-1]['about']['endTime'], CONTEXT.clock_pair_conflicted(terminal[-1]['about']))
    for play in plays:
        if CONTEXT.play_has_plate_appearance_structure(play):
            pair(play['about'], game + '/plate-appearance/' + str(play['about']['atBatIndex']), 'PlateAppearance')
        for event in play['playEvents']:
            if event.get('isPitch') is True:
                pair(event, game + '/pitch/' + CONTEXT.require_segment(event.get('playId'), 'pitch clock identity'), 'PitchAct')
    doc[CONTEXT.CONTEXT_KEY] = {'runnerHistoryReconciliation': {'sourceConsistency': source['status']}}
    awards = CONTEXT.automatic_count_awards(doc)['automaticAwards']
    return dict(gamePk=game_pk, game=game, sourceSha256=B.sha(raw), sourceRevision=source['sourceRevision'],
                sourceReconciled=source['status'] == 'consistent', blockingIssues=source['blockingIssues'],
                clockConflicts=source['clockConflicts'], clockDecision=source['clockDecision'],
                expected=expected, withheld=withheld, processes=processes, awards=awards)


def shape_text(source):
    # Keep exact values and identity cardinalities in SHACL, not imperative RDF
    # inspection. Consistent pairs and preserved processes are checked too.
    shapes = []

    def node(target, parts):
        shapes.append('[] a sh:NodeShape ; sh:targetNode ' + B.iri(target) + ' ;\n' + ' ;\n'.join(parts) + ' .')

    def prop(path, value):
        return 'sh:property [ sh:path ' + path + ' ; sh:hasValue ' + B.iri(value) + ' ; sh:minCount 1 ; sh:maxCount 1 ]'

    for row in source['expected']:
        value = Literal(row['value'], datatype=XSD.dateTime).n3()
        node(row['timestamp'], ['sh:class base:BaseballTimestampICE',
            prop('cco:ont00001808', row['process']), prop('cco:ont00001916', row['instant']),
            'sh:property [ sh:path cco:ont00001767 ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:dateTime ; '
            'sh:minInclusive ' + value + ' ; sh:maxInclusive ' + value + ' ]'])
    for row in source['processes']:
        process = row['process']
        node(process, ['sh:class base:' + row['kind'], prop('obo:BFO_0000199', process + '/temporal-interval')])
        node(process + '/temporal-interval', ['sh:class obo:BFO_0000038',
            prop('obo:BFO_0000222', process + '/temporal-instant/start'),
            prop('obo:BFO_0000224', process + '/temporal-instant/end')])
        for side in ('start', 'end'):
            node(process + '/temporal-instant/' + side, ['sh:class base:BaseballEventTemporalInstant'])
    for row in source['withheld']:
        query = B.PREFIXES + 'SELECT $this WHERE { { $this ?p ?o } UNION { ?s ?p $this } }'
        node(row['timestamp'], ['sh:sparql [ sh:message "T1 forbids either measurement of a contradictory pair" ; sh:select ' + Literal(query).n3() + ' ]'])
        node(row['instant'], ['sh:property [ sh:path [ sh:inversePath cco:ont00001916 ] ; '
            'sh:qualifiedValueShape [ sh:class base:BaseballTimestampICE ] ; sh:qualifiedMaxCount 0 ]'])
    for row in source['awards']:
        node(row['processIri'], ['sh:class base:' + row['kind'].title() + 'Process',
            prop('obo:BFO_0000132', row['plateAppearanceIri']), prop('obo:BFO_0000117', row['judgmentIri'])])
        node(row['judgmentIri'], ['sh:class base:' + row['kind'].title() + 'JudgmentAct',
            prop('cco:ont00001986', row['decisionIri']), prop('cco:ont00001921', row['ruleIri'])])
        node(row['decisionIri'], ['sh:class base:' + row['kind'].title() + 'DecisionICE',
            prop('cco:ont00001808', row['processIri'])])
        if not row.get('clockOrderSupported', True):
            node(row['processIri'], [
                'sh:property [ sh:path obo:BFO_0000063 ; sh:maxCount 0 ]',
                'sh:property [ sh:path [ sh:inversePath obo:BFO_0000063 ] ; sh:maxCount 0 ]'])
    text = SHAPE.read_text(encoding='utf-8').replace('# __CLOCK_SHAPES__', '\n'.join(shapes))
    Graph().parse(data=text, format='turtle')
    return text


def prove(*, raw, game_pk, rdf_path, output, java=None, classpath=None):
    source = census(raw, game_pk)
    implementation, rdf_sha = fingerprint(), B.sha(rdf_path.read_bytes())
    proof = dict(artifactType='baseballo-clock-admission', contractVersion=1, gamePk=game_pk,
        sourceSha256=source['sourceSha256'], authoritativeRdfSha256=rdf_sha, implementationSha256=implementation,
        sourceReconciled=source['sourceReconciled'], graphConforms=False, status='withheld',
        conflictCount=len(source['clockConflicts']), withheldMeasurements=len(source['withheld']),
        expectedMeasurements=len(source['expected']), clockDecision=source['clockDecision'],
        metricPopulationAdmitted=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    source_path = output.with_suffix('.source.json')
    B.SOURCE.write_atomic(source_path, source)
    proof['sourceCensusSha256'] = B.sha(source_path.read_bytes())
    if source['sourceReconciled']:
        shapes = output.with_suffix('.shapes.ttl')
        shapes.write_text(shape_text(source), encoding='utf-8', newline='\n')
        if java:
            validator = B.module(ROOT / 'scripts/pipeline/validate-shacl.py', 'clock_shacl')
            conforms, report, _ = validator.validate_with_jena(data_path=rdf_path.resolve(), shape_path=shapes.resolve(),
                java=java, classpath=classpath, max_heap='384m')
        else:
            from pyshacl import validate
            conforms, report, _ = validate(Graph().parse(rdf_path), shacl_graph=Graph().parse(shapes), inference='none', advanced=True)
        report_path = output.with_suffix('.report.ttl')
        report.serialize(destination=report_path, format='turtle')
        proof.update(graphConforms=bool(conforms), shapeSha256=B.sha(shapes.read_bytes()),
                     reportSha256=B.sha(report_path.read_bytes()), engine='jena' if java else 'pyshacl')
    if proof['sourceReconciled'] and proof['graphConforms']:
        proof['status'] = 'admitted'
    if rdf_sha != B.sha(rdf_path.read_bytes()) or implementation != fingerprint():
        raise ValueError('Clock proof inputs changed during validation')
    B.SOURCE.write_atomic(output, proof)
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('input', 'rdf', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--game-pk', required=True)
    parser.add_argument('--java', type=Path)
    parser.add_argument('--jena-classpath', type=Path)
    args = parser.parse_args()
    if args.java and not args.jena_classpath:
        parser.error('--java requires --jena-classpath')
    outputs = {args.output.resolve(), *(args.output.with_suffix(s).resolve() for s in ('.source.json', '.shapes.ttl', '.report.ttl'))}
    if outputs & {args.input.resolve(), args.rdf.resolve()}:
        raise ValueError('Clock proof cannot overwrite source or RDF')
    raw = args.input.read_bytes()
    result = prove(raw=raw, game_pk=args.game_pk, rdf_path=args.rdf, output=args.output, java=args.java, classpath=args.jena_classpath)
    if raw != args.input.read_bytes():
        raise ValueError('Clock source changed during validation')
    print(json.dumps(result))
    if result['status'] != 'admitted':
        raise SystemExit('T1 clock source/graph conformance failed; promotion must stop')
