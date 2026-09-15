"""Accepted attribution on admitted consequences, without source inference."""
import importlib.util
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('metric_suite', ROOT / 'serving/metric_suite.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def participants():
    return [
        dict(participant='b', start=0, end=None, terminal='out', evidence=['urn:out:b']),
        dict(participant='r', start=1, end=None, terminal='out', evidence=['urn:out:r']),
        dict(participant='third', start=3, end=3, terminal='stranded', evidence=['urn:state:third'])]


def score(rows=None, **options):
    defaults = dict(batter='b', runner='r', confirmed=True,
                    confirmation_evidence=['urn:confirmed:called-strategy'], complete=True)
    return M.failed_hit_and_run_scores(participants() if rows is None else rows, 1, **(defaults | options))


class FailedHitAndRun(unittest.TestCase):
    def test_batter_bears_both_outs_and_existing_third_out_erosion_once(self):
        rows = participants()
        original = deepcopy(rows)
        result = score(rows)
        self.assertEqual(M.fraction(result['value']), Fraction(-19, 12))
        self.assertEqual(M.fraction(result['components']['destruction']), Fraction(7, 12))
        self.assertEqual(M.fraction(result['components']['erosion']), 1)
        self.assertEqual(result['batter'], 'b')
        self.assertEqual(result['runner'], 'r')
        self.assertEqual(result['attributedOuts'], 2)
        self.assertEqual(result['independentRunningScores'], [])
        self.assertEqual(rows, original)
        self.assertEqual(set(result['evidence']), {'urn:out:b', 'urn:out:r', 'urn:state:third', 'urn:confirmed:called-strategy'})

    def test_actual_scored_runner_has_no_erosion_or_positive_batter_credit(self):
        rows = participants()
        rows[2].update(terminal='scored', end=4)
        result = score(rows)
        self.assertEqual(M.fraction(result['value']), Fraction(-7, 12))
        self.assertEqual(M.fraction(result['components']['progress']), 0)
        self.assertEqual(M.fraction(result['components']['erosion']), 0)

    def test_strikeout_and_runner_out_do_not_confirm_strategy(self):
        for options in [dict(confirmed=False), dict(confirmation_evidence=[]), dict(complete=False)]:
            with self.subTest(options=options):
                self.assertEqual(score(**options)['status'], 'unavailable')

    def test_partial_missing_and_unsupported_consequences_are_withheld(self):
        self.assertEqual(score(participants()[1:])['gaps'], ['MISSING_PARTICIPANTS'])
        unknown = participants()
        unknown[2]['terminal'] = 'unknown'
        self.assertEqual(score(unknown)['gaps'], ['UNKNOWN_TERMINAL_STATE'])
        for replacement in [dict(terminal='safe', end=2), dict(start=0)]:
            rows = participants()
            rows[1].update(replacement)
            with self.assertRaises(M.EvidenceError):
                score(rows)
        with self.assertRaises(M.EvidenceError):
            score(runner='b')
        with self.assertRaises(M.EvidenceError):
            score(confirmed='true')

    def test_identical_duplicates_do_not_duplicate_outs_but_conflicts_fail(self):
        rows = participants()
        self.assertEqual(score(rows + [rows[1]]), score(rows))
        with self.assertRaises(M.EvidenceError):
            score(rows + [dict(rows[1], start=2)])

    def test_exact_allocated_result_round_trips_through_serving_sql(self):
        connection = sqlite3.connect(':memory:')
        self.addCleanup(connection.close)
        M.initialize_sql(connection)
        result = score()
        M.store_result(connection, 'urn:game:test', 'tfs', 'urn:pa:test', result)
        self.assertEqual(M.read_results(connection, 'urn:game:test', 'tfs'), [result])


if __name__ == '__main__':
    unittest.main()
