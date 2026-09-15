"""One admitted game: source SHACL -> graph Recovery histories -> exact SQL.

This developer proof never promotes graphs or treats one game as a season.
"""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

from prove_run_construction import JAVA,M


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','manifest','output','java','jena-classpath'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('count_proof',M.ROOT/'sources/mlb-game/pipeline/pitch-count-admission.py')
    A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    raw=args.input.read_bytes();manifest=json.loads(args.manifest.read_bytes())
    rdf=Path(manifest['outputPath']);game=str(manifest['gamePk'])
    assert manifest['shaclStatus']=='validated'
    assert manifest['inputSha256']==A.B.sha(raw) and manifest['outputSha256']==A.B.sha(rdf.read_bytes())
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    admission=A.prove(raw=raw,game_pk=game,rdf_path=rdf,output=output/'count-admission.json',
                      java=args.java,classpath=args.jena_classpath)
    assert admission['status']=='admitted',admission
    batting=A.B.prove(raw=raw,game_pk=game,rdf_path=rdf,output=output/'batting-admission.json',
                      java=args.java,classpath=args.jena_classpath)
    assert batting['status']=='admitted',batting
    graph='https://w3id.org/baseball/graph/game/'+game
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    (output/'query.rq').write_text(M.evidence_query([graph]),encoding='utf-8')
    subprocess.run([str(args.java),'-Xmx512m','--class-path',str(args.jena_classpath),str(output/'MetricQuery.java'),
        str(rdf),graph,str(output/'query.rq'),str(output/'bindings.json')],check=True,timeout=90)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph])
    result=M.recovery_game_inputs(rows,graph=graph,batting_admission=batting,pitch_count_admission=admission)
    assert result['complete'],result
    with sqlite3.connect(':memory:') as conn:
        conn.execute('PRAGMA foreign_keys=ON');conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
        day=json.loads(raw)['gameData']['datetime']['officialDate']
        conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,rows[0]['game'],game,day,day+'T00:00:00Z',int(day[:4]),'regular_season',None,None,None,None,None,None))
        M.materialize_game(conn,graph,bindings,batting_admission=batting,pitch_count_admission=admission)
        retained,=M.read_results(conn,graph,'recovery-quality')
        assert retained['recoveryInputs']==result
        assert retained['status']=='unavailable'  # This proof has no season reference.
    eligible=[r for r in result['plateAppearances'] if r['twoStrikeEligible']]
    report=dict(artifactType='baseballo-recovery-input-developer-proof',gamePk=game,
        sourceSha256=A.B.sha(raw),rdfSha256=A.B.sha(rdf.read_bytes()),implementationSha256=M.fingerprint(),
        sourceAdmission=admission,battingAdmission=batting,jenaQueryPassed=True,sqlExactMatch=True,
        officialPlateAppearances=len(result['plateAppearances']),twoStrikeEligible=len(eligible),
        knownIneligible=len(result['plateAppearances'])-len(eligible),
        recoveryStepDistribution=dict(sorted(Counter(r['value']['numerator'] for r in eligible).items())),
        result=result,seasonPopulationComplete=False,livePopulationComplete=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('result','sourceAdmission','battingAdmission')}))


if __name__=='__main__':main()
