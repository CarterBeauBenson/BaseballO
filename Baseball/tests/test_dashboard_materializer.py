"""Incremental SQL publication, interruption recovery and independent reads."""
from contextlib import ExitStack, closing
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dashboard_builder', ROOT/'scripts/pipeline/materialize-dashboard.py')
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)


class DashboardMaterializer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.args = SimpleNamespace(state_root=self.state, endpoint='unused', timeout=1,
            max_games=None, no_promote=False, force=True, workers=2, quiet_seconds=0)
        self.graphs = ['https://w3id.org/baseball/graph/game/'+str(n) for n in (101,102)]
        self.snapshot = dict(fingerprint='corpus-one', inventory=dict(games={}), live=dict(dimensions=[]))
        for graph in self.graphs:
            pk = graph.rsplit('/',1)[1]
            self.snapshot['inventory']['games'][pk] = dict(gamePk=pk,authoritativeGraph=graph,authoritativeRdfSha256='a'*64)
            values = dict(graph=graph,game='https://baseballontology.org/data/game/'+pk,
                          start='2026-08-01T12:00:00Z',rdfGameSet='regular_season')
            self.snapshot['live']['dimensions'].append({key:dict(value=value) for key,value in values.items()})
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name,value in [('corpus_snapshot',None),('official_metadata',{})]:
            mock = self.stack.enter_context(patch.object(D.SOURCE,name,return_value=value))
            if name == 'corpus_snapshot': self.source = mock; mock.side_effect = lambda *a: copy.deepcopy(self.snapshot)
        for adapter in D.ADMISSIONS.values():
            self.stack.enter_context(patch.object(adapter,'promoted_admission',return_value={'status':'withheld'}))
        self.stack.enter_context(patch.object(D.ADMISSION_EVIDENCE,'load',return_value={'status':'withheld'}))
        self.stack.enter_context(patch.object(D.SOURCE._batting_admission,'schedule_coverage',return_value={}))
        self.stack.enter_context(patch.object(D.SOURCE._schedule_qualification,'merge_snapshots',return_value={}))
        self.fetched = []
        self.bindings = {}
        fetched = self.fetched
        bindings = self.bindings
        class Cache:
            stats = {}
            def __init__(self,*a): pass
            def query(self,**kw):
                if kw['slot'] == 'metric-display':
                    graph = kw['promotion']['authoritativeGraph']
                    return {'results':{'bindings':[dict(graph=dict(type='uri',value=graph),
                        entity=dict(type='uri',value='https://baseballontology.org/data/player/1'),
                        label=dict(type='literal',value='Prepared player'))]}}
                fetched.append(kw['promotion']['gamePk'])
                return {'results':{'bindings':bindings.get(kw['promotion']['gamePk'],[])}}
        self.stack.enter_context(patch.object(D.SOURCE._query_cache,'ServingQueryCache',Cache))

    def pointer(self): return D.RELEASE.read(self.state/'serving/dashboard-current.json')
    def working(self): return next((self.state/'serving/dashboard').glob('working-*.sqlite'))

    def test_reuses_sql_and_replaces_only_changed_game_with_real_metric_roundtrip(self):
        first = D.build(self.args)
        self.assertEqual(first['status'],'published'); self.assertEqual(first['changedGames'],2)
        self.assertCountEqual(self.fetched,['101','102'])
        old = self.pointer(); old_bytes = Path(old['databasePath']).read_bytes()
        self.fetched.clear()
        unchanged = D.build(self.args)
        self.assertEqual(unchanged['reusedGames'],2); self.assertEqual(self.fetched,[])
        self.snapshot['inventory']['games']['102']['authoritativeRdfSha256'] = 'b'*64
        self.snapshot['fingerprint'] = 'corpus-two'
        changed = D.build(self.args)
        self.assertEqual((changed['changedGames'],changed['reusedGames']),(1,1))
        self.assertEqual(self.fetched,['102'])
        self.assertEqual(Path(old['databasePath']).read_bytes(),old_bytes)
        self.assertEqual(changed['affectedSeasons'],[2026])
        # Report configuration failures do not participate in dashboard reads.
        reader = D.SOURCE._reader; original = reader.load_object
        with patch.object(reader,'load_object',side_effect=lambda p: original(p) if p==reader.CONTRACT else (_ for _ in ()).throw(AssertionError('report dependency'))):
            result = reader.query(self.args,dict(route='metric-suite',view='dashboard',gameSet='regular_season',dateScope={'preset':'one_day'}))
        self.assertEqual(len(result['metrics']),20)  # Includes the catalog's retained legacy metric.
        self.assertEqual(result['serving']['publication'],'dashboard')
        self.assertEqual(result['display']['source'],'prepared-sql-labels')
        self.assertEqual([r['label'] for r in result['display']['labels']], ['Prepared player']*2)

    def test_failed_game_rolls_back_and_resume_reuses_committed_games(self):
        materialize = D.METRICS.materialize_game
        def fail_second(connection, graph, *a, **kw):
            if graph == self.graphs[1]: raise RuntimeError('simulated interruption')
            return materialize(connection,graph,*a,**kw)
        with patch.object(D.METRICS,'materialize_game',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'interruption'): D.build(self.args)
        self.assertFalse((self.state/'serving/dashboard-current.json').exists())
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT graph_iri FROM dashboard_checkpoint').fetchall(),[(self.graphs[0],)])
            self.assertEqual(db.execute('SELECT graph_iri FROM game_dimension').fetchall(),[(self.graphs[0],)])
        self.fetched.clear(); result = D.build(self.args)
        self.assertEqual((result['changedGames'],result['reusedGames']),(1,1))
        self.assertEqual(self.fetched,['102'])
        old = self.pointer()
        self.snapshot['inventory']['games']['102']['authoritativeRdfSha256'] = 'c'*64
        with patch.object(D.METRICS,'materialize_game',side_effect=fail_second):
            with self.assertRaises(RuntimeError): D.build(self.args)
        self.assertEqual(self.pointer(),old)
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM dashboard_checkpoint').fetchone()[0],2)

    def test_compatibility_metadata_reuses_old_checkpoints_but_actual_admission_changes_recalculate(self):
        old=dict(status='withheld',implementationReuse={'recordSha256':'old-record'})
        new=dict(status='withheld',implementationReuse={'recordSha256':'extended-record'})
        with patch.object(D.ADMISSION_EVIDENCE,'load',return_value=old):D.build(self.args)
        with closing(sqlite3.connect(self.working())) as db,db:
            for dimension in self.snapshot['live']['dimensions']:
                graph=D.SOURCE.lexical(dimension,'graph');promotion=self.snapshot['inventory']['games'][graph.rsplit('/',1)[-1]]
                legacy=D.input_identity(promotion,D.dimension_values(dimension,promotion,{}),
                    {name:old for name in D.ADMISSIONS},D.METRICS.calculation_fingerprint(),legacy=True)
                db.execute('UPDATE dashboard_checkpoint SET input_sha256=? WHERE graph_iri=?',(legacy,graph))
        self.fetched.clear()
        with patch.object(D.ADMISSION_EVIDENCE,'load',return_value=new),patch.object(D.METRICS,'materialize_game',
                side_effect=AssertionError('Metadata is not a new calculation')):
            result=D.build(self.args)
        self.assertEqual((result['changedGames'],result['reusedGames']),(0,2))
        self.assertEqual(self.fetched,[])
        with closing(sqlite3.connect(self.working())) as db:
            for table in D.ADMISSION_TABLES.values():
                self.assertEqual([json.loads(r[0]) for r in db.execute(f'SELECT proof_json FROM {table}')],[new,new])
        def change_one(adapter,state,promotion,family):
            return {**new,'status':'admitted'} if promotion['gamePk']=='101' else new
        with patch.object(D.ADMISSION_EVIDENCE,'load',side_effect=change_one):result=D.build(self.args)
        self.assertEqual((result['changedGames'],result['reusedGames']),(1,1))
        self.assertEqual(result['admissionUpdatedGames'],1)
        self.assertEqual(self.fetched,[])

    def test_admission_only_update_matches_full_calculation_without_rewriting_evidence(self):
        from test_contribution_sql import sample,PROOF
        graph,bindings=sample(101,'safe');self.bindings['101']=bindings
        D.build(self.args)
        self.fetched.clear()
        with patch.object(D.ADMISSION_EVIDENCE,'load',side_effect=lambda adapter,state,promotion,family:
                PROOF if promotion['gamePk']=='101' else {'status':'withheld'}),patch.object(
                D.METRICS,'live_result',side_effect=AssertionError('Unchanged game kernel')):
            result=D.build(self.args)
        self.assertEqual(result['admissionUpdatedGames'],1)
        self.assertEqual(self.fetched,[])
        with closing(sqlite3.connect(self.working())) as actual,closing(sqlite3.connect(':memory:')) as full:
            full.executescript(D.SCHEMA.read_text());D.METRICS.initialize_sql(full)
            dimension=actual.execute('SELECT * FROM game_dimension WHERE graph_iri=?',(graph,)).fetchone()
            full.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',dimension)
            D.METRICS.materialize_game(full,graph,bindings,**{name:PROOF for name in D.ADMISSIONS})
            self.assertTrue(D.METRICS.read_results(actual,graph,'tfs')[0]['contributionInputs']['complete'])
            for table in D.graph_tables(full):
                self.assertEqual(sorted(actual.execute(f'SELECT * FROM {table} WHERE graph_iri=?',(graph,)).fetchall()),
                    sorted(full.execute(f'SELECT * FROM {table} WHERE graph_iri=?',(graph,)).fetchall()),table)
            # A metadata-only refresh of the proof still reuses every score.
            previous={name:PROOF for name in D.ADMISSIONS}
            statements=[];actual.set_trace_callback(statements.append)
            D.refresh_admission_inputs(actual,graph,previous,{name:dict(PROOF,receipt='new') for name in D.ADMISSIONS})
            self.assertFalse(any('metric_suite_evidence' in s and s.startswith(('INSERT','DELETE','UPDATE')) for s in statements))
            actual.execute('DELETE FROM metric_suite_evidence WHERE rowid IN (SELECT rowid FROM metric_suite_evidence LIMIT 1)')
            with self.assertRaisesRegex(ValueError,'incomplete'):
                D.refresh_admission_inputs(actual,graph,previous,{name:dict(PROOF,status='withheld') for name in D.ADMISSIONS})

    def test_source_change_preserves_work_but_cannot_publish(self):
        D.build(self.args); old = self.pointer()
        changed = copy.deepcopy(self.snapshot); changed['fingerprint'] = 'changed-during-build'
        self.source.side_effect = [self.snapshot,changed]
        result = D.build(self.args)
        self.assertEqual(result['status'],'waiting-for-source'); self.assertEqual(self.pointer(),old)
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM dashboard_checkpoint').fetchone()[0],2)

    def test_promotion_during_snapshot_waits_for_next_tick_and_preserves_publication(self):
        D.build(self.args);old=self.pointer()
        for phase in ('initial','final'):
            drift=D.SOURCE.SourceSnapshotChanged('Promotion inventory changed during capture')
            self.source.side_effect=drift if phase=='initial' else [self.snapshot,drift]
            result=D.build(self.args)
            self.assertEqual(result['status'],'waiting-for-source')
            self.assertNotIn('error',result)
            self.assertEqual(self.pointer(),old)
            with closing(sqlite3.connect(self.working())) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM dashboard_checkpoint').fetchone()[0],2)
        self.source.side_effect=lambda *args:copy.deepcopy(self.snapshot)
        self.fetched.clear();result=D.build(self.args)
        self.assertEqual(result['status'],'published');self.assertEqual(self.fetched,[])

    def test_unchanged_tick_exits_without_querying_and_development_cannot_prune_full_store(self):
        D.build(self.args); self.fetched.clear(); self.args.force = False
        with patch.object(D.SOURCE,'corpus_snapshot',side_effect=AssertionError('no graph read')):
            self.assertEqual(D.build(self.args)['status'],'unchanged')
        old = self.pointer(); self.args.max_games = 1
        self.snapshot['live']['dimensions'] = self.snapshot['live']['dimensions'][:1]
        self.snapshot['inventory']['games'].pop('102')
        self.assertEqual(D.build(self.args)['status'],'ready-for-promotion')
        self.assertEqual(self.pointer(),old)
        with closing(sqlite3.connect(self.working())) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM dashboard_checkpoint').fetchone()[0],2)

    def test_rank_invalidation_is_limited_to_changed_season(self):
        D.build(self.args)
        with closing(sqlite3.connect(self.working())) as db, db:
            for year in (2025,2026):
                db.execute('INSERT INTO metric_suite_reference VALUES (?,?,?,?)',('test',year,'hash',0))
            db.execute('INSERT INTO metric_suite_input_row VALUES (?,?,?,?,?,?,?,?,?,?)',
                (self.graphs[0],'test','entity',None,None,0,None,None,'{}','hash'))
            self.assertEqual(db.execute('SELECT season FROM metric_suite_reference').fetchall(),[(2025,)])
            with patch.object(D.METRICS._blocks,'read_scope',side_effect=AssertionError('unaffected season')):
                self.assertEqual(D.METRICS.materialize_reference_ranks(db,seasons={2024}),[])

    def test_writer_lock_is_exclusive_and_released_after_failure(self):
        lock = self.state/'writer.lock'
        with D.writer_lock(lock):
            with self.assertRaises(BlockingIOError):
                with D.writer_lock(lock): pass
        with D.writer_lock(lock): pass
        self.assertEqual(lock.stat().st_size,1)


if __name__ == '__main__': unittest.main()
