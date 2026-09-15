"""Focused accepted B2 game: source SHACL -> canonical query -> continuation -> SQL."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

from prove_run_construction import JAVA, M


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','manifest','output','java','jena-classpath'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--pa',type=int,required=True)
    parser.add_argument('--expected-reach',type=int,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('contact_admission',M.ROOT/'sources/mlb-game/pipeline/contact-continuation-admission.py')
    A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    raw=args.input.read_bytes();manifest=json.loads(args.manifest.read_bytes())
    rdf=Path(manifest['outputPath']);game=str(manifest['gamePk'])
    assert manifest['shaclStatus']=='validated'
    assert manifest['inputSha256']==A.sha(raw) and manifest['outputSha256']==A.sha(rdf.read_bytes())
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    admission=A.prove(raw,game,rdf,output/'contact-admission.json',args.java,args.jena_classpath)
    assert admission['conforms'] is True,admission
    graph='https://w3id.org/baseball/graph/game/'+game
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    (output/'query.rq').write_text(M.evidence_query([graph]),encoding='utf-8')
    subprocess.run([str(args.java),'-Xmx512m','--class-path',str(args.jena_classpath),str(output/'MetricQuery.java'),
        str(rdf),graph,str(output/'query.rq'),str(output/'bindings.json')],check=True,timeout=60)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph]);all_progress=M.batting_progress_evidence(rows)
    pa='https://baseballontology.org/data/game/'+game+'/plate-appearance/'+str(args.pa)
    result,=[p for p in all_progress['plateAppearances'] if p['plateAppearance']==pa]
    assert result['reach']==args.expected_reach,result
    assert len(result['coalescedContactPaths'])==3 and result['batterPositive'] is False,result
    batter,=[p for p in result['coalescedContactPaths'] if p['player']==result['player']]
    assert (batter['start'],batter['end'],batter['positive'])==(0,None,False)
    assert sum(len(p['segments']) for p in result['coalescedContactPaths'])==6
    # Independent source counts validate graph membership only; every metric
    # value above and below comes from these canonical RDF query bindings.
    with sqlite3.connect(':memory:') as connection:
        connection.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(connection)
        day=json.loads(raw)['gameData']['datetime']['officialDate']
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,rows[0]['game'],game,day,day+'T00:00:00Z',int(day[:4]),
             'regular_season',None,None,None,None,None,None))
        M.materialize_game(connection,graph,bindings)
        retained=[json.loads(t) for (t,) in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
        sql=M.batting_progress_evidence(retained)
        assert all_progress==sql
    report=dict(artifactType='baseballo-contact-progress-developer-proof',gamePk=game,atBatIndex=args.pa,
        sourceSha256=A.sha(raw),rdfSha256=A.sha(rdf.read_bytes()),implementationSha256=M.fingerprint(),
        sourceAdmission=admission,jenaQueryPassed=True,sqlExactMatch=True,result=result,
        supportedPlateAppearances=len(all_progress['plateAppearances']),
        unresolvedPlateAppearances=all_progress['unresolvedPlateAppearances'],
        playerPopulationComplete=False,livePopulationComplete=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(gamePk=game,atBatIndex=args.pa,offensiveReach=result['reach'],
        coalescedPaths=len(result['coalescedContactPaths']),batterPositive=result['batterPositive'],
        sqlExactMatch=True,unresolvedPAs=len(all_progress['unresolvedPlateAppearances']))))


if __name__=='__main__':main()
