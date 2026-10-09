"""Official eligibility and binary scoring credit preserve actual actors."""
import copy
import unittest
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


if __name__=='__main__':unittest.main()
