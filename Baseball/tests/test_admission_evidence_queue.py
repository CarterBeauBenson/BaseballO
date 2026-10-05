import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'sources/mlb-game/pipeline/admission-evidence-queue.py'
spec = importlib.util.spec_from_file_location('admission_queue_test', SCRIPT)
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)


class DeferredEvidenceQueue(unittest.TestCase):
    def test_resume_deferred_game_before_sweep_and_keep_failure_retries_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            control = state/'pipeline/control/mlb-game/admission-evidence'
            marker = state/'pipeline/evidence/nifi/game-promotion/999/latest.json'
            Q.E.atomic(marker, dict(gamePk='999', promotedAtUtc='2026-10-01T00:00:00Z'))
            Q.E.atomic(control/'999.json', dict(status='waiting-for-memory', checkedAtUtc='2026-10-01T00:00:00Z'))
            # This retired deferred job must not be resumed.
            Q.E.atomic(control/'998.json', dict(status='waiting-for-memory', checkedAtUtc='2026-09-01T00:00:00Z'))
            inventory = SimpleNamespace(validated_promotion_record=lambda *a:dict(gamePk=a[2]),
                                        query_index_contract_admission=lambda: {})
            def module(path, name):
                if Path(path).name == 'work_scope.py':
                    return SimpleNamespace(excluded_games=lambda state: {'998'})
                if Path(path).name == 'game_promotion_inventory.py':
                    return inventory
                return SimpleNamespace(fingerprint=lambda:'producer')
            with patch.object(Q.E, 'module', side_effect=module), \
                 patch.object(Q.E, 'fingerprint', return_value='unchanged-producer'), \
                 patch.object(Q.E, 'preserve_interrupted_refresh', return_value=[]), \
                 patch.object(Q.E, 'refresh_game', side_effect=ValueError('recorded failure')) as refresh, \
                 patch.object(Q.E, 'tick', return_value={'status':'sweep'}) as sweep:
                self.assertEqual(Q.tick(state, None, None)['resumedGame'], '999')
                self.assertEqual(Q.tick(state, None, None)['resumedGame'], '999')
                self.assertEqual(Q.tick(state, None, None)['status'], 'sweep')
                self.assertEqual(refresh.call_count, 2)
                sweep.assert_called_once()
                record = json.loads((control/'999.json').read_text())
                self.assertEqual(record['failureAttempts'], 2)
                self.assertFalse(record['rdfChanged'])
                # New promotion inputs get their own bounded retry.
                Q.E.atomic(marker, dict(gamePk='999', promotedAtUtc='2026-10-02T00:00:00Z'))
                refresh.side_effect = None
                refresh.return_value = dict(status='current', refreshed=[])
                self.assertEqual(Q.tick(state, None, None)['outcomes'], {'current':1})
                self.assertEqual(json.loads((control/'999.json').read_text())['failureAttempts'], 0)
                self.assertEqual(Q.tick(state, None, None)['status'], 'sweep')


if __name__ == '__main__':
    unittest.main()
