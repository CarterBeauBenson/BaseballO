"""Real source evidence and negative cases named in the user's final decision."""
import copy
import json
import unittest

from test_runner_structural_patterns import CONTEXT, ROOT


def play(game, index):
    path = ROOT / ('data/raw/game-566279.json' if game == '566279' else f'data/raw/samples/2026-08-25/{game}.json')
    return json.loads(path.read_bytes())['liveData']['plays']['allPlays'][index]


class FinalSourceDecisionTests(unittest.TestCase):
    def evidence(self, source, index='40', season='2026'):
        return CONTEXT.runner_metric_evidence(source, index, season)

    def test_batter_walk_hbp_and_intentional_walk(self):
        for game, index in [('566279', 4), ('823016', 54)]:
            row, = self.evidence(play(game, index))['awardAdvances']
            self.assertEqual(row['resolutionKind'], 'reach')
            self.assertIn(row['ruleCode'], {'5.05(b)(1)', '5.05(b)(2)'})
        source = play('566279', 4)
        source['result']['eventType'] = 'intent_walk'
        source['runners'][0]['details']['eventType'] = 'intent_walk'
        source['playEvents'][-1]['isPitch'] = False
        source['playEvents'][-1]['details']['eventType'] = 'intent_walk'
        self.assertEqual(len(self.evidence(source)['awardAdvances']), 1)

    def test_loaded_walk_admits_all_three_positive_forces_and_batter(self):
        evidence = self.evidence(play('823016', 40))
        self.assertEqual([(r['runnerIndex'], r['ruleCode']) for r in evidence['awardAdvances']],
                         [('0', '5.06(b)(3)(B)'), ('1', '5.06(b)(3)(B)'), ('2', '5.06(b)(3)(B)'), ('3', '5.05(b)(1)')])
        self.assertEqual(evidence['awardAdvances'][0]['resolutionKind'], 'score')
        self.assertEqual([r['baseCode'] for r in evidence['segmentOrigins']], ['3B', '2B', '1B'])

    def test_hbp_unrelated_movement_and_nonforce_reason_are_excluded(self):
        for reason, event_type in [('r_adv_play', 'hit_by_pitch'), ('r_adv_force', 'stolen_base')]:
            source = play('823016', 39)
            source['runners'][0]['details'].update(movementReason=reason, eventType=event_type)
            self.assertNotIn('0', [r['runnerIndex'] for r in self.evidence(source)['awardAdvances']])

    def test_overshoot_and_walk_wild_pitch_extra_advance(self):
        source = play('823016', 40)
        source['runners'][2]['movement']['end'] = '3B'
        self.assertNotIn('2', [r['runnerIndex'] for r in self.evidence(source)['awardAdvances']])
        source = play('566279', 4)
        source['runners'][0]['movement']['end'] = '2B'
        source['runners'][0]['details']['movementReason'] = 'r_adv_play'
        self.assertEqual(self.evidence(source)['awardAdvances'], [])

    def test_review_incomplete_ambiguous_event_and_mixed_same_runner(self):
        for fault in ['review', 'incomplete', 'duplicate-event', 'boolean-index', 'mixed-segment']:
            source = play('566279', 4)
            if fault == 'review': source['about']['hasReview'] = True
            elif fault == 'incomplete': source['about']['isComplete'] = False
            elif fault == 'duplicate-event': source['playEvents'].append(copy.deepcopy(source['playEvents'][-1]))
            elif fault == 'boolean-index': source['runners'][0]['details']['playIndex'] = True
            else:
                extra = copy.deepcopy(source['runners'][0])
                extra['movement'].update(start='1B', end='2B')
                extra['details']['eventType'] = 'wild_pitch'
                source['runners'].append(extra)
            self.assertEqual(self.evidence(source)['awardAdvances'], [], fault)

    def test_start_is_segment_origin_even_when_origin_base_differs(self):
        source = play('823016', 40)
        source['runners'] = [source['runners'][0]]
        source['runners'][0]['movement'].update(originBase='2B', start='3B', end='score')
        row, = self.evidence(source)['segmentOrigins']
        self.assertEqual(row['baseCode'], '3B')

    def test_two_segments_of_same_runner_keep_distinct_starts(self):
        source = play('823016', 40)
        first = copy.deepcopy(source['runners'][0])
        first['movement'].update(originBase='2B', start='2B', end='3B')
        second = copy.deepcopy(first)
        second['movement'].update(start='3B', end='score')
        source['runners'] = [first, second]
        self.assertEqual([r['baseCode'] for r in self.evidence(source)['segmentOrigins']], ['2B', '3B'])

    def test_missing_unsupported_or_ambiguous_origin_stays_unavailable(self):
        for fault in ['missing', 'unsupported', 'runner', 'duplicate-row', 'act']:
            source = play('823016', 40)
            source['runners'] = [source['runners'][0]]
            if fault == 'missing': source['runners'][0]['movement'].pop('start')
            elif fault == 'unsupported': source['runners'][0]['movement']['start'] = 'HOME'
            elif fault == 'runner': source['runners'][0]['details']['runner']['id'] = None
            elif fault == 'duplicate-row': source['runners'].append(copy.deepcopy(source['runners'][0]))
            self.assertEqual(self.evidence(source, index='ambiguous' if fault == 'act' else '40')['segmentOrigins'], [], fault)

    def test_no_stasis_mutation_and_no_unverified_rule_edition(self):
        source = play('823016', 40)
        before = copy.deepcopy(source)
        result = self.evidence(source, season='1900')
        self.assertTrue(result['segmentOrigins'])
        self.assertEqual(result['awardAdvances'], [])
        self.assertEqual(source, before)
        self.assertEqual(set(result), {'segmentOrigins', 'awardAdvances'})


if __name__ == '__main__':
    unittest.main()
