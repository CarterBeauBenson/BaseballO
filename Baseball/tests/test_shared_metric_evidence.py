"""Shared evaluation preserves scores, withholding and per-card isolation."""
import copy
import unittest
from unittest.mock import patch

from test_batting_progress_players import fixture, PROOF, SCOPE
from test_metric_suite_serving import M, G1, bindings


class SharedMetricEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = M.normalize_bindings(bindings(fixture(), [G1]), [G1])

    def test_dashboard_matches_independent_evaluations_without_coverage_leak(self):
        expected = [M.live_result(e['id'], self.rows, graph_count=1)
                    for e in M.catalog()['metrics']]
        with patch.object(M, 'batting_participation', wraps=M.batting_participation) as inventory:
            actual = M.selected_results({'view': 'dashboard'}, self.rows, graph_count=1)['metrics']
        self.assertEqual(actual, expected)
        self.assertEqual(inventory.call_count, 1)
        actual[0]['coverage']['populationComplete'] = True
        actual[0]['coverage']['battingParticipation']['players'].clear()
        self.assertEqual(actual[1:], expected[1:])
        self.assertEqual(M.selected_results({'view': 'dashboard'}, self.rows, graph_count=1)['metrics'], expected)

    def test_progress_metrics_reuse_exact_evidence_after_their_independent_gates(self):
        qualification = M.batting_qualification(self.rows, graphs=[G1], admissions={G1: PROOF},
            date_scope=SCOPE, selected_games_complete=True)
        args = dict(graphs=[G1], admissions={G1: PROOF}, qualification=qualification, date_scope=SCOPE)
        expected = {metric: M.batting_progress_players(metric, self.rows, **args) for metric in M.PROGRESS_METRICS}
        shared = M._EvidenceEvaluation(self.rows, 1)
        with patch.object(M, 'batting_progress_evidence', wraps=M.batting_progress_evidence) as projection:
            actual = {metric: M.batting_progress_players(metric, self.rows, **args, _evaluation=shared)
                      for metric in M.PROGRESS_METRICS}
        self.assertEqual(actual, expected)
        self.assertEqual(projection.call_count, 1)
        withheld = M.batting_progress_players('offensive-reach', self.rows,
            **dict(args, admissions={}), _evaluation=shared)
        self.assertFalse(withheld['playerPopulationComplete'])
        self.assertEqual(withheld['playerResults'], [])

    def test_evidence_cannot_cross_request_or_graph_scope(self):
        shared = M._EvidenceEvaluation(self.rows, 1)
        for rows, count in ((copy.deepcopy(self.rows), 1), (self.rows, 2)):
            with self.assertRaisesRegex(M.EvidenceError, 'request scope'):
                M.live_result('offensive-reach', rows, graph_count=count, _evaluation=shared)
        proof = shared.coverage()
        proof['populationComplete'] = True
        self.assertFalse(shared.coverage()['populationComplete'])


if __name__ == '__main__':
    unittest.main()
