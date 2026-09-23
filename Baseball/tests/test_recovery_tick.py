import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recovery_tick',ROOT/'scripts/pipeline/recovery_tick.py')
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)


class RecoveryTick(unittest.TestCase):
    def test_pending_dependency_does_not_submit_or_sleep_and_backup_id_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=dict(stateRoot=str(root),backups=str(root/'backups'),server='http://127.0.0.1:3031',dataset='baseball-dev')
            with patch.object(T.P,'reconcile_builds',return_value=[{'status':'running'}]),patch.object(T.R,'submit') as submit:
                deferred=T.tick(config);self.assertEqual(deferred['status'],'waiting-for-serving');submit.assert_not_called()
            with patch.object(T.P,'reconcile_builds',return_value=[]),patch.object(T.R,'submit',return_value={'taskId':'1'}) as submit:
                submitted=T.tick(config)
                self.assertEqual(submit.call_args.kwargs['request_id'],deferred['jobId'])
                self.assertEqual(submitted['phase'],'submitted')
            with patch.object(T.P,'reconcile_builds',return_value=[]),patch.object(T.R,'submit') as submit,patch.object(T.R,'complete',return_value={'status':'pending'}):
                self.assertEqual(T.tick(config)['status'],'pending');submit.assert_not_called()

    def test_same_drive_export_is_rejected_before_copying(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);recovery=root/'recovery';recovery.mkdir()
            T.R.atomic_json(recovery/'current.json',dict(phase='verified',jobId='1',archive={'path':str(root/'source.nq.gz'),'bytes':1}))
            with patch.object(T.P,'reconcile_builds',return_value=[]),patch.object(T.R,'export') as export:
                result=T.tick(dict(stateRoot=str(root),exportDirectory=str(root/'exports'),reserveBytes=0))
                self.assertEqual(result['status'],'failed');self.assertIn('separate drive',result['error']);export.assert_not_called()


if __name__=='__main__':unittest.main()
