"""Review evidence retention across MLB's two record locations."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('review_inventory',ROOT/'sources/mlb-game/pipeline/review-inventory.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class ReviewInventory(unittest.TestCase):
    def fixture(self):return (ROOT/'data/raw/samples/2026-08-25/822773.json').read_bytes()

    def test_real_terminal_review_completes_the_observed_mj_records(self):
        raw=self.fixture();r=M.inventory(raw,'822773')
        self.assertEqual(r['status'],'diagnostic');self.assertFalse(r['metricPopulationAdmitted'])
        self.assertFalse(r['graphConformanceAssessed']);self.assertEqual(r['issues'],[])
        rows=[o for o in r['observations'] if o['reviewDetails']['reviewType']=='MJ']
        self.assertEqual(len(rows),5)
        self.assertEqual(sum(o['reviewDetails']['isOverturned'] for o in rows),3)
        terminal,=[o for o in rows if o['eventIndex'] is None]
        self.assertEqual(terminal['atBatIndex'],15)
        self.assertEqual(terminal['reportedBatterId'],695600)
        self.assertEqual(terminal['reviewDetails']['player']['id'],678218)
        self.assertEqual(r['observationCounts'],[
            dict(providerCode='MJ',outcome='affirmed',count=2),
            dict(providerCode='MJ',outcome='overturned',count=3),
            dict(providerCode='MO',outcome='affirmed',count=1)])
        self.assertEqual(self.fixture(),raw)

    def test_duplicate_locations_are_retained_without_inventing_identity(self):
        d=json.loads(self.fixture());play=d['liveData']['plays']['allPlays'][15]
        play['playEvents'][-1]['reviewDetails']=play['reviewDetails']
        r=M.inventory(json.dumps(d).encode(),'822773')
        self.assertEqual(len(r['observations']),7)
        self.assertFalse(r['metricPopulationAdmitted'])
        self.assertFalse(any('reviewIri' in o for o in r['observations']))

    def test_incomplete_review_flag_is_visible_and_unknown_codes_are_not_translated(self):
        d=json.loads(self.fixture());event=d['liveData']['plays']['allPlays'][0]['playEvents'][0]
        event['details']['hasReview']=True
        r=M.inventory(json.dumps(d).encode(),'822773')
        self.assertEqual(r['issues'][0]['code'],'REVIEW_FLAG_WITHOUT_DETAILS')
        event['reviewDetails']=dict(reviewType='new-provider-code',inProgress=True)
        r=M.inventory(json.dumps(d).encode(),'822773')
        self.assertIn(dict(providerCode='new-provider-code',outcome='pending',count=1),r['observationCounts'])
        self.assertFalse(any('mechanism' in o for o in r['observations']))

    def test_wrong_game_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity'):M.inventory(self.fixture(),'999')


if __name__=='__main__':unittest.main()
