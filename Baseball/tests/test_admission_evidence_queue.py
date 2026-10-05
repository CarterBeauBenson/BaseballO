import importlib.util
import json
import sqlite3
from contextlib import closing
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
    def test_missing_player_proofs_precede_maintenance_without_repeating_terminal_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            database = state/'serving/dashboard/builds/published.sqlite'
            database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as db:
                db.executescript('''
                    CREATE TABLE game_dimension(graph_iri TEXT, game_pk TEXT, game_set TEXT);
                    CREATE TABLE metric_suite_admission(graph_iri TEXT, proof_json TEXT);
                    CREATE TABLE dashboard_player_admission(graph_iri TEXT,proof_json TEXT);
                    CREATE TABLE dashboard_player_game(graph_iri TEXT,plate_appearances INTEGER);
                    INSERT INTO game_dimension VALUES ('g1','999','regular_season'),
                        ('g2','998','regular_season'), ('g3','997','regular_season');
                    INSERT INTO metric_suite_admission VALUES ('g1','{"status":"withheld"}'),
                        ('g2','{"status":"withheld"}'), ('g3','{"status":"admitted"}');
                    INSERT INTO dashboard_player_admission VALUES ('g2','{}');
                ''')
            Q.E.atomic(state/'serving/dashboard-current.json', {'databasePath':str(database)})
            self.assertEqual(Q.missing_player_games(state), {'999'})
            with closing(sqlite3.connect(database)) as db:
                db.execute('UPDATE dashboard_player_admission SET proof_json=?',
                    (json.dumps(dict(implementationSha256='old',players=[dict(status='withheld')])),))
                db.execute('INSERT INTO dashboard_player_game VALUES (?,NULL)',('g2',));db.commit()
            self.assertEqual(Q.missing_player_games(state), {'999','998'})
            control = state/'pipeline/control/mlb-game/admission-evidence'
            for game, status in [('999', 'retained-rdf-unavailable'), ('998', 'partial-refreshed')]:
                Q.E.atomic(state/f'pipeline/evidence/nifi/game-promotion/{game}/latest.json',
                           dict(gamePk=game, promotedAtUtc='2026-10-05T00:00:00Z'))
                Q.E.atomic(control/(game+'.json'), dict(status=status,
                    checkedAtUtc='2026-09-29T00:00:00Z' if game=='999' else '2026-09-30T00:00:00Z'))
            inventory = SimpleNamespace(validated_promotion_record=lambda *a:dict(gamePk=a[2]),
                                        query_index_contract_admission=lambda: {})
            def module(path, name):
                if Path(path).name == 'work_scope.py':
                    return SimpleNamespace(excluded_games=lambda state: set())
                if Path(path).name == 'game_promotion_inventory.py':
                    return inventory
                return SimpleNamespace(fingerprint=lambda:'producer')
            with patch.object(Q.E, 'module', side_effect=module), \
                 patch.object(Q.E, 'fingerprint', return_value='unchanged-producer'), \
                 patch.object(Q.E, 'preserve_interrupted_refresh', return_value=[]), \
                 patch.object(Q.E, 'refresh_game', return_value=dict(status='current', refreshed=[])) as refresh, \
                 patch.object(Q.E, 'tick', return_value={'status':'sweep'}) as sweep:
                self.assertEqual(Q.tick(state, None, None)['resumedGames'], ['999', '998'])
                self.assertEqual([call.args[1]['gamePk'] for call in refresh.call_args_list], ['999', '998'])
                # The published snapshot has not changed; current evidence must still be skipped.
                self.assertEqual(Q.tick(state, None, None)['status'], 'sweep')
                self.assertEqual(refresh.call_count, 2)
                sweep.assert_called_once()

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
