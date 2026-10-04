"""Resource contention defers work without killing workers or losing requests."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('serving_budget',ROOT/'scripts/infra/serving-budget.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)


class ServingBudget(unittest.TestCase):
    def test_existing_nifi_dashboard_entrypoint_defers_before_loading_a_build(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);progress=state/'serving/builds/prior.progress.json'
            progress.parent.mkdir(parents=True)
            progress.write_text(json.dumps(dict(status='running',processId=os.getpid())))
            env=dict(os.environ);env.pop('BASEBALLO_SERVING_BUDGET_HELD',None)
            result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pipeline/materialize-dashboard.py'),
                '--state-root',str(state)],env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),dict(status='deferred',reason='existing-serving-worker'))
            self.assertFalse((state/'serving/dashboard/progress.json').exists())

    def test_shared_lease_dashboard_priority_and_exception_release(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
            state=Path(temp);lock=state/'pipeline/work/mlb-game-locks/targeted-repair-budget.lock'
            with B.LOCK.exclusive(lock), B.reserve(state,'dashboard') as reason:
                self.assertEqual(reason,'heavy-worker-busy')
            with B.reserve(state,'report') as reason:self.assertEqual(reason,'waiting-dashboard')
            with self.assertRaisesRegex(RuntimeError,'worker failed'):
                with B.reserve(state,'dashboard') as reason:
                    self.assertIsNone(reason);raise RuntimeError('worker failed')
            with B.reserve(state,'report') as reason:self.assertIsNone(reason)

    def test_existing_worker_and_memory_limit_preserve_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);progress=state/'serving/builds/prior.progress.json'
            progress.parent.mkdir(parents=True)
            original=json.dumps(dict(status='running',processId=os.getpid()))
            progress.write_text(original)
            with B.reserve(state,'dashboard') as reason:self.assertEqual(reason,'existing-serving-worker')
            self.assertEqual(progress.read_text(),original)
            progress.write_text(json.dumps(dict(status='published')))
            with patch.object(B.PROCESS,'available_memory',return_value=500*1024**2):
                with B.reserve(state,'dashboard') as reason:self.assertEqual(reason,'waiting-for-memory')
            # A stopped dashboard timer must not leave a permanent priority lock.
            ticket=state/'serving/dashboard-budget-request.json'
            ticket.write_text(json.dumps(dict(expiresAt=time.time()-1)))
            with patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
                with B.reserve(state,'report') as reason:self.assertIsNone(reason)


if __name__=='__main__':unittest.main()
