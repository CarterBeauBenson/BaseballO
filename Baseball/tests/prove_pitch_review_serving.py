"""Focused accepted M2 game RDF -> Jena -> review metric -> SQL proof.

Consumes the hash-pinned M1/M2 developer output. No acquisition, mapping,
promotion, corpus materialization or inferred graph is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile

from prove_run_construction import JAVA, M, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rdf', type=Path, required=True)
    parser.add_argument('--java', required=True)
    parser.add_argument('--jena-classpath', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof_path = ROOT/'benchmarks/metrics/m1-m2-mappings-2026-09-15/result.json'
    proof = json.loads(proof_path.read_bytes())
    rdf_hash = hashlib.sha256(args.rdf.read_bytes()).hexdigest()
    assert proof['shaclConforms'] and proof['sourceToGraphMembershipVerified']
    assert rdf_hash == proof['rdfSha256'], 'RDF differs from the passed source proof'
    graph = 'https://w3id.org/baseball/graph/game/' + proof['gamePk']
    query = M.evidence_query([graph])
    with tempfile.TemporaryDirectory(prefix='baseballo-pitch-review-query-') as temporary:
        directory = Path(temporary)
        (directory/'MetricQuery.java').write_text(JAVA, encoding='utf-8')
        (directory/'query.rq').write_text(query, encoding='utf-8')
        subprocess.run([args.java, '-Xmx512m', '--class-path', args.jena_classpath,
                        str(directory/'MetricQuery.java'), str(args.rdf.resolve()), graph,
                        str(directory/'query.rq'), str(directory/'bindings.json')], check=True, timeout=60)
        bindings = json.loads((directory/'bindings.json').read_bytes())['results']['bindings']
    rows = M.normalize_bindings(bindings, [graph])
    reviews = [row for row in rows if row['kind'] == 'review']
    result = M.live_result('adjudication-volatility', rows, graph_count=1)
    assert len({row['entity'] for row in reviews}) == proof['allReviews'], reviews
    for mapped in proof['reviews']:
        matched = [row for row in reviews if row['entity'] == mapped['reviewIri']]
        assert len(matched) == 1, matched
        assert matched[0]['original'] == mapped['originalDecisionIri']
        assert matched[0]['operative'] == mapped['operativeDecisionIri']
        assert matched[0]['decision'] == 'affirmed'
    assert result['coverage']['resolvedReviews'] == proof['allReviews'], result
    assert result['coverage']['unresolvedReviews'] == 0
    assert not result['coverage']['populationComplete']
    with sqlite3.connect(':memory:') as database:
        database.executescript((ROOT/'serving/schema.sql').read_text())
        M.initialize_sql(database)
        database.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph, 'https://baseballontology.org/data/game/'+proof['gamePk'], proof['gamePk'],
             '2026-08-23', '2026-08-23T00:00:00Z', 2026, 'regular_season', None, None, None, None, None, None))
        M.materialize_game(database, graph, bindings)
        response = M.query_sql(database, {'metricId': 'adjudication-volatility'},
            {'gameSet': 'regular_season', 'startDate': '2026-08-23', 'endDate': '2026-08-23'})
        assert response['metric'] == result
    report = dict(status='passed-isolated-developer-proof', graph=graph, rdfSha256=rdf_hash,
                  mappingProof=proof_path.relative_to(ROOT).as_posix(),
                  querySha256=hashlib.sha256(query.encode()).hexdigest(),
                  implementationSha256=M.fingerprint(), suiteVersion=M.VERSION,
                  jenaQueryPassed=True, sqlExactMatch=True, reviewRows=reviews, metric=result,
                  corpusPromotion='not-performed', playerPopulationAdmitted=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(resolvedReviews=result['coverage']['resolvedReviews'],
                         value=result['value'], sqlExactMatch=True)))


if __name__ == '__main__':
    main()
