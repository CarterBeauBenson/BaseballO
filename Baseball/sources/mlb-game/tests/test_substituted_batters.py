"""Actual batting participation and official statistical credit stay distinct."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from pyshacl import validate
from rdflib import Dataset, Graph, RDF, URIRef
from test_metric_mapping_completion import ROOT, CONTEXT, BASE, BFO, CCO, SHAPE

sys.path.insert(0, str(ROOT/'tests'))
from test_rmlmapper_iterator_compatibility import installed_tools, materialized_subset, RR

SOURCE = ROOT/'data/raw/samples/2026-07-18/824169.json'


def source_play():
    return json.loads(SOURCE.read_bytes())['liveData']['plays']['allPlays'][31]


class SubstitutedBatters(unittest.TestCase):
    def test_actual_swings_follow_each_batter_and_input_is_immutable(self):
        play = source_play(); original = copy.deepcopy(play)
        rows = CONTEXT.batter_participation_context(play, '824169', source_consistent=True)
        self.assertEqual(play, original)
        first, last = rows['participations']
        self.assertEqual((first['playerId'],last['playerId']),('572233','664774'))
        self.assertEqual(len(first['pitchIds']),1)
        self.assertEqual(len(last['pitchIds']),4)
        self.assertEqual(rows['pitches'][first['pitchIds'][0]]['batterId'],'572233')
        self.assertTrue(first['actIri'].endswith('/batter-act/572233'))
        self.assertTrue(last['actIri'].endswith('/batter-act/664774'))

    def test_pre_turn_lineup_replacement_does_not_invent_an_earlier_act(self):
        play = source_play()
        play['playEvents'] = play['playEvents'][3:]
        for i,e in enumerate(play['playEvents']): e['index']=i
        row, = CONTEXT.batter_participation_context(play,'824169',source_consistent=True)['participations']
        self.assertEqual(row['playerId'],'664774')
        self.assertTrue(row['actIri'].endswith('/batter-act'))

    def test_pr_does_not_change_the_batter(self):
        play=source_play(); change=play['playEvents'][3]
        change['position']['abbreviation']='PR'
        result=CONTEXT.batter_participation_context(play,'824169',source_consistent=True)
        self.assertEqual(len(result['participations']),1)
        self.assertEqual({r['batterId'] for r in result['pitches'].values()},{'664774'})

    def test_replacement_without_participation_does_not_get_an_invented_act(self):
        play=source_play(); play['playEvents']=play['playEvents'][:4]
        with self.assertRaisesRegex(ValueError,'no supported batting participation'):
            CONTEXT.batter_participation_context(play,'824169',source_consistent=True)

    def test_ambiguous_substitution_cannot_publish_false_actors(self):
        for fault in ['source','final','outgoing','incoming','index','flag','position','review','time','missing-time']:
            with self.subTest(fault=fault):
                play=source_play(); change=play['playEvents'][3]
                if fault=='final': play['matchup']['batter']['id']=1
                elif fault=='outgoing': change['replacedPlayer']['id']=change['player']['id']
                elif fault=='incoming': change['player']['id']=1
                elif fault=='index': change['index']=6
                elif fault=='flag': change['isSubstitution']=False
                elif fault=='position': change['position']['abbreviation']='?'
                elif fault=='review': change['details']['hasReview']=True
                elif fault=='time': change['startTime']=play['playEvents'][1]['startTime']
                elif fault=='missing-time': del change['endTime']
                with self.assertRaises(ValueError):
                    CONTEXT.batter_participation_context(play,'824169',source_consistent=fault!='source')

    def test_real_rml_shacl_query_and_sql_preserve_both_batters(self):
        workspace=Path(tempfile.mkdtemp(prefix='baseballo-substituted-batters-'))
        (workspace/'game.json').write_bytes(SOURCE.read_bytes())
        full=workspace/'full-context.json'
        run=subprocess.run([sys.executable,str(ROOT/'scripts/pipeline/prepare-rml-context.py'),str(SOURCE),str(full)],capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
        d=json.loads(full.read_bytes())
        d['liveData']['plays']['allPlays']=[d['liveData']['plays']['allPlays'][31]]
        d['_baseballO']['runnerHistoryReconciliation']['histories']=[]
        d['_baseballO']['runnerHistoryReconciliation']['episodeMembership']=[]
        d['_baseballO']['metricPitchReviews']=[]
        d['_baseballO']['metricAutomaticAwards']=[]
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
            return validate(graph,shacl_graph=shapes,use_shapes=[str(SHAPE.PlateAppearanceShape),str(SHAPE.BatterActShape),str(SHAPE.BattingActionShape)])
        ok,_,report=conforms(g); self.assertTrue(ok,report)
        acts=list(g.subjects(RDF.type,BASE.BatterAct)); self.assertEqual(len(acts),2)
        self.assertEqual(len(set(g.subjects(RDF.type,BASE.PlateAppearance))),1)
        assigned=d['liveData']['plays']['allPlays'][0]['_baseballO']['batterParticipations']
        for row in assigned:
            person=URIRef('https://baseballontology.org/data/player/'+row['playerId'])
            act=URIRef(row['actIri'])
            self.assertIn((act,BFO.BFO_0000057,person),g)
            for pid in row['pitchIds']:
                pitch=URIRef('https://baseballontology.org/data/game/824169/pitch/'+pid)
                for swing in g.subjects(BFO.BFO_0000062,pitch):
                    if (swing,RDF.type,BASE.SwingAct) in g:
                        self.assertIn((swing,BFO.BFO_0000057,person),g)
                        self.assertIn((swing,BFO.BFO_0000132,act),g)
        prior=URIRef(assigned[0]['actIri']); later=URIRef(assigned[1]['actIri'])
        swing=next(s for s in g.subjects(BFO.BFO_0000132,prior) if (s,RDF.type,BASE.SwingAct) in g)
        broken=Graph()+g; broken.remove((swing,BFO.BFO_0000132,prior)); broken.add((swing,BFO.BFO_0000132,later))
        self.assertFalse(conforms(broken)[0],'A prior swing cannot belong to the replacement act')
        broken=Graph()+g; broken.add((prior,BFO.BFO_0000057,URIRef('https://baseballontology.org/data/player/664774')))
        self.assertFalse(conforms(broken)[0],'A Batter Act cannot merge two people')
        spec=importlib.util.spec_from_file_location('batter_serving',ROOT/'serving/metric_suite.py')
        serving=importlib.util.module_from_spec(spec);spec.loader.exec_module(serving)
        dataset=Dataset(); graph_iri='https://w3id.org/baseball/graph/game/824169'
        for triple in g: dataset.graph(URIRef(graph_iri)).add(triple)
        bindings=json.loads(dataset.query(serving.evidence_query([graph_iri])).serialize(format='json'))['results']['bindings']
        rows=serving.normalize_bindings(bindings,[graph_iri])
        inventory=serving.batting_participation(rows)
        self.assertEqual(inventory['observedPlateAppearances'],1)
        self.assertEqual(inventory['withMultipleBatters'],1)
        self.assertFalse(inventory['officialPlateAppearanceCreditVerified'])
        with sqlite3.connect(':memory:') as connection:
            serving.initialize_sql(connection)
            self.assertTrue(serving.materialize_game(connection,graph_iri,bindings)['exactRoundTrip'])
            retained=[json.loads(r[0]) for r in connection.execute('SELECT binding_json FROM metric_suite_evidence')]
            self.assertEqual(serving.batting_participation(retained),inventory)
        print('Substituted-batter RML/SHACL/query/SQL proof:',workspace)


if __name__=='__main__': unittest.main()
