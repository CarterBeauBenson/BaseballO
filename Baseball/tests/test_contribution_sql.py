"""Contributions and PAQ reach SQL only with complete, checked populations."""
from datetime import date,timedelta
import json
import sqlite3
import unittest

from test_contribution_players import M,fixture,inputs,GAME,BATTER,RUNNER,BASE,G1,PROOF


def sample(game,mode):
    rows=fixture(outs=1,contact=mode!='out');pa=rows[0]['entity']
    rows[0].update(act=pa+'/batter-act',paResult=pa+'/result',paResultJudgment=pa+'/judgment',
        paResultDecision=pa+'/decision',paResultRecord=pa+'/record')
    if mode!='out':
        rows[0]['paResultType']=BASE+('SingleProcess' if mode=='safe' else 'HomeRunProcess')
        runner=rows[-1];runner.update(hasOutType='false')
        if mode=='safe':
            runner.update(hasSafeType='true',destinationBase=GAME+'/base/1',destinationCode='1B',safeJudgment=pa+'/safe',safeDecision=pa+'/safe-decision')
        else:
            runner['hasRunType']='true'
            rows.append(dict(runner,entity=pa+'/runner-score',resolution=pa+'/runner-score',runner=RUNNER,metricOrigin='3',
                act=pa+'/runner-act',episode=pa+'/runner-episode',originDesignation=pa+'/origin',originBase=GAME+'/base/3',originCode='3B'))
    rows.append(dict(kind='player_team_game',graph=G1,game=GAME,entity=BATTER+'/team-role',playerTeamRole=BATTER+'/team-role',
        player=BATTER,team='https://baseballontology.org/data/team/1',teamRole=GAME+'/home-role'))
    graph='https://w3id.org/baseball/graph/game/'+str(game)
    newgame='https://baseballontology.org/data/game/'+str(game)
    rows=[{k:v.replace(GAME,newgame).replace(G1,graph) for k,v in row.items()} for row in rows]
    bindings=[{k:dict(type='uri' if v.startswith('https://') else 'literal',value=v) for k,v in row.items()} for row in rows]
    return graph,bindings


def database():
    conn=sqlite3.connect(':memory:');conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
    for i,mode in enumerate(('out','safe','score'),1):
        graph,rows=sample(100+i,mode);day=f'2026-08-0{i}';game=str(100+i)
        conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+game,game,day,day+'T12:00:00Z',2026,'regular_season',None,None,None,None,None,None))
        M.materialize_game(conn,graph,rows,batting_admission=PROOF,runner_resolution_admission=PROOF,runner_boundary_admission=PROOF)
        stored,=M.read_results(conn,graph,'tfs')
        assert stored['contributionInputs']['complete'],stored
    day=date(2026,1,1)
    while day<=date(2026,8,3):
        games=[dict(gamePk=str(100+day.day),gameType='R',final=True,unplayed=False)] if day.month==8 else []
        text=M._json(dict(completeResponse=True,games=games))
        conn.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day.isoformat(),text,M._hash(text)))
        day+=timedelta(days=1)
    return conn


SCOPE=dict(startDate='2026-08-02',endDate='2026-08-03',gameSet='regular_season')


