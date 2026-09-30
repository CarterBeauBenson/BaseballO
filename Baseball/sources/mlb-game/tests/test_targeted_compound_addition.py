"""K1 preserves existing identities and rejects mismatched out evidence."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph,Namespace,RDF,URIRef
from pyshacl import validate

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('k1',ROOT/'sources/mlb-game/pipeline/targeted-compound-addition.py')
K=importlib.util.module_from_spec(spec);spec.loader.exec_module(K)
BASE=Namespace('https://baseballontology.org/');OBO=Namespace('http://purl.obolibrary.org/obo/')
CCO=Namespace('https://www.commoncoreontologies.org/')


def fixture():
    return json.loads((ROOT/'data/raw/samples/2026-07-21/824895.json').read_bytes())


class CompoundAddition(unittest.TestCase):
    def test_called_strike_wording_and_completed_earlier_pitch_review(self):
        play=fixture()['liveData']['plays']['allPlays'][22]
        expected=K.C.compound_double_play_parts(play)
        play['result']['description']=play['result']['description'].replace('strikes out swinging','called out on strikes')
        event=play['playEvents'][0]
        event['details']['hasReview']=True
        event['reviewDetails']=dict(inProgress=False,isOverturned=False,reviewType='MJ')
        self.assertEqual(K.C.compound_double_play_parts(play),expected)
        event['reviewDetails']['inProgress']=True
        self.assertEqual(K.C.compound_double_play_parts(play),[])

    def test_real_source_selects_exact_existing_parts_and_b1_whole(self):
        doc=fixture();play=doc['liveData']['plays']['allPlays'][22];before=copy.deepcopy(play)
        parts=K.C.compound_double_play_parts(play)
        self.assertEqual(parts,[dict(atBatIndex='22',runnerIndex='0',runnerId='592518'),
                                dict(atBatIndex='22',runnerIndex='1',runnerId='630105')])
        self.assertEqual(play,before)
        census=K.W.C.B.census(json.dumps(doc).encode(),'824895')
        self.assertEqual(next(r for r in census['members'] if r['atBatIndex']==22)['resultType'],str(BASE.DoublePlayProcess))

    def test_unknown_continuity_or_wrong_membership_is_not_selected(self):
        for fault in ('narrative','participant','event','third-out','review','extra-out','safe','pitch'):
            p=fixture()['liveData']['plays']['allPlays'][22]
            if fault=='narrative':p['result']['description']='Strikeout Double Play'
            elif fault=='participant':p['runners'][1]['details']['runner']['id']=p['matchup']['batter']['id']
            elif fault=='event':p['runners'][1]['details']['playIndex']=0
            elif fault=='third-out':p['count']['outs']=3
            elif fault=='review':p['about']['hasReview']=True
            elif fault=='extra-out':p['runners'].append(copy.deepcopy(p['runners'][1]))
            elif fault=='safe':p['runners'][1]['movement']['isOut']=False
            else:p['playEvents'][-1]['isPitch']=False
            self.assertEqual(K.C.compound_double_play_parts(p),[],fault)

    def test_addition_cannot_manufacture_missing_referents(self):
        p=fixture()['liveData']['plays']['allPlays'][22];game='https://baseballontology.org/data/game/824895'
        selected=dict(pa=game+'/plate-appearance/22',result=game+'/plate-appearance/22/result',parts=K.C.compound_double_play_parts(p))
        shape=Graph().parse(data=K.shapes('824895',selected),format='turtle')
        result,pa=URIRef(selected['result']),URIRef(selected['pa']);graph=Graph()
        def pattern(entity,judgment_type,decision_type):
            judgment=URIRef(str(entity)+'/j');decision=URIRef(str(entity)+'/d');record=URIRef(str(entity)+'/r')
            for triple in [(entity,OBO.BFO_0000117,judgment),(judgment,RDF.type,judgment_type),
                (judgment,CCO.ont00001986,decision),(decision,RDF.type,decision_type),
                (decision,CCO.ont00001808,entity),(record,RDF.type,BASE.BaseballEventRecord)]:graph.add(triple)
            for node in (entity,judgment,decision):graph.add((record,CCO.ont00001808,node))
        graph.add((pa,RDF.type,BASE.PlateAppearance))
        for kind in (BASE.DoublePlayProcess,BASE.BaseballInstitutionalProcess):graph.add((result,RDF.type,kind))
        graph.add((result,OBO.BFO_0000132,pa));pattern(result,BASE.BaseballAdjudicationAct,BASE.BaseballDecisionICE)
        for part in selected['parts']:
            out=URIRef(game+'/runner-resolution/out/22/'+part['runnerIndex']);person=URIRef(str(BASE)+'data/player/'+part['runnerId'])
            graph.add((result,CCO.ont00001777,out));graph.add((out,OBO.BFO_0000132,pa));graph.add((out,OBO.BFO_0000057,person))
            for kind in (BASE.OutProcess,BASE.RunnerResolutionProcess):graph.add((out,RDF.type,kind))
            pattern(out,BASE.OutJudgmentAct,BASE.OutDecisionICE)
        self.assertTrue(validate(graph,shacl_graph=shape)[0])
        graph.remove((out,OBO.BFO_0000057,person))
        self.assertFalse(validate(graph,shacl_graph=shape)[0])
        with tempfile.TemporaryDirectory() as directory:
            context=Path(directory)/'game-context.json';mapping=Path(directory)/'addition.rml.ttl'
            K.execution_inputs(b'', '824895',selected,context,mapping)
            mapped=Graph().parse(mapping);rr=Namespace('http://www.w3.org/ns/r2rml#')
            self.assertEqual(set(mapped.objects(None,rr['class'])),{BASE.DoublePlayProcess})
            self.assertNotIn('{$.gamePk}',mapping.read_text())

    def test_bounded_inventory_requires_first_game_and_reuses_acquisition(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(K,'fingerprint',return_value='v'):
            state=Path(directory)
            self.assertEqual(K.next_game(state),'823327')
            K.W.atomic(state/'pipeline/control/mlb-game/compound-addition/823327.json',dict(status='failed',attempts=2,implementationSha256='v'))
            self.assertIsNone(K.next_game(state))
            with self.assertRaises(ValueError):K.acquire(state,'824895')


if __name__=='__main__':unittest.main()
