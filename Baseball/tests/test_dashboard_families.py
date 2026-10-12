"""A defensive failure must not hold offensive publication or reads hostage."""
import sqlite3
import json
import unittest
from datetime import datetime, timezone
from contextlib import closing
from unittest.mock import patch

import test_dashboard_materializer as fixture
from test_contribution_sql import sample, PROOF
D=fixture.D


class DashboardFamilies(unittest.TestCase):
    pointer=fixture.DashboardMaterializer.pointer
    working=fixture.DashboardMaterializer.working

    def setUp(self):
        fixture.DashboardMaterializer.setUp(self)
        self.args.family='offense'
        self.bindings['101']=sample(101,'safe')[1]
        self.snapshot['live']['dimensions']=self.snapshot['live']['dimensions'][:1]
        self.snapshot['inventory']['games'].pop('102')
        self.stack.enter_context(patch.object(D.ADMISSION_EVIDENCE,'load',return_value=PROOF))
        self.stack.enter_context(patch.object(D.SOURCE._schedule_qualification,'merge_snapshots',return_value={
            '2026-08-01':dict(completeResponse=True,games=[dict(gamePk='101',gameType='R',final=True,unplayed=False)])}))

    def query(self):
        return D.SOURCE._reader.query_dashboard(self.args,dict(view='dashboard',gameSet='regular_season',
            dateScope=dict(preset='custom',startDate='2026-08-01',endDate='2026-08-01')),self.pointer())

    def test_player_projection_does_not_repeat_current_incomplete_game_calculation(self):
        original=D.METRICS.contribution_game_inputs
        def calculate(*args,**kwargs):
            return dict(original(*args,**kwargs),complete=False)
        individual=dict(rosterComplete=True,plateAppearanceInventoryComplete=True,
            paBoundaries=dict(plateAppearances=[]))
        with patch.object(D.ADMISSION_EVIDENCE,'player_admission',return_value=individual), \
             patch.object(D.METRICS,'contribution_game_inputs',side_effect=calculate) as compute:
            result=D.build(self.args)
        self.assertEqual(result['status'],'published',result)
        self.assertEqual(compute.call_count,1)
        with closing(sqlite3.connect(self.working())) as db:
            retained,=D.METRICS.read_results(db,self.graphs[0],'tfs')
            self.assertFalse(retained['contributionInputs']['complete'])

    def test_offense_publishes_and_reads_while_defense_fails_then_retries(self):
        with (patch.object(D.METRICS,'defensive_game_inputs',side_effect=ValueError('broken defense')),
              patch.object(D.METRICS,'defensive_players',side_effect=ValueError('broken defensive projection'))):
            offense=D.build(self.args)
            self.assertEqual(offense['status'],'published',offense)
            first=self.pointer()['families']['offense']
            result=self.query();metric=next(m for m in result['metrics'] if m['metricId']=='tfs')
            self.assertEqual(metric['playerResults'][0]['value'],D.METRICS.exact(D.METRICS.Fraction(1,4)))
            self.assertEqual(len(result['metrics']),20)
            self.args.family='defense'
            failed=D.build(self.args)
            self.assertEqual(failed['status'],'family-failed',failed)
            self.assertEqual(self.pointer()['families']['offense'],first)
            after=next(m for m in self.query()['metrics'] if m['metricId']=='tfs')
            self.assertEqual(after,metric)
        self.fetched.clear()
        recovered=D.build(self.args)
        self.assertEqual(recovered['status'],'published',recovered)
        self.assertEqual(self.fetched,[])  # The RDF answer is shared, not queried again.
        self.assertEqual(self.pointer()['families']['offense'],first)
        after=next(m for m in self.query()['metrics'] if m['metricId']=='tfs')
        self.assertEqual(after,metric)

    def test_retains_prior_defense_snapshot_and_bounds_retries_without_starving(self):
        D.build(self.args);self.args.family='defense'
        built=D.build(self.args);self.assertEqual(built['status'],'published',built)
        before=self.pointer()['families']['defense']
        self.snapshot['inventory']['games']['101']['authoritativeRdfSha256']='b'*64
        with patch.object(D.METRICS,'defensive_game_inputs',side_effect=ValueError('new defense failure')):
            result=D.build(self.args)
        self.assertEqual(result['status'],'family-failed',result)
        self.assertEqual(self.pointer()['families']['defense'],before)
        defense=next(m for m in self.query()['metrics'] if m['metricId']=='resolution-depth')
        self.assertEqual(defense['freshness']['status'],'retained')
        owner=D.module(D.ROOT/'serving/family_build.py','test_family_owner')
        families=['offense','defense','combined','other']
        attempts={'offense':dict(notification='n',attempts=3,attemptedAtUtc='1')}
        self.assertEqual(owner.choose(families,{},attempts,'n','auto',False),'defense')

    def test_all_families_publish_without_recalculating_sibling_metrics(self):
        for family in ('offense','defense','combined','other'):
            self.args.family=family
            result=D.build(self.args)
            self.assertEqual(result['status'],'published',result)
        self.assertEqual(set(self.pointer()['families']),{'offense','defense','combined','other'})
        result=self.query()
        self.assertEqual(len(result['metrics']),20)
        self.assertFalse(any(m['gaps']==['FAMILY_PUBLICATION_PENDING'] for m in result['metrics']),result)
        # A new offensive publication cannot overwrite the active defense file.
        defense=self.pointer()['families']['defense']
        self.args.family='offense';D.build(self.args)
        self.assertEqual(self.pointer()['families']['defense'],defense)
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT COUNT(DISTINCT family) FROM dashboard_family_checkpoint').fetchone()[0],4)

    def test_completed_empty_game_repair_gets_one_turn_then_rotation_resumes(self):
        owner=D.module(D.ROOT/'serving/family_build.py','test_repair_priority')
        families=['offense','defense','combined','other']
        published={'offense':dict(buildId='offense-before-repair',
            sourceSnapshotCapturedAtUtc='2026-10-12T02:17:55+00:00',familyNotificationKey='old')}
        control=self.args.state_root/'pipeline/control/mlb-game'
        (control/'empty-game-addition').mkdir(parents=True,exist_ok=True)
        plan=dict(publicationId='offense-before-repair',families=[dict(games=[dict(gamePk='101')])])
        (control/'empty-game-repair-plan.json').write_text(json.dumps(plan))
        receipt=control/'empty-game-addition/101.json'
        receipt.write_text(json.dumps(dict(gamePk='101',status='complete',checkedAtUtc='2026-10-12T02:45:28Z')))
        repaired=owner.completed_offense_repair(self.args.state_root,published)
        self.assertEqual(repaired,datetime(2026,10,12,2,45,28,tzinfo=timezone.utc))
        attempts={f:dict(notification='old',attempts=1,attemptedAtUtc=t) for f,t in [
            ('offense','2026-10-12T02:16:01Z'),('defense','2026-10-12T01:41:00Z'),
            ('combined','2026-10-12T01:50:27Z'),('other','2026-10-12T02:07:08Z')]}
        self.assertEqual(owner.choose(families,published,attempts,'new','auto',False,repaired_offense=repaired),'offense')
        attempts['offense']=dict(notification='new',attempts=1,attemptedAtUtc='2026-10-12T03:00:00Z',status='family-failed')
        self.assertEqual(owner.choose(families,published,attempts,'new','auto',False,repaired_offense=repaired),'defense')
        attempts['offense'].update(attempts=3,attemptedAtUtc='2026-10-12T02:20:00Z')
        self.assertEqual(owner.choose(families,published,attempts,'new','auto',False,repaired_offense=repaired),'defense')
        self.assertEqual(owner.choose(families,published,attempts,'new','other',False,repaired_offense=repaired),'other')
        published['offense']['buildId']='newer-offense'
        self.assertIsNone(owner.completed_offense_repair(self.args.state_root,published))
        published['offense']['buildId']='offense-before-repair'
        for status in ('failed','already-present'):
            receipt.write_text(json.dumps(dict(gamePk='101',status=status,checkedAtUtc='2026-10-12T02:45:28Z')))
            self.assertIsNone(owner.completed_offense_repair(self.args.state_root,published))

    def test_legacy_offensive_values_survive_migration_without_a_graph_read(self):
        del self.args.family
        legacy=D.build(self.args);self.assertEqual(legacy['status'],'published',legacy)
        before={m['metricId']:m for m in self.query()['metrics']}
        self.args.family='offense';self.fetched.clear()
        with patch.object(D.METRICS,'defensive_game_inputs',side_effect=AssertionError('defense dependency')):
            migrated=D.build(self.args)
        self.assertEqual(migrated['status'],'published',migrated)
        self.assertEqual(self.fetched,[])
        families=D.module(D.ROOT/'serving/metric_families.py','test_families')
        for metric in self.query()['metrics']:
            if metric['metricId'] in families.OFFENSE:
                metric.pop('freshness')
                self.assertEqual(metric,before[metric['metricId']])

    def test_player_projection_failure_keeps_previous_publication_and_resumes_checkpoint(self):
        D.build(self.args);self.args.family='defense';D.build(self.args)
        old=self.pointer()['families']['defense']
        with patch.object(D.ADMISSION_EVIDENCE,'load',return_value=dict(PROOF,proofSha256='updated-proof')):
            with patch.object(D.METRICS,'defensive_players',side_effect=ValueError('projection interrupted')):
                failed=D.build(self.args)
            self.assertEqual(failed['status'],'family-failed',failed)
            self.assertEqual(self.pointer()['families']['defense'],old)
            with patch.object(D.METRICS,'defensive_game_inputs',side_effect=AssertionError('repeated committed game')):
                resumed=D.build(self.args)
            self.assertEqual(resumed['status'],'published',resumed)
            self.assertEqual(resumed['changedGames'],0)
        # New defense never rewrites the existing offensive SQL participation.
        offense=next(m for m in self.query()['metrics'] if m['metricId']=='tfs')
        self.assertEqual(offense['playerResults'][0]['value'],D.METRICS.exact(D.METRICS.Fraction(1,4)))

    def test_eg6_reuses_unchanged_graph_answers_with_their_original_query_provenance(self):
        query=D.METRICS.evidence_query
        with patch.object(D.METRICS,'evidence_query',side_effect=lambda graphs:query(graphs,prior_empty_game=True)):
            self.assertEqual(D.build(self.args)['status'],'published')
        with closing(sqlite3.connect(self.working())) as db:
            before=db.execute('SELECT query_sha256 FROM dashboard_evidence_checkpoint').fetchall()
        self.fetched.clear()
        with patch.object(D.ADMISSION_EVIDENCE,'load',return_value=dict(PROOF,proofSha256='eg6-proof')):
            self.assertEqual(D.build(self.args)['status'],'published')
        self.assertEqual(self.fetched,[])
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT query_sha256 FROM dashboard_evidence_checkpoint').fetchall(),before)
        self.snapshot['inventory']['games']['101']['authoritativeRdfSha256']='c'*64
        self.assertEqual(D.build(self.args)['status'],'published')
        self.assertTrue(self.fetched)  # A targeted graph addition always requires a new answer.

    def test_eg6_refreshes_ambiguous_actors_interference_and_compound_results(self):
        owner=D.module(D.ROOT/'serving/family_build.py','eg6_retained_answers')
        graph='https://w3id.org/baseball/graph/game/1';m=D.METRICS;base='https://baseballontology.org/'
        old=D.digest(m.evidence_query([graph],prior_empty_game=True));current=D.digest(m.evidence_query([graph]))
        row=dict(kind='plate_appearance',entity='pa',player='player',paResultType=base+'SingleProcess')
        variants=[[row],[row,dict(row,player='replacement')],[dict(row,paResultType=base+'InterferenceProcess')],
            [dict(row,paResultType=base+'SacrificeFlyProcess'),dict(row,paResultType=base+'DoublePlayProcess')]]
        for index,rows in enumerate(variants):
            with closing(sqlite3.connect(':memory:')) as db:
                db.execute('CREATE TABLE dashboard_evidence_checkpoint (graph_iri,rdf_sha256,query_sha256,row_count)')
                db.execute('CREATE TABLE metric_suite_evidence (graph_iri,binding_sha256,binding_json)')
                db.execute('INSERT INTO dashboard_evidence_checkpoint VALUES (?,?,?,?)',(graph,'rdf',old,len(rows)))
                for item in rows:
                    text=m._json(item);db.execute('INSERT INTO metric_suite_evidence VALUES (?,?,?)',(graph,m._hash(text),text))
                result=owner.retained_rows(D,db,graph,dict(authoritativeRdfSha256='rdf'),None,current,None)
                self.assertEqual(result is not None,index==0)


if __name__=='__main__':unittest.main()
