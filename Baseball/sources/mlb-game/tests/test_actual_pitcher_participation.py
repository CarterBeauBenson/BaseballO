"""P1 per-pitch attribution, source SHACL and exact correction scope."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from rdflib import Dataset, Graph, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from pyshacl import validate

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('p1_worker',ROOT/'sources/mlb-game/pipeline/targeted-pitcher-correction.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
CASE=P.W.read(P.EVIDENCE);RAW=Path(CASE['sourceWitness']['path']).read_bytes()
OBO=Namespace('http://purl.obolibrary.org/obo/')


class ActualPitcher(unittest.TestCase):
    def fixture(self):
        doc=json.loads(RAW);play=next(p for p in doc['liveData']['plays']['allPlays'] if p['atBatIndex']==38)
        return doc,play

    def test_replacement_separates_actual_pitching_from_final_pa_assignment(self):
        doc,play=self.fixture();before=copy.deepcopy(play)
        result=P.P.CONTEXT.pitcher_participation_context(doc,play)
        self.assertFalse(result['issues']);self.assertEqual(play,before)
        self.assertEqual(result['pitches'][CASE['correction']['earlierPitch']],'690928')
        self.assertEqual(set(result['pitches'].values()),{'690928','657571'})
        self.assertEqual(len([p for p in result['pitches'].values() if p=='657571']),5)
        self.assertEqual({p['playerId'] for p in result['participants']},{'690928','657571'})
        self.assertEqual(play['matchup']['pitcher']['id'],657571)

    def test_contradictory_join_never_assigns_earlier_pitch_to_final_pitcher(self):
        for fault in ('name','incoming','order','replaced-id','ambiguous-name'):
            doc,play=self.fixture();event=play['playEvents'][2]
            if fault=='name':event['details']['description']='Pitching Change: Caleb Ferguson replaces Unknown.'
            elif fault=='incoming':event['player']['id']=999999
            elif fault=='order':event['index']=1
            elif fault=='replaced-id':event['replacedPlayer']={'id':999999}
            else:
                team=doc['liveData']['boxscore']['teams']['away'];team['pitchers'].append(999999)
                team['players']['ID999999']={'person':{'fullName':'Hunter Dobbins'}}
            result=P.P.CONTEXT.pitcher_participation_context(doc,play)
            self.assertTrue(result['issues'],fault);self.assertEqual(result['pitches'],{},fault)

    def test_pre_pitch_replacement_needs_no_outgoing_pitcher_and_null_id_is_absent(self):
        doc,play=self.fixture();play['playEvents'][2]['replacedPlayer']=None
        self.assertFalse(P.P.CONTEXT.pitcher_participation_context(doc,play)['issues'])
        play['playEvents']=play['playEvents'][2:]
        play['playEvents'][0]['details']['description']='Pitching Change: Caleb Ferguson replaces Unknown.'
        for i,e in enumerate(play['playEvents']):e['index']=i
        result=P.P.CONTEXT.pitcher_participation_context(doc,play)
        self.assertFalse(result['issues']);self.assertEqual(set(result['pitches'].values()),{'657571'})

    def test_rml_slice_contains_only_selected_pitch_pa_and_persistent_role(self):
        selected=P.select(RAW,'823420')
        with tempfile.TemporaryDirectory() as temp:
            context=Path(temp)/'game-context.json';mapping=Path(temp)/'mapping.ttl'
            P.execution_inputs(RAW,'823420',selected,context,mapping)
            doc=P.W.read(context);pa=doc['liveData']['plays']['allPlays'][0]
            self.assertEqual(len(pa['playEvents']),1)
            self.assertEqual(pa['playEvents'][0]['_baseballO']['pitcherId'],'690928')
            self.assertEqual(doc['_baseballO']['pitcherRoleBearers'],[{'playerId':'690928'}])
            graph=Graph().parse(mapping);rr=Namespace('http://www.w3.org/ns/r2rml#')
            self.assertEqual({str(s).rsplit('#',1)[-1] for s in graph.subjects(RDF.type,rr.TriplesMap)},set(P.MAPS))
            self.assertNotIn('{$.',mapping.read_text())

    def test_source_shacl_rejects_old_assignment_and_missing_pa_or_role(self):
        source=P.select(RAW,'823420');old,new=P.approved_delta();graph=Graph()+new
        row=source['pitches'][0];game=P.P.BASE+'game/823420';player=URIRef(P.P.BASE+'player/'+row['playerId'])
        role=URIRef(str(player)+'/role/pitcher');pitch=URIRef(game+'/pitch/'+row['playId'])
        graph.add((player,RDF.type,URIRef('https://www.commoncoreontologies.org/ont00001262')))
        graph.add((role,RDF.type,URIRef('https://baseballontology.org/PitcherRole')))
        graph.add((role,OBO.BFO_0000197,player))
        graph.add((pitch,RDF.type,URIRef('https://baseballontology.org/PitchAct')))
        graph.add((pitch,OBO.BFO_0000132,URIRef(game+'/plate-appearance/38')))
        shapes=Graph().parse(data=P.P.shapes('823420',source),format='turtle')
        self.assertTrue(validate(graph,shacl_graph=shapes)[0])
        self.assertFalse(validate(graph+old,shacl_graph=shapes)[0])
        for triple in new:
            broken=graph-Graph().add(triple)
            self.assertFalse(validate(broken,shacl_graph=shapes)[0])
        broken=graph-Graph().add((role,OBO.BFO_0000197,player))
        self.assertFalse(validate(broken,shacl_graph=shapes)[0])

    def test_atomic_mutation_preserves_unrelated_facts_and_is_idempotent(self):
        old,new=P.approved_delta();unrelated=Graph().parse(data='<urn:keep> <urn:p> <urn:o>.',format='turtle')
        base=old+unrelated;selected=P.select(RAW,'823420')
        removed=P.removals(base,new,'823420',selected)
        self.assertEqual(len(removed),2)
        with patch.object(P.W.urllib.request,'urlopen') as send:
            send.return_value.__enter__.return_value.status=204
            P.W.apply_delta(Mock(),'urn:game',new,removed)
            request=send.call_args.args[0]
            self.assertEqual(request.get_header('Content-type'),'application/sparql-update')
            ds=Dataset();target=ds.graph(URIRef('urn:game'))
            for t in base:target.add(t)
            ds.update(request.data.decode())
            self.assertTrue(isomorphic(target,new+unrelated))
            self.assertEqual(len(P.removals(target,new,'823420',selected)),0)
        for delta in (new+Graph().parse(data='<urn:outside> <urn:p> <urn:o>.',format='turtle'),Graph()):
            with self.assertRaisesRegex(ValueError,'exceeds or omits'):P.removals(base,delta,'823420',selected)
        with self.assertRaisesRegex(ValueError,'inventory'):P.removals(base+new,new,'823420',selected)
        with patch.object(P.W.urllib.request,'urlopen') as send:
            send.return_value.__enter__.return_value.status=204
            store=Mock();store._url.return_value='http://localhost/data?graph=urn:game'
            P.W.apply_delta(store,'urn:game',new,Graph())
            self.assertEqual(send.call_args.args[0].get_header('Content-type'),'application/n-triples')


if __name__=='__main__':unittest.main()
