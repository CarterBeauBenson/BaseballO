"""Reconcile explicit upheld tag outcomes without inventing review assertions."""
import copy
import json
import unittest

from test_runner_structural_patterns import CONTEXT, ROOT


def source(game):
    return json.loads((ROOT/f'data/raw/samples/2026-08-25/{game}.json').read_bytes())


class RunnerTagReviewEffects(unittest.TestCase):
    def test_real_upheld_out_preserves_personal_replacement_and_action_identity(self):
        doc = source(823826)
        history = CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        ninth = next(h for h in history['halves'] if h['inning'] == 9 and h['half'] == 'top')
        self.assertEqual(ninth['status'], 'reconciled')
        runner = next(h for h in history['histories'] if h['runnerId'] == '642201' and h['terminal'] == 'out')
        self.assertTrue(runner['entryAnchor'].startswith('replacement/9/top/'))
        self.assertEqual(runner['terminationAnchor'],
                         'action/c0cfa943-62b2-37af-b3ca-e30728f2d8b2/caught_stealing_2b/642201')
        self.assertEqual(len(runner['episodes']), 1)
        remaining = [h for h in history['halves'] if h['status'] != 'reconciled']
        self.assertEqual([(h['inning'], h['half']) for h in remaining], [(8, 'top')])
        self.assertEqual(remaining[0]['issues'][0]['code'], 'CONFLICTING_BASE_OCCUPANCY')

    def test_real_upheld_steal_keeps_independent_advance_and_all_scoring_histories(self):
        doc = source(825042); original = copy.deepcopy(doc)
        history = CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        self.assertTrue(all(h['status'] == 'reconciled' for h in history['halves']))
        self.assertEqual(sum(h['terminal'] == 'score' for h in history['histories']), 9)
        runner = next(h for h in history['histories'] if h['runnerId'] == '699912' and h['inning'] == '9')
        self.assertEqual(runner['terminal'], 'score')
        self.assertTrue(runner['entryAnchor'].startswith('replacement/9/bottom/'))
        self.assertEqual([(e['atBatIndex'], e['runnerIndex']) for e in runner['episodes']], [('70', '0'), ('70', '2')])
        self.assertEqual(doc, original)
        self.assertFalse(history['metricPopulationAdmitted'])
        review = CONTEXT.accounted_runner_history_reviews(doc['liveData']['plays']['allPlays'][70])
        self.assertEqual(set(review['events'][4]), {'kind', 'runnerId', 'overturned', 'scope'})

    def test_unknown_overturned_or_contradictory_review_never_becomes_an_affirmation(self):
        for fault in ('pending', 'overturned', 'missing-disposition', 'unknown-code',
                      'wrong-type', 'narrative-overturned', 'wrong-person', 'wrong-outcome'):
            with self.subTest(fault=fault):
                play = source(823826)['liveData']['plays']['allPlays'][68]
                event = play['playEvents'][3]
                if fault == 'pending': event['reviewDetails']['inProgress'] = True
                elif fault == 'overturned': event['reviewDetails']['isOverturned'] = True
                elif fault == 'missing-disposition': event['reviewDetails'].pop('isOverturned')
                elif fault == 'unknown-code': event['reviewDetails']['reviewType'] = 'unknown'
                elif fault == 'wrong-type': event['details']['description'] = event['details']['description'].replace('tag play', 'pitch result')
                elif fault == 'narrative-overturned': event['details']['description'] = event['details']['description'].replace('upheld', 'overturned')
                elif fault == 'wrong-person': event['details']['description'] = event['details']['description'].replace('Eli White', 'Someone Else')
                else: event['details']['description'] = event['details']['description'].replace('caught stealing', 'steals')
                result = CONTEXT.accounted_runner_history_reviews(play)
                self.assertNotIn(3, result['events'])
                self.assertIn('UNRESOLVED_EVENT_REVIEW', result['issues'])

    def test_counter_runner_and_source_flags_must_reconcile(self):
        for fault in ('balls', 'strikes', 'outs', 'out-ordinal', 'origin', 'destination',
                      'scoring', 'event-out', 'duplicate', 'unknown-person', 'substitution', 'complete'):
            with self.subTest(fault=fault):
                play = source(823826)['liveData']['plays']['allPlays'][68]
                event = play['playEvents'][3]; row = play['runners'][0]
                if fault in ('balls', 'strikes', 'outs'): event['count'][fault] += 1
                elif fault == 'out-ordinal': row['movement']['outNumber'] = 3
                elif fault == 'origin': row['movement']['start'] = '2B'
                elif fault == 'destination': row['movement']['outBase'] = '3B'
                elif fault == 'scoring': row['details']['isScoringEvent'] = True
                elif fault == 'event-out': event['details']['isOut'] = False
                elif fault == 'duplicate': play['runners'].append(copy.deepcopy(row))
                elif fault == 'unknown-person': row['details']['runner']['id'] = None
                elif fault == 'substitution': event['isSubstitution'] = True
                else: play['about']['isComplete'] = False
                self.assertIsNone(CONTEXT.unchanged_runner_tag_review(play, 3))

    def test_missing_action_anchor_still_withholds_the_out_history(self):
        doc = source(823826)
        doc['liveData']['plays']['allPlays'][68]['playEvents'][3].pop('actionPlayId')
        history = CONTEXT.personal_runner_histories(json.dumps(doc).encode())
        half = next(h for h in history['halves'] if h['inning'] == 9 and h['half'] == 'top')
        self.assertEqual(half['status'], 'withheld')
        self.assertIn('MISSING_STABLE_MOVEMENT_ANCHOR', {i['code'] for i in half['issues']})


if __name__ == '__main__':
    unittest.main()
