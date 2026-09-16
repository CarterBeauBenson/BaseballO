"""A completed strikeout is not automatically a second runner movement/out."""
import copy
import importlib.util
from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('resolution_records',ROOT/'sources/mlb-game/pipeline/runner-resolution-admission.py')
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)


def play():
    return dict(result=dict(eventType='strikeout',isOut=False),about=dict(hasReview=False),
        count=dict(strikes=3),matchup=dict(batter=dict(id=1),postOnFirst=dict(id=1)),
        playEvents=[dict(index=10,isPitch=True,count=dict(strikes=3),details=dict(isInPlay=False))],
        runners=[dict(movement=dict(originBase=None,start=None,end=None,outBase=None,isOut=None,outNumber=None),
                      details=dict(runner=dict(id=1),eventType='strikeout',playIndex=10,isScoringEvent=False)),
                 dict(movement=dict(originBase=None,start=None,end='1B',outBase=None,isOut=False,outNumber=None),
                      details=dict(runner=dict(id=1),eventType='wild_pitch',playIndex=10,isScoringEvent=False))])


class NonmovementRecords(unittest.TestCase):
    def test_empty_strikeout_record_needs_positive_matching_companion_and_poststate(self):
        for cause in ('wild_pitch','passed_ball'):
            p=play();p['runners'][1]['details']['eventType']=cause
            self.assertEqual(A.nonmovement_strikeout_records(p),{0:1})
        for fault in ('missing-companion','extra-companion','other-runner','other-event','missing-post',
                      'out','partial-boundary','not-strike-three','no-count','review','unknown-cause'):
            p=copy.deepcopy(play())
            if fault=='missing-companion':p['runners'].pop()
            elif fault=='extra-companion':p['runners'].append(copy.deepcopy(p['runners'][1]))
            elif fault=='other-runner':p['runners'][1]['details']['runner']['id']=2
            elif fault=='other-event':p['runners'][1]['details']['playIndex']=9
            elif fault=='missing-post':p['matchup'].pop('postOnFirst')
            elif fault=='out':p['result']['isOut']=True
            elif fault=='partial-boundary':p['runners'][0]['movement']['outBase']='1B'
            elif fault=='not-strike-three':p['playEvents'][0]['count']['strikes']=2
            elif fault=='no-count':p.pop('count')
            elif fault=='review':p['about']['hasReview']=True
            else:p['runners'][1]['details']['eventType']='unknown'
            self.assertEqual(A.nonmovement_strikeout_records(p),{},fault)

    def test_shacl_requires_uncaught_strike_structure_and_rejects_an_invented_extra_act(self):
        base=Namespace(A.B.BASE);bfo=Namespace('http://purl.obolibrary.org/obo/')
        cco=Namespace('https://www.commoncoreontologies.org/')
        game=A.B.BASE+'data/game/1';pa=game+'/plate-appearance/0';act=game+'/runner-act/movement/0/0'
        source=dict(game=game,resolutions=[],nonMovementRecords=[dict(pa=pa,absentAct=act)])
        shape=Graph().parse(data=A.shape_text(source),format='turtle');g=Graph()
        process=URIRef(pa+'/uncaught-third-strike');judgment=URIRef(pa+'/judgment');decision=URIRef(pa+'/decision')
        def conforms():return validate(g,shacl_graph=shape,inference='none',advanced=True)[0]
        self.assertFalse(conforms())
        g.add((process,RDF.type,base.UncaughtThirdStrikeProcess));g.add((process,bfo.BFO_0000132,URIRef(pa)))
        g.add((process,bfo.BFO_0000117,judgment));g.add((judgment,RDF.type,base.UmpireJudgmentAct))
        g.add((judgment,cco.ont00001986,decision));g.add((decision,RDF.type,base.BaseballDecisionICE))
        g.add((decision,cco.ont00001808,process));self.assertTrue(conforms())
        g.add((URIRef(act),RDF.type,base.BaserunningAct));self.assertFalse(conforms())


if __name__=='__main__':unittest.main()
