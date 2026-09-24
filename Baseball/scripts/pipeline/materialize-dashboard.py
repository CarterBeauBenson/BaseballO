"""NiFi-owned incremental dashboard SQL over existing promoted RDF.

One committed game is one resumable checkpoint. The mutable work database is
never served; publication uses an immutable SQLite snapshot and its own pointer.
Report/Explorer materialization and RDF ingestion are independent of this job.
"""
from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


RELEASE = module(ROOT/'scripts/pipeline/serving_release.py', 'dashboard_release')
if __name__ == '__main__':
    result = RELEASE.dispatch(ROOT, sys.argv[1:], mode='dashboard-build')
    if result is not None: raise SystemExit(result)

# Reuse the existing source-neutral inventory, source snapshot and admission
# adapters. The legacy builder's report queries and build() are never invoked.
SOURCE = module(ROOT/'scripts/pipeline/materialize-serving-layer.py', 'dashboard_source')
METRICS = SOURCE._metric_suite
DISPLAY = module(ROOT/'serving/dashboard_display.py', 'dashboard_display')
REFERENCES = module(ROOT/'serving/reference_products.py', 'dashboard_references')
ADMISSION_EVIDENCE = module(ROOT/'sources/mlb-game/pipeline/admission-evidence.py','dashboard_admission_evidence')
SCHEMA = ROOT/'serving/dashboard-schema.sql'
POINTER = 'dashboard-current.json'
ADMISSIONS = {
    'batting_admission': SOURCE._batting_admission,
    'scoring_run_admission': SOURCE._run_admission,
    'runner_resolution_admission': SOURCE._resolution_admission,
    'pitch_count_admission': SOURCE._count_admission,
    'runner_boundary_admission': SOURCE._boundary_admission,
    'defensive_admission': SOURCE._defense_admission,
}
ADMISSION_TABLES = dict(zip(ADMISSIONS,('metric_suite_admission','metric_suite_run_admission',
    'metric_suite_runner_resolution_admission','metric_suite_count_admission',
    'metric_suite_boundary_admission','metric_suite_defensive_admission')))


def digest(value):
    return hashlib.sha256(RELEASE.encoded(value)).hexdigest()


