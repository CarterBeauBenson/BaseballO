"""Q8 supported walk-off completion, with unchanged counted effects."""
import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from pyshacl import validate
from rdflib import Graph, RDF, URIRef
from test_metric_mapping_completion import ROOT, CONTEXT, BASE, BFO, CCO, SHAPE

sys.path.insert(0,str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, local_root, materialized_subset, RR
from prove_run_construction import JAVA

SOURCE=ROOT/'data/raw/samples/2026-07-20/824087.json'


class WalkoffRunnerBoundary(unittest.TestCase):
    def test_real_walkoff_preserves_score_and_two_safe_histories_without_outs(self):
        raw=SOURCE.read_bytes();result=CONTEXT.personal_runner_histories(raw)
        half=result['halves'][-1]
        self.assertEqual(half['status'],'reconciled')
        self.assertEqual(half['personalHistories'],3)
        histories=[h for h in result['histories'] if h['inning']=='9' and h['half']=='bottom']
        self.assertEqual({h['runnerId']:h['terminal'] for h in histories},
                         {'668942':'score','686475':'game-ended','679845':'game-ended'})
        for history in histories:
            if history['terminal']=='game-ended':
                self.assertTrue(history['gameEndInstantIri'].endswith('/game/824087/temporal-instant/end'))
                self.assertTrue(all(e['resolutionKind'] not in ('out','score') for e in history['episodes']))
        self.assertEqual(SOURCE.read_bytes(),raw)
        self.assertEqual(CONTEXT.personal_runner_histories(raw),result)
        self.assertFalse(result['metricPopulationAdmitted'])

    def test_home_run_keeps_all_counted_scoring_histories(self):
        result=CONTEXT.personal_runner_histories((ROOT/'data/raw/samples/2026-07-18/824412.json').read_bytes())
        self.assertEqual(result['halves'][-1]['status'],'reconciled')
        last=[h for h in result['histories'] if h['inning']=='9' and h['half']=='bottom']
        self.assertEqual({h['runnerId'] for h in last if h['terminal']=='score'},{'683953','680757'})
        self.assertTrue(all('gameEndInstantIri' not in h for h in last))

    def test_unconfirmed_or_contradictory_ending_is_withheld(self):
        for fault in ['live','top','early','tied','already-leading','score-census','event-id','time','later-event']:
            with self.subTest(fault=fault):
                doc=json.loads(SOURCE.read_bytes());last=doc['liveData']['plays']['allPlays'][-1]
                if fault=='live':doc['gameData']['status']['abstractGameState']='Live'
                elif fault=='top':last['about']['halfInning']='top'
                elif fault=='early':last['about']['inning']=1
                elif fault=='tied':last['result']['homeScore']=last['result']['awayScore']
                elif fault=='already-leading':doc['liveData']['plays']['allPlays'][-2]['result']['homeScore']=99
                elif fault=='score-census':last['runners'][0]['details']['isScoringEvent']=False
                elif fault=='event-id':last['playEvents'][-1]['playId']=None
                elif fault=='time':last['playEvents'][-1]['endTime']='2026-07-21T02:10:39Z'
                elif fault=='later-event':last['playEvents'].append(copy.deepcopy(last['playEvents'][0]))
                self.assertIsNone(CONTEXT.supported_walkoff_boundary(doc,last))

    def test_walkoff_does_not_bypass_review_or_placed_runner_gaps(self):
        doc=json.loads(SOURCE.read_bytes());doc['liveData']['plays']['allPlays'][-1]['about']['hasReview']=True
        result=CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        self.assertEqual(result['halves'][-1]['status'],'withheld')
        self.assertTrue(any(i['code']=='UNRESOLVED_REVIEW_EFFECT' for i in result['halves'][-1]['issues']))
        result=CONTEXT.personal_runner_histories((ROOT/'data/raw/samples/2026-07-18/823116.json').read_bytes())
        self.assertEqual(result['halves'][-1]['status'],'withheld')
        self.assertTrue(any('runner_placed' in i['code'] for i in result['halves'][-1]['issues']))

    def test_real_half_rml_shacl_query_and_sql_preserve_game_boundary(self):
        workspace=Path(tempfile.mkdtemp(prefix='baseballo-walkoff-runner-'))
        (workspace/'game.json').write_bytes(SOURCE.read_bytes())
        full=workspace/'full-context.json'
        run=subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(SOURCE),str(full)],capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
        d=json.loads(full.read_bytes());d['liveData']['plays']['allPlays']=[p for p in d['liveData']['plays']['allPlays'] if p['about']['inning']==9 and p['about']['halfInning']=='bottom']
        evidence=d['_baseballO']['runnerHistoryReconciliation']
        evidence['histories']=[h for h in evidence['histories'] if h['inning']=='9' and h['half']=='bottom']
        keys={h['lifetimeKey'] for h in evidence['histories']}
        evidence['episodeMembership']=[m for m in evidence['episodeMembership'] if m['lifetimeKey'] in keys]
        d['_baseballO']['metricPitchReviews']=[];d['_baseballO']['metricAutomaticAwards']=[]
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        mapping_graph=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        mapping=materialized_subset(mapping_graph,list(mapping_graph.subjects(RDF.type,URIRef(RR+'TriplesMap'))),workspace)
        java,mapper=installed_tools();output=workspace/'one-half.ttl'
        run=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),'-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True)
        (workspace/'mapper.log').write_bytes(run.stdout+run.stderr);self.assertEqual(run.returncode,0,str(workspace/'mapper.log'))
        g=Graph().parse(output);shapes=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')
        # Explicit focus nodes exercise the referenced C1 shape itself; a
        # selective run of just its wrapper can omit the named child shape.
        focus=[f"https://baseballontology.org/data/game/824087/runner-trajectory/{h['lifetimeKey']}" for h in evidence['histories']]
        def conforms(graph):return validate(graph,shacl_graph=shapes,
            use_shapes=[str(SHAPE.PersonalRunnerProcessShape)],focus_nodes=focus)
        ok,_,report=conforms(g);self.assertTrue(ok,report)
        ended=[h for h in evidence['histories'] if h['terminal']=='game-ended'];self.assertEqual(len(ended),2)
        root='https://baseballontology.org/data/game/824087/'
        self.assertEqual(len(set(g.subjects(RDF.type,BASE.OutProcess))),1)
        self.assertEqual(len(set(g.subjects(RDF.type,BASE.RunProcess))),1)
        for h in ended:
            interval=URIRef(root+'runner-trajectory/'+h['lifetimeKey']+'/temporal-interval')
            self.assertIn((interval,BFO.BFO_0000224,URIRef(h['gameEndInstantIri'])),g)
        interval=URIRef(root+'runner-trajectory/'+ended[0]['lifetimeKey']+'/temporal-interval')
        for fault in ['other-game','missing-timestamp','fake-out','extra-end']:
            broken=Graph()+g
            if fault=='other-game':broken.remove((interval,BFO.BFO_0000224,None));broken.add((interval,BFO.BFO_0000224,URIRef('urn:another-game-end')))
            elif fault=='missing-timestamp':broken.remove((URIRef(root+'timestamp/end'),CCO.ont00001767,None))
            elif fault=='extra-end':broken.add((interval,BFO.BFO_0000224,URIRef('urn:extra-end')))
            else:
                episode=URIRef(root+f"runner-episode/{ended[0]['episodes'][0]['atBatIndex']}/{ended[0]['episodes'][0]['runnerIndex']}")
                broken.add((episode,BFO.BFO_0000117,URIRef('urn:fake-out')));broken.add((URIRef('urn:fake-out'),RDF.type,BASE.OutProcess))
            self.assertFalse(conforms(broken)[0],fault)
        spec=importlib.util.spec_from_file_location('walkoff_serving',ROOT/'serving/metric_suite.py');serving=importlib.util.module_from_spec(spec);spec.loader.exec_module(serving)
        # Use the production query engine; RDFLib's evaluation of this complete
        # OPTIONAL-heavy query can stall even on the one-half fixture.
        graph_iri='https://w3id.org/baseball/graph/game/824087'
        jars=list((local_root()/'runtimes').glob('*/fuseki-server.jar'))
        self.assertEqual(len(jars),1,'Expected one installed Jena runtime')
        (workspace/'MetricQuery.java').write_text(JAVA,encoding='utf-8')
        (workspace/'query.rq').write_text(serving.evidence_query([graph_iri]),encoding='utf-8')
        subprocess.run([str(java),'-Xmx512m','--class-path',str(jars[0]),str(workspace/'MetricQuery.java'),
            str(output),graph_iri,str(workspace/'query.rq'),str(workspace/'bindings.json')],check=True,timeout=60)
        bindings=json.loads((workspace/'bindings.json').read_bytes())['results']['bindings']
        rows=serving.normalize_bindings(bindings,[graph_iri])
        run,=serving.run_construction_evidence(rows)['runs']
        self.assertEqual(run['runner'],'https://baseballontology.org/data/player/668942')
        self.assertEqual(run['value'],{'numerator':'4','denominator':'1'})
        self.assertEqual([(e['start'],e['end']) for e in run['episodes']],[(0,1),(1,2),(2,3),(3,4)])
        end_rows=[r for r in rows if r.get('trajectoryEndInstant')]
        self.assertEqual({r['player'].rsplit('/',1)[-1] for r in end_rows},{'686475','679845'})
        self.assertEqual({datetime.fromisoformat(r['gameEnd'].replace('Z','+00:00')) for r in end_rows},
                         {datetime.fromisoformat('2026-07-21T02:10:40.603000+00:00')})
        with sqlite3.connect(':memory:') as connection:
            serving.initialize_sql(connection);self.assertTrue(serving.materialize_game(connection,graph_iri,bindings)['exactRoundTrip'])
            retained=[json.loads(r[0]) for r in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
            self.assertTrue(all(r in retained for r in end_rows))
            stored=serving.read_results(connection,graph_iri,'run-construction-depth')[0]
            self.assertEqual(stored['runs'][0]['value'],run['value'])
            self.assertEqual(stored['status'],'unavailable')  # Complete run, not complete player population.
        print('Walk-off runner half RML/SHACL/query/SQL proof:',workspace)


if __name__=='__main__':unittest.main()