class ContributionSQL(unittest.TestCase):
    def test_known_contribution_does_not_manufacture_an_adjusted_paq_state(self):
        with database() as conn:
            stored,=M.read_results(conn,G1,'tfs')
            stored['contributionInputs']['plateAppearances'][0]['comparisonState']=None
            M.store_result(conn,G1,'tfs','game-scope',stored)
            scope=dict(SCOPE,startDate='2026-08-01')
            for metric in ('tfs','paq-2'):
                self.assertTrue(M.query_sql(conn,dict(metricId=metric),scope)['metric']['playerPopulationComplete'])
            adjusted=M.query_sql(conn,dict(metricId='paq-a'),scope)['metric']
            self.assertFalse(adjusted['playerPopulationComplete'])
            self.assertEqual(adjusted['playerSummaryGaps'],['PAQ_A_STATE'])

    def test_empty_damage_averages_only_empty_games_and_requires_independent_coverage(self):
        with database() as conn:
            scope=dict(SCOPE,startDate='2026-08-01')
            result=M.query_sql(conn,dict(metricId='empty-game-damage'),scope)['metric']
            self.assertTrue(result['playerPopulationComplete'],result)
            player,=result['playerResults']
            self.assertEqual(player['value'],M.exact(M.fraction('3/4')))
            self.assertEqual(player['aggregate']['count'],1)
            self.assertEqual(player['plateAppearances'],3)
            stored,=M.read_results(conn,G1,'tfs')
            stored['contributionInputs']['independentDamageComplete']=False
            M.store_result(conn,G1,'tfs','game-scope',stored)
            result=M.query_sql(conn,dict(metricId='empty-game-damage'),scope)['metric']
            self.assertFalse(result['playerPopulationComplete'])
            self.assertEqual(result['playerSummaryGaps'],['INDEPENDENT_DAMAGE_COVERAGE'])

    def test_all_four_selected_period_producers_use_exact_values(self):
        with database() as conn:
            for metric,value in [('tfs','9/8'),('opportunity-erosion',0),('rally-kill-rate',0),('rally-kill-severity',0)]:
                result=M.query_sql(conn,dict(metricId=metric),SCOPE)['metric']
                self.assertTrue(result['playerPopulationComplete'],result)
                player,=result['playerResults'];self.assertEqual(M.fraction(player['value']),M.fraction(value))
                self.assertEqual(player['plateAppearances'],2);self.assertEqual(player['teamGames'],2)

    def test_paq_season_reference_precedes_display_filter_for_both_ranks(self):
        with database() as conn:
            for metric in ('paq-2','paq-a'):
                result=M.query_sql(conn,dict(metricId=metric),SCOPE)['metric']
                self.assertTrue(result['playerPopulationComplete'],result)
                player,=result['playerResults'];self.assertEqual(player['value'],M.exact(75))
                self.assertEqual(player['aggregate'],dict(kind='mean',count=2,sum=M.exact(150)))
                self.assertEqual(result['referencePopulations'][0]['applicablePlateAppearances'],3)

    def test_reference_schedule_and_all_three_admissions_are_required(self):
        for fault in ('schedule','metric_suite_admission','metric_suite_runner_resolution_admission','metric_suite_boundary_admission'):
            with self.subTest(fault=fault),database() as conn:
                if fault=='schedule':conn.execute("DELETE FROM metric_suite_schedule_coverage WHERE official_date='2026-01-01'")
                else:
                    text=M._json(dict(status='withheld'))
                    conn.execute(f'UPDATE {fault} SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),G1))
                for metric in ('paq-2','paq-a'):
                    result=M.query_sql(conn,dict(metricId=metric),SCOPE)['metric']
                    self.assertFalse(result['playerPopulationComplete']);self.assertEqual(result['playerResults'],[])

    def test_changed_selected_resolution_proof_withholds_all_four_producers(self):
        with database() as conn:
            text=M._json(dict(status='withheld'))
            conn.execute('UPDATE metric_suite_runner_resolution_admission SET proof_json=?,proof_sha256=?', (text,M._hash(text)))
            for metric in M.CONTRIBUTION_METRICS:
                result=M.query_sql(conn,dict(metricId=metric),SCOPE)['metric']
                self.assertFalse(result['playerPopulationComplete'])
                self.assertEqual(result['status'],'unavailable')

    def test_small_state_cohort_and_tampered_result_never_rank(self):
        with database() as conn:
            result,=M.read_results(conn,G1,'tfs')
            result['contributionInputs']['plateAppearances'][0]['comparisonState']['outs']=0
            M.store_result(conn,G1,'tfs','game-scope',result)
            # The singleton lies outside the selected display range. It does
            # not corrupt the complete, separate two-member selected cohort.
            got=M.query_sql(conn,dict(metricId='paq-a'),SCOPE)['metric']
            self.assertTrue(got['playerPopulationComplete'],got)
            all_scope=dict(SCOPE,startDate='2026-08-01')
            got=M.query_sql(conn,dict(metricId='paq-a'),all_scope)['metric']
            self.assertFalse(got['playerPopulationComplete'])
            conn.execute("UPDATE metric_suite_result SET result_json='{}' WHERE graph_iri=? AND metric_id='tfs'",(G1,))
            with self.assertRaisesRegex(M.EvidenceError,'checksum'):M.query_sql(conn,dict(metricId='paq-2'),SCOPE)


if __name__=='__main__':unittest.main()
