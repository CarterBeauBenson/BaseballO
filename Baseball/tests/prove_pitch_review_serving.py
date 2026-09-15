"""Focused accepted M2 game RDF -> Jena -> review metric -> SQL proof.

Consumes the hash-pinned M1/M2 developer output. No acquisition, mapping,
promotion, corpus materialization or inferred graph is performed.
"""
import argparse
import hashlib
import importlib.util
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
    parser.add_argument('--include-batting-context', action='store_true')
    parser.add_argument('--batting-admission', type=Path)
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
    batting_admission = None
    if args.batting_admission:
        module_spec = importlib.util.spec_from_file_location('b1_proof',
            ROOT/'sources/mlb-game/pipeline/batting-admission.py')
        b1 = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(b1)
        batting_admission = json.loads(args.batting_admission.read_bytes())
        assert batting_admission['status'] == 'admitted'
        assert batting_admission['authoritativeRdfSha256'] == rdf_hash
        assert batting_admission['implementationSha256'] == b1.fingerprint()
        assert batting_admission['sourceSha256'] == hashlib.sha256((ROOT/proof['source']).read_bytes()).hexdigest()
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
        M.materialize_game(database, graph, bindings, batting_admission=batting_admission)
        stored = [json.loads(row[0]) for row in database.execute(
            'SELECT binding_json FROM metric_suite_evidence WHERE graph_iri=?', (graph,))]
        assert sorted(stored, key=M._json) == sorted(rows, key=M._json)
        response = M.query_sql(database, {'metricId': 'adjudication-volatility'},
            {'gameSet': 'regular_season', 'startDate': '2026-08-23', 'endDate': '2026-08-23'})
        assert response['metric'] == result
    report = dict(status='passed-isolated-developer-proof', graph=graph, rdfSha256=rdf_hash,
                  mappingProof=proof_path.relative_to(ROOT).as_posix(),
                  querySha256=hashlib.sha256(query.encode()).hexdigest(),
                  implementationSha256=M.fingerprint(), suiteVersion=M.VERSION,
                  jenaQueryPassed=True, sqlExactMatch=True, reviewRows=reviews, metric=result,
                  corpusPromotion='not-performed', playerPopulationAdmitted=False)
    if args.include_batting_context:
        source = json.loads((ROOT/proof['source']).read_bytes())
        expected = {(str(player['person']['id']), str(team['team']['id']))
                    for team in source['liveData']['boxscore']['teams'].values()
                    for player in team['players'].values()}
        roster = [row for row in rows if row['kind'] == 'player_team_game']
        assert all(row.get('teamRole') for row in roster)
        actual = {(row['player'].rsplit('/', 1)[-1], row['team'].rsplit('/', 1)[-1]) for row in roster}
        assert actual == expected
        report['battingContext'] = dict(playerTeamGameRows=roster,
            sourceRosterPairs=len(expected), sourceRosterMatches=True,
            adjudicatedResults=[row for row in rows if row['kind'] == 'plate_appearance' and row.get('paResult')],
            qualificationAdmitted=False)
    if batting_admission:
        scope={'gameSet':'regular_season','startDate':'2026-08-23','endDate':'2026-08-23'}
        qualification=M.batting_qualification(rows, graphs=[graph], admissions={graph:batting_admission},date_scope=scope)
        expected_source=b1.census((ROOT/proof['source']).read_bytes(),proof['gamePk'])
        expected={p['player']:p['officialPA'] for p in expected_source['roster']}
        actual={p['player']:p['plateAppearances'] for p in qualification['participation']}
        assert actual==expected
        assert len(qualification['expectedObservations'])==77
        assert response['battingQualification']['officialPlateAppearances']==77
        assert response['battingQualification']['rosteredPlayers']==52
        assert response['battingQualification']['officialPlateAppearanceCreditVerified']
        assert not response['battingQualification']['teamGameExposureVerified']
        report['battingAdmission']=dict(proofSha256=hashlib.sha256(args.batting_admission.read_bytes()).hexdigest(),
            allPlayerCountsMatchSource=True, officialPlateAppearances=77, rosteredPlayers=52,
            zeroPAPlayers=sum(n==0 for n in actual.values()), sqlExactMatch=True,
            selectedScheduleComplete=False, completePlayerScores=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(resolvedReviews=result['coverage']['resolvedReviews'],
                         value=result['value'], sqlExactMatch=True)))


if __name__ == '__main__':
    main()
