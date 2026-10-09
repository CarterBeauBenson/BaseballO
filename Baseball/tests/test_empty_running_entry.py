"""EG3 settles only binary running credit, with the existing census/eligibility."""
import copy
import json
import unittest
from unittest.mock import patch

from test_player_ranges import M, P, G, U, SCOPE


class EmptyRunningEntry(unittest.TestCase):
    def rows(self, kind='WildPitchProcess'):
        graph=G+'1';game='game';pa='pa';player=U+'1'
        move=dict(kind='runner_movement',graph=graph,game=game,plateAppearance=pa,
            runner=player,batter=player,act='act',episode='episode',resolution='safe',record='record',
            metricOrigin='0',destinationBase='first',destinationCode='1B',safeJudgment='safe-j',safeDecision='safe-d',
            hasSafeType='true',hasOutType='false',hasRunType='false',
            independentRunningProcess='process',independentRunningType='https://baseballontology.org/'+kind,
            independentRunningJudgment='judgment',independentRunningDecision='decision',
            trajectory='whole',trajectoryHalf='half',trajectoryInterval='interval')
        return [dict(kind='plate_appearance',entity=pa,player=player,graph=graph,game=game,
                     recognizedBattingResult='true',paResultType='https://baseballontology.org/StrikeoutProcess'),move]

    def read(self, rows):
        return P.empty_running_entries(M,rows,dict(unresolvedPlateAppearances=[dict(plateAppearance='pa')]))

    def test_safe_entry_is_binary_running_only_and_needs_its_complete_pattern(self):
        for kind in ('WildPitchProcess','PassedBallProcess'):
            rows=self.rows(kind)
            self.assertEqual(self.read(rows),{'pa':[U+'1']})
            self.assertIsNone(M.independent_running_act(rows[1]))  # no new scalar weight
            for missing in ('safeDecision','record','independentRunningJudgment','independentRunningDecision'):
                broken=copy.deepcopy(rows);broken[1].pop(missing)
                self.assertEqual(self.read(broken),{})
        for kind in ('BalkProcess','ErrorProcess','InterferenceProcess'):
            self.assertEqual(self.read(self.rows(kind)),{})

    def test_continuation_needs_exact_history_and_cannot_keep_a_consumed_entry(self):
        rows=self.rows();step=dict(rows[1],episode='later',resolution='later-safe',act='later-act',
            originDesignation='origin',originBase='first',originCode='1B',destinationCode='2B',destinationBase='second')
        for field in M.INDEPENDENT_RUNNING_FIELDS:step.pop(field)
        rows.append(step)
        self.assertEqual(self.read(rows),{})  # continuity cannot come from same person alone
        rows.extend(dict(kind='runner_history',graph=G+'1',game='game',player=U+'1',
            trajectory='whole',trajectoryHalf='half',trajectoryInterval='interval',episode=e) for e in ('episode','later'))
        self.assertEqual(self.read(rows),{'pa':[U+'1']})
        step.update(hasSafeType='false',hasOutType='true')
        self.assertEqual(self.read(rows),{})

    def test_prepared_count_keeps_eligibility_and_resolution_admission_separate(self):
        rows=self.rows();rows.append(dict(kind='player_team_game',graph=G+'1',game='game',player=U+'1',team='team',teamRole='role'))
        progress=dict(plateAppearances=[],unresolvedPlateAppearances=[dict(plateAppearance='pa',player=U+'1',
            officialResult=True,possiblePositivePlayers=[U+'1'],gaps=['UNRESOLVED_PROGRESS_ATTRIBUTION'])])
        for eligible,admitted,expected in ((1,True,(1,0,1)),(1,False,(0,1,1)),(0,True,(1,0,0))):
            q=dict(participation=[dict(player=U+'1',plateAppearances=eligible)],
                expectedObservations=[dict(player=U+'1',plateAppearance='pa')] if eligible else [])
            with patch.object(P,'qualification',return_value=q):
                _,records=P.project(M,graph=G+'1',scope=SCOPE,rows=rows,
                    proofs=dict(batting={},run={},players=dict(rosterComplete=True),resolution=dict(status='admitted',sourceReconciled=True,graphConforms=True) if admitted else {}),
                    inputs=dict(contribution={},progress=progress,emptyRunningEntries=self.read(rows)),
                    runs={},run_people={},metric_ids={'empty-game-rate'})
            record=records[0];aggregate=json.loads(record[4])
            self.assertEqual((record[3],aggregate['count'],aggregate['eligibleGames']),expected)


if __name__=='__main__':unittest.main()
