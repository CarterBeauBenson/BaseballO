from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('rdf_recovery', Path(__file__).resolve().parents[1] / 'scripts/pipeline/rdf-recovery.py')
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backups = self.root / 'backups'
        self.backups.mkdir()
        self.job = RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'test', self.backups,
                                   request=lambda *args: {'taskId': '7'})
        self.task = {'taskId': '7', 'task': 'backup',
                     'started': (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                     'finished': (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat(), 'success': True}

    def archive(self, name='test_fresh.nq.gz'):
        path = self.backups / name
        with gzip.open(path, 'wb') as out:
            out.write(b'<urn:runner> <http://www.w3.org/2000/01/rdf-schema#label> "Runner" <urn:game> .\n')
        return path

    def complete(self, task=None):
        return RECOVERY.complete(self.root, self.job['jobId'], lambda *args: [task or self.task])

    def test_pending_does_not_require_or_claim_a_backup(self):
        task = dict(self.task)
        del task['finished']
        self.assertEqual(self.complete(task)['status'], 'pending')
        self.assertEqual(RECOVERY.read_job(self.root, self.job['jobId'])[1]['status'], 'submitted')

    def test_fuseki_six_task_object_uses_capitalized_backup_name(self):
        self.archive()
        result = RECOVERY.complete(self.root, self.job['jobId'], lambda *args: {**self.task, 'task': 'Backup'})
        self.assertEqual(result['status'], 'verified')

    def test_completed_task_without_fresh_archive_fails(self):
        with self.assertRaisesRegex(ValueError, 'exactly one fresh'):
            self.complete()

    def test_old_backup_is_not_mistaken_for_task_output(self):
        self.archive('test_old.nq.gz')
        self.job = RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'test', self.backups,
                                   request=lambda *args: {'taskId': '7'})
        with self.assertRaisesRegex(ValueError, 'exactly one fresh'):
            self.complete()

    def test_concurrent_backup_artifacts_are_ambiguous(self):
        self.archive()
        self.archive('test_other.nq.gz')
        with self.assertRaisesRegex(ValueError, 'exactly one fresh'):
            self.complete()

    def test_failed_task_is_terminal(self):
        self.archive()
        with self.assertRaisesRegex(ValueError, 'task failed'):
            self.complete({**self.task, 'success': False})
        self.assertEqual(RECOVERY.read_job(self.root, self.job['jobId'])[1]['status'], 'failed')

    def test_task_identity_and_started_time_must_match(self):
        for task in ({**self.task, 'taskId': '8'}, {**self.task, 'task': 'compact'},
                     {**self.task, 'started': '2000-01-01T00:00:00Z'}):
            with self.subTest(task=task), self.assertRaises(ValueError):
                self.complete(task)

    def test_truncated_gzip_never_verifies(self):
        path = self.archive()
        path.write_bytes(path.read_bytes()[:-5])
        with self.assertRaises(EOFError):
            self.complete()

    def test_verified_archive_rechecks_integrity_and_exports_idempotently(self):
        archive = self.archive()
        job = self.complete()
        self.assertEqual(job['status'], 'verified')
        destination = self.root / 'destination'
        destination.mkdir()
        first = RECOVERY.export(self.root, job['jobId'], destination)
        self.assertEqual(first, RECOVERY.export(self.root, job['jobId'], destination))
        archive.write_bytes(b'changed')
        with self.assertRaises((ValueError, OSError)):
            RECOVERY.verify(self.root, job['jobId'])

    def test_partial_copy_is_not_published(self):
        self.archive()
        self.complete()
        destination = self.root / 'destination'
        destination.mkdir()
        with patch.object(RECOVERY.shutil, 'copyfile', side_effect=OSError('Disconnected destination')):
            with self.assertRaises(OSError):
                RECOVERY.export(self.root, self.job['jobId'], destination)
        self.assertFalse((destination / ('baseballo-rdf-' + self.job['jobId'])).exists())

    def test_ambiguous_submission_is_retained_without_resubmission(self):
        def uncertain(*args):
            raise TimeoutError('Response lost')
        with self.assertRaises(TimeoutError):
            RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'test', self.backups, request=uncertain)
        jobs = [json.loads(p.read_text()) for p in (self.root / 'jobs').glob('*.json')]
        uncertain_job = next(j for j in jobs if j['status'] == 'submission-uncertain')
        with self.assertRaisesRegex(ValueError, 'unambiguous submitted'):
            RECOVERY.complete(self.root, uncertain_job['jobId'], request=uncertain)

    def test_restore_rejects_modified_export_before_starting_java(self):
        self.archive()
        self.complete()
        destination = self.root / 'destination'
        destination.mkdir()
        RECOVERY.export(self.root, self.job['jobId'], destination)
        export = destination / ('baseballo-rdf-' + self.job['jobId'])
        (export / 'dataset.nq.gz').write_bytes(b'corrupt')
        with patch.object(RECOVERY.subprocess, 'Popen') as run:
            with self.assertRaises((ValueError, OSError)):
                RECOVERY.stage_restore(export, self.root, Path('java'), Path('jena'))
            run.assert_not_called()
        self.assertFalse((self.root / 'restores').exists())

    def test_invalid_job_cannot_escape_recovery_root(self):
        with self.assertRaises(ValueError):
            RECOVERY.read_job(self.root, '../current')

    def test_stable_request_identity_does_not_submit_twice(self):
        request_id = '135bfc60-f439-4e0a-9c34-a1e7867e0bd1'
        with patch.object(RECOVERY, 'http_json', return_value={'taskId': '9'}) as request:
            first = RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'test', self.backups,
                                    request=request, request_id=request_id)
            second = RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'test', self.backups,
                                     request=request, request_id=request_id)
            self.assertEqual(first, second)
            self.assertEqual(request.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'different inputs'):
                RECOVERY.submit(self.root, 'http://127.0.0.1:3031', 'other', self.backups,
                                request=request, request_id=request_id)


if __name__ == '__main__':
    unittest.main()
