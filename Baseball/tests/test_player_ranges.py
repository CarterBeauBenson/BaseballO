"""Full-range completeness, isolated exclusions and exact pooled aggregates."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

from test_metric_suite_serving import M

spec=importlib.util.spec_from_file_location('player_ranges',M.ROOT/'serving/player_ranges.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
G='https://w3id.org/baseball/graph/game/'
U='https://baseballontology.org/data/player/'
SCOPE=dict(gameSet='regular_season',startDate='2026-09-01',endDate='2026-09-02')


class PlayerRanges(unittest.TestCase):
    def db(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.executescript('''CREATE TABLE game_dimension(graph_iri TEXT PRIMARY KEY,official_date TEXT,game_set TEXT);
            CREATE TABLE dashboard_checkpoint(graph_iri TEXT PRIMARY KEY,input_sha256 TEXT);
            CREATE TABLE metric_suite_schedule_coverage(official_date TEXT,proof_json TEXT,proof_sha256 TEXT);''')
        P.initialize(db)
        for day,pk in [('2026-09-01','1'),('2026-09-02','2')]:
            graph=G+pk;db.execute('INSERT INTO game_dimension VALUES (?,?,?)',(graph,day,'regular_season'))
            db.execute('INSERT INTO dashboard_checkpoint VALUES (?,?)',(graph,'source-'+pk))
            db.execute('INSERT INTO dashboard_player_partition VALUES (?,?)',(graph,M._hash('source-'+pk+P.fingerprint())))
            proof=M._json(dict(completeResponse=True,games=[dict(gamePk=pk,gameType='R',final=True,unplayed=False)]))
            db.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day,proof,M._hash(proof)))
            for player in (U+'1',U+'2'):
                db.execute('INSERT INTO dashboard_player_game VALUES (?,?,?,?,?)',(graph,player,'team',4,1))
        return db

    def test_one_incomplete_game_excludes_whole_player_not_the_other_player(self):
        db=self.db()
        for graph,player,complete,total,count in [(G+'1',U+'1',1,100,4),(G+'2',U+'1',0,0,0),
                                                (G+'1',U+'2',1,3,1),(G+'2',U+'2',1,6,3)]:
            db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                (graph,player,'tfs',complete,M._json(dict(kind='mean',sum=M.exact(total),count=count)),None if complete else 'MISSING_PA'))
        result=P.query(M,db,{'metricId':'tfs'},SCOPE)['metric']
        self.assertFalse(result['playerPopulationComplete'])
        self.assertTrue(result['playerRecordsComplete'])
        self.assertEqual(result['rankingCoverage']['excludedPlayers'],1)
        player,=result['playerResults']
        self.assertEqual(player['player'],U+'2')
        self.assertEqual(player['value'],M.exact(M.Fraction(9,4)))
        self.assertEqual(player['dateScope'],SCOPE)
        self.assertEqual(player['plateAppearances'],8)
        self.assertEqual(player['teamGames'],2)

    def test_missing_schedule_game_cannot_be_silently_dropped(self):
        db=self.db();proof=M._json(dict(completeResponse=True,games=[dict(gamePk='3',gameType='R',final=True,unplayed=False)]))
        db.execute('UPDATE metric_suite_schedule_coverage SET proof_json=?,proof_sha256=? WHERE official_date=?',
                   (proof,M._hash(proof),'2026-09-02'))
        result=P.query(M,db,{'metricId':'tfs'},SCOPE)['metric']
        self.assertEqual(result['playerResults'],[])
        self.assertEqual(result['playerSummaryGaps'],['COMPLETE_SELECTED_SCHEDULE'])

    def test_changed_game_partition_requires_preparation(self):
        db=self.db();db.execute("UPDATE dashboard_checkpoint SET input_sha256='changed' WHERE graph_iri=?",(G+'1',))
        with self.assertRaisesRegex(M.EvidenceError,'NiFi preparation'):
            P.query(M,db,{'metricId':'tfs'},SCOPE)

    def test_missing_game_roster_cannot_claim_complete_player_records(self):
        db=self.db();db.execute('DELETE FROM dashboard_player_game WHERE graph_iri=?',(G+'2',))
        result=P.query(M,db,{'metricId':'tfs'},SCOPE)['metric']
        self.assertFalse(result['playerRecordsComplete'])
        self.assertEqual(result['playerSummaryGaps'],['COMPLETE_PARTICIPATION'])

    def test_run_and_empty_game_gaps_are_scoped_to_the_affected_player(self):
        graph=G+'1';game='https://baseballontology.org/data/game/1'
        proof=dict(status='admitted',sourceReconciled=True,graphConforms=True)
        rows=[]
        for i in (1,2):
            rows.extend([dict(kind='player_team_game',entity=U+str(i),player=U+str(i),graph=graph,game=game,team='team',teamRole='role'),
                dict(kind='plate_appearance',entity='pa'+str(i),graph=graph,game=game,player=U+str(i),act='act'+str(i),
                    recognizedBattingResult='true',paResult='result'+str(i),paResultType='type',paResultJudgment='judgment',
                    paResultDecision='decision',paResultRecord='record'),dict(kind='run',entity='run'+str(i),graph=graph,game=game)])
        progress=dict(plateAppearances=[dict(graph=graph,game=game,plateAppearance='pa1',player=U+'1',officialResult=True,
            reach=1,batterPositive=True,otherPositivePlayers=[],independentPositive=[],independentEpisodes=[],independentEpisodeGaps=[],
            positiveChannels=[dict(player=U+'1',play='pa1',channel='batter_self')])],
            unresolvedPlateAppearances=[dict(graph=graph,game=game,plateAppearance='pa2',player=U+'2',officialResult=True,
                possiblePositivePlayers=[U+'2'],confirmedPositivePlayers=[],gaps=['UNRESOLVED_PROGRESS_ATTRIBUTION'])])
        runs={metric:dict(runs=[dict(run='run1',runner=U+'1',status='available',completeTrajectory=True,value=M.exact(2))],
                         unresolvedRuns=[dict(run='run2')]) for metric in P.RUNS}
        _,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
            proofs={'batting':proof,'run':proof,'resolution':proof},
            inputs=dict(contribution={'complete':False,'plateAppearances':[]},progress=progress,defense={'complete':False}),
            runs=runs,run_people={'run2':{U+'2'}})
        by_key={(r[1],r[2]):r for r in records}
        for metric in [*P.RUNS,'empty-game-rate','offensive-reach']:
            self.assertEqual(by_key[(U+'1',metric)][3],1,metric)
            self.assertEqual(by_key[(U+'2',metric)][3],0,metric)
        self.assertEqual(json.loads(by_key[(U+'1','empty-game-rate')][4]),dict(kind='count',count=0,eligibleGames=1))


if __name__=='__main__':unittest.main()
