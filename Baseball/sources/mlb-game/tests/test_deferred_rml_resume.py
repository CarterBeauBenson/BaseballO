"""A preserved queue resumes only after its specifically requested proof."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('batch_resume',
    Path(__file__).resolve().parents[1]/'pipeline/materialize-pending-batches.py')
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class DeferredRmlResume(unittest.TestCase):
    def test_waits_for_exact_proof_then_restores_parallelism_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root/'pipeline/control/mlb-game/replay-readiness-resume.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'rml': dict(name='RML', afterProofRunId='new-run',
                groupId='source', concurrentTasks=2)}))
            entity = dict(revision={'version': 1}, component=dict(name='RML',
                parentGroupId='source', type='org.apache.nifi.processors.standard.ExecuteStreamCommand',
                state='STOPPED'), status={'aggregateSnapshot': {'activeThreadCount': 0}})
            calls = []
            def request(method, route, body=None):
                calls.append((method, route, body))
                return entity
            for release in (None, {'proofRunId': 'old-run'}):
                M.resume_replay_workers(root, request, lambda state: release)
                self.assertEqual(calls, [])
                self.assertTrue(path.exists())
            M.resume_replay_workers(root, request, lambda state: {'proofRunId': 'new-run'})
            self.assertEqual([call[0] for call in calls], ['GET', 'PUT', 'PUT'])
            self.assertEqual(calls[1][2]['component']['config']['concurrentlySchedulableTaskCount'], 2)
            self.assertEqual(calls[2][2]['state'], 'RUNNING')
            self.assertFalse(path.exists())
            M.resume_replay_workers(root, request, lambda state: {'proofRunId': 'new-run'})
            self.assertEqual(len(calls), 3)


if __name__ == '__main__': unittest.main()
