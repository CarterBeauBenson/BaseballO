"""Real D1 graph -> canonical Jena query -> SQL admission-retention proof."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from prove_run_construction import JAVA, M


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    for name in ('manifest','admission','output'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('java','jena-classpath'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_bytes());proof=json.loads(args.admission.read_bytes())
    rdf=Path(manifest['outputPath']);raw=Path(manifest['inputPath']);source=json.loads(raw.read_bytes())
    assert manifest['shaclStatus']=='validated' and proof['graphConforms'] is True
    assert sha(rdf)==manifest['outputSha256']==proof['authoritativeRdfSha256']
    assert sha(raw)==manifest['inputSha256']==proof['sourceSha256']
    graph=manifest['graphIri'];output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    query=M.evidence_query([graph]);(output/'query.rq').write_text(query,encoding='utf-8')
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    subprocess.run([args.java,'-Xmx512m','--class-path',args.jena_classpath,str(output/'MetricQuery.java'),
        str(rdf),graph,str(output/'query.rq'),str(output/'bindings.json')],check=True,timeout=60)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph]);actual={}
    for row in rows:
        if row['kind']=='batted_play' and row.get('defensiveAct'):
            actual.setdefault(row['defensiveAct'],set()).add((row['entity'],row['defensiveAgent'],row['defensiveRole'],row['defensiveActType']))
    expected={}
    for r in manifest['defensiveEvidence']['acts']:
        classes=[r['classIri']]+(['https://baseballontology.org/FieldingAttemptAct'] if r['catch'] else [])
        expected[r['actIri']]={(r['playIri'],r['agentIri'],r['roleIri'],kind) for kind in classes}
    assert actual==expected,(actual,expected)
    scope=dict(gameSet='regular_season',startDate=manifest['officialDate'],endDate=manifest['officialDate'])
    with sqlite3.connect(':memory:') as conn:
        conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
        conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+str(manifest['gamePk']),str(manifest['gamePk']),
             manifest['officialDate'],source['gameData']['gameInfo']['firstPitch'],int(source['gameData']['game']['season']),
             'regular_season',None,None,None,None,None,None))
        M.materialize_game(conn,graph,bindings,defensive_admission=proof)
        retained=json.loads(conn.execute('SELECT proof_json FROM metric_suite_defensive_admission WHERE graph_iri=?',(graph,)).fetchone()[0])
        assert retained==proof
        for metric in ('resolution-depth','defender-breadth'):
            result=M.query_sql(conn,{'metricId':metric},scope)['metric']
            assert result['playerPopulationComplete'] is False and result['playerResults']==[]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    report=dict(artifactType='baseballo-defensive-input-developer-proof',gamePk=manifest['gamePk'],
        sourceSha256=manifest['inputSha256'],rdfSha256=manifest['outputSha256'],admissionSha256=sha(args.admission),
        implementationSha256=M.fingerprint(),querySha256=hashlib.sha256(query.encode()).hexdigest(),
        actsVerified=len(actual),contactPlaysVerified=len({r['entity'] for r in rows if r['kind']=='batted_play'}),
        jenaQueryExactMatch=True,sqlProofExactMatch=True,incompletePopulationWithheld=True,corpusPromotion='not-performed')
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
