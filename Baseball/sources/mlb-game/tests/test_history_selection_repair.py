"""Regression cases from the five exact September 29/30 source responses."""
import copy
import json
import unittest
from pathlib import Path

from test_runner_structural_patterns import CONTEXT

CASES = json.loads((Path(__file__).parent/'fixtures/history-selection-cases.json').read_text())['cases']


def play(game, pa):
    return copy.deepcopy(next(c['play'] for c in CASES
        if c['gamePk'] == str(game) and c['play']['atBatIndex'] == pa))


class HistorySelectionRepair(unittest.TestCase):
    def test_final_reviews_keep_original_call_and_pitch_review_separate(self):
        for game, pa in [(849848,41), (849848,43), (849843,56), (849845,64), (849849,29)]:
            with self.subTest(game=game, pa=pa):
                p = play(game, pa); before = copy.deepcopy(p)
                result = CONTEXT.accounted_runner_history_reviews(p)
                self.assertEqual(result['issues'], [])
                self.assertEqual(p, before)
                self.assertNotIn('originalDecision', result.get('accountedFieldReview', {}))
                self.assertTrue(CONTEXT.accounted_runner_count_reviews(p)['issues'])
        # The earlier ABS review remains accounted independently of the final shift review.
        self.assertEqual(CONTEXT.accounted_runner_history_reviews(play(849849,29))['events'][2]['kind'], 'strike')

    def test_unknown_pending_or_conflicting_terminal_review_remains_withheld(self):
        for game, pa in [(849848,41), (849848,43), (849845,64), (849849,29)]:
            for fault in ('pending','mechanism','disposition','narrative','identity','movement'):
                with self.subTest(game=game, fault=fault):
                    p = play(game,pa)
                    if fault == 'pending': p['reviewDetails']['inProgress'] = True
                    elif fault == 'mechanism': p['reviewDetails']['reviewType'] = 'UNKNOWN'
                    elif fault == 'disposition': p['reviewDetails']['isOverturned'] = not p['reviewDetails']['isOverturned']
                    elif fault == 'narrative': p['result']['description'] = 'Review result unknown.'
                    elif fault == 'identity': p['playEvents'][-1].pop('playId')
                    else: p['runners'][-1]['movement']['isOut'] = None
                    self.assertTrue(CONTEXT.accounted_runner_history_reviews(p)['issues'])

    def test_reviewed_uncaught_third_strike_keeps_one_real_movement(self):
        p = play(849848,43)
        self.assertEqual(CONTEXT.nonmovement_strikeout_records(p), {0:1})
        self.assertEqual(len(CONTEXT.runner_episode_evidence(p,'43')['runnerEpisodes']), 1)
        for fault in ('pending','safe-companion','post-state','null-record'):
            q = copy.deepcopy(p)
            if fault == 'pending': q['reviewDetails']['inProgress'] = True
            elif fault == 'safe-companion': q['runners'][1]['movement']['end'] = '2B'
            elif fault == 'post-state': q['matchup'].pop('postOnFirst')
            else: q['runners'][0]['movement']['isOut'] = False
            self.assertEqual(CONTEXT.nonmovement_strikeout_records(q), {}, fault)

    def test_pickoff_requires_association_person_count_and_final_out(self):
        p = play(849843,56)
        self.assertTrue(CONTEXT.completed_pickoff_review(p,2)['overturned'])
        for fault in ('association','person','count','out','text','pending'):
            q = copy.deepcopy(p); event = q['playEvents'][2]
            if fault == 'association': event['actionPlayId'] = 'unmatched'
            elif fault == 'person': event['player']['id'] += 1
            elif fault == 'count': event['count']['outs'] += 1
            elif fault == 'out': q['runners'][0]['movement']['isOut'] = False
            elif fault == 'text': event['details']['description'] = event['details']['description'].replace('Dustin Harris','Different Person')
            else: event['reviewDetails']['inProgress'] = True
            self.assertIsNone(CONTEXT.completed_pickoff_review(q,2), fault)

    def test_overlapping_passed_ball_needs_independent_association_and_count(self):
        p = play(849843,41); earlier, following = p['playEvents'][1], p['playEvents'][3]
        self.assertLess(following['startTime'], earlier['endTime'])
        self.assertTrue(CONTEXT.reconciled_action_pitch_overlap(p,earlier,following))
        for fault in ('association','count','unknown-call','runner-effect','another-pa'):
            q = copy.deepcopy(p); a,b = q['playEvents'][1],q['playEvents'][3]
            if fault == 'association': a['actionPlayId'] = 'unmatched'
            elif fault == 'count': b['count']['strikes'] = 2
            elif fault == 'unknown-call': b['details']['call']['code'] = 'unknown'
            elif fault == 'runner-effect': q['runners'][0]['details']['playIndex'] = b['index']
            else: a = copy.deepcopy(a)
            self.assertFalse(CONTEXT.reconciled_action_pitch_overlap(q,a,b), fault)


if __name__ == '__main__': unittest.main()
