"""Full-range completeness, isolated exclusions and exact pooled aggregates."""
import importlib.util
import copy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from test_metric_suite_serving import M

spec=importlib.util.spec_from_file_location('player_ranges',M.ROOT/'serving/player_ranges.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
spec=importlib.util.spec_from_file_location('player_range_query',M.ROOT/'serving/player_range_query.py')
Q=importlib.util.module_from_spec(spec);spec.loader.exec_module(Q)
G='https://w3id.org/baseball/graph/game/'
U='https://baseballontology.org/data/player/'
SCOPE=dict(gameSet='regular_season',startDate='2026-09-01',endDate='2026-09-02')


class PlayerRanges(unittest.TestCase):
    def test_running_channel_gap_does_not_exclude_unrelated_players(self):
        graph=G+'1';game='https://baseballontology.org/data/game/1'
        proof=dict(status='admitted',sourceReconciled=True,graphConforms=True)
        rows=[];pas=[]
        for i in (1,2,3):
            player=U+str(i);pa='pa'+str(i)
            rows.extend([dict(kind='player_team_game',player=player,graph=graph,game=game,team='team',teamRole='role'),
                dict(kind='plate_appearance',entity=pa,graph=graph,game=game,player=player,act='act'+str(i),
                    recognizedBattingResult='true',paResult='result'+str(i),paResultType='type',paResultJudgment='judgment',
                    paResultDecision='decision',paResultRecord='record')])
            pas.append(dict(graph=graph,game=game,plateAppearance=pa,player=player,officialResult=True,
                reach=1,batterPositive=True,otherPositivePlayers=[],independentPositive=[],independentEpisodes=[],
                independentEpisodeGaps=['UNRESOLVED_RUNNING_EPISODE_ATTRIBUTION'] if i==1 else [],
                positiveChannels=[dict(player=player,play=pa,channel='batter_self')]))
        rows.append(dict(kind='runner_movement',graph=graph,game=game,plateAppearance='pa1',runner=U+'2'))
        progress=dict(plateAppearances=pas,unresolvedPlateAppearances=[])
        bounded=P.channel_gap_players(rows,progress)
        self.assertEqual(bounded,{'pa1':[U+'1',U+'2']})
        for bounds,admission,expected in (({},proof,0),(bounded,proof,1),(bounded,{},0)):
            _,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
                proofs=dict(batting=proof,run={},resolution=admission),
                inputs=dict(contribution={},progress=progress,defense={},channelGapPlayers=bounds),
                runs={metric:{} for metric in P.RUNS},run_people={})
            mixed={r[1]:r for r in records if r[2]=='contribution-path-diversity'}
            self.assertEqual(mixed[U+'3'][3],expected)
            self.assertEqual(mixed[U+'1'][3],0)
            self.assertEqual(mixed[U+'2'][3],0)
            self.assertEqual(json.loads(mixed[U+'3'][4]),dict(kind='channel_entropy',channelCounts=[1,0,0],independentRunningEpisodes=0))
        rows[-1].pop('runner')
        self.assertEqual(P.channel_gap_players(rows,progress),{})

    def test_channel_upgrade_reuses_unaffected_player_products(self):
        db=self.db()
        for i in (1,2):
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                (M._hash('source-'+str(i)+P.PREVIOUS_CHANNEL_VERSION),G+str(i)))
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('no unchanged projection')):
            self.assertEqual(P.prepare(M,db)['preparedGames'],0)
        self.assertEqual(dict(db.execute('SELECT * FROM dashboard_player_partition')),
                         {G+str(i):M._hash('source-'+str(i)+P.fingerprint()) for i in (1,2)})

    def test_binary_help_keeps_exact_denominator_despite_unrelated_unknown_progress(self):
        from test_batting_progress_players import fixture, bindings, G1, GAME, P1, PROOF
        rows=M.normalize_bindings(bindings(fixture(),[G1]),[G1])
        pa0=str(GAME)+'/plate-appearance/0';pa1=str(GAME)+'/plate-appearance/1'
        for pa in (pa0,pa1):
            known=next(r for r in rows if r['kind']=='runner_movement' and r['plateAppearance']==pa)
            unknown=dict(known,runner=U+'3',act=pa+'/unknown-act',episode=pa+'/unknown-episode',
                entity=pa+'/unknown-result',resolution=pa+'/unknown-result',metricOrigin='1',originCode='1B',
                hasOutType='false',hasSafeType='true',hasRunType='false',destinationCode='2B')
            unknown.pop('contactPlay',None);rows.append(unknown)
        progress=M.batting_progress_evidence(rows)
        self.assertEqual({r['plateAppearance'] for r in progress['unresolvedPlateAppearances']},{pa0,pa1})
        binary=P.binary_help_inputs(M,rows,progress)
        self.assertEqual(binary[pa0],dict(player=str(P1),eligible=False,positive=True))
        self.assertEqual(binary[pa1],dict(player=str(P1),eligible=True,value=1,positive=True))
        for resolution,expected in ((PROOF,1),({},0)):
            _,records=P.project(M,graph=str(G1),scope=SCOPE,rows=rows,
                proofs=dict(batting=PROOF,run={},resolution=resolution),
                inputs=dict(contribution={},progress=progress,defense={},binaryHelp=binary),
                runs={metric:{} for metric in P.RUNS},run_people={})
            by_key={(r[1],r[2]):r for r in records}
            help_row=by_key[(str(P1),'hidden-help-rate')]
            self.assertEqual(help_row[3],expected)
            self.assertEqual(json.loads(help_row[4]),P.mean(M,[M.Fraction(1),M.Fraction(0)]))
            self.assertEqual(by_key[(str(P1),'offensive-reach')][3],0)
            self.assertEqual(by_key[(str(P1),'tfs')][3],0)
            self.assertEqual(by_key[(str(P1),'empty-game-rate')][3],expected)
        # If every other advance lacks attribution, Help is still unknown.
        unknown=copy.deepcopy(rows)
        for row in unknown:
            if row['kind']=='runner_movement' and row['plateAppearance']==pa1 and row.get('runner')!=str(P1):
                row.pop('contactPlay',None)
        self.assertNotIn(pa1,P.binary_help_inputs(M,unknown,M.batting_progress_evidence(unknown)))
        # An unknown batter's own progress cannot establish Help eligibility.
        unknown=copy.deepcopy(rows)
        for row in unknown:
            if row['kind']=='runner_movement' and row['plateAppearance']==pa1 and row.get('runner')==str(P1):
                row.update(hasOutType='false',hasSafeType='true',destinationCode='1B')
                row.pop('contactPlay',None)
        self.assertNotIn(pa1,P.binary_help_inputs(M,unknown,M.batting_progress_evidence(unknown)))

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

    def test_binary_help_upgrade_reuses_unaffected_sql_partitions(self):
        db=self.db()
        db.execute('CREATE TABLE metric_suite_input_state(graph_iri TEXT,family TEXT,state_json TEXT,state_sha256 TEXT)')
        db.execute('CREATE TABLE metric_suite_runner_resolution_admission(graph_iri TEXT,proof_json TEXT,proof_sha256 TEXT)')
        for i in (1,2):
            graph=G+str(i)
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                       (M._hash('source-'+str(i)+P.PREVIOUS_HELP_VERSION),graph))
            state=M._json(dict(unresolvedPlateAppearances=[] if i==1 else [
                dict(plateAppearance='pa',player=U+'1',officialResult=True)]))
            db.execute('INSERT INTO metric_suite_input_state VALUES (?,?,?,?)',(graph,'progress',state,M._hash(state)))
            proof=M._json(dict(status='withheld'))
            db.execute('INSERT INTO metric_suite_runner_resolution_admission VALUES (?,?,?)',(graph,proof,M._hash(proof)))
            db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                       (graph,U+'1','hidden-help-rate',int(i==1),M._json(P.zero()),None if i==1 else 'COMPLETE_PA_PROGRESS'))
        before=db.execute('SELECT * FROM dashboard_player_metric').fetchall()
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('must reuse unaffected products')):
            result=P.prepare(M,db)
        self.assertEqual((result['preparedGames'],result['reusedGames']),(0,2))
        self.assertEqual(before,db.execute('SELECT * FROM dashboard_player_metric').fetchall())
        self.assertEqual(dict(db.execute('SELECT * FROM dashboard_player_partition')),
                         {G+str(i):M._hash('source-'+str(i)+P.fingerprint()) for i in (1,2)})

    def test_ambiguous_batter_does_not_withhold_an_uninvolved_players_empty_game(self):
        graph=G+'1';game='game';proof=dict(status='admitted',sourceReconciled=True,graphConforms=True)
        rows=[dict(kind='player_team_game',player=U+str(i),graph=graph,game=game,team='team',teamRole='role')
              for i in (1,2,3)]
        for i in (1,2,3):
            rows.append(dict(kind='plate_appearance',entity='pa1' if i==1 else 'pa2',graph=graph,game=game,
                player=U+str(i),act='act'+str(i),recognizedBattingResult='true',paResult='result',
                paResultType='type',paResultJudgment='judgment',paResultDecision='decision',paResultRecord='record'))
        movement=dict(kind='runner_movement',plateAppearance='pa2',runner=U+'2')
        progress=dict(plateAppearances=[dict(graph=graph,game=game,plateAppearance='pa1',player=U+'1',
            officialResult=True,reach=0,batterPositive=False,otherPositivePlayers=[],independentPositive=[],
            positiveChannels=[],independentEpisodes=[],independentEpisodeGaps=[])],unresolvedPlateAppearances=[
                dict(graph=graph,plateAppearance='pa2',gaps=['AMBIGUOUS_BATTING_CONTRIBUTOR'])])
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            players=[dict(player=U+str(i),status='admitted' if i==1 else 'withheld') for i in (1,2,3)])
        for case,expected in [('bounded',1),('uninformed',0),('involved',0),('missing-runner',0),
                              ('missing-batter',0),('missing-movement',0),('unverified-census',0)]:
            evidence=copy.deepcopy(rows)+[dict(movement)]
            if case=='involved':evidence[-1]['runner']=U+'1'
            if case=='missing-runner':evidence[-1].pop('runner')
            if case=='missing-batter':evidence[-2].pop('player')
            if case=='missing-movement':evidence.pop()
            bounded=P.ambiguous_progress_players(evidence,progress)
            if case=='bounded':self.assertEqual(bounded,{'pa2':[U+'2',U+'3']})
            inputs=dict(contribution={},progress=progress,defense={})
            if case!='uninformed':inputs['ambiguousProgressPlayers']=bounded
            _,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
                proofs=dict(batting={},run=proof,resolution={} if case=='unverified-census' else proof,players=individual),
                inputs=inputs,runs={m:{} for m in P.RUNS},run_people={})
            records={(r[1],r[2]):r for r in records}
            row=records[(U+'1','empty-game-rate')]
            self.assertEqual(row[3],expected,case)
            if expected:self.assertEqual(json.loads(row[4]),dict(kind='count',count=1,eligibleGames=1))
            for player in (U+'2',U+'3'):
                self.assertEqual(records[(player,'empty-game-rate')][3],0,case)
                self.assertEqual(records[(player,'offensive-reach')][3],0,case)
        self.assertNotIn('possiblePositivePlayers',progress['unresolvedPlateAppearances'][0])

    def test_ambiguity_upgrade_reuses_unaffected_games_and_reprojects_affected_game(self):
        db=self.db()
        db.execute('CREATE TABLE metric_suite_input_state(graph_iri TEXT,family TEXT,state_json TEXT,state_sha256 TEXT)')
        for i in (1,2):
            graph=G+str(i)
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                       (M._hash('source-'+str(i)+P.PREVIOUS_AMBIGUOUS_PROGRESS_VERSION),graph))
            state=M._json(dict(unresolvedPlateAppearances=[] if i==1 else [
                dict(plateAppearance='pa2',gaps=['AMBIGUOUS_BATTING_CONTRIBUTOR'])]))
            db.execute('INSERT INTO metric_suite_input_state VALUES (?,?,?,?)',(graph,'progress',state,M._hash(state)))
        with patch.object(M._blocks,'read_scope',side_effect=RuntimeError('affected game needs retained evidence')) as read:
            with self.assertRaisesRegex(RuntimeError,'affected game needs retained evidence'):P.prepare(M,db)
        self.assertEqual(read.call_count,1)
        self.assertEqual(read.call_args.args[2],[G+'2'])
        partitions=dict(db.execute('SELECT * FROM dashboard_player_partition'))
        self.assertEqual(partitions[G+'1'],M._hash('source-1'+P.fingerprint()))
        self.assertEqual(partitions[G+'2'],M._hash('source-2'+P.PREVIOUS_AMBIGUOUS_PROGRESS_VERSION))

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

    def test_unrelated_early_reference_does_not_reconstruct_selected_season(self):
        db=self.db()
        db.execute('CREATE TABLE dashboard_reference(metric_id TEXT,season INTEGER,graph_set_sha256 TEXT)')
        db.execute('INSERT INTO dashboard_reference VALUES (?,?,?)',
                   ('recovery-quality',2026,M._hash(M._json([G+'1']))))
        with patch.object(M,'query_sql',side_effect=AssertionError('must not decode game inputs')):
            result=Q.query(M,P,db,{'metricId':'recovery-quality'},SCOPE)['metric']
        self.assertEqual(result['playerSummaryGaps'],['SEASON_REFERENCE_UNAVAILABLE'])
        self.assertEqual(result['playerResults'],[])
        db.execute('INSERT INTO dashboard_reference VALUES (?,?,?)',
                   ('recovery-quality',2026,M._hash(M._json([G+'1',G+'2']))))
        # Ranks alone cannot authorize request-time player reconstruction.
        self.assertFalse(Q.reference_available(M,db,'recovery-quality',SCOPE))
        self.assertFalse(Q.reference_available(M,db,'paq-2',SCOPE))

    def test_reader_keeps_exact_producer_partition_and_pooling_contract(self):
        db=self.db()
        for graph in (G+'1',G+'2'):
            for player in (U+'1',U+'2'):
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                    (graph,player,'tfs',1,M._json(dict(kind='mean',sum=M.exact(3),count=4)),None))
        request={'metricId':'tfs'}
        result=Q.query(M,P,db,request,SCOPE)
        coverage=result.pop('participationCoverage')
        self.assertEqual(coverage,dict(games=2,verifiedGames=2,unverifiedGames=[]))
        self.assertEqual(result,P.query(M,db,request,SCOPE))

    def test_incomplete_roster_is_reported_without_shortening_selected_range(self):
        db=self.db();db.execute('DELETE FROM dashboard_player_game WHERE graph_iri=?',(G+'2',))
        result=Q.query(M,P,db,{'metricId':'tfs'},SCOPE)
        self.assertEqual(result['dateScope'],SCOPE)
        self.assertEqual(result['participationCoverage'],dict(games=2,verifiedGames=1,
            unverifiedGames=[dict(graph=G+'2',gamePk='2',date='2026-09-02')]))
        self.assertEqual(result['metric']['playerSummaryGaps'],['COMPLETE_PARTICIPATION'])

    def test_reader_decodes_only_whole_range_complete_players(self):
        self.check_complete_player_reads(covered=False)

    def test_covering_index_reads_only_complete_player_aggregates(self):
        self.check_complete_player_reads(covered=True)

    def test_player_index_reads_only_complete_player_aggregates(self):
        self.check_complete_player_reads(covered=True,player_index=True)

    def check_complete_player_reads(self, *, covered, player_index=False):
        db=self.db()
        if covered:db.execute('CREATE INDEX dashboard_player_metric_coverage '
            'ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
        if player_index:db.execute('CREATE INDEX dashboard_player_metric_by_player '
            'ON dashboard_player_metric(metric_id,player,graph_iri)')
        # Player 1 fails after an otherwise usable game. Player 2 is complete,
        # player 3 lacks a metric row, and player 4 has known zero observations.
        for graph in (G+'1',G+'2'):
            for player in (U+'3',U+'4'):
                db.execute('INSERT INTO dashboard_player_game VALUES (?,?,?,?,?)',(graph,player,'team',0,1))
        expected_metrics=[]
        for metric in sorted(P.PREPARED):
            def aggregate(count):
                if metric=='empty-game-rate':return dict(kind='count',count=count,eligibleGames=count)
                if metric=='contribution-path-diversity':return dict(kind='channel_entropy',channelCounts=[count,2*count,0],
                                                                   independentRunningEpisodes=count)
                if not count:return P.zero()
                return dict(kind='mean',sum=M.exact(M.Fraction(count,3)),count=count,independentRunningEpisodes=count)
            for graph in (G+'1',G+'2'):
                for player in (U+'1',U+'2',U+'3',U+'4'):
                    if player==U+'3' and graph==G+'2':continue
                    complete=not(player==U+'1' and graph==G+'2')
                    db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                        (graph,player,metric,int(complete),M._json(aggregate(0 if player==U+'4' else int(graph[-1]))),
                         None if complete else 'MISSING_PA'))
            request={'metricId':metric}
            expected=P.query(M,db,request,SCOPE)
            aggregate_decodes=[];loads=json.loads
            def tracked_loads(text,*args,**kwargs):
                value=loads(text,*args,**kwargs)
                if isinstance(value,dict) and value.get('kind') in ('mean','count','channel_entropy'):
                    aggregate_decodes.append(value)
                return value
            with patch.object(Q.json,'loads',side_effect=tracked_loads):
                actual=Q.query(M,P,db,request,SCOPE)
            actual.pop('participationCoverage')
            self.assertEqual(actual,expected,metric)
            self.assertEqual(len(aggregate_decodes),2 if covered else 4,metric)
            self.assertEqual(actual['metric']['rankingCoverage']['completePlayers'],2,metric)
            self.assertEqual(actual['metric']['rankingCoverage']['excludedPlayers'],2,metric)
            expected_metrics.append(expected['metric'])
        statements=[];db.set_trace_callback(statements.append)
        with patch.object(M,'requested_metric_ids',return_value=sorted(P.PREPARED)):
            dashboard=Q.query(M,P,db,{'view':'dashboard'},SCOPE)
        db.set_trace_callback(None)
        self.assertEqual(dashboard['metrics'],expected_metrics)
        self.assertEqual(sum('JOIN dashboard_player_metric ' in sql for sql in statements),2 if covered and not player_index else 1)
        if covered:
            aggregate_reads=[s for s in statements if 'SELECT p.metric_id,p.player,p.aggregate_json' in s]
            self.assertEqual(len(aggregate_reads),1)
            self.assertNotIn("'"+U+'1'+"'",aggregate_reads[0])
            self.assertNotIn("'"+U+'3'+"'",aggregate_reads[0])
            if player_index:
                plan=[row[3] for row in db.execute('EXPLAIN QUERY PLAN '+aggregate_reads[0])]
                self.assertIn('dashboard_player_metric_by_player (metric_id=? AND player=?)',plan[0])
                self.assertTrue(any('SEARCH g ' in step for step in plan[1:]), plan)

    def test_empty_payload_filter_preserves_zero_scores_and_independent_running_exposure(self):
        db=self.db()
        db.execute('CREATE INDEX dashboard_player_metric_coverage '
            'ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
        for metric,parts in {
            'tfs':[dict(kind='mean',sum=M.exact(0),count=4),dict(kind='mean',sum=M.exact(2),count=2)],
            'empty-game-rate':[dict(kind='count',count=0,eligibleGames=1),dict(kind='count',count=1,eligibleGames=1)],
            'contribution-path-diversity':[
                dict(kind='channel_entropy',channelCounts=[0,0,0],independentRunningEpisodes=3),
                dict(kind='channel_entropy',channelCounts=[1,1,0],independentRunningEpisodes=1)],
        }.items():
            for graph,part in zip((G+'1',G+'2'),parts):
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                           (graph,U+'1',metric,1,M._json(part),None))
            request={'metricId':metric};actual=Q.query(M,P,db,request,SCOPE)
            actual.pop('participationCoverage')
            self.assertEqual(actual,P.query(M,db,request,SCOPE),metric)

    def test_reader_rejects_equal_counts_with_different_game_membership(self):
        db=self.db()
        db.execute('CREATE INDEX dashboard_player_metric_coverage '
            'ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
        db.execute('DELETE FROM dashboard_player_game WHERE graph_iri=? AND player=?',(G+'2',U+'1'))
        db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                   (G+'2',U+'1','tfs',1,M._json(P.mean(M,[M.Fraction(10)])),None))
        actual=Q.query(M,P,db,{'metricId':'tfs'},SCOPE)
        actual.pop('participationCoverage')
        self.assertEqual(actual,P.query(M,db,{'metricId':'tfs'},SCOPE))
        self.assertEqual(actual['metric']['playerResults'],[])
        self.assertEqual(actual['metric']['rankingCoverage']['completePlayers'],0)

    def test_nifi_prepared_season_serves_dashboard_and_detail_without_range_scan(self):
        db=self.db();db.execute('ALTER TABLE game_dimension ADD COLUMN season INTEGER DEFAULT 2026')
        db.execute("UPDATE game_dimension SET official_date=replace(official_date,'2026-09','2026-01')")
        db.execute("UPDATE metric_suite_schedule_coverage SET official_date=replace(official_date,'2026-09','2026-01')")
        db.execute('CREATE TABLE dashboard_build(input_set_sha256 TEXT)')
        db.execute("INSERT INTO dashboard_build VALUES ('inputs-one')")
        for graph in (G+'1',G+'2'):
            for player in (U+'1',U+'2'):
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                    (graph,player,'tfs',1,M._json(dict(kind='mean',sum=M.exact(3),count=4)),None))
        scope=dict(SCOPE,startDate='2026-01-01',endDate='2026-01-02')
        expected=Q.query(M,P,db,dict(view='dashboard'),scope)
        self.assertEqual(Q.prepare_seasons(M,P,db,'inputs-one'),1)
        with patch.object(Q,'player_records',side_effect=AssertionError('request-time range scan')):
            self.assertEqual(Q.query(M,P,db,dict(view='dashboard'),scope),expected)
            detail=Q.query(M,P,db,dict(metricId='tfs'),scope)
            self.assertEqual(detail['metric'],next(r for r in expected['metrics'] if r['metricId']=='tfs'))
            self.assertEqual(Q.prepare_seasons(M,P,db,'inputs-one'),0)
        db.execute("UPDATE dashboard_build SET input_set_sha256='different-publication'")
        with patch.object(Q,'player_records',wraps=Q.player_records) as scan:
            self.assertEqual(Q.query(M,P,db,dict(view='dashboard'),scope),expected)
            self.assertTrue(scan.called)

    def test_unselected_exhibition_products_do_not_block_dashboard_preparation(self):
        db=self.db()
        db.execute('INSERT INTO game_dimension VALUES (?,?,?)',(G+'3','2026-09-02','exhibition'))
        db.execute('INSERT INTO dashboard_checkpoint VALUES (?,?)',(G+'3','unrelated-exhibition'))
        # No source tables for that unrelated game: attempting to project it
        # would fail. The two dashboard game partitions are already prepared.
        result=P.prepare(M,db)
        self.assertEqual((result['preparedGames'],result['reusedGames']),(0,2))

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
        # A complete resolution census for one PA supports its exact batting
        # indicator and certain non-emptiness, not the unrelated PA or TFS.
        scoped=dict(paResolutions=dict(plateAppearances=[
            dict(plateAppearance='pa1',status='admitted'),dict(plateAppearance='pa2',status='withheld')]))
        for admitted_pa in (True,False):
            scoped['paResolutions']['plateAppearances'][0]['status']='admitted' if admitted_pa else 'withheld'
            _,isolated=P.project(M,graph=graph,scope=SCOPE,rows=rows,
                proofs=dict(batting=proof,run=proof,resolution={},players=scoped),
                inputs=dict(contribution={},progress=progress,defense={}),runs=runs,run_people={'run2':{U+'2'}})
            isolated={(r[1],r[2]):r for r in isolated}
            for metric in ('offensive-reach','hidden-help-rate','empty-game-rate','empty-game-damage'):
                self.assertEqual(isolated[(U+'1',metric)][3],int(admitted_pa),metric)
                self.assertEqual(isolated[(U+'2',metric)][3],0,metric)
            self.assertEqual(isolated[(U+'1','tfs')][3],0)
            if admitted_pa:
                self.assertEqual(json.loads(isolated[(U+'1','offensive-reach')][4]),P.mean(M,[M.Fraction(1)]))
                self.assertEqual(json.loads(isolated[(U+'1','empty-game-rate')][4]),dict(kind='count',count=0,eligibleGames=1))
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            players=[dict(player=U+'1',status='admitted'),dict(player=U+'2',status='withheld')])
        partial=dict(plateAppearances=[],unresolvedPlateAppearances=[
            dict(graph=graph,game=game,plateAppearance='pa1',player=U+'1',officialResult=True,
                 confirmedPositivePlayers=[U+'1'],possiblePositivePlayers=[U+'2'],gaps=['UNRESOLVED_PROGRESS_ATTRIBUTION']),
            *progress['unresolvedPlateAppearances']])
        scoped['paResolutions']['plateAppearances'][0]['status']='admitted'
        _,isolated=P.project(M,graph=graph,scope=SCOPE,rows=rows,
            proofs=dict(batting=proof,run=proof,resolution={},players=scoped),
            inputs=dict(contribution={},progress=partial,defense={}),runs=runs,run_people={'run2':{U+'2'}})
        isolated={(r[1],r[2]):r for r in isolated}
        self.assertEqual(isolated[(U+'1','empty-game-rate')][3],1)
        self.assertEqual(isolated[(U+'1','offensive-reach')][3],0)
        progress['plateAppearances'][0].update(reach=0,batterPositive=False,positiveChannels=[])
        for affected,expected_complete in [([U+'2'],1),([U+'1',U+'2'],0)]:
            progress['unresolvedPlateAppearances'][0]['possiblePositivePlayers']=affected
            _,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
                proofs={'batting':{'status':'withheld'},'run':proof,'resolution':proof,'players':individual},
                inputs=dict(contribution={'complete':False,'plateAppearances':[]},progress=progress,defense={'complete':False}),
                runs=runs,run_people={'run2':{U+'2'}})
            by_key={(r[1],r[2]):r for r in records}
            self.assertEqual(by_key[(U+'1','empty-game-rate')][3],expected_complete)
            self.assertEqual(by_key[(U+'2','empty-game-rate')][3],0)

        # Another runner's unresolved turn cannot make the first player's
        # known negative PA contribution disappear from Empty Game Damage.
        progress['unresolvedPlateAppearances'][0]['possiblePositivePlayers']=[U+'2']
        contribution=dict(complete=False,independentDamageComplete=False,plateAppearances=[
            dict(graph=graph,game=game,plateAppearance='pa1',player=U+'1',runnerOnBase=False,
                independentPositive=[],unattributedNonbattingEpisodes=[],participants=[],
                existingRunnerOuts=0,existingDestruction=M.exact(0),
                score=M.available(M.Fraction(-1,4),components=dict(progress=M.exact(0),erosion=M.exact(0))))])
        movements=[dict(kind='runner_movement',runner=U+'1',plateAppearance='pa1'),
                   dict(kind='runner_movement',runner=U+'2',plateAppearance='pa2')]
        for change,expected_complete in [('other-runner',1),('own-interruption',0),('unknown-runner',0),('no-census',0)]:
            evidence=rows+movements
            if change=='own-interruption':evidence+=[dict(kind='runner_movement',runner=U+'1',plateAppearance='interrupted')]
            if change=='unknown-runner':evidence+=[dict(kind='runner_movement',plateAppearance='interrupted')]
            contribution['zeroIndependentDamagePlayers']=sorted(P.zero_independent_damage_players(
                evidence,contribution,{} if change=='no-census' else proof))
            _,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
                proofs={'batting':{'status':'withheld'},'run':proof,'resolution':proof,'players':individual},
                inputs=dict(contribution=contribution,progress=progress,defense={'complete':False}),
                runs=runs,run_people={'run2':{U+'2'}})
            by_key={(r[1],r[2]):r for r in records}
            damage=by_key[(U+'1','empty-game-damage')]
            self.assertEqual(damage[3],expected_complete,change)
            if expected_complete:
                self.assertEqual(json.loads(damage[4]),dict(kind='mean',sum=M.exact(M.Fraction(1,4)),count=1))
            self.assertEqual(by_key[(U+'2','empty-game-damage')][3],0)

    def test_individual_admission_uses_rdf_counts_and_keeps_failed_player_unknown(self):
        rows=[dict(kind='player_team_game',player=U+str(i),graph=G+'1',game='game',team='team',teamRole='role') for i in (1,2,3)]
        rows.append(dict(kind='plate_appearance',entity='pa1',graph=G+'1',game='game',player=U+'1',
            recognizedBattingResult='true',act='act',paResult='result',paResultType='type',
            paResultJudgment='judgment',paResultDecision='decision',paResultRecord='record'))
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            players=[dict(player=U+str(i),status='withheld' if i==2 else 'admitted',officialPA=999) for i in (1,2,3)])
        result=P.qualification(M,rows,G+'1',SCOPE,dict(status='withheld'),individual)
        self.assertEqual({p['player']:p['plateAppearances'] for p in result['participation']},{U+'1':1,U+'3':0})
        self.assertEqual(result['expectedObservations'],[dict(graph=G+'1',plateAppearance='pa1',player=U+'1')])
        individual['plateAppearanceInventoryComplete']=False
        self.assertEqual(P.qualification(M,rows,G+'1',SCOPE,{},individual)['participation'],[])

    def test_zero_pa_batting_averages_do_not_depend_on_other_runners(self):
        graph=G+'1';game='https://baseballontology.org/data/game/1'
        rows=[dict(kind='player_team_game',player=U+str(i),graph=graph,game=game,team='team',teamRole='role') for i in (1,2,3)]
        rows.append(dict(kind='plate_appearance',entity='pa1',graph=graph,game=game,player=U+'1',
            recognizedBattingResult='true',act='act',paResult='result',paResultType='type',
            paResultJudgment='judgment',paResultDecision='decision',paResultRecord='record'))
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            players=[dict(player=U+str(i),status='withheld' if i==3 else 'admitted') for i in (1,2,3)])
        participation,records=P.project(M,graph=graph,scope=SCOPE,rows=rows,
            proofs=dict(batting={},run={},resolution={},players=individual),
            inputs=dict(contribution={},progress={},defense={}),runs={m:{} for m in P.RUNS},run_people={})
        self.assertEqual({p[1]:p[3] for p in participation},{U+'1':1,U+'2':0,U+'3':None})
        by_key={(r[1],r[2]):r for r in records}
        for metric in ('offensive-reach','hidden-help-rate'):
            self.assertEqual(by_key[(U+'1',metric)][3],0)
            self.assertEqual(by_key[(U+'3',metric)][3],0)
            no_pa=by_key[(U+'2',metric)]
            self.assertEqual(no_pa[3],1)
            self.assertEqual(json.loads(no_pa[4]),P.zero())
        self.assertEqual(by_key[(U+'2','contribution-path-diversity')][3],0)

    def test_resolution_extension_reuses_unchanged_player_partitions(self):
        db=self.db()
        for i,v in ((1,P.PREVIOUS_RESOLUTION_VERSION),(2,P.PREVIOUS_SCOPED_RESOLUTION_VERSION)):
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                (M._hash('source-'+str(i)+v),G+str(i)))
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('no unchanged projection')):
            result=P.prepare(M,db)
        self.assertEqual((result['preparedGames'],result['reusedGames']),(0,2))
        self.assertEqual(dict(db.execute('SELECT * FROM dashboard_player_partition')),
            {G+str(i):M._hash('source-'+str(i)+P.fingerprint()) for i in (1,2)})

    def test_scoped_contribution_upgrade_reuses_players_without_changed_pa_admissions(self):
        db=self.db()
        for i in (1,2):
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                (M._hash('source-'+str(i)+P.PREVIOUS_PA_CONTRIBUTION_VERSION),G+str(i)))
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('no unchanged projection')):
            self.assertEqual(P.prepare(M,db)['preparedGames'],0)

    def test_zero_pa_migration_preserves_scores_and_repairs_only_known_absences(self):
        db=self.db()
        for index in (1,2):
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                (M._hash('source-'+str(index)+P.PREVIOUS_ZERO_PA_VERSION),G+str(index)))
        db.execute('UPDATE dashboard_player_game SET plate_appearances=0 WHERE graph_iri=? AND player=?',(G+'1',U+'2'))
        db.execute('UPDATE dashboard_player_game SET plate_appearances=NULL WHERE player=?',(U+'1',))
        for metric in ('offensive-reach','hidden-help-rate','tfs'):
            for player in (U+'1',U+'2'):
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                    (G+'1',player,metric,0,M._json(P.zero()),'COMPLETE_PA_PROGRESS'))
                db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                    (G+'2',player,metric,1,M._json(dict(kind='mean',sum=M.exact(3),count=4)),None))
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('must not reconstruct inputs')), \
             patch.object(M,'run_kernel',side_effect=AssertionError('must not recalculate games')):
            migration=P.prepare(M,db)
        self.assertEqual(migration['preparedGames'],0)
        self.assertEqual(migration['repairedZeroPARows'],2)
        for metric in ('offensive-reach','hidden-help-rate'):
            result=Q.query(M,P,db,dict(metricId=metric),SCOPE)['metric']
            row,=result['playerResults']
            self.assertEqual(row['player'],U+'2');self.assertEqual(row['teamGames'],2)
            self.assertEqual(row['plateAppearances'],4)
            self.assertEqual(row['aggregate'],dict(kind='mean',sum=M.exact(3),count=4))
            self.assertEqual(row['value'],M.exact(M.Fraction(3,4)))
            self.assertEqual(result['rankingCoverage']['excludedPlayers'],1)
        self.assertEqual(Q.query(M,P,db,dict(metricId='tfs'),SCOPE)['metric']['playerResults'],[])
        self.assertEqual(P.prepare(M,db)['repairedZeroPARows'],0)

    def test_deployment_preserves_unchanged_player_products(self):
        db=self.db()
        for i,version in [(1,P.PREVIOUS_VERSION),(2,P.PREVIOUS_DAMAGE_VERSION)]:
            db.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                (M._hash('source-'+str(i)+version),G+str(i)))
        with patch.object(M._blocks,'read_scope',side_effect=AssertionError('must reuse existing products')):
            self.assertEqual(P.prepare(M,db)['preparedGames'],0)
        self.assertEqual(Q.query(M,P,db,{'metricId':'tfs'},SCOPE)['graphCount'],2)

    def test_individual_proof_updates_only_affected_projection_and_retains_provenance(self):
        db=self.db();proof=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,players=[])
        for table in ('metric_suite_admission','metric_suite_run_admission','metric_suite_runner_resolution_admission','metric_suite_boundary_admission'):
            db.execute(f'CREATE TABLE {table}(graph_iri TEXT,proof_json TEXT,proof_sha256 TEXT)')
        db.execute('CREATE TABLE metric_suite_evidence(graph_iri TEXT,binding_json TEXT,binding_sha256 TEXT)')
        movement=M._json(dict(kind='runner_movement',resolution='run',runner=U+'1'))
        db.execute('INSERT INTO metric_suite_evidence VALUES (?,?,?)',(G+'1',movement,M._hash(movement)))
        with patch.object(M._blocks,'read_scope',return_value=[]), \
             patch.object(M._blocks,'read_inputs',return_value={G+'1':{}}), \
             patch.object(M,'read_results',return_value=[dict(unresolvedRuns=[dict(run='run')])]), \
             patch.object(P,'project',return_value=([],[])) as project:
            result=P.prepare(M,db,player_admissions={G+'1':proof})
        self.assertEqual(result['preparedGames'],1)
        self.assertEqual(project.call_count,1)
        text,digest=db.execute('SELECT proof_json,proof_sha256 FROM dashboard_player_admission').fetchone()
        self.assertEqual(json.loads(text),proof)
        self.assertEqual(digest,M._hash(text))
        # The reader accepts this exact prepared partition without rebuilding it.
        Q.query(M,P,db,{'metricId':'tfs'},SCOPE)


if __name__=='__main__':unittest.main()
