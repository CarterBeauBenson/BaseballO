"""Focused M2/Q4 graph -> Jena -> SQL proof over a passed RML manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from prove_run_construction import JAVA, M


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    for name in ('manifest','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--java',required=True)
    parser.add_argument('--jena-classpath',required=True)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_bytes());rdf=Path(manifest['outputPath'])
    assert manifest['shaclStatus']=='validated' and manifest['metricMappingMembershipVerified'] is True
    assert sha(rdf)==manifest['outputSha256']
    assert sha(Path(manifest['inputPath']))==manifest['inputSha256']
    source=json.loads(Path(manifest['inputPath']).read_bytes())
    graph=manifest['graphIri'];output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    query=M.evidence_query([graph])
    (output/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
    (output/'query.rq').write_text(query,encoding='utf-8')
    subprocess.run([args.java,'-Xmx512m','--class-path',args.jena_classpath,
        str(output/'MetricQuery.java'),str(rdf),graph,str(output/'query.rq'),str(output/'bindings.json')],
        check=True,timeout=60)
    bindings=json.loads((output/'bindings.json').read_bytes())['results']['bindings']
    rows=M.normalize_bindings(bindings,[graph]);subjects=M.review_player_evidence(rows)
    expected={}
    for review in manifest['metricMappingEvidence']['pitchReviews']:
        stints=[s for s in manifest['batterParticipationEvidence'] if s['atBatIndex']==review['atBatIndex']]
        if len(stints)==1 and review['playId'] in stints[0]['pitchIds']:
            expected[review['reviewIri']]='https://baseballontology.org/data/player/'+stints[0]['playerId']
    actual={r['review']:r['affectedPlayer'] for r in subjects if r['attributionStatus']=='supported'}
    assert actual==expected,(actual,expected)
    result=M.live_result('adjudication-volatility',rows,graph_count=1)
    scope=dict(gameSet='regular_season',startDate=manifest['officialDate'],endDate=manifest['officialDate'])
    with sqlite3.connect(':memory:') as conn:
        conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
        conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+str(manifest['gamePk']),str(manifest['gamePk']),
             manifest['officialDate'],source['gameData']['gameInfo']['firstPitch'],
             int(source['gameData']['game']['season']),'regular_season',None,None,None,None,None,None))
        M.materialize_game(conn,graph,bindings)
        assert M.query_sql(conn,{'metricId':'adjudication-volatility'},scope)['metric']==result
    assert result['coverage']['populationComplete'] is False
    report=dict(artifactType='baseballo-review-subject-developer-proof',gamePk=manifest['gamePk'],
        sourceSha256=manifest['inputSha256'],rdfSha256=manifest['outputSha256'],
        rmlManifestSha256=sha(args.manifest),implementationSha256=M.fingerprint(),
        querySha256=hashlib.sha256(query.encode()).hexdigest(),jenaQueryPassed=True,sqlExactMatch=True,
        subjects=subjects,affectedBattersVerified=len(actual),sourceShaclConforms=True,
        playerPopulationComplete=False,reviewMechanismsAdmitted=False,corpusPromotion='not-performed')
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='subjects'}))


if __name__=='__main__':main()
