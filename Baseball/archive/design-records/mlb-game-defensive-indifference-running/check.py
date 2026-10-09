"""Review-only D2 selector and retained-case checks; never modifies active RML."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/pipeline/prepare-rml-context.py').is_file())
spec=importlib.util.spec_from_file_location('d2_context',ROOT/'scripts/pipeline/prepare-rml-context.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


def select(play):
    if play.get('about',{}).get('isComplete') is not True:return []
    if C.accounted_runner_history_reviews(play)['issues']:return []
    index=play.get('atBatIndex');events=play.get('playEvents',[])
    if type(index) is not int:return []
    known={r['runnerIndex'] for r in C.runner_episode_evidence(play,str(index))['runnerEpisodes']}
    selected=[];positions={'1B':1,'2B':2,'3B':3,'score':4}
    for i,row in enumerate(play.get('runners',[])):
        d=row.get('details',{});m=row.get('movement',{});runner=d.get('runner',{}).get('id')
        if (d.get('eventType')!='defensive_indiff' or d.get('movementReason')!='r_defensive_indiff'
                or str(i) not in known or type(runner) is not int or type(d.get('playIndex')) is not int
                or m.get('isOut') is not False or m.get('start') not in {'1B','2B','3B'}
                or positions.get(m.get('end'),0)<=positions[m['start']]
                or d.get('rbi') is not False or type(d.get('isScoringEvent')) is not bool
                or d['isScoringEvent']!=(m.get('end')=='score')):continue
        matches=[e for e in events if e.get('index')==d['playIndex']]
        if len(matches)!=1:continue
        event=matches[0];detail=event.get('details',{})
        if (event.get('type')!='action' or event.get('isPitch') is not False
                or event.get('isBaseRunningPlay') is not True or event.get('isSubstitution') is True
                or event.get('player',{}).get('id')!=runner or detail.get('eventType')!='defensive_indiff'
                or detail.get('isInPlay') is True or detail.get('isOut') is True):continue
        duplicates=[r for r in play['runners'] if r.get('details',{}).get('playIndex')==d['playIndex']
                    and r.get('details',{}).get('runner',{}).get('id')==runner]
        if len(duplicates)!=1:continue
        selected.append(dict(atBatIndex=str(index),runnerIndex=str(i),runnerId=str(runner)))
    return selected


class DefensiveIndifference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=json.loads((HERE/'evidence.json').read_text())['witnesses']

    def test_retained_cases(self):
        for case in self.cases:
            with self.subTest(game=case['gamePk']):self.assertEqual(select(case['play']),case['expected'])

    def test_identity_outcome_and_attribution_refusals(self):
        for change in ('runner','event','duplicate','out','backward','rbi','batted','unknown-review'):
            with self.subTest(change=change):
                p=copy.deepcopy(self.cases[0]['play']);r=p['runners'][0];event=next(e for e in p['playEvents'] if e['index']==r['details']['playIndex'])
                if change=='runner':event['player']['id']=-1
                if change=='event':event['details']['eventType']='stolen_base_2b'
                if change=='duplicate':p['runners'].append(copy.deepcopy(r))
                if change=='out':r['movement']['isOut']=True
                if change=='backward':r['movement']['end']='1B'
                if change=='rbi':r['details']['rbi']=True
                if change=='batted':event['details']['isInPlay']=True
                if change=='unknown-review':event['details']['hasReview']=True;event['reviewDetails']={'isInProgress':True}
                self.assertEqual(select(p),[])


if __name__=='__main__':unittest.main()
