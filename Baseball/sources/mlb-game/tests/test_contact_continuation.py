"""B2 real source selection and adversarial owning-SHACL conformance."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('b2', ROOT/'sources/mlb-game/pipeline/contact-continuation-admission.py')
B2 = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(B2)
BASE = Namespace('https://baseballontology.org/')
BFO = Namespace('http://purl.obolibrary.org/obo/')


class ContactContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT/'data/raw/samples/2026-08-23/824315.json').read_bytes()
        cls.play = json.loads(cls.raw)['liveData']['plays']['allPlays'][6]
        cls.histories = B2.CONTEXT.personal_runner_histories(cls.raw)

    def test_six_real_segments_keep_three_personal_histories(self):
        links = B2.CONTEXT.batted_runner_resolution_links(self.play, '6', self.histories)
        self.assertEqual([(r['runnerIndex'],r['resolutionKind']) for r in links],
                         [('0','reach'),('1','advance'),('2','advance'),('3','out'),('4','advance'),('5','score')])
        self.assertEqual(len({r['lifetimeKey'] for r in self.histories['episodeMembership'] if r['atBatIndex']=='6'}),3)
        self.assertEqual(B2.CONTEXT.batted_runner_resolution_links(self.play,'6'),[])

    def test_ambiguous_or_independent_effects_withhold_whole_contact(self):
        for fault in ('independent','missing-membership','review','substitution','duplicate-index','conflicting-result','wrong-person'):
            with self.subTest(fault=fault):
                play, histories=copy.deepcopy(self.play),copy.deepcopy(self.histories)
                if fault=='independent': play['runners'][5]['details']['eventType']='passed_ball'
                elif fault=='missing-membership': histories['episodeMembership']=[m for m in histories['episodeMembership'] if not (m['atBatIndex']=='6' and m['runnerIndex']=='5')]
                elif fault=='review': play['playEvents'][0]['details']['hasReview']=True
                elif fault=='substitution': play['playEvents'][0]['isSubstitution']=True
                elif fault=='duplicate-index': play['playEvents'][1]['index']=0
                elif fault=='conflicting-result': play['runners'][3]['details']['eventType']='field_error'
                elif fault=='wrong-person': play['runners'][5]['details']['runner']['id']=123
                self.assertEqual(B2.CONTEXT.batted_runner_resolution_links(play,'6',histories),[])

    def test_shacl_requires_all_six_members_and_no_extra_resolution(self):
        source=B2.census(self.raw,'824315')
        play=next(p for p in source['plays'] if p['atBatIndex']=='6')
        source['plays']=[play]
        shapes=Graph().parse(data=B2.shape_text(source),format='turtle')
        root='https://baseballontology.org/data/game/824315'
        target=URIRef(root+'/process/batted-ball-play/'+play['playId'])
        graph=Graph(); graph.add((target,RDF.type,BASE.BattedBallPlayProcess))
        for row in play['links']:
            r=URIRef(root+'/runner-resolution/'+row['resolutionKind']+'/6/'+row['runnerIndex'])
            graph.add((target,BFO.BFO_0000117,r)); graph.add((r,RDF.type,BASE.RunnerResolutionProcess))
        for row in play['memberships']:
            graph.add((URIRef(root+'/runner-trajectory/'+row['lifetimeKey']),BFO.BFO_0000117,
                       URIRef(root+'/runner-episode/6/'+row['runnerIndex'])))
        self.assertTrue(validate(graph,shacl_graph=shapes)[0])
        required=(target,BFO.BFO_0000117,URIRef(root+'/runner-resolution/score/6/5'))
        graph.remove(required)
        self.assertFalse(validate(graph,shacl_graph=shapes)[0])
        graph.add(required)
        graph.add((target,BFO.BFO_0000117,URIRef(root+'/extra')))
        graph.add((URIRef(root+'/extra'),RDF.type,BASE.RunnerResolutionProcess))
        self.assertFalse(validate(graph,shacl_graph=shapes)[0])

    def test_separate_steal_before_reviewed_contact_keeps_both_contributions_separate(self):
        raw=(ROOT/'data/raw/samples/2026-08-25/823098.json').read_bytes()
        histories=B2.CONTEXT.personal_runner_histories(raw)
        play=json.loads(raw)['liveData']['plays']['allPlays'][45]
        links=B2.CONTEXT.batted_runner_resolution_links(play,'45',histories)
        self.assertEqual([(r['runnerIndex'],r['resolutionKind']) for r in links],
                         [('1','reach'),('2','score'),('3','out')])
        # Row 0 remains in the personal history, outside contact membership.
        self.assertTrue(any(m['atBatIndex']=='45' and m['runnerIndex']=='0' for m in histories['episodeMembership']))
        for fault in ('same-event','unknown-prefix','missing-prefix-membership','pending-review','substitution'):
            p,h=copy.deepcopy(play),copy.deepcopy(histories)
            if fault=='same-event':p['runners'][0]['details']['playIndex']=8
            elif fault=='unknown-prefix':p['playEvents'][7]['details']['eventType']='unknown'
            elif fault=='missing-prefix-membership':h['episodeMembership']=[m for m in h['episodeMembership'] if not (m['atBatIndex']=='45' and m['runnerIndex']=='0')]
            elif fault=='pending-review':p['reviewDetails']['inProgress']=True
            else:p['playEvents'][5]['isSubstitution']=True
            self.assertEqual(B2.CONTEXT.batted_runner_resolution_links(p,'45',h),[],fault)

    def test_owning_shape_rejects_steal_resolution_inside_later_contact(self):
        raw=(ROOT/'data/raw/samples/2026-08-25/823098.json').read_bytes()
        source=B2.census(raw,'823098');source['plays']=[p for p in source['plays'] if p['atBatIndex']=='45']
        play,=source['plays'];self.assertEqual(play['status'],'admitted')
        shapes=Graph().parse(data=B2.shape_text(source),format='turtle')
        root='https://baseballontology.org/data/game/823098';target=URIRef(root+'/process/batted-ball-play/'+play['playId'])
        graph=Graph();graph.add((target,RDF.type,BASE.BattedBallPlayProcess))
        for row in play['links']:
            r=URIRef(root+'/runner-resolution/'+row['resolutionKind']+'/45/'+row['runnerIndex'])
            graph.add((target,BFO.BFO_0000117,r));graph.add((r,RDF.type,BASE.RunnerResolutionProcess))
        for row in play['memberships']:
            graph.add((URIRef(root+'/runner-trajectory/'+row['lifetimeKey']),BFO.BFO_0000117,
                       URIRef(root+'/runner-episode/45/'+row['runnerIndex'])))
        self.assertTrue(validate(graph,shacl_graph=shapes)[0])
        steal=URIRef(root+'/runner-resolution/advance/45/0')
        graph.add((steal,RDF.type,BASE.RunnerResolutionProcess));graph.add((target,BFO.BFO_0000117,steal))
        self.assertFalse(validate(graph,shacl_graph=shapes)[0])


if __name__=='__main__': unittest.main()
