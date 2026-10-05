"""Resource contention defers work without killing workers or losing requests."""
import importlib.util
from contextlib import contextmanager
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
    def test_short_contention_hands_off_and_persistent_contention_stays_bounded(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
            attempts=[];clock=[0.0]
            @contextmanager
            def briefly_busy(path):
                attempts.append(path)
                if len(attempts)<3:raise BlockingIOError('admission sweep still owns slot')
                yield
            with patch.object(B.LOCK,'exclusive',briefly_busy),patch.object(B.time,'monotonic',side_effect=lambda:clock[0]),\
                    patch.object(B.time,'sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds)):
                with B.reserve(Path(temp),'dashboard',wait_seconds=15) as reason:self.assertIsNone(reason)
            self.assertEqual(len(attempts),3);self.assertEqual(clock[0],0.5)
            with patch.object(B.LOCK,'exclusive',side_effect=PermissionError('shared Windows handle')),\
                    patch.object(B.time,'monotonic',side_effect=lambda:clock[0]),\
                    patch.object(B.time,'sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds)):
                with B.reserve(Path(temp),'report',wait_seconds=1) as reason:self.assertEqual(reason,'heavy-worker-busy')
            self.assertEqual(clock[0],1.5)

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

    def test_shared_lease_without_dashboard_priority_and_exception_release(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
            state=Path(temp);lock=state/'pipeline/work/mlb-game-locks/targeted-repair-budget.lock'
            with B.LOCK.exclusive(lock), B.reserve(state,'dashboard') as reason:
                self.assertEqual(reason,'heavy-worker-busy')
            with B.reserve(state,'report') as reason:self.assertIsNone(reason)
            with self.assertRaisesRegex(RuntimeError,'worker failed'):
                with B.reserve(state,'dashboard') as reason:
                    self.assertIsNone(reason);raise RuntimeError('worker failed')
            with B.reserve(state,'report') as reason:self.assertIsNone(reason)

    def test_requested_upstream_phase_defers_both_builds_then_releases_once(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
            state=Path(temp);control=state/'pipeline/control/mlb-game';control.mkdir(parents=True)
            request=control/'repair-priority.json';report=control/'repair-status.json'
            request.write_text(json.dumps(dict(enabled=True,requestedAtUtc='2026-10-04T23:00:00.3055604Z')))
            for kind in ('dashboard','report'):
                with B.reserve(state,kind) as reason:self.assertEqual(reason,'upstream-repairs-first')
            # A clear report predating this request cannot release the phase.
            report.write_text(json.dumps(dict(recordedWorkClear=True,checkedAtUtc='2026-10-04T22:00:00Z')))
            with B.reserve(state,'dashboard') as reason:self.assertEqual(reason,'upstream-repairs-first')
            report.write_text(json.dumps(dict(recordedWorkClear=False,checkedAtUtc='2026-10-04T23:01:00Z')))
            with B.reserve(state,'report') as reason:self.assertEqual(reason,'upstream-repairs-first')
            report.write_text(json.dumps(dict(recordedWorkClear=True,checkedAtUtc='2026-10-04T23:02:00Z')))
            with B.reserve(state,'report') as reason:self.assertIsNone(reason)
            self.assertFalse(json.loads(request.read_text())['enabled'])
            report.write_text(json.dumps(dict(recordedWorkClear=False,checkedAtUtc='2026-10-05T00:00:00Z')))
            with B.reserve(state,'dashboard') as reason:self.assertIsNone(reason)

    def test_canonical_build_entrypoints_honor_upstream_phase_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game';control.mkdir(parents=True)
            (control/'repair-priority.json').write_text(json.dumps(dict(enabled=True,requestedAtUtc='2026-10-04T23:00:00Z')))
            env=dict(os.environ);env.pop('BASEBALLO_SERVING_BUDGET_HELD',None)
            for script in ('materialize-dashboard.py','materialize-serving-layer.py'):
                result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pipeline'/script),
                    '--state-root',str(state)],env=env,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),dict(status='deferred',reason='upstream-repairs-first'))
            self.assertFalse((state/'serving/releases').exists())

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
            # Even an unexpired ticket from old code cannot favor SQL.
            ticket=state/'serving/dashboard-budget-request.json'
            ticket.write_text(json.dumps(dict(expiresAt=time.time()+120)))
            with patch.object(B.PROCESS,'available_memory',return_value=2*1024**3):
                with B.reserve(state,'report') as reason:self.assertIsNone(reason)


if __name__=='__main__':unittest.main()
