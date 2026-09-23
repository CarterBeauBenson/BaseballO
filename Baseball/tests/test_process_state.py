import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('worker_state',ROOT/'scripts/pipeline/process_state.py')
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


class ProcessState(unittest.TestCase):
    def test_only_confirmed_dead_worker_becomes_interrupted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'progress.json'
            running=dict(status='running',processId=123,completedGames=20)
            for answer in (True,None,False):
                path.write_text(json.dumps(running))
                result=M.reconcile(path,is_alive=lambda pid:answer)
                self.assertEqual(result['status'],'interrupted' if answer is False else 'running')
                self.assertEqual(result['completedGames'],20)
            path.write_text(json.dumps(dict(status='published',processId=123)))
            self.assertEqual(M.reconcile(path,is_alive=lambda pid:False)['status'],'published')


if __name__=='__main__':unittest.main()
