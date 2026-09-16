import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]
ROOT = MODULE.parents[1]
SPEC = importlib.util.spec_from_file_location('metric_source', MODULE / 'pipeline/reconcile-metric-source.py')
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
SOURCE = ROOT / 'data/raw/samples/2026-08-23/824315.json'


class ReconciliationTests(unittest.TestCase):
    def test_unplayed_bottom_half_is_not_inserted_by_membership_comparison(self):
        raw=(ROOT/'data/raw/samples/2026-07-18/824088.json').read_bytes()
        source=json.loads(raw)
        self.assertNotIn('runs',source['liveData']['linescore']['innings'][8]['home'])
        self.assertFalse(source['liveData']['plays']['playsByInning'][8]['bottom'])
        actual=R.reconcile(raw,'824088')
        self.assertEqual(actual['status'],'consistent',actual['issues'])
        self.assertFalse(any(p['inning']==9 and p['half']=='bottom' for p in actual['inventory']))

    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()
        cls.source = json.loads(cls.raw)
        cls.actual = R.reconcile(cls.raw, '824315')

    def changed(self, mutate):
        doc = copy.deepcopy(self.source)
        mutate(doc)
        return R.reconcile(json.dumps(doc).encode(), '824315')

    def codes(self, result):
        return {item['code'] for item in result['issues']}

    def test_real_source_census_preserves_known_boundary_ambiguity(self):
        self.assertEqual(self.actual['status'], 'consistent', self.actual['issues'])
        self.assertEqual(self.actual['inputSha256'], '5fcc75d37a20a516d312b3bfb3d5cefb4371ebafa639851ff16173d9b1a6607c')
        plays = self.source['liveData']['plays']['allPlays']
        self.assertEqual(self.actual['counts']['events'], sum(len(p['playEvents']) for p in plays))
        self.assertEqual(self.actual['counts']['movements'], sum(len(p['runners']) for p in plays))
        pa35 = self.actual['inventory'][35]
        self.assertEqual(len(pa35['events']), 9)
        self.assertEqual(pa35['events'][3]['eventType'], 'batter_timeout')
        self.assertEqual(pa35['postBaseObservations']['postOnThird']['id'], 800050)
        self.assertEqual(pa35['events'][-1]['count']['outs'], 1)
        self.assertEqual(pa35['paCount']['outs'], 2)
        self.assertEqual(self.actual['inventory'][16]['postBaseObservations'], {})
        for field in ('sourceHistoryAdmitted', 'graphCoverageVerified', 'metricPopulationAdmitted'):
            self.assertFalse(self.actual[field])

    def test_pitch_index_is_not_a_pitch_count(self):
        pa43 = self.actual['inventory'][43]
        self.assertEqual(pa43['pitchIndex'], [0, 1, 2])
        self.assertEqual(sum(e['isPitch'] is True for e in pa43['events']), 2)
        self.assertEqual(pa43['events'][1]['type'], 'pickoff')
        report = self.changed(lambda d: d['liveData']['plays']['allPlays'][43]['pitchIndex'].remove(2))
        self.assertIn('PITCH_MEMBERSHIP_MISMATCH', self.codes(report))

    def test_missing_pa_detected_by_independent_inning_membership(self):
        report = self.changed(lambda d: d['liveData']['plays']['allPlays'].pop(35))
        self.assertIn('INNING_MEMBERSHIP_MISMATCH', self.codes(report))

    def test_missing_scoring_index_and_wrong_totals_detected(self):
        report = self.changed(lambda d: d['liveData']['plays']['scoringPlays'].pop())
        self.assertIn('SCORING_INDEX_MISMATCH', self.codes(report))
        report = self.changed(lambda d: d['liveData']['linescore']['teams']['away'].update(runs=999))
        self.assertIn('TEAM_RUN_TOTAL_MISMATCH', self.codes(report))
        report = self.changed(lambda d: d['liveData']['linescore']['innings'][0]['away'].update(runs=999))
        self.assertIn('INNING_RUN_TOTAL_MISMATCH', self.codes(report))

    def test_event_scoring_evidence_survives_a_nonscoring_pa_header(self):
        doc=copy.deepcopy(self.source)
        p=next(p for p in doc['liveData']['plays']['allPlays'] if p['about']['isScoringPlay'])
        p['about']['isScoringPlay']=False
        scored={r['details']['playIndex'] for r in p['runners'] if r['details']['isScoringEvent']}
        for e in p['playEvents']:
            if e['index'] in scored:e['details']['isScoringPlay']=True
        report=R.reconcile(json.dumps(doc).encode(),'824315')
        self.assertEqual(report['status'],'consistent',report['issues'])
        for fault in ('missing-event-flag','missing-index','phantom-event-run'):
            changed=copy.deepcopy(doc);play=changed['liveData']['plays']['allPlays'][p['atBatIndex']]
            if fault=='missing-event-flag':
                for e in play['playEvents']:e['details']['isScoringPlay']=False
                code='SCORING_MEMBERSHIP_MISMATCH'
            elif fault=='missing-index':
                changed['liveData']['plays']['scoringPlays'].remove(p['atBatIndex']);code='SCORING_INDEX_MISMATCH'
            else:
                next(e for e in play['playEvents'] if e['index'] not in scored)['details']['isScoringPlay']=True
                code='SCORING_EVENT_MEMBERSHIP_MISMATCH'
            self.assertIn(code,self.codes(R.reconcile(json.dumps(changed).encode(),'824315')))

    def test_missing_or_duplicate_event_cannot_satisfy_movement_link(self):
        report = self.changed(lambda d: d['liveData']['plays']['allPlays'][35]['playEvents'].pop())
        self.assertIn('MOVEMENT_EVENT_MEMBERSHIP_MISMATCH', self.codes(report))
        self.assertIn('PITCH_MEMBERSHIP_MISMATCH', self.codes(report))
        def duplicate(d):
            events = d['liveData']['plays']['allPlays'][35]['playEvents']
            events.append(copy.deepcopy(events[-1]))
        self.assertIn('MOVEMENT_EVENT_MEMBERSHIP_MISMATCH', self.codes(self.changed(duplicate)))

    def test_missing_views_are_unknown_not_empty(self):
        report = self.changed(lambda d: d['liveData']['plays'].pop('playsByInning'))
        self.assertIn('MISSING_INNING_MEMBERSHIP', self.codes(report))
        report = self.changed(lambda d: d['liveData']['linescore'].pop('innings'))
        self.assertIn('MISSING_LINESCORE_INNINGS', self.codes(report))

    def test_game_and_revision_are_required(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            R.reconcile(self.raw, '123')
        report = self.changed(lambda d: d['metaData'].pop('timeStamp'))
        self.assertIn('MISSING_SOURCE_REVISION', self.codes(report))
        report = self.changed(lambda d: d['gameData']['status'].update(abstractGameState='Live'))
        self.assertIn('GAME_NOT_FINAL', self.codes(report))

    def test_identical_retry_is_deterministic_and_keeps_raw_unchanged(self):
        self.assertEqual(R.reconcile(self.raw, '824315'), self.actual)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'report.json'
            R.write_atomic(target, self.actual)
            first = target.read_bytes()
            R.write_atomic(target, self.actual)
            self.assertEqual(target.read_bytes(), first)
            self.assertEqual(json.loads(first), self.actual)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), self.actual['inputSha256'])

    def test_nifi_retains_inventory_before_mapping_and_binds_stage_result(self):
        stage = (MODULE / 'pipeline/stage.ps1').read_text(encoding='utf-8')
        self.assertLess(stage.index("'reconcile-metric-source.py'"), stage.index("'scripts\\pipeline\\run-rml.ps1'"))
        self.assertIn('metricSourceReconciliationSha256', stage)
        cleanup = stage[stage.index("    'cleanup' {"):stage.index("    'quarantine' {")]
        self.assertNotIn('metricSourcePath', cleanup)


if __name__ == '__main__':
    unittest.main()
