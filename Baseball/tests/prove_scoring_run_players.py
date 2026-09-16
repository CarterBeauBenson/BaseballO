"""One real, already validated game: full Run census -> Jena query -> SQL.

This is a focused developer proof, never a substitute for a complete MLB
schedule or promotion. The public SQL request must stay unavailable when the
independent selected-schedule proof is absent.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

from prove_run_construction import JAVA, M

spec = importlib.util.spec_from_file_location('run_proof_admission',
    M.ROOT/'sources/mlb-game/pipeline/scoring-run-admission.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def main():
    parser=argparse.ArgumentParser()
    for name in ('input','manifest','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--java',required=True)
    parser.add_argument('--jena-classpath',required=True)
    parser.add_argument('--metrics',nargs='+',choices=('run-construction-depth','run-construction-breadth'),
                        default=['run-construction-depth','run-construction-breadth'])
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_bytes())
    game=str(manifest['gamePk'])
    rdf=Path(manifest['outputPath'])
    assert manifest['shaclStatus']=='validated'
    assert manifest['inputSha256']==A.B.sha(args.input.read_bytes())
    assert manifest['outputSha256']==A.B.sha(rdf.read_bytes())
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    proof=A.prove(raw=args.input.read_bytes(),game_pk=game,rdf_path=rdf,
                  output=output/'admission.json',java=Path(args.java),classpath=Path(args.jena_classpath))
    assert proof['status']=='admitted',proof
    graph='https://w3id.org/baseball/graph/game/'+game
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    (output/'query.rq').write_text(M.evidence_query([graph]),encoding='utf-8')
    subprocess.run([args.java,'-Xmx512m','--class-path',args.jena_classpath,
                    str(output/'MetricQuery.java'),str(rdf),graph,
                    str(output/'query.rq'),str(output/'bindings.json')],check=True,timeout=60)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph])
    results={metric:M.live_result(metric,rows,graph_count=1) for metric in args.metrics}
    source=json.loads((output/'admission.source.json').read_bytes())
    for result in results.values():
        assert result['unresolvedRuns']==[],result['unresolvedRuns']
        assert {r['run'] for r in source['runs']}=={r['run'] for r in result['runs']}
    # The developer proof's declared game scope is one complete game. This
    # internal calculation tests means only; it does not manufacture schedule
    # proof rows or make the public date-range API claim complete MLB coverage.
    # Scope metadata only; no score or source-derived aggregate enters SQL.
    day=json.loads(args.input.read_bytes())['gameData']['datetime']['officialDate']
    scope=dict(startDate=day,endDate=day,gameSet='regular_season')
    scoped={metric:M.scoring_run_players(rows,graphs=[graph],admissions={graph:proof},date_scope=scope,
        schedule={'complete':True},evidence=result) for metric,result in results.items()}
    for summary in scoped.values():
        assert summary['playerPopulationComplete'] is True
        assert sum(p['aggregate']['count'] for p in summary['playerResults'])==len(source['runs'])
    with sqlite3.connect(':memory:') as connection:
        connection.executescript((M.ROOT/'serving/schema.sql').read_text())
        M.initialize_sql(connection)
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,source['game'],game,scope['startDate'],scope['startDate']+'T00:00:00Z',
             2026,'regular_season',None,None,None,None,None,None))
        M.materialize_game(connection,graph,bindings,scoring_run_admission=proof)
        for metric,result in results.items():
            response=M.query_sql(connection,{'metricId':metric},scope)
            assert response['metric']['runs']==result['runs']
            assert response['metric']['unresolvedRuns']==[]
            assert response['metric']['playerPopulationComplete'] is False
            assert response['metric']['playerSummaryGaps']==['COMPLETE_SELECTED_SCHEDULE']
        assert connection.execute('SELECT COUNT(*) FROM metric_suite_evidence').fetchone()[0]==len(rows)
    report=dict(artifactType='baseballo-scoring-run-player-developer-proof',gamePk=game,
        metrics=list(results),
        sourceSha256=proof['sourceSha256'],rdfSha256=proof['authoritativeRdfSha256'],
        implementationSha256=M.fingerprint(),admission=proof,jenaQueryPassed=True,
        observedRuns=len(source['runs']),unresolvedRuns=0,sqlExactMatch=True,
        isolatedOneGamePlayerMeans={metric:summary['playerResults'] for metric,summary in scoped.items()},
        publicDateRangeWithoutScheduleAdmission='withheld',livePopulationComplete=False,
        runs={metric:result['runs'] for metric,result in results.items()})
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','admission','isolatedOneGamePlayerMeans')}))


if __name__=='__main__':main()
