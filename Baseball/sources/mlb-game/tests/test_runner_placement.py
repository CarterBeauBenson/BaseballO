"""Placed runners without movement and retirement of the offensive side."""
import copy
import json
import unittest
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from pyshacl import validate
from test_runner_boundary_anchors import A, BASE, BFO, CCO, ROOT, source, history


class RunnerPlacement(unittest.TestCase):
    def test_third_out_closes_histories_without_guessing_missing_advance(self):
        d=source(823826);result=history(d)
        self.assertTrue(all(h['status']=='reconciled' for h in result['halves']))
        gasper=next(h for h in result['histories'] if h['runnerId']=='681508' and h['inning']=='8')
        self.assertEqual(gasper['terminal'],'stranded')
        self.assertEqual(gasper['terminationAnchor'],'9fa77d6a-1e46-3dc0-826e-4caceae12644')
        self.assertEqual({r['atBatIndex'] for r in gasper['episodes']},{'60'})
        self.assertFalse(any(r['atBatIndex']=='61' and r['runnerId']=='681508' for r in result['episodeMembership']))

    def test_conflicting_bases_before_third_out_are_still_rejected(self):
        d=source(823826);p=d['liveData']['plays']['allPlays'][60]
        next(r for r in p['runners'] if r['details']['runner']['id']==677800)['movement']['end']='1B'
        result=history(d)
        self.assertIn('CONFLICTING_BASE_OCCUPANCY',{i['code'] for h in result['halves'] for i in h['issues']})

    def test_pitch_after_third_out_is_rejected(self):
        d=source(823826);p=d['liveData']['plays']['allPlays'][61]
        e=copy.deepcopy(p['playEvents'][-1]);e['index']+=1;e['count']['outs']=3
        p['playEvents'].append(e)
        result=history(d)
        self.assertTrue(result['sourceConsistency']!='consistent' or any(i['code']=='EVENT_AFTER_HALF_END' for h in result['halves'] for i in h['issues']))

    def test_positive_placement_graph_and_negative_mutations(self):
        census=A.census(json.dumps(source(823585)).encode(),'823585')
        row=next(h for h in census['history']['histories'] if not h['episodes'])
        census['history']['histories']=[row]
        exact=Graph().parse(data=A.shape_text(census),format='turtle')
        profile=Graph().parse(ROOT/'sources/mlb-game/shacl/authoritative.ttl')
        shape=Namespace('https://w3id.org/baseball/shacl/')
        pending=[shape.PersonalRunnerProcessTargetShape,shape.RunnerPlacementTargetShape,shape.JudgmentShape,shape.DecisionShape];seen=set()
        while pending:
            item=pending.pop()
            if item in seen:continue
            seen.add(item)
            for triple in profile.triples((item,None,None)):
                exact.add(triple)
                if isinstance(triple[2],BNode) or str(triple[2]).startswith(str(shape)):pending.append(triple[2])
        whole=URIRef(census['game']+'/runner-trajectory/'+row['lifetimeKey'])
        interval=URIRef(str(whole)+'/temporal-interval')
        half=URIRef(census['game']+'/inning/10/top');person=URIRef(str(BASE)+'data/player/'+row['runnerId'])
        p={k:URIRef(v) for k,v in row['placement'].items()};j=p['judgmentIri'];decision=p['decisionIri']
        g=Graph()
        for triple in ((whole,RDF.type,BFO.BFO_0000015),(whole,BFO.BFO_0000057,person),
            (whole,BFO.BFO_0000132,half),(whole,BFO.BFO_0000199,interval),(whole,BFO.BFO_0000117,j),
            (person,RDF.type,CCO.ont00001262),(half,RDF.type,BASE.HalfInning),(interval,RDF.type,BFO.BFO_0000038),
            (j,RDF.type,BASE.BaseballAdjudicationAct),(j,RDF.type,BASE.BaseballJudgmentAct),(j,BFO.BFO_0000132,whole),
            (j,CCO.ont00001986,decision),(j,CCO.ont00001921,p['ruleIri']),
            (decision,RDF.type,BASE.BaseballDecisionICE),(p['baseIri'],RDF.type,BASE.Base),
            (p['ruleIri'],RDF.type,BASE.BaseballRule),(p['recordIri'],RDF.type,BASE.BaseballEventRecord)):
            g.add(triple)
        for target in (whole,person,p['baseIri']):g.add((decision,CCO.ont00001808,target))
        for target in (j,decision):g.add((p['recordIri'],CCO.ont00001808,target))
        ident=URIRef(str(p['baseIri'])+'/identifier/source-base-code')
        g.add((ident,RDF.type,CCO.ont00000649));g.add((ident,CCO.ont00001916,p['baseIri']));g.add((ident,CCO.ont00001765,Literal('2B')))
        conforms,_,report=validate(g,shacl_graph=exact)
        self.assertTrue(conforms,report)
        for fault in ('no-placement','no-output','wrong-person','wrong-base','fake-running','safe','invented-agent'):
            with self.subTest(fault=fault):
                changed=Graph()
                for t in g:changed.add(t)
                if fault=='no-placement':changed.remove((whole,BFO.BFO_0000117,None))
                elif fault=='no-output':changed.remove((j,CCO.ont00001986,None))
                elif fault=='wrong-person':changed.remove((decision,CCO.ont00001808,person))
                elif fault=='wrong-base':changed.set((ident,CCO.ont00001765,Literal('1B')))
                elif fault=='fake-running':changed.add((j,RDF.type,BASE.BaserunningAct))
                elif fault=='safe':changed.add((j,RDF.type,BASE.SafeJudgmentAct))
                else:changed.add((j,CCO.ont00001833,person))
                self.assertFalse(validate(changed,shacl_graph=exact)[0])


if __name__=='__main__':unittest.main()
