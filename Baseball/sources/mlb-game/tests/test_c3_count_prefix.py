"""An already reconciled pinch runner does not change the batter's count."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_metric_mapping_completion import CONTEXT, ROOT


class C3CountPrefix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix='baseballo-c3-count-prefix-'))
        target = cls.workspace/'context.json'
        subprocess.run([sys.executable, str(ROOT/'scripts/pipeline/prepare-rml-context.py'),
            str(ROOT/'data/raw/samples/2026-08-25/823585.json'), str(target)], check=True, capture_output=True)
        cls.context = json.loads(target.read_bytes())

    def select(self, fault=None):
        document = copy.deepcopy(self.context)
        play = document['liveData']['plays']['allPlays'][35]
        document['liveData']['plays']['allPlays'] = [play]
        event = play['playEvents'][0]
        history = document['_baseballO']['runnerHistoryReconciliation']
        if fault == 'missing-history': history['histories'] = []
        elif fault == 'withheld': history['sourceConsistency'] = 'inconsistent'
        elif fault == 'duplicate': history['histories'] *= 2
        elif fault == 'incoming': event['player']['id'] = 1
        elif fault == 'outgoing': event['replacedPlayer']['id'] = 1
        elif fault == 'base': event['base'] = 3
        elif fault == 'time': event['endTime'] = event['startTime']
        elif fault == 'batter': play['matchup']['batter']['id'] = event['player']['id']
        elif fault == 'pinch-hitter': event['position']['abbreviation'] = 'PH'
        elif fault == 'count': event['count']['strikes'] = 1
        elif fault == 'review': event['details']['hasReview'] = True
        elif fault == 'movement': play['runners'][0]['details']['playIndex'] = 0
        elif fault == 'overlap': play['playEvents'][1]['startTime'] = event['startTime']
        elif fault == 'pitch-overlap': play['playEvents'][2]['startTime'] = play['playEvents'][1]['startTime']
        return CONTEXT.metric_pitch_context(document)

    def test_real_supported_replacement_retains_the_complete_foul_prefix(self):
        evidence = self.select()
        self.assertEqual([r['eventIndex'] for r in evidence['countedFouls']], [4])
        self.assertEqual(evidence['prefixInventory'][0]['accountedExtension'], 'reconciled-pinch-runner')
        self.assertTrue(all(r['problem'] is None for r in evidence['prefixInventory']))

    def test_incomplete_c3_or_changed_count_and_batter_cannot_supply_a_prefix(self):
        for fault in ('missing-history','withheld','duplicate','incoming','outgoing','base','time',
                      'batter','pinch-hitter','count','review','movement','pitch-overlap'):
            self.assertFalse(self.select(fault)['countedFouls'], fault)

    def test_reconciled_replacement_can_overlap_the_first_pitch_under_h3(self):
        evidence = self.select('overlap')
        self.assertEqual([r['eventIndex'] for r in evidence['countedFouls']], [4])
        self.assertTrue(all(r['problem'] is None for r in evidence['prefixInventory']))

    def test_f4_reuses_zero_episode_witness_without_admitting_a_history(self):
        document = copy.deepcopy(self.context)
        play = document['liveData']['plays']['allPlays'][35]
        document['liveData']['plays']['allPlays'] = [play]
        event = play['playEvents'][0]
        history = document['_baseballO']['runnerHistoryReconciliation']
        anchor = f"replacement/{play['about']['inning']}/{play['about']['halfInning']}/{event['replacedPlayer']['id']}/{event['player']['id']}"
        incoming = next(h for h in history['histories'] if h.get('entryAnchor') == anchor)
        history['histories'].remove(incoming)
        incoming['episodes'] = []
        history['withheldHistories'].append(dict(inning=play['about']['inning'],
            half=play['about']['halfInning'], issues=[dict(code='ZERO_EPISODE_PERSONAL_HISTORY')],
            completedCandidates=[incoming]))
        before = copy.deepcopy(history)
        evidence = CONTEXT.metric_pitch_context(document)
        self.assertEqual([r['eventIndex'] for r in evidence['countedFouls']], [4])
        self.assertEqual(history, before)
        history['boundaryAnchorCensus'] *= 2
        self.assertFalse(CONTEXT.metric_pitch_context(document)['countedFouls'])

    def test_f4_rostered_initial_dh_switch_is_count_neutral(self):
        document = copy.deepcopy(self.context)
        play = document['liveData']['plays']['allPlays'][35]
        document['liveData']['plays']['allPlays'] = [play]
        event = play['playEvents'][0]
        side = 'home' if play['about']['isTopInning'] else 'away'
        roster = document['liveData']['boxscore']['teams'][side]['players']
        event['player']['id'] = next(iter(roster.values()))['person']['id']
        event['position']['abbreviation'] = 'DH'
        event['details']['eventType'] = 'defensive_switch'
        evidence = CONTEXT.metric_pitch_context(document)
        self.assertEqual([r['eventIndex'] for r in evidence['countedFouls']], [4])
        roster.clear()
        self.assertFalse(CONTEXT.metric_pitch_context(document)['countedFouls'])


if __name__ == '__main__':
    unittest.main()
