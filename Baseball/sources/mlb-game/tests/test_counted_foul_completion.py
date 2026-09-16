"""M3/M4 actual-feed witnesses and mutations at each accepted boundary."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_metric_mapping_completion import CONTEXT, ROOT


class CountedFoulCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix='baseballo-m3m4-source-'))
        target = cls.workspace/'context.json'
        subprocess.run([sys.executable, str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
            str(ROOT/'data/raw/samples/2026-07-20/824087.json'), str(target)], check=True, capture_output=True)
        cls.context = json.loads(target.read_bytes())

    def selected(self, pa, mutate=lambda p,d: None):
        d = copy.deepcopy(self.context)
        p = d['liveData']['plays']['allPlays'][pa]
        d['liveData']['plays']['allPlays'] = [p]
        mutate(p,d)
        return CONTEXT.metric_pitch_context(d)

    def test_four_real_omissions_now_selected(self):
        for pa,index in [(37,3),(64,2),(65,2),(72,0)]:
            evidence=self.selected(pa)
            self.assertEqual([r['eventIndex'] for r in evidence['countedFouls']], [index])
            self.assertEqual(len(evidence['prefixInventory']),len(self.context['liveData']['plays']['allPlays'][pa]['playEvents']))

    def test_steal_requires_exact_safe_runner_and_unchanged_count(self):
        for fault in ('runner','duplicate','out','score','counter'):
            def change(p,d):
                if fault=='runner':p['playEvents'][2]['player']['id']=1
                if fault=='duplicate':p['runners'].append(copy.deepcopy(p['runners'][0]))
                if fault=='out':p['runners'][0]['movement']['isOut']=True
                if fault=='score':p['runners'][0]['details']['isScoringEvent']=True
                if fault=='counter':p['playEvents'][2]['count']['strikes']=0
            self.assertFalse(self.selected(37,change)['countedFouls'],fault)

    def test_initial_pitcher_change_requires_roster_identity_and_actual_agency(self):
        for fault in ('unrostered','outgoing','agency','mid-count','batter'):
            def change(p,d):
                if fault=='unrostered':d['liveData']['boxscore']['teams']['home']['pitchers'].remove(656638)
                if fault=='outgoing':p['playEvents'][0]['details']['description']='Pitching Change: Alex Lange replaces Someone Else.'
                if fault=='agency':p['playEvents'][1]['_baseballO']['pitcherId']='608379'
                if fault=='mid-count':p['playEvents'][0]['count']['strikes']=1
                if fault=='batter':p['playEvents'][0]['details']['eventType']='offensive_substitution'
            self.assertFalse(self.selected(64,change)['countedFouls'],fault)

    def test_completed_review_does_not_expand_m2_overturn_mapping(self):
        evidence=self.selected(65)
        self.assertEqual(len(evidence['countedFouls']),1)
        self.assertFalse(evidence['pitchReviews'])
        for fault in ('progress','unknown-disposition','mechanism','call-flags','count','duplicate-id'):
            def change(p,d):
                e=p['playEvents'][1]
                if fault=='progress':e['reviewDetails']['inProgress']=True
                if fault=='unknown-disposition':e['reviewDetails'].pop('isOverturned')
                if fault=='mechanism':e['reviewDetails']['reviewType']='MO'
                if fault=='call-flags':e['details']['isStrike']=True
                if fault=='count':e['count']['balls']=2
                if fault=='duplicate-id':p['playEvents'][0]['playId']=e['playId']
            self.assertFalse(self.selected(65,change)['countedFouls'],fault)

    def test_bunt_requires_contact_count_and_actual_participants(self):
        for fault in ('contact','batter','pitcher','flags','counter','third-without-strikeout'):
            def change(p,d):
                e=p['playEvents'][0]
                if fault=='contact':e['_baseballO']['matchesBuntContactSource']=False
                if fault=='batter':e['_baseballO'].pop('batterId')
                if fault=='pitcher':e['_baseballO'].pop('pitcherId')
                if fault=='flags':e['details']['isStrike']=False
                if fault=='counter':e['count']['balls']=1
                if fault=='third-without-strikeout':e['count']['strikes']=3
            self.assertFalse(self.selected(72,change)['countedFouls'],fault)

    def test_held_count_and_ambiguous_order_stay_withheld(self):
        for pa,index in [(37,3),(64,2),(65,2)]:
            evidence=self.selected(pa,lambda p,d: p['playEvents'][index].update(startTime=p['playEvents'][index-1]['startTime']))
            self.assertFalse(evidence['countedFouls'])
        evidence=self.selected(64)
        self.assertTrue(any(r['eventIndex']==4 and r['reason']=='NO_SECOND_STRIKE_INCREMENT' for r in evidence['withheldFouls']))


if __name__=='__main__':
    unittest.main()
