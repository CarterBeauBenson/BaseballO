"""Official eligibility and binary scoring credit preserve actual actors."""
import copy
import json
import unittest
from unittest.mock import patch
from test_player_ranges import M, P, G, U, SCOPE

BASE='https://baseballontology.org/'
PROOF=dict(status='admitted',sourceReconciled=True,graphConforms=True)


class EmptyScoringCredit(unittest.TestCase):
    def turn(self):
        return dict(kind='plate_appearance',graph=G+'1',game='game',entity='pa',player=U+'1',act='bat1',
            recognizedBattingResult='true',paResultType=BASE+'BattedBallOutProcess',paResult='result',
            paResultJudgment='pj',paResultDecision='pd',paResultRecord='pr')

    def error(self):
        return dict(kind='runner_movement',graph=G+'1',game='game',plateAppearance='pa',runner=U+'2',batter=U+'1',
            act='act',episode='episode',resolution='resolution',record='record',
            originDesignation='origin',originBase='second',originCode='2B',destinationBase='third',destinationCode='3B',
            safeJudgment='sj',safeDecision='sd',hasSafeType='true',hasOutType='false',hasRunType='false',
            secondaryError='error',errorJudgment='ej',errorDecision='ed',
            trajectory='whole',trajectoryHalf='half',trajectoryInterval='interval')

    def read(self,rows):
        return P.empty_scoring_inputs(M,rows,dict(unresolvedPlateAppearances=[dict(plateAppearance='pa')]))['pa']

    def test_official_credit_counts_once_without_reassigning_actual_acts(self):
        turn=self.turn();turn.update(creditedPlayer=U+'2',creditJudgment='cj',creditDecision='cd',creditRecord='cr')
        rows=[turn,dict(turn,player=U+'2',act='bat2')]
        rows += [dict(kind='player_team_game',graph=G+'1',game='game',player=U+str(i),team='team',teamRole='role') for i in (1,2)]
        before=copy.deepcopy(rows)
        q=M.batting_qualification(rows,graphs=[G+'1'],admissions={G+'1':PROOF},date_scope=SCOPE,selected_games_complete=True)
        self.assertEqual({r['player']:r['plateAppearances'] for r in q['participation']},{U+'1':0,U+'2':1})
        self.assertEqual(rows,before)
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,players=[dict(player=U+str(i),status='admitted') for i in (1,2)])
        self.assertEqual(P.qualification(M,rows,G+'1',SCOPE,{},individual)['participation'],q['participation'])
        rows[1]['creditedPlayer']=U+'1'
        with self.assertRaises(M.EvidenceError):M.batting_qualification(rows,graphs=[G+'1'],admissions={G+'1':PROOF},date_scope=SCOPE)

    def test_error_only_is_zero_but_mixed_contact_remains_unknown(self):
        rows=[self.turn(),self.error()]
        self.assertEqual(self.read(rows),dict(positivePlayers=[],possiblePositivePlayers=[]))
        rows[1]['errorContactPlay']='contact'
        self.assertEqual(self.read(rows)['possiblePositivePlayers'],[U+'1',U+'2'])
        rows[1].pop('errorContactPlay');rows[1].pop('errorDecision')
        self.assertEqual(self.read(rows)['possiblePositivePlayers'],[U+'1',U+'2'])

    def test_error_does_not_erase_a_safe_steal_but_terminal_out_does(self):
        error=self.error();steal=dict(error,act='steal-act',resolution='steal-resolution',episode='steal',
            originBase='first',originCode='1B',destinationBase='second',destinationCode='2B',independentStealAct='steal-act')
        for field in ('secondaryError','errorJudgment','errorDecision'):steal.pop(field)
        rows=[self.turn(),steal,error]
        self.assertEqual(self.read(rows)['positivePlayers'],[])  # missing C1 membership
        rows += [dict(kind='runner_history',graph=G+'1',game='game',player=U+'2',trajectory='whole',
                      trajectoryHalf='half',trajectoryInterval='interval',episode=e) for e in ('steal','episode')]
        self.assertEqual(self.read(rows),dict(positivePlayers=[U+'2'],possiblePositivePlayers=[]))
        error.update(hasSafeType='false',hasOutType='true')
        self.assertEqual(self.read(rows),dict(positivePlayers=[],possiblePositivePlayers=[]))

    def test_rbi_is_batting_only_with_accepted_result_exclusions(self):
        run=self.error();run.update(hasSafeType='false',hasRunType='true',errorContactPlay='contact',
            rbiPlayer=U+'1',rbiJudgment='rj',rbiDecision='rd',rbiRecord='rr')
        rows=[self.turn(),run]
        self.assertEqual(self.read(rows)['positivePlayers'],[U+'1'])
        for kind in ('ErrorProcess','FieldersChoiceProcess','InterferenceProcess'):
            rows[0]['paResultType']=BASE+kind
            self.assertEqual(self.read(rows)['positivePlayers'],[])
        rows[0]['paResultType']=BASE+'SacrificeFlyProcess';run['hasRunType']='false';run['hasOutType']='true'
        self.assertEqual(self.read(rows)['positivePlayers'],[])

    def terminal_path(self):
        first=self.error()
        first.update(runner=U+'1',metricOrigin='0',destinationBase='first',destinationCode='1B')
        for field in ('originDesignation','originBase','originCode','secondaryError','errorJudgment','errorDecision'):
            first.pop(field)
        out=dict(first,act='out-act',episode='out-episode',resolution='out-resolution',
            originDesignation='origin',originBase='first',originCode='1B',
            hasSafeType='false',hasOutType='true')
        return [self.turn(),first,out,*[dict(kind='runner_history',graph=G+'1',game='game',player=U+'1',
            trajectory='whole',trajectoryHalf='half',trajectoryInterval='interval',episode=e)
            for e in ('episode','out-episode')]]

    def test_explicit_counted_rbi_survives_an_unavailable_runner_path(self):
        first=self.error();first['originCode']='1B';first['destinationCode']='2B'
        run=dict(self.error(),resolution='run',episode='scored',act='scoring-act',
            hasSafeType='false',hasRunType='true',rbiPlayer=U+'1',
            rbiJudgment='rj',rbiDecision='rd',rbiRecord='rr',errorContactPlay='contact')
        rows=[self.turn(),first,run]  # no complete C1 membership
        self.assertEqual(self.read(rows)['positivePlayers'],[U+'1'])
        self.assertEqual(self.read(rows)['possiblePositivePlayers'],[U+'1',U+'2'])
        conflict=dict(run,rbiPlayer=U+'2')
        self.assertEqual(self.read([*rows,conflict])['positivePlayers'],[])
        run.pop('rbiDecision')
        self.assertEqual(self.read(rows)['positivePlayers'],[])

    def test_unattributed_advance_is_consumed_only_by_a_complete_terminal_path(self):
        rows=self.terminal_path()
        self.assertEqual(self.read(rows),dict(positivePlayers=[],possiblePositivePlayers=[]))
        self.assertEqual(self.read(rows[:-1])['possiblePositivePlayers'],[U+'1'])
        rows[2].update(hasSafeType='true',hasOutType='false',destinationBase='second',destinationCode='2B')
        self.assertEqual(self.read(rows),dict(positivePlayers=[],possiblePositivePlayers=[U+'1']))
        self.assertEqual(P.empty_scoring_inputs(M,[self.turn()],dict(
            unresolvedPlateAppearances=[dict(plateAppearance='pa')])),{})

    def test_completed_batting_row_can_clear_only_its_admitted_running_gap(self):
        rows=self.terminal_path()
        rows.append(dict(kind='player_team_game',graph=G+'1',game='game',player=U+'1',team='team',teamRole='role'))
        progress=dict(plateAppearances=[dict(plateAppearance='pa',player=U+'1',officialResult=True,
            reach=0,batterPositive=False,otherPositivePlayers=[],independentPositive=[],positiveChannels=[],
            independentEpisodes=[],independentEpisodeGaps=['UNKNOWN_CHANNEL'],independentPositiveGaps=['UNKNOWN_CHANNEL'],
            unresolvedRunningPositivePlayers=[U+'1'])],unresolvedPlateAppearances=[])
        q=dict(participation=[dict(player=U+'1',plateAppearances=1)],
            expectedObservations=[dict(player=U+'1',plateAppearance='pa')])
        for resolution,expected in ((PROOF,1),({},0)):
            with patch.object(P,'qualification',return_value=q):
                _,records=P.project(M,graph=G+'1',scope=SCOPE,rows=rows,
                    proofs=dict(batting=PROOF,run={},players={},resolution=resolution),
                    inputs=dict(contribution={},progress=progress,emptyScoring=P.empty_scoring_inputs(M,rows,progress)),
                    runs={},run_people={},metric_ids={'empty-game-rate'})
            self.assertEqual(records[0][3],expected)
            self.assertEqual(json.loads(records[0][4])['count'],1)

    def test_awarded_batter_positive_does_not_assign_the_other_batters_contribution(self):
        first=self.terminal_path()[1]
        first.update(award='walk',awardRule='walk-rule')
        other=dict(first,batter=U+'2');other.pop('metricOrigin')
        rows=[dict(self.turn(),paResultType=BASE+'WalkProcess'),
              dict(self.turn(),player=U+'2',act='bat2',paResultType=BASE+'WalkProcess'),first,other]
        self.assertEqual(self.read(rows),dict(positivePlayers=[U+'1'],possiblePositivePlayers=[U+'2']))
        # Official eligibility does not move the actual award to someone else.
        for r in rows[:2]:r.update(creditedPlayer=U+'2',creditJudgment='cj',creditDecision='cd',creditRecord='cr')
        self.assertEqual(self.read(rows)['positivePlayers'],[U+'1'])
        broken=copy.deepcopy(rows);broken[-1]['resolution']='conflicting-resolution'
        self.assertEqual(self.read(broken)['positivePlayers'],[])
        broken=copy.deepcopy(rows);broken[-1]['safeDecision']='conflicting-decision'
        self.assertEqual(self.read(broken)['positivePlayers'],[])
        out=self.terminal_path()[2];rows.append(out)
        self.assertEqual(self.read(rows)['positivePlayers'],[])  # incomplete C1 path
        rows.extend(self.terminal_path()[3:])
        self.assertEqual(self.read(rows),dict(positivePlayers=[],possiblePositivePlayers=[]))

    def test_scoring_refinement_preserves_known_batting_zero_and_all_out_exclusion(self):
        def completed(pa,player):
            return dict(plateAppearance=pa,player=player,officialResult=True,reach=0,
                batterPositive=False,otherPositivePlayers=[],independentPositive=[],positiveChannels=[],
                independentEpisodes=[],independentEpisodeGaps=[],independentPositiveGaps=[])
        other=dict(self.turn(),entity='other-pa',player=U+'2',act='other-act')
        roster=[dict(kind='player_team_game',graph=G+'1',game='game',player=U+str(i),team='team',teamRole='role') for i in (1,2)]
        q=dict(participation=[dict(player=U+str(i),plateAppearances=1) for i in (1,2)],
            expectedObservations=[dict(player=U+'1',plateAppearance='pa'),dict(player=U+'2',plateAppearance='other-pa')])
        unknown=self.error()
        for field in ('secondaryError','errorJudgment','errorDecision'):unknown.pop(field)
        rows=[self.turn(),other,unknown,*roster]
        progress=dict(plateAppearances=[completed('pa',U+'1'),completed('other-pa',U+'2')],unresolvedPlateAppearances=[])
        progress['plateAppearances'][0].update(independentPositiveGaps=['UNKNOWN_CHANNEL'],unresolvedRunningPositivePlayers=[U+'2'])
        scoring=P.empty_scoring_inputs(M,rows,progress)
        self.assertEqual(scoring['pa']['possiblePositivePlayers'],[U+'1',U+'2'])
        def project(inputs,evidence):
            with patch.object(P,'qualification',return_value=q):
                _,records=P.project(M,graph=G+'1',scope=SCOPE,rows=evidence,
                    proofs=dict(batting=PROOF,run={},players={},resolution=PROOF),
                    inputs=dict(contribution={},**inputs),runs={},run_people={},metric_ids={'empty-game-rate'})
            return {r[1]:(r[3],json.loads(r[4])['count']) for r in records}
        self.assertEqual(project(dict(progress=progress,emptyScoring=scoring),rows),{U+'1':(1,1),U+'2':(0,1)})
        # Two actual-batter bindings repeat one out. The existing all-out
        # exclusion already proves zero; unresolved attribution cannot undo it.
        out=dict(unknown,hasSafeType='false',hasOutType='true',runner=U+'1')
        rows=[self.turn(),dict(self.turn(),player=U+'2',act='bat2'),other,out,dict(out,batter=U+'2'),*roster]
        progress=dict(plateAppearances=[completed('other-pa',U+'2')],unresolvedPlateAppearances=[dict(
            plateAppearance='pa',player=U+'1',officialResult=True,possiblePositivePlayers=None,gaps=['AMBIGUOUS_BATTING_CONTRIBUTOR'])])
        inputs=dict(progress=progress,emptyScoring=P.empty_scoring_inputs(M,rows,progress),
            ambiguousProgressPlayers={'pa':[U+'1',U+'2']},ambiguousEmptyPositivePlayers={'pa':[]})
        self.assertEqual(project(inputs,rows),{U+'1':(1,1),U+'2':(1,1)})


if __name__=='__main__':unittest.main()
