"""Approved EG2 selectors over reviewed source excerpts, never ingestion inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('eg2_context',ROOT/'scripts/pipeline/prepare-rml-context.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
WITNESSES=json.loads((ROOT/'archive/design-records/mlb-game-empty-game-remaining-selections/evidence.json').read_text())['witnesses']


class RemainingSelections(unittest.TestCase):
    def witnesses(self, selection):
        return [copy.deepcopy(w) for w in WITNESSES if w['selection']==selection]

    def test_contact_accepts_verified_initial_ph_and_rejects_midturn_or_missing_history(self):
        w,=self.witnesses('EG2a');p=w['play'];pa=str(w['atBatIndex'])
        histories=dict(sourceConsistency='consistent',episodeMembership=[dict(atBatIndex=pa,
            runnerIndex=str(i),runnerId=str(r['details']['runner']['id']),lifetimeKey='whole-'+str(r['details']['runner']['id']))
            for i,r in enumerate(p['runners'])])
        self.assertEqual(len(C.batted_runner_resolution_links(p,pa,histories)),len(p['runners']))
        for mutation in ('count','incoming','history','review'):
            play=copy.deepcopy(p);proof=copy.deepcopy(histories)
            if mutation=='count':play['playEvents'][0]['count']['strikes']=1
            elif mutation=='incoming':play['playEvents'][0]['player']['id']=1
            elif mutation=='history':proof['episodeMembership'].pop()
            else:play['about']['hasReview']=True
            self.assertEqual(C.batted_runner_resolution_links(play,pa,proof),[],mutation)

    def test_placeholder_with_second_base_continuation_preserves_two_actual_moves(self):
        w,=self.witnesses('EG2b');p=w['play']
        selected=C.nonmovement_strikeout_records(p)
        self.assertEqual(len(selected),1)
        self.assertEqual(len(C.runner_episode_evidence(p,str(w['atBatIndex']))['runnerEpisodes']),2)
        for change in ('destination','post','event','out'):
            play=copy.deepcopy(p)
            extra=next(r for r in play['runners'] if r['movement'].get('start')=='1B')
            if change=='destination':extra['movement']['end']='3B'
            elif change=='post':play['matchup']['postOnSecond']['id']=1
            elif change=='event':extra['details']['playIndex']+=1
            else:extra['movement']['isOut']=True
            self.assertEqual(C.nonmovement_strikeout_records(play),{},change)

    def test_compound_uses_reconciled_review_and_keeps_two_distinct_outs(self):
        w,=self.witnesses('EG2c');p=w['play']
        self.assertEqual(len(C.compound_double_play_parts(p)),2)
        for change in ('pending','direction','outs'):
            play=copy.deepcopy(p)
            if change=='pending':play['reviewDetails']['inProgress']=True
            elif change=='direction':play['reviewDetails']['isOverturned']=True
            else:play['count']['outs']-=1
            self.assertEqual(C.compound_double_play_parts(play),[],change)

    def test_hbp_survives_an_earlier_reconciled_review_without_reclassifying_it(self):
        for w in self.witnesses('EG2d'):
            p=w['play'];pa=str(w['atBatIndex'])
            selected=C.runner_metric_evidence(p,pa,'2026')['awardAdvances']
            self.assertTrue(selected,w['gamePk'])
            self.assertEqual({r['runnerId'] for r in selected},{str(p['matchup']['batter']['id'])})
            reviewed=next(e for e in p['playEvents'] if e.get('reviewDetails'))
            reviewed['reviewDetails']['inProgress']=True
            self.assertEqual(C.runner_metric_evidence(p,pa,'2026')['awardAdvances'],[])

    def test_disengagement_balk_requires_explicit_violation_and_exact_one_base(self):
        for w in self.witnesses('EG2e'):
            p=w['play'];pa=str(w['atBatIndex'])
            rows=C.balk_runner_evidence(p,pa)
            self.assertEqual(len(rows),sum(r['details']['eventType']=='forced_balk' for r in p['runners']))
            event=next(e for e in p['playEvents'] if e.get('details',{}).get('eventType')=='forced_balk')
            event['details']['violation']['type']='pitch_timer'
            self.assertEqual(C.balk_runner_evidence(p,pa),[])


if __name__=='__main__':unittest.main()
