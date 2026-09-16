"""Q5 clock award beside an affirmed pitch review: real RDF, query and SQL.

Checks one affected PA without asserting complete game or season admission.
The complete source count census must still reject the four draft M3/M4 cases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from rdflib import Graph, Namespace
from prove_run_construction import JAVA, M


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'manifest', 'count-admission', 'output', 'java', 'jena-classpath'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    manifest = json.loads(args.manifest.read_bytes())
    rdf = Path(manifest['outputPath'])
    sha = lambda data: hashlib.sha256(data).hexdigest()
    assert str(manifest['gamePk']) == '824087'
    assert manifest['shaclStatus'] == 'validated'
    assert manifest['inputSha256'] == sha(raw)
    assert manifest['outputSha256'] == sha(rdf.read_bytes())
    admission = json.loads(args.count_admission.read_bytes())
    assert admission['sourceSha256'] == sha(raw)
    assert admission['authoritativeRdfSha256'] == sha(rdf.read_bytes())
    assert admission['sourceReconciled'] and not admission['graphConforms']
    assert admission['issues'] == [{'code': 'PITCH_COUNT_MAPPING_COVERAGE'}]
    report = args.count_admission.with_suffix('.report.ttl')
    assert admission['reportSha256'] == sha(report.read_bytes())
    # Every failing focus belongs to these four still-unapproved foul cases.
    sh = Namespace('http://www.w3.org/ns/shacl#')
    report_graph = Graph().parse(report)
    failing = sorted({str(node).rsplit('/', 1)[-1] for node in report_graph.objects(None, sh.focusNode)})
    expected = sorted(['afb3e724-c0c9-3b8e-ad34-13efc7d0c3e4', '41fa6af0-ca1c-3a9e-a799-53ad322b012b',
                       '2e43cea2-8987-3504-bdea-1d14260ec2ec', '42fceb08-17db-3716-83d0-b5c23445239e'])
    assert failing == expected, failing
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    graph = 'https://w3id.org/baseball/graph/game/824087'
    (output/'MetricQuery.java').write_text(JAVA, encoding='utf-8')
    (output/'query.rq').write_text(M.evidence_query([graph]), encoding='utf-8')
    subprocess.run([str(args.java), '-Xmx512m', '--class-path', str(args.jena_classpath),
        str(output/'MetricQuery.java'), str(rdf), graph, str(output/'query.rq'), str(output/'bindings.json')], check=True, timeout=90)
    bindings = json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows = M.normalize_bindings(bindings, [graph])
    pa = 'https://baseballontology.org/data/game/824087/plate-appearance/32'
    award, = [r for r in rows if r['kind'] == 'automatic_count_award' and r['plateAppearance'] == pa]
    assert award['countAwardKind'] == 'strike' and not award.get('priorPitch')
    assert award['nextPitch'].endswith('/6873c9fd-f246-3cb0-8a43-93fe587a5d94')
    history, = [p for p in M.recovery_histories(rows)['plateAppearances'] if p['plateAppearance'] == pa]
    assert history['status'] == 'available' and history['value'] == M.exact(1), history
    assert [r['strikesAfter'] for r in history['countHistory']] == [1, 2, 2, 2]
    assert sum('pitch' in r for r in history['countHistory']) == 3
    assert history['countHistory'][0]['countAward'] == award['entity']
    with sqlite3.connect(':memory:') as connection:
        M.initialize_sql(connection)
        result = M.materialize_game(connection, graph, bindings)
        assert result['exactRoundTrip']
        retained = [json.loads(r[0]) for r in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
        assert award in retained
        assert M.recovery_histories(retained) == M.recovery_histories(rows)
        assert M.read_results(connection, graph, 'recovery-quality')[0]['status'] == 'unavailable'
    assert args.input.read_bytes() == raw
    result = dict(artifactType='baseballo-automatic-award-review-developer-proof', gamePk='824087',
        sourceSha256=sha(raw), rdfSha256=sha(rdf.read_bytes()), implementationSha256=M.fingerprint(),
        sourceShaclPassed=True, jenaQueryPassed=True, sqlExactMatch=True,
        affectedPlateAppearance=history, selectedAutomaticAwards=1, deliveredPitchesInAffectedPA=3,
        countAdmission=admission, countAdmissionFailingPlayIds=failing,
        fullGameCountAdmission=False, seasonPopulationComplete=False, livePopulationComplete=False)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('affectedPlateAppearance', 'countAdmission')}))


if __name__ == '__main__':
    main()
