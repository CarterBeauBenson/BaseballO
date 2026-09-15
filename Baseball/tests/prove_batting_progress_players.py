"""One already validated game: E1/B1 SHACL -> canonical Jena query -> SQL.

The explicit one-game developer scope never substitutes for a complete date
range. The public SQL route must still withhold a missing schedule admission.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

from prove_run_construction import JAVA, M


def main():
    parser=argparse.ArgumentParser()
    for name in ('input','manifest','output','java','jena-classpath'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_bytes())
    spec=importlib.util.spec_from_file_location('progress_source_proof',M.ROOT/'sources/mlb-game/pipeline/runner-resolution-admission.py')
    A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    raw=args.input.read_bytes();rdf=Path(manifest['outputPath']);game=str(manifest['gamePk'])
    assert manifest['shaclStatus']=='validated'
    assert manifest['inputSha256']==A.B.sha(raw) and manifest['outputSha256']==A.B.sha(rdf.read_bytes())
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    arguments=dict(raw=raw,game_pk=game,rdf_path=rdf,java=args.java,classpath=args.jena_classpath)
    resolution=A.prove(**arguments,output=output/'resolutions.json')
    batting=A.B.prove(**arguments,output=output/'batting.json')
    assert resolution['status']==batting['status']=='admitted',(resolution,batting)
    graph='https://w3id.org/baseball/graph/game/'+game
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    (output/'query.rq').write_text(M.evidence_query([graph]),encoding='utf-8')
    subprocess.run([str(args.java),'-Xmx512m','--class-path',str(args.jena_classpath),str(output/'MetricQuery.java'),
        str(rdf),graph,str(output/'query.rq'),str(output/'bindings.json')],check=True,timeout=60)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph])
    day=json.loads(raw)['gameData']['datetime']['officialDate']
    scope=dict(startDate=day,endDate=day,gameSet='regular_season')
    # Explicit fixture scope: one complete game. No schedule row is fabricated.
    qualification=M.batting_qualification(rows,graphs=[graph],admissions={graph:batting},date_scope=scope,
        selected_games_complete=True)
    scoped={metric:M.batting_progress_players(metric,rows,graphs=[graph],admissions={graph:resolution},
        qualification=qualification,date_scope=scope) for metric in sorted(M.PROGRESS_METRICS)}
    for result in scoped.values():
        assert result['playerPopulationComplete'] is True,result
        assert result['progressEvidence']['unresolvedPlateAppearances']==[]
    with sqlite3.connect(':memory:') as connection:
        connection.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(connection)
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+game,game,day,day+'T00:00:00Z',
             int(day[:4]),'regular_season',None,None,None,None,None,None))
        M.materialize_game(connection,graph,bindings,batting_admission=batting,runner_resolution_admission=resolution)
        # Exact facts retained in SQL, with no use of the source census as scores.
        retained=[json.loads(t) for (t,) in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
        sql_qualification=M.batting_qualification(retained,graphs=[graph],admissions={graph:batting},date_scope=scope,
            selected_games_complete=True)
        for metric,result in scoped.items():
            assert result==M.batting_progress_players(metric,retained,graphs=[graph],admissions={graph:resolution},
                qualification=sql_qualification,date_scope=scope)
            public=M.query_sql(connection,dict(metricId=metric),scope)['metric']
            assert public['playerPopulationComplete'] is False
            assert public['playerSummaryGaps']==['COMPLETE_SELECTED_SCHEDULE']
    report=dict(artifactType='baseballo-batting-progress-player-developer-proof',gamePk=game,
        sourceSha256=A.B.sha(raw),rdfSha256=A.B.sha(rdf.read_bytes()),implementationSha256=M.fingerprint(),
        sourceAdmissions=dict(batting=batting,runnerResolutions=resolution),jenaQueryPassed=True,
        sqlExactMatch=True,officialPlateAppearances=len(qualification['expectedObservations']),
        observedRunnerResolutions=len({r['resolution'] for r in rows if r['kind']=='runner_movement'}),
        isolatedOneGameResults=scoped,publicDateRangeWithoutScheduleAdmission='withheld',livePopulationComplete=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('isolatedOneGameResults','sourceAdmissions')}))


if __name__=='__main__':main()
