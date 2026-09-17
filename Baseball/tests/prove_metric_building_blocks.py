"""Bounded read-only promoted graph -> SQL blocks -> exact reader comparison.

This developer check neither acquires MLB data nor maps/promotes graphs. The
requested game's promotion/proofs are checked before and after its canonical
query. No selected-date or season completeness is fabricated.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('block_proof_materializer',ROOT/'scripts/pipeline/materialize-serving-layer.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
M=B._metric_suite


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--state-root',type=Path,required=True)
    parser.add_argument('--game-pk',required=True)
    parser.add_argument('--official-date',required=True)
    parser.add_argument('--endpoint',default='http://127.0.0.1:3031/baseball-dev/query')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();state=args.state_root.resolve()
    inventory=B._promotion_inventory.promotion_inventory(state)
    promotion=inventory['games'][args.game_pk]
    graph=promotion['authoritativeGraph']
    modules={'batting_admission':B._batting_admission,'scoring_run_admission':B._run_admission,
        'runner_resolution_admission':B._resolution_admission,'pitch_count_admission':B._count_admission,
        'runner_boundary_admission':B._boundary_admission,'defensive_admission':B._defense_admission}
    proofs={name:module.promoted_admission(state,promotion) for name,module in modules.items()}
    query=M.evidence_query([graph])
    request=urllib.request.Request(args.endpoint,data=urllib.parse.urlencode({'query':query}).encode(),
        headers={'Accept':'application/sparql-results+json','Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(request,timeout=60) as response:
        payload=json.load(response)
    after=B._promotion_inventory.promotion_inventory(state)['games'][args.game_pk]
    if after!=promotion:raise ValueError('Game promotion changed during developer proof')
    if proofs!={name:module.promoted_admission(state,after) for name,module in modules.items()}:
        raise ValueError('Game admission changed during developer proof')
    raw_bindings=payload['results']['bindings'];day=args.official_date
    scope=dict(startDate=day,endDate=day,gameSet='regular_season')
    with sqlite3.connect(':memory:') as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript((ROOT/'serving/schema.sql').read_text());M.initialize_sql(connection)
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+args.game_pk,args.game_pk,day,day+'T00:00:00Z',
             int(day[:4]),'regular_season',None,None,None,None,None,None))
        stored=M.materialize_game(connection,graph,raw_bindings,**proofs)
        def evaluate(use_blocks):
            start=time.perf_counter()
            result=M.query_sql(connection,dict(view='dashboard'),scope,_use_blocks=use_blocks)
            return result,round(1000*(time.perf_counter()-start),3)
        old,old_ms=evaluate(False);new,new_ms=evaluate(True)
        assert {k:v for k,v in new.items() if k!='buildingBlockCoverage'}=={
            k:v for k,v in old.items() if k!='buildingBlockCoverage'},'Reader results differ'
        counts={table:connection.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in
            ('metric_suite_evidence','metric_suite_scope_fact','metric_suite_input_row','metric_suite_shell')}
        report=dict(artifactType='baseballo-metric-building-block-developer-proof',gamePk=args.game_pk,
            promotionManifestSha256=promotion['promotionManifestSha256'],authoritativeRdfSha256=promotion['authoritativeRdfSha256'],
            implementationSha256=M.fingerprint(),querySha256=hashlib.sha256(query.encode()).hexdigest(),
            normalizedBindingsSha256=M._hash(M._json(M.normalize_bindings(raw_bindings,[graph]))),
            sourceAdmissionStatuses={name:proof.get('status') for name,proof in proofs.items()},
            stored=stored,rowCounts=counts,exactMetricComparisons=len(new['metrics']),
            evidenceReaderMs=old_ms,buildingBlockReaderMs=new_ms,buildingBlockCoverage=new['buildingBlockCoverage'],
            publicDateRangeWithoutScheduleAdmission='withheld',livePopulationComplete=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
