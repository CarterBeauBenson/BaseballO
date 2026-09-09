"""C2 projects admitted state; it neither verifies raw history nor mints RDF."""
import unittest
from test_metric_suite_serving import M


def event(key, ordinal, base=None, *, known=True, changes=True):
    return dict(event=key, ordinal=ordinal, base=base, known=known, changesState=changes)


def project(rows, boundary, **kwargs):
    arguments = dict(history_complete=True, boundary_supported=True, evidence=['urn:verified-history'])
    arguments.update(kwargs)
    return M.project_runner_boundary(rows, boundary, **arguments)


class BoundaryProjectionTests(unittest.TestCase):
    def test_safe_state_persists_only_until_a_supported_change(self):
        rows = [event('safe-first', 1, 1), event('pitch', 2, changes=False)]
        self.assertEqual(project(rows, 2)['basePosition'], 1)
        rows += [event('steal-safe-second', 3, 2)]
        result = project(rows, 3)
        self.assertEqual((result['basePosition'], result['sourceEvent']), (2, 'steal-safe-second'))
        self.assertEqual(project(rows, 2)['sourceEvent'], 'safe-first')

    def test_out_score_replacement_and_unresolved_movement_stop_safe_projection(self):
        for terminal in ('out', 'score-on-passed-ball', 'pinch-runner-replacement', 'movement'):
            with self.subTest(terminal=terminal):
                result = project([event('safe-third', 1, 3), event(terminal, 2)], 2)
                self.assertEqual(result['status'], 'unavailable')
                self.assertIsNone(result['value'])

    def test_stranding_boundary_is_distinct_from_clearing_the_inning(self):
        rows = [event('safe-third', 1, 3), event('other-player-third-out', 2, changes=False),
                event('inning-ended', 3)]
        # Boundary 2 is independently supported stranding, before the reset.
        self.assertEqual(project(rows, 2)['basePosition'], 3)
        self.assertEqual(project(rows, 3)['status'], 'unavailable')

    def test_unknown_history_boundary_review_or_order_withholds_the_projection(self):
        rows = [event('safe', 1, 2)]
        for kwargs in ({'history_complete': False}, {'boundary_supported': False}, {'evidence': []}):
            self.assertEqual(project(rows, 2, **kwargs)['status'], 'unavailable')
        self.assertEqual(project(rows + [event('unresolved-review', 2, known=False)], 2)['status'], 'unavailable')
        self.assertEqual(project(rows + [event('ambiguous-same-position-change', 1)], 2)['status'], 'unavailable')
        self.assertEqual(project([], 2)['status'], 'unavailable')

    def test_supported_corrected_state_is_used_without_reassigning_contributions(self):
        rows = [event('old-safe', 1, 2), event('operative-corrected-safe', 2, 1)]
        result = project(rows, 2)
        self.assertEqual(result['basePosition'], 1)
        self.assertEqual(result['sourceEvent'], 'operative-corrected-safe')
        self.assertNotIn('creditProgress', result)
        with self.assertRaises(M.EvidenceError):
            project(rows + [event('old-safe', 1, 3)], 2)


if __name__ == '__main__':
    unittest.main()
