"""Retiring a competition stops work without deleting or admitting its data."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


S=module(ROOT/'sources/mlb-game/pipeline/work_scope.py','test_work_scope')
P=module(ROOT/'sources/mlb-game/nifi/prepare-schedule-batch.py','scope_schedule')
I=module(ROOT/'scripts/pipeline/game_promotion_inventory.py','scope_inventory')
R=module(ROOT/'sources/mlb-game/pipeline/repair-status.py','scope_status')


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


class WorkScope(unittest.TestCase):
    def test_world_series_and_ordinary_spring_league_team_metadata_remain_active(self):
        for kind in ('R','F','D','L','W','C','P','A'):
            self.assertIsNone(S.exclusion_reason(dict(gameData=dict(game=dict(type=kind),
                teams=dict(home=dict(league=dict(id=103),springLeague=dict(id=115)))))))
        for league in (159,160):
            self.assertEqual(S.exclusion_reason(dict(gameData=dict(game=dict(type='W'),
                teams=dict(away=dict(league=dict(id=league)))))), 'world-baseball-classic')

    def test_schedule_excludes_work_but_keeps_complete_transport_census(self):
        games=[dict(gamePk=n,gameType=kind,officialDate='2026-03-01',
            status=dict(abstractGameState='Final',detailedState='Final'))
            for n,kind in enumerate(('R','W','S','E','R'),1)]
        games[-1]['teams']=dict(home=dict(team=dict(league=dict(id=160))))
        document=dict(totalGames=5,dates=[dict(date='2026-03-01',totalGames=5,games=games)])
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)
            output=P.transform(json.dumps(document).encode(),SimpleNamespace(state_root=state,
                batch_id='a'*32,request_kind='backfill',start_date='2026-03-01',end_date='2026-03-01'))
            self.assertEqual([g['gamePk'] for g in output['games']],['1','2'])
            batch=json.loads(next((state/'pipeline/control/mlb-game/batches').glob('*.json')).read_bytes())
            self.assertTrue(batch['qualificationCoverage']['completeResponse'])
            self.assertEqual(batch['qualificationCoverage']['coveredOccurrences'],5)
            self.assertEqual(set(S.excluded_games(state)),{'3','4','5'})

    def test_retained_batch_classification_updates_cache_without_touching_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);path=state/'pipeline/control/mlb-game/batches/old.json'
            write(path,dict(games=[dict(gamePk='1',gameType='S'),dict(gamePk='2',gameType='R')]))
            original=path.read_bytes()
            self.assertEqual(set(S.excluded_games(state)),{'1'})
            write(path.with_name('new.json'),dict(excludedGames=[dict(gamePk='3',reason='world-baseball-classic')]))
            self.assertEqual(set(S.excluded_games(state)),{'1','3'})
            self.assertEqual(path.read_bytes(),original)

    def test_sql_inventory_skips_archived_proof_before_validating_active_games(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);promoted=state/'pipeline/evidence/nifi/game-promotion'
            write(promoted/'1/marker.json',dict(broken='historical diagnostic stays intact'))
            write(promoted/'2/marker.json',dict(promotedAtUtc='2026-10-04T00:00:00Z'))
            admission=dict(routingSha256='a',semanticContractId='b',semanticContractSha256='c',fixedLegacyImplementationSha256=[])
            with patch.object(I,'query_index_contract_admission',return_value=admission), \
                    patch.object(I,'validated_promotion_record',return_value=dict(gamePk='2',queryIndexImplementationSha256='d')) as check:
                inventory=I.promotion_inventory(state,excluded_game_pks={'1'})
            self.assertEqual(set(inventory['games']),{'2'})
            check.assert_called_once()
            self.assertTrue((promoted/'1/marker.json').exists())

    def test_observer_separates_archived_failures_without_claiming_they_were_fixed(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp);control=state/'pipeline/control/mlb-game'
            write(control/'batches/old.json',dict(games=[dict(gamePk='1',gameType='E')]))
            failure=control/'admission-evidence/1.json'
            write(failure,dict(status='partial',familyFailures={'roster':'ambiguous'}))
            write(state/'pipeline/evidence/nifi/game-promotion/1/marker.json',{})
            owner=SimpleNamespace(cases=lambda:[],DISCOVERY=SimpleNamespace(fingerprint=lambda owner:'v'),
                completed_case=lambda previous,case:False,TX=SimpleNamespace(now=lambda:'now'))
            report=R.observe(state,owner)
            self.assertEqual(report['promotedGames'],0)
            self.assertEqual(report['retainedPromotedGames'],1)
            self.assertEqual(report['excludedFromActiveWork']['unresolvedCheckpointsPreserved'],1)
            self.assertEqual(report['issues'],[])
            self.assertEqual(json.loads(failure.read_bytes())['status'],'partial')
            self.assertFalse(report['recordedWorkClear'])


if __name__=='__main__':unittest.main()
