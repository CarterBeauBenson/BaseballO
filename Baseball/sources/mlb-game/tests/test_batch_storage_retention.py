"""A failed SQL build must not prevent ordinary snapshot retention."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('batch_retention',
    Path(__file__).resolve().parents[1]/'pipeline/materialize-pending-batches.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class BatchStorageRetention(unittest.TestCase):
    def test_retains_current_and_newest_builds_without_touching_dashboard_or_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);store=state/'serving';builds=store/'builds';builds.mkdir(parents=True)
            paths=[builds/(str(i)+'.sqlite') for i in range(6)]
            for i,p in enumerate(paths):
                p.write_bytes(b'derived SQL');os.utime(p,ns=(i+1,i+1))
            pointer=store/'current.json';pointer.write_text(json.dumps(dict(databasePath=str(paths[1]))))
            dashboard=store/'dashboard/builds/current.sqlite';dashboard.parent.mkdir(parents=True)
            dashboard.write_bytes(b'current dashboard')
            evidence=store/'evidence/failed.json';evidence.parent.mkdir();evidence.write_text('{"status":"failed"}')
            before={p:p.read_bytes() for p in (pointer,dashboard,evidence)}
            result=M.maintain_serving_storage(state)
            self.assertEqual(result['removedBuildCount'],3)
            self.assertEqual({p.name for p in builds.glob('*.sqlite')},{'1.sqlite','4.sqlite','5.sqlite'})
            self.assertEqual({p:p.read_bytes() for p in before},before)
            self.assertIsNone(M.maintain_serving_storage(state))

    def test_invalid_current_pointer_cannot_trigger_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);store=state/'serving';builds=store/'builds';builds.mkdir(parents=True)
            for i in range(4):(builds/(str(i)+'.sqlite')).write_bytes(b'sql')
            (store/'current.json').write_text(json.dumps(dict(databasePath=str(state/'elsewhere.sqlite'))))
            with self.assertRaisesRegex(ValueError,'existing current'):
                M.maintain_serving_storage(state)
            self.assertEqual(len(list(builds.glob('*.sqlite'))),4)


if __name__=='__main__':unittest.main()
