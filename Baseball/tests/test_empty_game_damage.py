"""Cross-PA running credit and Empty Game Damage through the SQL adapter."""
import copy
import sqlite3
import unittest

from test_contribution_players import M, fixture, inputs, GAME, BATTER, RUNNER, G1, PROOF
from test_batting_progress_players import SCOPE


def successful_steal():
    rows=fixture(outs=1,runner_base=1)
    pa=rows[0]['entity']
    rows.append(dict(rows[-1],entity=pa+'/steal-safe',resolution=pa+'/steal-safe',runner=RUNNER,
        act=pa+'/steal',independentStealAct=pa+'/steal',episode=pa+'/steal-episode',
        originDesignation=pa+'/steal-origin',originBase=GAME+'/base/1',originCode='1B',
        destinationBase=GAME+'/base/2',destinationCode='2B',safeJudgment=pa+'/safe',
        safeDecision=pa+'/safe-decision',hasSafeType='true',hasOutType='false'))
    # The runner also has an otherwise empty batting performance in this game.
    rows.extend({k:v.replace('/plate-appearance/0','/plate-appearance/1').replace(BATTER,RUNNER)
                 for k,v in row.items()} for row in fixture(outs=0,runner_base=None))
    for row in rows:
        if row['kind']=='plate_appearance':
            key=row['entity']
            row.update(act=key+'/batter-act',paResult=key+'/result',paResultJudgment=key+'/judgment',
                paResultDecision=key+'/decision',paResultRecord=key+'/record')
    for player in (BATTER,RUNNER):
        rows.append(dict(kind='player_team_game',graph=G1,game=GAME,entity=player+'/team-role',
            playerTeamRole=player+'/team-role',player=player,team=GAME+'/team',teamRole=GAME+'/home-role'))
    return rows


def summarize(rows):
    admitted=inputs(rows)
    qualification=M.batting_qualification(rows,graphs=[G1],admissions={G1:PROOF},
        date_scope=SCOPE,selected_games_complete=True)
    return admitted,M.contribution_players('empty-game-damage',[admitted],qualification=qualification,date_scope=SCOPE)


class EmptyGameDamage(unittest.TestCase):
    def test_successful_steal_prevents_only_its_runners_empty_game(self):
        rows=successful_steal()
        admitted,result=summarize(rows)
        self.assertTrue(admitted['complete'],admitted)
        self.assertTrue(admitted['independentDamageComplete'])
        self.assertTrue(result['playerPopulationComplete'],result)
        player,=result['playerResults']
        self.assertEqual(player['player'],BATTER)
        self.assertEqual(player['aggregate']['count'],1)
        # The batter still receives actual-end-state erosion and no steal credit.
        pa=next(p for p in admitted['plateAppearances'] if p['player']==BATTER)
        self.assertEqual(player['value'],M.exact(-M.fraction(pa['score']['value'])))
        self.assertEqual(pa['score']['components']['progress'],M.exact(0))
        self.assertEqual(summarize(list(reversed(rows))), (admitted,result))

    def test_unknown_or_conflicting_running_credit_and_actual_out_stay_withheld(self):
        for fault in ('missing_attribution','contact_conflict','runner_out','interrupted_turn'):
            with self.subTest(fault=fault):
                rows=successful_steal();steal=next(r for r in rows if r.get('independentStealAct'))
                if fault=='missing_attribution':steal.pop('independentStealAct')
                elif fault=='contact_conflict':steal['contactPlay']=GAME+'/contact'
                elif fault=='runner_out':steal.update(hasSafeType='false',hasOutType='true')
                else:
                    turn=copy.deepcopy(rows[0]);turn['entity']=GAME+'/plate-appearance/interrupted'
                    turn['recognizedBattingResult']='false';rows.append(turn)
                admitted,result=summarize(rows)
                self.assertFalse(admitted.get('independentDamageComplete',False))
                self.assertFalse(result['playerPopulationComplete'])
                self.assertEqual(result['playerResults'],[])

    def test_sql_preserves_cross_pa_credit_and_agrees_with_empty_game_count(self):
        rows=successful_steal();admitted,expected=summarize(rows)
        bindings=[{k:dict(type='uri' if v.startswith('https://') else 'literal',value=v)
                   for k,v in row.items()} for row in rows]
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
            day=SCOPE['startDate']
            conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (G1,GAME,'101',day,day+'T12:00:00Z',2026,'regular_season',None,None,None,None,None,None))
            M.materialize_game(conn,G1,bindings,batting_admission=PROOF,
                runner_resolution_admission=PROOF,runner_boundary_admission=PROOF)
            text=M._json(dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)]))
            conn.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day,text,M._hash(text)))
            retained,=M.read_results(conn,G1,'tfs')
            self.assertEqual(retained['contributionInputs'],admitted)
            result=M.query_sql(conn,dict(metricId='empty-game-damage'),SCOPE)['metric']
            self.assertEqual(result['playerResults'],expected['playerResults'])
            counts=M.query_sql(conn,dict(metricId='empty-game-rate'),SCOPE)['metric']
            self.assertTrue(counts['playerPopulationComplete'],counts)
            self.assertEqual({p['player']:p['aggregate']['count'] for p in counts['playerResults']},
                             {BATTER:1,RUNNER:0})
            # Missing schedule proof still blocks the public selected period.
            conn.execute('DELETE FROM metric_suite_schedule_coverage')
            self.assertFalse(M.query_sql(conn,dict(metricId='empty-game-damage'),SCOPE)['metric']['playerPopulationComplete'])


if __name__=='__main__':unittest.main()
