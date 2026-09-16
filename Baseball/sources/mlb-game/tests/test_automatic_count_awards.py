"""Q5 source selection and actual RML/SHACL proof, never live admission by test."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import unittest

from pyshacl import validate
from rdflib import Dataset, Graph, RDF, URIRef
from test_metric_mapping_completion import ROOT, CONTEXT, BASE, BFO, CCO, SHAPE, selected

sys.path.insert(0, str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR


def play(game='824088', pa=33):
    d = json.loads((ROOT/f'data/raw/samples/2026-07-18/{game}.json').read_bytes())
    return d['liveData']['plays']['allPlays'][pa]


class AutomaticAwardSelection(unittest.TestCase):
    def test_separate_completed_affirmed_pitch_review_does_not_hide_clock_award(self):
        raw=(ROOT/'data/raw/samples/2026-07-20/824087.json').read_bytes()
        p=json.loads(raw)['liveData']['plays']['allPlays'][32]
        original=copy.deepcopy(p)
        _,result=selected([p])
        award,=result['automaticAwards']
        self.assertEqual(award['playId'],'6e1edbb8-f263-41d9-9613-56400d396d2f')
        self.assertEqual(award['strikesAfter'],1)
        self.assertEqual(len(result['pitchReviews']),1)
        self.assertEqual(p,original)
        for fault in ('overturned','in-progress','count','award-review'):
            changed=copy.deepcopy(p)
            if fault=='overturned':changed['playEvents'][1]['reviewDetails']['isOverturned']=True
            elif fault=='in-progress':changed['playEvents'][1]['reviewDetails']['inProgress']=True
            elif fault=='count':changed['playEvents'][1]['count']['strikes']=1
            else:changed['playEvents'][0]['reviewDetails']=changed['playEvents'][1]['reviewDetails']
            _,denied=selected([changed])
            self.assertFalse(denied['automaticAwards'],fault)
            self.assertIn('UNRESOLVED_COUNT_REVIEW',{r['reason'] for r in denied['withheldAutomaticAwards']})

    def test_real_ball_and_strike_are_awards_with_neighbor_pitches(self):
        for p, kind in [(play(),'strike'), (play('823116',76),'ball')]:
            original = copy.deepcopy(p)
            d,e = selected([p])
            row, = e['automaticAwards']
            self.assertEqual(row['kind'], kind)
            self.assertIn('nextPitchIri', row)
            self.assertNotIn('previousPitchIri', row)
            self.assertNotIn('umpireId', row)
            self.assertEqual(p, original)
            self.assertEqual(d['_baseballO']['metricAutomaticAwards'], e['automaticAwards'])

    def test_ambiguous_or_contradictory_source_withholds_awards(self):
        for fault in ['pitch','id','count','flag','violation','review','time','index','source','incomplete']:
            p=play(); e=p['playEvents'][0]
            if fault=='pitch': e['isPitch']=True
            elif fault=='id': e['playId']=p['playEvents'][1]['playId']
            elif fault=='count': e['count']['strikes']=2
            elif fault=='flag': e['details']['isBall']=True
            elif fault=='violation': e['details']['violation']['type']='pitcher_pitch_timer'
            elif fault=='review': p['about']['hasReview']=True
            elif fault=='time': e['endTime']=p['playEvents'][1]['endTime']
            elif fault=='index': e['index']=1
            elif fault=='incomplete': p['about']['isComplete']=False
            _, result=selected([p], consistent=fault!='source')
            self.assertFalse(result['automaticAwards'], fault)
            self.assertEqual(len(result['withheldAutomaticAwards']),1,fault)

    def test_provider_intentional_walk_rows_are_not_four_judgments(self):
        d=json.loads((ROOT/'data/raw/samples/2026-07-16/823440.json').read_bytes())
        _, result=selected([d['liveData']['plays']['allPlays'][33]])
        self.assertFalse(result['automaticAwards'])
        self.assertEqual(len(result['withheldAutomaticAwards']),4)
        self.assertEqual({r['reason'] for r in result['withheldAutomaticAwards']},{'AUTOMATIC_AWARD_KIND_NOT_ADMITTED'})

    def test_automatic_second_strike_does_not_create_a_third_foul_strike(self):
        p=play()
        clock=copy.deepcopy(p['playEvents'][0])
        pitched=copy.deepcopy(p['playEvents'][1])
        events=[]
        for i,(code,strikes,is_pitch) in enumerate([('C',1,True),('AC',2,False),('F',2,True),('X',2,True)]):
            e=copy.deepcopy(pitched if is_pitch else clock)
            e.update(index=i, playId='test-'+str(i), startTime=f'2026-07-18T21:22:{10+i*2:02d}Z', endTime=f'2026-07-18T21:22:{11+i*2:02d}Z')
            e['count'].update(balls=0,strikes=strikes)
            e['details']['call']['code']=code
            e['details'].update(isBall=False,isStrike=code!='X',isInPlay=code=='X')
            events.append(e)
        p['playEvents']=events
        _,result=selected([p])
        self.assertEqual(len(result['automaticAwards']),1)
        self.assertFalse(result['countedFouls'])
        self.assertEqual(result['automaticAwards'][0]['strikesAfter'],2)


class AutomaticAwardRml(unittest.TestCase):
    def test_strict_mapper_handles_absent_neighbors_without_dropping_awards(self):
        source=ROOT/'data/raw/samples/2026-07-20/824087.json'
        raw=source.read_bytes();p=json.loads(raw)['liveData']['plays']['allPlays'][32]
        _,selected_rows=selected([p]);row=selected_rows['automaticAwards'][0]
        mapping_graph=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        maps=[m for m in mapping_graph.subjects(RDF.type,URIRef(RR+'TriplesMap')) if '#AutomaticCount' in str(m)]
        java,mapper=installed_tools()
        with tempfile.TemporaryDirectory(prefix='baseballo-q5-optional-neighbor-') as directory:
            workspace=Path(directory);(workspace/'game.json').write_bytes(raw)
            mapping=materialized_subset(mapping_graph,maps,workspace)
            # An isolated one-record execution checks both boundary cases.
            for side in ('nextPitchIri','previousPitchIri',None):
                with self.subTest(neighbor=side):
                    item={k:v for k,v in row.items() if k not in ('previousPitchIri','nextPitchIri')}
                    if side:item[side]='https://baseballontology.org/data/game/824087/pitch/neighbor'
                    (workspace/'game-context.json').write_text(json.dumps({'_baseballO':{'metricAutomaticAwards':[item]}}),encoding='utf-8')
                    output=workspace/'award.ttl'
                    run=subprocess.run([str(java),'-Xmx256m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),
                        '-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True)
                    self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
                    g=Graph().parse(output);award=URIRef(row['processIri'])
                    self.assertIn((award,RDF.type,BASE.StrikeProcess),g)
                    edges=set(g.subject_objects(BFO.BFO_0000063))
                    expected=set() if side is None else {(award,URIRef(item[side])) if side=='nextPitchIri' else (URIRef(item[side]),award)}
                    self.assertEqual(edges,expected)
        self.assertEqual(source.read_bytes(),raw)

    def test_real_one_pa_rml_and_adversarial_source_shacl(self):
        workspace=Path(tempfile.mkdtemp(prefix='baseballo-auto-count-one-pa-'))
        # This fixture has an actual automatic strike and no count review.
        # The separate reconciliation regression covers 824088's repaired
        # unplayed-bottom-ninth membership bug.
        source=ROOT/'data/raw/samples/2026-07-22/823518.json'
        (workspace/'game.json').write_bytes(source.read_bytes())
        full=workspace/'full-context.json'
        run=subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(source),str(full)],capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
        d=json.loads(full.read_bytes())
        self.assertEqual(d['_baseballO']['runnerHistoryReconciliation']['sourceConsistency'],'consistent')
        d['liveData']['plays']['allPlays']=[d['liveData']['plays']['allPlays'][45]]
        d['_baseballO']['runnerHistoryReconciliation']['histories']=[]
        d['_baseballO']['runnerHistoryReconciliation']['episodeMembership']=[]
        d['_baseballO']['metricPitchReviews']=[]
        d['_baseballO']['metricAutomaticAwards']=[r for r in d['_baseballO']['metricAutomaticAwards'] if r['atBatIndex']=='45']
        row,=d['_baseballO']['metricAutomaticAwards']
        (workspace/'game-context.json').write_text(json.dumps(d),encoding='utf-8')
        mapping_graph=Graph().parse(ROOT/'sources/mlb-game/mapping/mlb-game.rml.ttl')
        maps=list(mapping_graph.subjects(RDF.type,URIRef(RR+'TriplesMap')))
        mapping=materialized_subset(mapping_graph,maps,workspace)
        java,mapper=installed_tools(); output=workspace/'one-pa.ttl'
        run=subprocess.run([str(java),'-Xmx512m','-jar',str(mapper),'-m',str(mapping),'-o',str(output),'-s','turtle','-b','https://baseballontology.org/mapping/mlb-direct','--strict'],cwd=workspace,capture_output=True)
        (workspace/'mapper.log').write_bytes(run.stdout+run.stderr)
        self.assertEqual(run.returncode,0,str(workspace/'mapper.log'))
        g=Graph().parse(output)
        shapes=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')
        def conforms(graph):
            return validate(graph,shacl_graph=shapes,use_shapes=[str(SHAPE.AutomaticCountAwardRecordShape)])
        ok,_,report=conforms(g)
        self.assertTrue(ok,report)
        self.assertIn((URIRef(row['processIri']),RDF.type,BASE.StrikeProcess),g)
        self.assertEqual(len(set(g.subjects(RDF.type,BASE.PitchAct))),sum(e.get('isPitch') is True for e in d['liveData']['plays']['allPlays'][0]['playEvents']))
        self.assertIn((URIRef(row['processIri']),BFO.BFO_0000063,URIRef(row['nextPitchIri'])),g)
        # Exercise the actual RML -> canonical query -> SQL boundary. This
        # one-PA fixture must not acquire a complete player-population flag.
        spec=importlib.util.spec_from_file_location('award_serving',ROOT/'serving/metric_suite.py')
        serving=importlib.util.module_from_spec(spec);spec.loader.exec_module(serving)
        dataset=Dataset(); graph_iri='https://w3id.org/baseball/graph/game/823518'
        for triple in g: dataset.graph(URIRef(graph_iri)).add(triple)
        bindings=json.loads(dataset.query(serving.evidence_query([graph_iri])).serialize(format='json'))['results']['bindings']
        normalized=serving.normalize_bindings(bindings,[graph_iri])
        award,= [r for r in normalized if r['kind']=='automatic_count_award']
        self.assertEqual(award['entity'],row['processIri'])
        self.assertEqual(award['countAwardKind'],'strike')
        self.assertEqual(award['nextPitch'],row['nextPitchIri'])
        with sqlite3.connect(':memory:') as connection:
            serving.initialize_sql(connection)
            summary=serving.materialize_game(connection,graph_iri,bindings)
            self.assertTrue(summary['exactRoundTrip'])
            retained=[json.loads(r[0]) for r in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
            self.assertIn(award,retained)
            self.assertEqual(serving.read_results(connection,graph_iri,'recovery-quality')[0]['status'],'unavailable')
        for fault in ['missing-decision','wrong-kind','fake-pitch','fake-agent','cycle','wrong-pa']:
            broken=Graph()+g
            if fault=='missing-decision': broken.remove((URIRef(row['judgmentIri']),CCO.ont00001986,None))
            elif fault=='wrong-kind': broken.add((URIRef(row['processIri']),RDF.type,BASE.BallProcess))
            elif fault=='fake-pitch': broken.add((URIRef(row['processIri'].replace('/process/strike/','/pitch/')),RDF.type,BASE.PitchAct))
            elif fault=='fake-agent': broken.add((URIRef(row['judgmentIri']),CCO.ont00001833,URIRef('urn:guessed-umpire')))
            elif fault=='cycle': broken.add((URIRef(row['nextPitchIri']),BFO.BFO_0000063,URIRef(row['processIri'])))
            elif fault=='wrong-pa': broken.remove((URIRef(row['nextPitchIri']),BFO.BFO_0000132,None))
            self.assertFalse(conforms(broken)[0],fault)
        print('Automatic-count one-PA RML and SHACL proof:',workspace)


if __name__=='__main__': unittest.main()