@contextmanager
def writer_lock(path):
    """OS lock releases on process termination; a stale file cannot block resume."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error: raise BlockingIOError('Dashboard writer is already running') from error
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try: yield
        finally:
            handle.seek(0)
            if os.name == 'nt': msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def bounded_fetch(items, fetch, workers):
    """At most two game payloads in flight; SQL always has a single writer."""
    if workers not in (1, 2): raise ValueError('Dashboard supports one or two read workers')
    iterator = iter(items)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = deque()
        for _ in range(workers):
            item = next(iterator, None)
            if item is not None: pending.append((item, executor.submit(fetch, item)))
        while pending:
            item, future = pending.popleft()
            yield item, future.result()
            next_item = next(iterator, None)
            if next_item is not None: pending.append((next_item, executor.submit(fetch, next_item)))


def graph_tables(connection):
    names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return [name for name in names if name.startswith('metric_suite_')
            and 'graph_iri' in {r[1] for r in connection.execute(f'PRAGMA table_info("{name}")')}]


def remove_game(connection, graph):
    # Keep the dimension until child-row triggers have invalidated its ranks.
    DISPLAY.remove(connection, graph)
    for table in graph_tables(connection):
        connection.execute(f'DELETE FROM "{table}" WHERE graph_iri=?', (graph,))
    connection.execute('DELETE FROM dashboard_checkpoint WHERE graph_iri=?', (graph,))
    connection.execute('DELETE FROM game_dimension WHERE graph_iri=?', (graph,))


def dimension_values(dimension, promotion, metadata):
    lex = SOURCE.lexical; graph = lex(dimension, 'graph'); pk = promotion['gamePk']
    meta = dict(metadata.get(pk, {}))
    if meta.get('gameSet') != 'fixture' and promotion.get('officialDate') and promotion.get('gameType'):
        meta.update(officialDate=promotion['officialDate'], gameSet=SOURCE.provenance_game_set(promotion['gameType']))
    day = meta.get('officialDate') or (lex(dimension, 'start') or '')[:10]
    rdf_set = lex(dimension, 'rdfGameSet'); game_set = meta.get('gameSet') or rdf_set
    if meta.get('gameSet') and rdf_set and game_set != rdf_set and game_set != 'fixture':
        raise ValueError('Game-set provenance disagrees with RDF: '+pk)
    if len(day) != 10 or game_set not in SOURCE.PERSISTENT_GAME_SETS:
        raise ValueError('Missing supported game/date provenance: '+pk)
    return (graph, lex(dimension, 'game'), pk, day, lex(dimension, 'start'), int(day[:4]), game_set,
            *(lex(dimension, key) for key in ('venue','venueLabel','homeTeam','homeTeamLabel','awayTeam','awayTeamLabel')))


def input_identity(promotion, dimension, admissions, calculation, *, legacy=False):
    # Index rebuilds and unrelated report changes do not invalidate dashboard
    # facts. Exact RDF bytes, validated admissions and calculation inputs do.
    if not legacy:
        admissions={name:{key:value for key,value in proof.items() if key!='implementationReuse'}
                    for name,proof in admissions.items()}
    return digest(dict(graph=promotion['authoritativeGraph'], rdf=promotion['authoritativeRdfSha256'],
                       dimension=dimension, admissions=admissions, calculation=calculation))


def reuse_game(connection, graph, saved, promotion, dimension, admissions, calculation):
    """Refresh compatibility provenance without repeating unchanged scores.

    Admission outcomes, exact original proof hashes, RDF, dimensions and math
    remain inputs. Only the independently rechecked code-compatibility receipt
    is bookkeeping. Recognize old checkpoints against their stored full proof
    objects, so deploying this distinction does not itself rebuild all games.
    """
    if saved is None:return False
    previous={}
    for name,table in ADMISSION_TABLES.items():
        row=connection.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
        if row is None:return False
        if METRICS._hash(row[0])!=row[1]:raise ValueError('Stored dashboard admission changed')
        previous[name]=json.loads(row[0])
    identity=input_identity(promotion,dimension,admissions,calculation)
    previous_identity=input_identity(promotion,dimension,previous,calculation)
    if saved not in {previous_identity,input_identity(promotion,dimension,previous,calculation,legacy=True)}:return False
    changed=previous_identity!=identity
    if changed:
        refresh_admission_inputs(connection,graph,previous,admissions)
        mark_dirty(connection,{dimension[5]})
    for name,table in ADMISSION_TABLES.items():
        if previous[name]==admissions[name]:continue
        text=METRICS._json(admissions[name])
        connection.execute(f'UPDATE {table} SET proof_json=?,proof_sha256=? WHERE graph_iri=?',
                           (text,METRICS._hash(text),graph))
    if saved!=identity:
        connection.execute('UPDATE dashboard_checkpoint SET input_sha256=? WHERE graph_iri=?',(identity,graph))
    return 'admissions' if changed else 'unchanged'


def mark_dirty(connection, seasons):
    row=connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()
    seasons=set(seasons)|set(json.loads(row[0]) if row else [])
    connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',
                       ('dirty-seasons',json.dumps(sorted(seasons))))


def refresh_admission_inputs(connection, graph, previous, admissions):
    """Recalculate only proof-dependent inputs over unchanged retained RDF rows.

    The caller has matched the old checkpoint against the same RDF, dimensions
    and calculation version. Game-level observations, scope facts and metric
    kernels have no admission argument; preserve their exact stored results.
    """
    def semantic(proof):return {k:v for k,v in proof.items() if k!='implementationReuse'}
    changed={name for name in ADMISSIONS if semantic(previous[name])!=semantic(admissions[name])}
    families={}
    dependencies={
        'resolution-depth':{'defensive_admission'},
        'tfs':{'batting_admission','runner_resolution_admission','runner_boundary_admission'},
        'recovery-quality':{'batting_admission','pitch_count_admission'},
    }
    affected={metric for metric,names in dependencies.items() if changed & names}
    if not affected:return
    rows=[]
    for text,sha in connection.execute('SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,)):
        if METRICS._hash(text)!=sha:raise ValueError('Stored dashboard evidence changed')
        rows.append(json.loads(text))
    rows.sort(key=METRICS._json)  # Preserve normalize_bindings' canonical order.
    proof=json.loads(connection.execute('SELECT proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()[0])
    if len(rows)!=proof['evidenceRows']:raise ValueError('Stored dashboard evidence is incomplete')
    # Reuse the existing calculators; this path defines no separate metric math.
    if 'resolution-depth' in affected:
        families['resolution-depth']=METRICS.defensive_game_inputs(rows,graph=graph,admission=admissions['defensive_admission'])
    if 'tfs' in affected:
        families['tfs']=METRICS.contribution_game_inputs(rows,graph=graph,
            **{name:admissions[name] for name in dependencies['tfs']})
    if 'recovery-quality' in affected:
        families['recovery-quality']=METRICS.recovery_game_inputs(rows,graph=graph,
            **{name:admissions[name] for name in dependencies['recovery-quality']})
    retained={}
    for metric in [*dependencies,'paq-2.1']:
        results=METRICS.read_results(connection,graph,metric)
        if len(results)!=1:raise ValueError('Stored dashboard game result is incomplete')
        retained[metric]=results[0]
    def product(metric):return families.get(metric,retained[metric][METRICS._blocks.INPUTS[metric][1]])
    families['paq-2.1']=METRICS.paq21_game_inputs(product('tfs'),product('recovery-quality'),product('resolution-depth'))
    for metric,product in families.items():
        family,key,_=METRICS._blocks.INPUTS[metric]
        if retained[metric][key]==product:continue
        result=dict(retained[metric],**{key:product})
        METRICS.store_result(connection,graph,metric,'game-scope',result)
        if METRICS.read_results(connection,graph,metric)!=[result]:raise ValueError('Refreshed dashboard result differs')
        if METRICS._blocks.read_inputs(METRICS._block_api(),connection,family,[graph])[graph]!=product:
            raise ValueError('Refreshed dashboard inputs differ')


def retain_snapshots(directory, current):
    """Only this product's old immutable files; active Windows readers may pin one."""
    directory = directory.resolve()
    snapshots = sorted(directory.glob('*-dashboard-*.sqlite'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for path in snapshots[3:]:
        if path.resolve().parent == directory and path.resolve() != current.resolve():
            try: path.unlink()
            except OSError: pass


def store_game(connection, item, bindings, product_cache=None):
    graph = item['graph']
    with connection:
        remove_game(connection, graph)
        connection.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', item['dimension'])
        proof = METRICS.materialize_game(connection, graph, bindings, product_cache=product_cache, **item['admissions'])
        connection.execute('INSERT INTO dashboard_checkpoint VALUES (?,?,?)',
                           (graph, item['identity'], json.dumps(proof, sort_keys=True)))
        dirty = {item['dimension'][5], *item.get('previousSeasons', [])}
        row = connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()
        dirty.update(json.loads(row[0]) if row else [])
        connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',
                           ('dirty-seasons', json.dumps(sorted(dirty))))
    return proof


def notification_key(state):
    """Cheap event check only; changed inputs still undergo the existing snapshot."""
    paths = list((state/'pipeline/evidence/nifi/game-promotion').glob('*/*.json'))
    paths += list((state/'pipeline/control/mlb-game/batches').glob('*.json'))
    paths += list((state/'pipeline/control/mlb-game/schedule-coverage').glob('*.json'))
    paths += list((state/'pipeline/evidence/mlb-game').glob('*/admission-refresh/*/*.receipt.json'))
    files = [(str(p.relative_to(state)), p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(paths)]
    return digest(dict(events=files, metrics=METRICS.fingerprint(), builder=SOURCE.sha256_file(Path(__file__)),
                       admissionReader=ADMISSION_EVIDENCE.fingerprint(),
                       display=DISPLAY.fingerprint(), references=REFERENCES.fingerprint(),
                       schema=SOURCE.sha256_file(SCHEMA))), max((v[2] for v in files), default=0)


def build(args):
    state = args.state_root.resolve(); serving = state/'serving'; work = serving/'dashboard'
    work.mkdir(parents=True, exist_ok=True)
    if args.max_games:
        # A bounded developer build must not remove full-corpus checkpoints.
        work = work/'development'/str(args.max_games)
        work.mkdir(parents=True, exist_ok=True)
    with writer_lock(work/'writer.lock'):
        return build_locked(args, state, serving, work)


def build_locked(args, state, serving, work):
    pointer_path = serving/POINTER
    notification, latest = notification_key(state)
    publication_issue = None
    try:
        old_pointer = RELEASE.read(pointer_path) if pointer_path.is_file() else {}
        if not isinstance(old_pointer, dict): raise ValueError('Dashboard pointer is not a JSON object')
    except (ValueError, UnicodeError) as error:
        # Preserve the damaged file until a successful atomic publication.
        # Its bytes are derived metadata, never a reason to repeat ingestion.
        old_pointer = {}
        publication_issue = str(error)
    if not args.force and not args.max_games and old_pointer.get('notificationKey') == notification:
        # Reuse the reader's existing file and metadata checks without scoring
        # anything. Valid bytes with a mismatched pointer are not a usable build.
        try:
            with SOURCE._reader.dashboard_database(state, old_pointer):
                return dict(status='unchanged', buildId=old_pointer['buildId'])
        except (OSError, ValueError, sqlite3.Error) as error:
            publication_issue = str(error)
    if not args.force and time.time_ns() - latest < args.quiet_seconds * 1_000_000_000:
        return dict(status='waiting-for-source', reason='Recent promotion or schedule update')
    started = time.perf_counter()
    build_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-dashboard-'+uuid.uuid4().hex[:12]
    progress = dict(artifactType='baseballo-dashboard-build-progress', buildId=build_id, processId=os.getpid(),
                    status='running', phase='source-snapshot', completedGames=0, changedGames=0, reusedGames=0)
    if publication_issue: progress['previousPublicationIssue'] = publication_issue
    progress_path = work/'progress.json'
    phase_started = time.perf_counter()
    durations = {}
    def checkpoint(**values):
        nonlocal phase_started
        if values.get('phase',progress['phase']) != progress['phase'] or values.get('status') in {'published','failed','ready-for-promotion','waiting-for-source'}:
            durations[progress['phase']] = round(durations.get(progress['phase'],0)+time.perf_counter()-phase_started,3)
            phase_started = time.perf_counter()
        progress['phaseSeconds'] = dict(durations)
        progress.update(values, updatedAtUtc=datetime.now(timezone.utc).isoformat())
        RELEASE.atomic(progress_path, progress)
    checkpoint()
    connection = None
    try:
        snapshot = SOURCE.corpus_snapshot(state, args.endpoint, args.timeout, args.max_games)
        metadata = SOURCE.official_metadata(state)
        inventory = snapshot['inventory']['games']
        dimensions = snapshot['live']['dimensions']
        schema_key = digest([SCHEMA.read_text(encoding='utf-8'), (ROOT/'serving/metric-suite-schema.sql').read_text(encoding='utf-8')])
        database = work/('working-'+schema_key[:16]+'.sqlite')
        connection = sqlite3.connect(database, timeout=30)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        METRICS.initialize_sql(connection); DISPLAY.initialize(connection); connection.commit()
        calculation = METRICS.calculation_fingerprint()
        cache = SOURCE._query_cache.ServingQueryCache(serving/'query-cache.sqlite')
        products = SOURCE._metric_cache.MetricProductCache(serving/'metric-cache.sqlite', calculation)
        pending = []; expected = {}; unchanged = 0; admission_updates = 0
        old_dimensions = dict(connection.execute('SELECT graph_iri,season FROM game_dimension'))
        saved = dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_checkpoint'))
        for dimension in dimensions:
            graph = SOURCE.lexical(dimension, 'graph'); pk = graph.rsplit('/',1)[-1]
            promotion = inventory[pk]
            admissions = {name: ADMISSION_EVIDENCE.load(adapter,state,promotion,name.removesuffix('_admission').replace('_','-'))
                          for name, adapter in ADMISSIONS.items()}
            values = dimension_values(dimension, promotion, metadata)
            identity = input_identity(promotion, values, admissions, calculation)
            expected[graph] = identity
            with connection:
                reused=reuse_game(connection,graph,saved.get(graph),promotion,values,admissions,calculation)
            if reused:
                if reused=='admissions':admission_updates+=1
                else:unchanged+=1
                continue
            pending.append(dict(graph=graph, promotion=promotion, dimension=values, identity=identity,
                                admissions=admissions, previousSeasons=[old_dimensions[graph]] if graph in old_dimensions else []))
        connection.commit()
        removed = set(old_dimensions) - set(expected)
        with connection:
            dirty_row = connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()
            dirty = set(json.loads(dirty_row[0]) if dirty_row else [])
            for graph in removed:
                dirty.add(old_dimensions[graph]); remove_game(connection, graph)
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)', ('dirty-seasons', json.dumps(sorted(dirty))))
        checkpoint(phase='game-products', totalGames=len(expected), changedGames=len(pending)+admission_updates,
                   admissionUpdatedGames=admission_updates,reusedGames=unchanged, completedGames=unchanged+admission_updates)
        def fetch(item):
            query = METRICS.evidence_query([item['graph']])
            return cache.query(endpoint=args.endpoint, query=query, slot='metric-suite', promotion=item['promotion'],
                               fetch=lambda: SOURCE.sparql(args.endpoint, query, args.timeout))['results']['bindings']
        for count, (item, bindings) in enumerate(bounded_fetch(pending, fetch, args.workers), 1):
            store_game(connection, item, bindings, products)
            checkpoint(completedGames=unchanged+admission_updates+count)
        checkpoint(phase='display-labels')
        saved_labels = dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_display_manifest'))
        display_version = DISPLAY.fingerprint()
        for promotion in inventory.values():
            graph = promotion['authoritativeGraph']
            if graph not in expected: continue
            identity = digest([promotion['authoritativeRdfSha256'],display_version])
            if saved_labels.get(graph) == identity: continue
            label_query = DISPLAY.query(graph)
            labels = cache.query(endpoint=args.endpoint, query=label_query, slot='metric-display', promotion=promotion,
                fetch=lambda: SOURCE.sparql(args.endpoint,label_query,args.timeout))['results']['bindings']
            DISPLAY.store(connection,graph,identity,labels)
        coverage = SOURCE._schedule_qualification.merge_snapshots(state, SOURCE._batting_admission.schedule_coverage(state))
        coverage_sha = digest(coverage)
        prior_coverage = connection.execute("SELECT value FROM dashboard_state WHERE name='schedule'").fetchone()
        with connection:
            if not prior_coverage or prior_coverage[0] != coverage_sha:
                dirty.update(r[0] for r in connection.execute('SELECT DISTINCT season FROM game_dimension'))
                connection.execute('DELETE FROM metric_suite_schedule_coverage')
                for day, proof in coverage.items():
                    text = METRICS._json(proof)
                    connection.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)', (day,text,METRICS._hash(text)))
                connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)', ('schedule',coverage_sha))
            dirty.update(json.loads(connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()[0]))
            checkpoint(phase='reference-ranks', affectedSeasons=sorted(dirty))
            reference_version = REFERENCES.fingerprint()
            prepared = connection.execute("SELECT value FROM dashboard_state WHERE name='reference-version'").fetchone()
            if not prepared or prepared[0] != reference_version:
                dirty.update(r[0] for r in connection.execute('SELECT DISTINCT season FROM game_dimension'))
            references = REFERENCES.prepare(METRICS,connection,seasons=dirty,checkpoint=checkpoint)
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('reference-version',reference_version))
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)', ('dirty-seasons','[]'))
        input_set = digest(dict(games=expected, coverage=coverage_sha, calculation=calculation))
        checkpoint(phase='publication')
        if dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_checkpoint')) != expected:
            raise ValueError('Dashboard checkpoints do not match the selected source snapshot')
        if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Dashboard SQL integrity failed')
        # Existing final source check remains at publication, never on HTTP.
        final_snapshot = SOURCE.corpus_snapshot(state, args.endpoint, args.timeout, args.max_games)
        if final_snapshot['fingerprint'] != snapshot['fingerprint']:
            checkpoint(status='waiting-for-source', reason='Source changed; committed games retained for the next NiFi tick')
            return progress
        with connection:
            connection.execute('INSERT OR REPLACE INTO dashboard_build VALUES (1,?,?,?,?)',
                               (build_id,snapshot['fingerprint'],input_set,'validated'))
        # The older report builder's retention job cannot touch this product.
        (work/'builds').mkdir(exist_ok=True)
        published = work/'builds'/(build_id+'.sqlite')
        with closing(sqlite3.connect(published)) as destination: connection.backup(destination)
        sha = SOURCE.sha256_file(published)
        SOURCE._reader.write_database_verification_cache(
            SOURCE._reader.database_verification_cache_path(serving,sha), sha, published, SOURCE._reader.file_identity(published))
        pointer = dict(artifactType='baseballo-dashboard-serving-pointer', contractVersion=1, buildId=build_id,
                       databasePath=str(published), databaseSha256=sha, corpusFingerprint=snapshot['fingerprint'],
                       inputSetSha256=input_set, metricSuiteSha256=METRICS.fingerprint(), schemaSha256=SOURCE.sha256_file(SCHEMA),
                       runtimeRelease=RELEASE.own_descriptor(ROOT), notificationKey=notification,
                       gameCount=len(expected), promotedAtUtc=datetime.now(timezone.utc).isoformat())
        if args.max_games or args.no_promote:
            checkpoint(status='ready-for-promotion', databasePath=str(published))
        else:
            RELEASE.atomic(pointer_path,pointer)
            checkpoint(status='published', databasePath=str(published))
            retain_snapshots(published.parent,published)
        evidence = dict(progress, durationSeconds=round(time.perf_counter()-started,2), queryCache=cache.stats,
                        metricProductCache=products.stats, references=references, pointer=pointer)
        RELEASE.atomic(serving/'evidence'/(build_id+'.json'), evidence)
        return evidence
    except SOURCE.SourceSnapshotChanged as error:
        checkpoint(status='waiting-for-source',reason=str(error))
        return progress
    except Exception as error:
        checkpoint(status='failed', error=str(error))
        raise
    finally:
        if connection is not None: connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,default=Path(os.environ.get('BASEBALLO_STATE_ROOT') or Path(os.environ.get('LOCALAPPDATA','.'))/'BaseballO/state'))
    parser.add_argument('--endpoint',default='http://127.0.0.1:3031/baseball-dev/query')
    parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--workers',type=int,choices=(1,2),default=2)
    parser.add_argument('--quiet-seconds',type=int,default=60)
    parser.add_argument('--max-games',type=int)
    parser.add_argument('--no-promote',action='store_true')
    parser.add_argument('--force',action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args))); return 0
    except BlockingIOError:
        print(json.dumps(dict(status='already-running'))); return 0
    except Exception as error:
        print(json.dumps(dict(status='failed',error=str(error)))); return 1


if __name__ == '__main__': raise SystemExit(main())
