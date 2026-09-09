"""The accepted metric initial state is distinct from source movement origin."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('origin_metrics', ROOT / 'serving/metric_suite.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class TrajectoryOriginPolicyTests(unittest.TestCase):
    def runner(self, code='2B'):
        return dict(participant='runner', act='act', originDesignations=[dict(
            designation='origin', record='record', act='act', baseCode=code)])

    def test_batter_double_and_awards_start_at_metric_home_without_origin(self):
        for end, expected in [(1, '1/4'), (2, '1/2')]:
            row = dict(participant='batter', start=None, end=end, terminal='safe', creditProgress=True, creditOut=False)
            result = M.trajectories([row], 0, 0, batter='batter')
            self.assertEqual(M.fraction(result['value']), M.fraction(expected))
            self.assertEqual(row['start'], None)

    def test_steal_then_attributed_advance_starts_at_second(self):
        row = self.runner()
        row.update(end=3, terminal='safe', creditProgress=True, creditOut=False)
        result = M.trajectories([row], 0, 0, batter='batter')
        self.assertEqual(M.fraction(result['value']), M.fraction('1/2'))
        self.assertEqual(M.trajectory_origin(row, 'batter')['originBasis'], 'segment-designation')

    def test_designation_has_priority_over_pa_start(self):
        row = self.runner()
        row['paStartOrigin'] = dict(baseCode='1B', act='act', runner='runner', stasis='stasis',
                                   actBeginsAtPAStart=True, noInterveningSameRunnerMovement=True, evidence=['proof'])
        self.assertEqual(M.fraction(M.trajectory_origin(row, 'batter')['value']), 2)
        row['originDesignations'] = []
        self.assertEqual(M.fraction(M.trajectory_origin(row, 'batter')['value']), 1)
        row['paStartOrigin']['noInterveningSameRunnerMovement'] = None
        self.assertEqual(M.trajectory_origin(row, 'batter')['status'], 'unavailable')

    def test_missing_conflicting_and_wrong_act_evidence_is_unavailable(self):
        for fault in ['missing', 'conflict', 'wrong-act', 'unsupported']:
            row = self.runner()
            if fault == 'missing': row['originDesignations'] = []
            elif fault == 'conflict': row['originDesignations'].append(dict(designation='other', record='record', act='act', baseCode='3B'))
            elif fault == 'wrong-act': row['originDesignations'][0]['act'] = 'other-act'
            else: row['originDesignations'][0]['baseCode'] = 'HOME'
            row.update(previousSafeBase='2B', lastKnownBase='2B', start=2)
            self.assertEqual(M.trajectory_origin(row, 'batter')['status'], 'unavailable', fault)


if __name__ == '__main__':
    unittest.main()
