"""Calendar correction retains transport evidence and never starts game work."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

SCRIPT=Path(__file__).resolve().parents[1]/'pipeline/schedule-qualification.py'
spec=importlib.util.spec_from_file_location('schedule_qualification_test',SCRIPT)
Q=importlib.util.module_from_spec(spec);spec.loader.exec_module(Q)


def payload():
    return dict(totalGames=2,dates=[dict(date='2026-05-23',totalGames=2,games=[
        dict(gamePk=823543,gameType='R',officialDate='2026-09-22',
             status=dict(abstractGameState='Final',detailedState='Postponed')),
        dict(gamePk=823544,gameType='R',officialDate='2026-05-23',
             status=dict(abstractGameState='Final',detailedState='Final'))])])


def batch(state, *, key='a'*32, when='2026-09-17T03:00:00Z', complete=False):
    value=dict(artifactType='baseballo-mlb-game-schedule-batch',contractVersion=1,batchId=key,
        status='pending',scheduleSha256='old-response',requestedStartDate='2026-05-23',
        requestedEndDate='2026-05-24',createdAtUtc=when,expectedGamePks=['823544'],
        qualificationCoverage=dict(contractVersion=1,completeResponse=complete,
            days={'2026-05-23':[dict(gamePk='823544',gameType='R',final=True,unplayed=False)],'2026-05-24':[]}))
    path=state/'pipeline/control/mlb-game/batches'/(key+'.json')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(Q.encoded(value))
    return path,value


def base_days(owner):
    return {day:dict(completeResponse=owner['qualificationCoverage']['completeResponse'],
        games=games,scheduleSha256=owner['scheduleSha256'],batchId=owner['batchId'],
        observedAt=owner['createdAtUtc'],provenanceSha256='old')
        for day,games in owner['qualificationCoverage']['days'].items()}


class ScheduleQualification(unittest.TestCase):
    def test_repair_is_idempotent_and_preserves_original_batch_and_unplayed_occurrence(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);path,owner=batch(state);before=path.read_bytes()
            raw=Q.encoded(payload());fetch=Mock(return_value=raw)
            result=Q.refresh_incomplete_batches(state,fetch=fetch,now='2026-09-17T12:00:00Z')
            self.assertEqual(result['status'],'refreshed')
            self.assertEqual(Q.refresh_incomplete_batches(state,fetch=fetch)['status'],'idle')
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(fetch.call_args.args[0],
                'https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-05-23&endDate=2026-05-24')
            days=Q.merge_snapshots(state,base_days(owner))
            self.assertTrue(all(d['completeResponse'] for d in days.values()))
            self.assertEqual(days['2026-05-23']['scheduleSha256'],Q.sha(raw))
            self.assertEqual(len(days['2026-05-23']['games']),2)
            self.assertEqual([g['gamePk'] for g in days['2026-05-23']['games'] if g['final']],['823544'])
            self.assertEqual(days['2026-05-24']['games'],[])
            self.assertFalse((state/'pipeline/quarantine').exists())

    def test_failed_totals_remain_withheld_and_quarantine_exact_input_after_two_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);_,owner=batch(state)
            data=payload();data['totalGames']=1;raw=Q.encoded(data);fetch=Mock(return_value=raw)
            self.assertEqual(Q.refresh_incomplete_batches(state,fetch=fetch)['status'],'retry')
            self.assertEqual(Q.refresh_incomplete_batches(state,fetch=fetch)['status'],'quarantined')
            self.assertEqual(Q.refresh_incomplete_batches(state,fetch=fetch)['requests'],0)
            self.assertEqual(fetch.call_count,2)
            self.assertFalse(Q.merge_snapshots(state,base_days(owner))['2026-05-23']['completeResponse'])
            files=list((state/'pipeline/quarantine').rglob('*.json'))
            self.assertEqual([p.read_bytes() for p in files],[raw])

    def test_corrupt_snapshot_or_changed_owner_is_rejected(self):
        for fault in ('snapshot','owner'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as directory:
                state=Path(directory);path,owner=batch(state)
                result=Q.refresh_incomplete_batches(state,fetch=lambda _:Q.encoded(payload()))
                if fault=='snapshot':Path(result['path']).write_bytes(b'{}')
                else:
                    owner['scheduleSha256']='changed';path.write_bytes(Q.encoded(owner))
                with self.assertRaises(ValueError):Q.merge_snapshots(state,base_days(owner))

    def test_invalid_json_root_is_retained_for_retry_without_a_coverage_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);batch(state)
            result=Q.refresh_incomplete_batches(state,fetch=lambda _:b'[]')
            self.assertEqual(result['status'],'retry')
            self.assertEqual(list(Q.root(state).glob('*.json')),[])
            self.assertEqual([p.read_bytes() for p in (state/'pipeline/quarantine').rglob('*.json')],[b'[]'])

    def test_newer_incomplete_batch_cannot_be_masked_by_old_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);batch(state)
            Q.refresh_incomplete_batches(state,fetch=lambda _:Q.encoded(payload()),now='2026-09-17T12:00:00Z')
            _,new=batch(state,key='b'*32,when='2026-09-17T13:00:00Z')
            self.assertFalse(Q.merge_snapshots(state,base_days(new))['2026-05-23']['completeResponse'])

    def test_latest_complete_batch_prevents_unneeded_fetch_of_an_older_failed_range(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);batch(state)
            batch(state,key='b'*32,when='2026-09-17T13:00:00Z',complete=True)
            fetch=Mock(side_effect=AssertionError('no acquisition required'))
            self.assertEqual(Q.refresh_incomplete_batches(state,fetch=fetch)['status'],'idle')

    def test_changed_implementation_needs_a_fresh_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);_,owner=batch(state)
            Q.refresh_incomplete_batches(state,fetch=lambda _:Q.encoded(payload()))
            with patch.object(Q,'fingerprint',return_value='new-version'):
                self.assertFalse(Q.merge_snapshots(state,base_days(owner))['2026-05-23']['completeResponse'])
                self.assertEqual(Q.refresh_incomplete_batches(state,fetch=lambda _:Q.encoded(payload()))['status'],'refreshed')


if __name__=='__main__':unittest.main()
