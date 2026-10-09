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
from functools import lru_cache
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
    # Existing NiFi commands gain the launch budget without interrupting a
    # running immutable release or waiting to reconfigure a busy processor.
    if (not RELEASE.own_descriptor(ROOT) and os.environ.get('BASEBALLO_SERVING_BUDGET_HELD')!='1'
            and not any(arg in {'-h','--help'} for arg in sys.argv[1:])):
        budget=module(ROOT/'scripts/infra/serving-budget.py','dashboard_launch_budget')
        raise SystemExit(budget.main(['--kind','dashboard',*sys.argv[1:]]))
    result = RELEASE.dispatch(ROOT, sys.argv[1:], mode='dashboard-build')
    if result is not None: raise SystemExit(result)

# Reuse the existing source-neutral inventory, source snapshot and admission
# adapters. The legacy builder's report queries and build() are never invoked.
SOURCE = module(ROOT/'scripts/pipeline/materialize-serving-layer.py', 'dashboard_source')
METRICS = SOURCE._metric_suite
DISPLAY = module(ROOT/'serving/dashboard_display.py', 'dashboard_display')
REFERENCES = module(ROOT/'serving/reference_products.py', 'dashboard_references')
PLAYER_RANGES = module(ROOT/'serving/player_ranges.py', 'dashboard_player_ranges')
ADMISSION_EVIDENCE = module(ROOT/'sources/mlb-game/pipeline/admission-evidence.py','dashboard_admission_evidence')
ADMISSION_HASHES = module(ROOT/'scripts/pipeline/game_promotion_inventory.py','dashboard_admission_hashes')
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
# The sole difference between these calculation versions is graph_datetime's
# support for Jena's shortened fractional seconds. Reuse unchanged game kernels
# only for this exact transition, with the same RDF, dimensions and proof inputs.
TIMESTAMP_CALCULATIONS = (
    'dccb2f1c60283f97469b7422ed1bd1f929ad326afcb22c33fee655ea027881b4',
    # Committed release bytes, not the working checkout's CRLF JSON copy.
    'c96e60528d720d6f245e01f88d0d2f5ded460599f049218948aa789d2f89d79b',
)
# Only the optional independently admitted PA entry point changed. Existing
# default game calculations are identical and must not rerun on deployment.
PLAYER_CALCULATIONS = (TIMESTAMP_CALCULATIONS[1],
    '46c59a0a572d58e69234dc3a832942a008ea3d00c15c0b0b051c7445d43a3e06')
# Q3/Q4 change only compound double-play inputs. Other game calculations and
# player partitions retain their existing evidence and exact stored results.
SHARED_OUT_CALCULATIONS = (PLAYER_CALCULATIONS[1], '98fe6a74abb52e6eb0dc7c3ffc71310509e4e7073b4c6efb06570d0e4c6cc79b')
ACT_COUNT_CALCULATIONS = (SHARED_OUT_CALCULATIONS[1], '542a6133d48d645d4e9685c000a2cc27cb30b4bd64f90640849178a621af4574')
SCOPED_PA_CALCULATIONS = (ACT_COUNT_CALCULATIONS[1], '385aa5ba8560e6ce86930e3602781902aca05a8f1302d0e072bc49f4c87d9d38')
PAQ_CATALOG_CALCULATIONS = (SCOPED_PA_CALCULATIONS[1], '10fc6c16e069b23b3b8fdb7cd1f1f33c9b0ab033d84d0be311f378ce36e3f3e9')
RUN_DEPTH_CALCULATIONS = (PAQ_CATALOG_CALCULATIONS[1], 'a97a7871f7704362049017cd0b0fc33e49d6064c89164a9060bdb4c04b2f95b5')
# The new optional individual-B1 route is used during reference preparation.
# Unchanged whole-game inputs still produce exactly the same game products.
INDIVIDUAL_REFERENCE_CALCULATIONS = (RUN_DEPTH_CALCULATIONS[1], '5f14bb675ca6c2aff0bf4bc60febb457c7b2de6a0509d61f1d8868ddb1d999fe')
# Extraction preserves unmeasured instants and correlates strike records to
# their pitch. Requery only games whose old bindings can differ; all other
# calculations and source proofs remain usable under this exact transition.
PARTIAL_TIME_CALCULATIONS = (INDIVIDUAL_REFERENCE_CALCULATIONS[1],
    'f1a36f7bba6e6be432cb6cc1e12fc09b5341ccba2d03aea433d40de6790b0199')
# BK1 adds structured facts only through additive promotions, which change the
# RDF identity. Unchanged graphs cannot acquire those joins from this code edit.
BALK_CALCULATIONS = (PARTIAL_TIME_CALCULATIONS[1],
    'f606cc7500e19a57487428d8fd8096d54345da365550ebdbb83cc3ad9273e7f7')
EMPTY_CERTAINTY_CALCULATIONS = (BALK_CALCULATIONS[1],
    'b5f7a7f7c269bfa131e6c9ddbbee22c0f70dffa04f650bb9a9ded34c132809ae')
SAFE_PREFIX_CALCULATIONS = (EMPTY_CERTAINTY_CALCULATIONS[1],
    'd4f3e6bff8f9e37ee53231db51a3c150446b85e4849074ae4d4273cbbd3c57ed')
# Keep a supported player's binary Empty Game answer independent of another
# runner's unresolved path. Refresh only retained progress inputs that can differ.
ISOLATED_PROGRESS_CALCULATIONS = (SAFE_PREFIX_CALCULATIONS[1],
    '67e3ead06fac32cdc31b7297881d24384ae5d86a4cbfecf239f58ba975478a09',
    '9b12fdc366c9e2961a652d86a657c7f68ccbf9bc213f1ff5cb709f01adafd8bc',
    'c63db0e59d19bd4901498bbf6ab3c5fab9c3a57735ca99dc10ca4e3b424e1dc3',
    'f9b93e1bc83fe404dda63f3c9759d4cb0f51b97ce69f384f5787d45192324d0e')


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


def query_game_snapshot(state,promotion,fetch):
    """Read one captured promotion while excluding its source-owned writer.

    Windows' existing NiFi FileShare.None game lock excludes a writer for the
    lifetime of this read handle, including a cached answer. Do not query an
    uncommitted graph or label a newer game with the captured version's hash.
    Other games can continue ingesting and already read products stay usable.
    """
    pk=promotion['gamePk']
    if not isinstance(pk,str) or not pk.isdecimal():raise ValueError('Invalid snapshot game')
    owner=Path(state)/'pipeline/evidence/nifi/game-promotion'/pk
    marker=Path(promotion['promotionManifest'])
    if marker.resolve().parent!=owner.resolve():raise ValueError('Snapshot promotion escaped its owner')
    lock=Path(state)/'pipeline/work/mlb-game-locks'/(pk+'.lock')
    lock.parent.mkdir(parents=True,exist_ok=True)
    try:handle=lock.open('a+b')
    except OSError as error:
        raise SOURCE.SourceSnapshotChanged('Game writer is active: '+pk) from error
    with handle:
        def current():
            latest=max(owner.glob('*.json'),key=lambda p:(RELEASE.read(p).get('promotedAtUtc',''),p.name))
            if latest.resolve()!=marker.resolve() or SOURCE.sha256_file(marker)!=promotion['promotionManifestSha256']:
                raise SOURCE.SourceSnapshotChanged('Captured game changed before its SQL read: '+pk)
            transactions=Path(state)/'pipeline/work/graph-pair-transactions'/pk
            if any(RELEASE.read(p).get('state')=='prepared' for p in transactions.glob('*/transaction.json')):
                raise SOURCE.SourceSnapshotChanged('Game has an unfinished graph transaction: '+pk)
        current()
        result=fetch()
        current()
        return result


def refresh_changed_game(state,item,*,endpoint,timeout,metadata,calculation,fetch):
    """Recapture only a changed game, including its proofs and display rows.

    The same source writer fence protects all reads. A new promotion never
    inherits the old promotion's dimensions, admissions or calculation hash.
    """
    pk=item['promotion']['gamePk']
    owner=Path(state)/'pipeline/evidence/nifi/game-promotion'/pk
    for attempt in range(2):
        marker=max(owner.glob('*.json'),key=lambda p:(RELEASE.read(p).get('promotedAtUtc',''),p.name))
        promotion=SOURCE.validated_promotion_record(state,marker,pk,SOURCE.query_index_contract_admission())
        if promotion['authoritativeGraph']!=item['graph']:raise ValueError('Refreshed game graph identity changed')
        def read():
            live=SOURCE.live_graph_state(endpoint,timeout,dict(games={pk:promotion}))
            if len(live['dimensions'])!=1:raise ValueError('Refreshed game lacks one complete dimension')
            with admission_versions(),admission_reads():
                admissions={name:ADMISSION_EVIDENCE.load(adapter,state,promotion,name.removesuffix('_admission').replace('_','-'))
                            for name,adapter in ADMISSIONS.items()}
                player=ADMISSION_EVIDENCE.player_admission(state,promotion)
            values=dimension_values(live['dimensions'][0],promotion,metadata)
            updated=dict(item,promotion=promotion,dimension=values,admissions=admissions,
                         identity=input_identity(promotion,values,admissions,calculation))
            return updated,fetch(updated),player
        try:return query_game_snapshot(state,promotion,read)
        except SOURCE.SourceSnapshotChanged:
            if attempt:raise


def graph_tables(connection):
    names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return [name for name in names if name.startswith('metric_suite_')
            and 'graph_iri' in {r[1] for r in connection.execute(f'PRAGMA table_info("{name}")')}]


def remove_game(connection, graph):
    # Keep the dimension until child-row triggers have invalidated its ranks.
    DISPLAY.remove(connection, graph)
    for table in ('dashboard_player_metric','dashboard_player_game','dashboard_player_admission','dashboard_player_partition'):
        connection.execute(f'DELETE FROM {table} WHERE graph_iri=?',(graph,))
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


@contextmanager
def admission_reads():
    """Reuse unchanged evidence bytes within one game's admission reads.

    Every caller retains its original hash/identity/conformance checks. Cache
    misses open and check the file on both sides of the read; hits check its
    current file identity. JSON bytes remain local to this context. Immutable
    SHACL artifact hashes use the existing persistent file-identity cache.
    """
    originals=ADMISSION_EVIDENCE.sha,ADMISSION_EVIDENCE.read
    cached={};used=0
    def identity(stat):
        return (stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
    def contents(path):
        nonlocal used
        path=Path(path);before=identity(path.stat());entry=cached.get(path)
        if entry is not None and entry[0]==before:return entry[1:]
        with path.open('rb') as source:
            if identity(os.fstat(source.fileno()))!=before:
                raise ValueError('Admission artifact changed while opening: '+str(path))
            raw=source.read()
            if identity(os.fstat(source.fileno()))!=before or identity(path.stat())!=before:
                raise ValueError('Admission artifact changed while reading: '+str(path))
        value=(raw,hashlib.sha256(raw).hexdigest())
        if entry is not None:used-=len(entry[1]);del cached[path]
        if used+len(raw)<=32*1024*1024 and len(cached)<128:
            cached[path]=(before,*value);used+=len(raw)
        return value
    # SHACL reports and shapes are immutable evidence files, never JSON reads.
    # Reuse the inventory's existing identity-checked hash cache across builds;
    # every original proof still compares its expected digest with that result.
    ADMISSION_EVIDENCE.sha=lambda path: (ADMISSION_HASHES.sha256_file(Path(path))
        if Path(path).suffix=='.ttl' else contents(path)[1])
    # Decode afresh so a caller cannot mutate another reader's JSON object.
    ADMISSION_EVIDENCE.read=lambda path:json.loads(contents(path)[0].decode('utf-8-sig'))
    try:yield
    finally:ADMISSION_EVIDENCE.sha,ADMISSION_EVIDENCE.read=originals


@contextmanager
def admission_versions():
    """Hash shared producer code once on each side of the input-reading batch.

    Every game's own proof/artifact checks still execute. NiFi already runs
    an immutable release; thousands of repeated opens of identical code files
    add no distinct input. Restore the functions before verifying or returning.
    """
    originals=[(adapter,adapter.fingerprint) for adapter in
               [*ADMISSIONS.values(),ADMISSION_EVIDENCE.RETAINED_BATTING,ADMISSION_EVIDENCE.PLAYER_PARTICIPATION,
                ADMISSION_EVIDENCE.PA_RESOLUTION]]
    versions=[function() for _,function in originals]
    equivalence=ADMISSION_EVIDENCE.code_equivalence
    compatibility=ADMISSION_EVIDENCE.sha(ADMISSION_EVIDENCE.COMPATIBILITY_PATH)
    ADMISSION_EVIDENCE.code_equivalence=lru_cache(maxsize=None)(equivalence)
    for (adapter,_),version in zip(originals,versions):
        adapter.fingerprint=lambda value=version:value
    try:yield
    finally:
        for adapter,function in originals:adapter.fingerprint=function
        ADMISSION_EVIDENCE.code_equivalence=equivalence
    if (any(function()!=version for (_,function),version in zip(originals,versions))
            or ADMISSION_EVIDENCE.sha(ADMISSION_EVIDENCE.COMPATIBILITY_PATH)!=compatibility):
        raise ValueError('Admission producer code changed during the dashboard input batch')


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
    timestamp_update=False;act_count_update=False;catalog_update=False;depth_update=False;progress_update=False
    if saved not in {previous_identity,input_identity(promotion,dimension,previous,calculation,legacy=True)}:
        compatible=[]
        if calculation in ISOLATED_PROGRESS_CALCULATIONS[1:]:
            compatible.extend((previous,False) for previous in
                ISOLATED_PROGRESS_CALCULATIONS[:ISOLATED_PROGRESS_CALCULATIONS.index(calculation)])
        if calculation in {SAFE_PREFIX_CALCULATIONS[1],*ISOLATED_PROGRESS_CALCULATIONS[1:]}:
            compatible.append((SAFE_PREFIX_CALCULATIONS[0],False))
        if calculation in {EMPTY_CERTAINTY_CALCULATIONS[1],SAFE_PREFIX_CALCULATIONS[1],*ISOLATED_PROGRESS_CALCULATIONS[1:]}:
            compatible.append((EMPTY_CERTAINTY_CALCULATIONS[0],False))
        if calculation in {BALK_CALCULATIONS[1],EMPTY_CERTAINTY_CALCULATIONS[1],SAFE_PREFIX_CALCULATIONS[1],*ISOLATED_PROGRESS_CALCULATIONS[1:]}:
            compatible.append((BALK_CALCULATIONS[0],False))
        if calculation in {PARTIAL_TIME_CALCULATIONS[1],BALK_CALCULATIONS[1],EMPTY_CERTAINTY_CALCULATIONS[1],SAFE_PREFIX_CALCULATIONS[1],*ISOLATED_PROGRESS_CALCULATIONS[1:]}:
            if not partial_time_bindings(connection,graph):
                compatible.append((PARTIAL_TIME_CALCULATIONS[0],False))
        if calculation==INDIVIDUAL_REFERENCE_CALCULATIONS[1]:
            compatible.append((INDIVIDUAL_REFERENCE_CALCULATIONS[0],False))
        if calculation==RUN_DEPTH_CALCULATIONS[1]:
            compatible.append((RUN_DEPTH_CALCULATIONS[0],False))
        if calculation==PAQ_CATALOG_CALCULATIONS[1]:
            compatible.append((PAQ_CATALOG_CALCULATIONS[0],False))
        if calculation in {SCOPED_PA_CALCULATIONS[1],PAQ_CATALOG_CALCULATIONS[1]}:
            compatible.append((SCOPED_PA_CALCULATIONS[0],False))
        if calculation in {ACT_COUNT_CALCULATIONS[1],SCOPED_PA_CALCULATIONS[1],PAQ_CATALOG_CALCULATIONS[1]}:
            compatible.append((ACT_COUNT_CALCULATIONS[0],False))
        if calculation in {SHARED_OUT_CALCULATIONS[1],ACT_COUNT_CALCULATIONS[1],SCOPED_PA_CALCULATIONS[1],PAQ_CATALOG_CALCULATIONS[1]}:
            compound=connection.execute("""SELECT 1 FROM metric_suite_scope_fact
                WHERE graph_iri=? AND kind='plate_appearance'
                AND json_extract(record_json,'$.paResultType')='https://baseballontology.org/DoublePlayProcess'
                LIMIT 1""",(graph,)).fetchone()
            if not compound:
                compatible.extend(((SHARED_OUT_CALCULATIONS[0],False),(PLAYER_CALCULATIONS[0],False),
                                   (TIMESTAMP_CALCULATIONS[0],True)))
        if calculation in {TIMESTAMP_CALCULATIONS[1],PLAYER_CALCULATIONS[1]}:
            compatible.append((TIMESTAMP_CALCULATIONS[0],True))
        if calculation==PLAYER_CALCULATIONS[1]:compatible.append((PLAYER_CALCULATIONS[0],False))
        matched=next(((old,timestamp) for old,timestamp in compatible if saved in {
            input_identity(promotion,dimension,previous,old),
            input_identity(promotion,dimension,previous,old,legacy=True)}),None)
        if matched is None:return False
        timestamp_update=matched[1]
        act_count_update=(calculation in {ACT_COUNT_CALCULATIONS[1],SCOPED_PA_CALCULATIONS[1],PAQ_CATALOG_CALCULATIONS[1]}
                          and matched[0] not in {ACT_COUNT_CALCULATIONS[1],SCOPED_PA_CALCULATIONS[1]})
        catalog_update=calculation==PAQ_CATALOG_CALCULATIONS[1]
        depth_update=calculation==RUN_DEPTH_CALCULATIONS[1]
        progress_update=calculation in {EMPTY_CERTAINTY_CALCULATIONS[1],SAFE_PREFIX_CALCULATIONS[1],*ISOLATED_PROGRESS_CALCULATIONS[1:]}
    changed=previous_identity!=identity
    if changed or timestamp_update or act_count_update:
        refresh_admission_inputs(connection,graph,previous,admissions,
            timestamp_update=timestamp_update,act_count_update=act_count_update)
        mark_dirty(connection,{dimension[5]})
    if catalog_update:
        # This catalog correction removes one obsolete prerequisite, without
        # changing scores or evidence. Preserve the already prepared PAQ input.
        result,=METRICS.read_results(connection,graph,'paq-2.1')
        if 'DEFENSIVE_ORDER' in result.get('gaps',[]):
            result['gaps']=[gap for gap in result['gaps'] if gap!='DEFENSIVE_ORDER']
            METRICS.store_result(connection,graph,'paq-2.1','game-scope',result)
            mark_dirty(connection,{dimension[5]})
    depth_changed=depth_update and refresh_run_depth(connection,graph)
    if depth_changed:mark_dirty(connection,{dimension[5]})
    progress_changed=progress_update and refresh_empty_certainty(connection,graph)
    if progress_changed:mark_dirty(connection,{dimension[5]})
    for name,table in ADMISSION_TABLES.items():
        if previous[name]==admissions[name]:continue
        text=METRICS._json(admissions[name])
        connection.execute(f'UPDATE {table} SET proof_json=?,proof_sha256=? WHERE graph_iri=?',
                           (text,METRICS._hash(text),graph))
    if saved!=identity:
        # Carry a verified player partition across a no-op game-version change.
        # Its own producer/proof identities still determine whether it needs work.
        if not changed and not timestamp_update and not act_count_update and not depth_changed and not progress_changed:
            partition=connection.execute('SELECT input_sha256 FROM dashboard_player_partition WHERE graph_iri=?',(graph,)).fetchone()
            individual=connection.execute('SELECT proof_sha256 FROM dashboard_player_admission WHERE graph_iri=?',(graph,)).fetchone()
            proof_sha=individual[0] if individual else ''
            for version in (PLAYER_RANGES.fingerprint(),PLAYER_RANGES.PREVIOUS_AMBIGUOUS_ERROR_VERSION,
                            PLAYER_RANGES.PREVIOUS_AMBIGUOUS_OUT_VERSION,
                            PLAYER_RANGES.PREVIOUS_EMPTY_SCOPE_VERSION,
                            PLAYER_RANGES.PREVIOUS_EMPTY_CACHE_VERSION,
                            PLAYER_RANGES.PREVIOUS_EMPTY_ELIGIBILITY_VERSION,PLAYER_RANGES.PREVIOUS_AMBIGUOUS_PROGRESS_VERSION,
                            PLAYER_RANGES.PREVIOUS_VERSION,
                            PLAYER_RANGES.PREVIOUS_INDIVIDUAL_VERSION,PLAYER_RANGES.PREVIOUS_BOUNDARY_VERSION,
                            PLAYER_RANGES.PREVIOUS_DAMAGE_VERSION,PLAYER_RANGES.PREVIOUS_ZERO_PA_VERSION,
                            PLAYER_RANGES.PREVIOUS_RESOLUTION_VERSION,PLAYER_RANGES.PREVIOUS_SCOPED_RESOLUTION_VERSION,
                            PLAYER_RANGES.PREVIOUS_SHARED_OUT_VERSION,PLAYER_RANGES.PREVIOUS_PA_CONTRIBUTION_VERSION):
                if partition and partition[0]==METRICS._hash(saved+version+proof_sha):
                    connection.execute('UPDATE dashboard_player_partition SET input_sha256=? WHERE graph_iri=?',
                        (METRICS._hash(identity+version+proof_sha),graph))
                    break
        connection.execute('UPDATE dashboard_checkpoint SET input_sha256=? WHERE graph_iri=?',(identity,graph))
    return 'calculations' if timestamp_update or act_count_update or depth_changed or progress_changed else 'admissions' if changed else 'unchanged'


def refresh_empty_certainty(connection,graph):
    """Repair only retained progress inputs; no graph query or source rerun."""
    result,=METRICS.read_results(connection,graph,'empty-game-rate')
    previous=result['progressInputs']
    if not (any(set(p.get('gaps',[])) & {'UNRESOLVED_PROGRESS_ATTRIBUTION','COMPLETE_CONSEQUENCE_COALESCENCE'}
                for p in previous.get('unresolvedPlateAppearances',[]))
            or any(p.get('independentPositiveGaps') for p in previous.get('plateAppearances',[]))):return False
    rows=[METRICS._blocks.decode(METRICS._block_api(),text,sha) for text,sha in connection.execute(
        'SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,))]
    proof=json.loads(connection.execute('SELECT proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()[0])
    if len(rows)!=proof['evidenceRows']:raise ValueError('Stored dashboard evidence is incomplete')
    rows.sort(key=METRICS._json)
    current=METRICS.batting_progress_evidence(rows)
    if current==previous:return False
    METRICS.store_result(connection,graph,'empty-game-rate','game-scope',dict(result,progressInputs=current))
    return True


def partial_time_bindings(connection,graph):
    """Locate candidates for the extraction correction, not missing RDF.

    This reads retained bindings once during the exact version upgrade. A
    candidate goes through the normal graph-locked SPARQL stage. Neither an
    instant nor its measurement is synthesized from an identifier here.
    """
    return connection.execute('''SELECT 1 FROM metric_suite_evidence WHERE graph_iri=? AND (
        (json_extract(binding_json,'$.kind')='plate_appearance'
         AND json_type(binding_json,'$.paInterval') IS NOT NULL
         AND (json_type(binding_json,'$.paStartInstant') IS NULL OR json_type(binding_json,'$.paEndInstant') IS NULL))
        OR (json_extract(binding_json,'$.kind')='pitch_count' AND (
            json_type(binding_json,'$.pitchStartInstant') IS NULL
            OR json_type(binding_json,'$.pitchEndInstant') IS NULL
            OR json_type(binding_json,'$.record') IS NULL
            OR json_extract(binding_json,'$.record') !=
               replace(json_extract(binding_json,'$.entity'),'/pitch/','/event-record/pitch/')))
        ) LIMIT 1''',(graph,)).fetchone() is not None


def refresh_run_depth(connection,graph):
    """Recalculate only the old duplicate-batter failures from retained SQL.

    Other metrics, successful run histories and unaffected games retain their
    results. This upgrade requires neither SPARQL nor an RDF/source refresh.
    """
    previous,=METRICS.read_results(connection,graph,'run-construction-depth')
    if not any('CONFLICTING_SEGMENT_STATE' in r.get('gaps',[]) for r in previous.get('unresolvedRuns',[])):
        return False
    rows=[]
    for text,sha in connection.execute('SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,)):
        if METRICS._hash(text)!=sha:raise ValueError('Stored dashboard evidence changed')
        rows.append(json.loads(text))
    proof=json.loads(connection.execute('SELECT proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()[0])
    if len(rows)!=proof['evidenceRows']:raise ValueError('Stored dashboard evidence is incomplete')
    rows.sort(key=METRICS._json)
    result=METRICS.live_result('run-construction-depth',rows,graph_count=1)
    if result==previous:return False
    METRICS.store_result(connection,graph,'run-construction-depth','game-scope',result)
    return True


def mark_dirty(connection, seasons):
    row=connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()
    seasons=set(seasons)|set(json.loads(row[0]) if row else [])
    connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',
                       ('dirty-seasons',json.dumps(sorted(seasons))))


def refresh_admission_inputs(connection, graph, previous, admissions, *, timestamp_update=False,act_count_update=False):
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
    if timestamp_update:affected.update({'tfs','recovery-quality'})
    if act_count_update:affected.add('resolution-depth')
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
        result=dict(retained[metric],**{key:product})
        if act_count_update and metric in {'resolution-depth','paq-2.1'}:
            result=dict(METRICS.live_result(metric,rows,graph_count=1),**{key:product})
        if timestamp_update and metric=='tfs':
            boundaries=METRICS.runner_boundary_states(rows)
            result['runnerBoundaryStates']=boundaries['states']
            result['coverage']=dict(result['coverage'],runnerBoundaryProjection=boundaries['coverage'])
        if retained[metric]==result:continue
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


def refresh_pending_rosters(connection,state,items,calculation,expected,player_admissions):
    """Pick up checks completed after this game's first input read.

    A targeted graph addition and its independent roster check finish at
    different times. Reread only those missing checks against the same captured
    promotion; ordinary incremental reuse updates their dependent SQL products.
    """
    updated=[]
    with admission_versions():
        for item in items:
            graph=item['graph'];promotion=item['promotion']
            with admission_reads():
                admissions={name:ADMISSION_EVIDENCE.load(adapter,state,promotion,
                    name.removesuffix('_admission').replace('_','-')) for name,adapter in ADMISSIONS.items()}
                individual=ADMISSION_EVIDENCE.player_admission(state,promotion)
            identity=input_identity(promotion,item['dimension'],admissions,calculation)
            if identity==expected[graph] and individual==player_admissions[graph]:continue
            with connection:
                if not reuse_game(connection,graph,expected[graph],promotion,item['dimension'],admissions,calculation):
                    raise ValueError('Captured roster refresh does not match the stored game: '+graph)
            expected[graph]=identity;player_admissions[graph]=individual;updated.append(graph)
    return updated


def default_roster_gaps(connection):
    """Read the same roster coverage used by the prepared default season."""
    return [r[0] for r in connection.execute("SELECT g.graph_iri FROM game_dimension g "
        "LEFT JOIN dashboard_player_game p USING(graph_iri) WHERE g.game_set='regular_season' "
        "AND g.season=(SELECT MAX(season) FROM game_dimension WHERE game_set='regular_season') "
        'GROUP BY g.graph_iri HAVING MAX(COALESCE(p.roster_complete,0))=0 ORDER BY g.graph_iri')]


READER_EXCLUDED_TABLES=frozenset({
    'metric_suite_evidence','metric_suite_result','metric_suite_scope_fact',
    'metric_suite_block_manifest','metric_suite_input_row','metric_suite_input_state',
    'metric_suite_shell','metric_suite_reference_rank','metric_suite_reference','dashboard_reference'})


def publish_snapshot(database, published, checkpoint=None):
    """Copy prepared reader products; keep rebuild inputs in the working DB.

    The dashboard now reads prepared player/game and reference-player products.
    Intermediate observations, game kernels and PA ranks belong to the builder.
    Omit those tables so an accidental calculation fallback fails explicitly.
    The writer lock remains held and all working transactions are committed.
    """
    excluded=READER_EXCLUDED_TABLES
    with closing(sqlite3.connect(published,uri=True)) as destination:
        destination.execute('PRAGMA foreign_keys=ON')
        destination.execute('ATTACH DATABASE ? AS prepared_source',(Path(database).as_uri()+'?mode=ro',))
        with destination:
            destination.execute('BEGIN')
            schema=destination.execute("SELECT type,name,tbl_name,sql FROM prepared_source.sqlite_schema "
                "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
            tables=sorted(((name,sql) for kind,name,owner,sql in schema if kind=='table' and name not in excluded),
                key=lambda t:(t[0] not in {'game_dimension','metric_suite_reference'},t[0]))
            for name,sql in tables:destination.execute(sql)
            for name,_ in tables:
                if checkpoint:checkpoint(publicationStep='copy-table',publicationTable=name)
                quoted='"'+name.replace('"','""')+'"'
                destination.execute(f'INSERT INTO main.{quoted} SELECT * FROM prepared_source.{quoted}')
            if checkpoint:checkpoint(publicationStep='copy-indexes',publicationTable=None)
            for kind,name,owner,sql in schema:
                if kind=='index' and owner not in excluded:destination.execute(sql)
            # Cover the first-pass range completeness scan without visiting
            # aggregate JSON pages for players who will be excluded anyway.
            destination.execute('CREATE INDEX IF NOT EXISTS dashboard_player_metric_coverage '
                'ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
            # Mutation triggers belong to the mutable producer. This publication
            # is always opened mode=ro and is never used as a build checkpoint.
        if checkpoint:checkpoint(publicationStep='snapshot-integrity')
        # Unqualified quick_check also scans the attached working database,
        # including the large intermediate tables deliberately omitted above.
        if destination.execute('PRAGMA main.quick_check').fetchone()[0]!='ok' or destination.execute('PRAGMA main.foreign_key_check').fetchall():
            raise ValueError('Prepared dashboard snapshot integrity failed')
        working_bytes=(destination.execute('PRAGMA prepared_source.page_count').fetchone()[0]
            *destination.execute('PRAGMA prepared_source.page_size').fetchone()[0])
    return dict(layout='prepared-reader-products-v2',retainedBuildOnlyTables=sorted(excluded),
        workingBytes=working_bytes,publishedBytes=Path(published).stat().st_size)


def notification_key(state):
    """Cheap event check only; changed inputs still undergo the existing snapshot."""
    excluded=SOURCE._work_scope.excluded_games(state)
    # Continuous admission maintenance is an update signal, not graph churn.
    # Including it in the quiet window can postpone publication indefinitely.
    source_paths = list((state/'pipeline/evidence/nifi/game-promotion').glob('*/*.json'))
    source_paths += list((state/'pipeline/control/mlb-game/schedule-coverage').glob('*.json'))
    paths = source_paths + list((state/'pipeline/control/mlb-game/batches').glob('*.json'))
    paths += list((state/'pipeline/evidence/mlb-game').glob('*/admission-refresh/*/*.receipt.json'))
    source_paths=[p for p in source_paths if p.parent.name not in excluded]
    paths=[p for p in paths if p.parent.name not in excluded
           and not (p.name.endswith('.receipt.json') and p.parents[2].name in excluded)]
    files = [(str(p.relative_to(state)), p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(paths)]
    return digest(dict(events=files, workScope=SOURCE.sha256_file(Path(SOURCE._work_scope.__file__)),
                       metrics=METRICS.fingerprint(), builder=SOURCE.sha256_file(Path(__file__)),
                       reader=SOURCE.sha256_file(Path(SOURCE._reader.__file__)),
                       playerRangeQuery=SOURCE.sha256_file(Path(SOURCE._reader._range_query.__file__)),
                       playerRanges=PLAYER_RANGES.fingerprint(),
                       admissionReader=ADMISSION_EVIDENCE.fingerprint(),
                       display=DISPLAY.fingerprint(), references=REFERENCES.fingerprint(),
                       schema=SOURCE.sha256_file(SCHEMA))), max((p.stat().st_mtime_ns for p in source_paths), default=0)


def build(args):
    state = args.state_root.resolve(); serving = state/'serving'; work = serving/'dashboard'
    work.mkdir(parents=True, exist_ok=True)
    if args.max_games:
        # A bounded developer build must not remove full-corpus checkpoints.
        work = work/'development'/str(args.max_games)
        work.mkdir(parents=True, exist_ok=True)
    with writer_lock(work/'writer.lock'), ADMISSION_HASHES.artifact_hash_cache(
            work/('admission-artifact-hashes-'+sys.implementation.cache_tag+'.json'),RELEASE.atomic):
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
        # Reuse the launcher's release check and the reader's database checks.
        # Both halves of the publication must remain readable; no scoring here.
        try:
            RELEASE.resolve_pointer_release(state, old_pointer)
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
        if values.get('phase',progress['phase']) != progress['phase'] or values.get('status') in {'published','unchanged','failed','ready-for-promotion','waiting-for-source'}:
            durations[progress['phase']] = round(durations.get(progress['phase'],0)+time.perf_counter()-phase_started,3)
            phase_started = time.perf_counter()
        progress['phaseSeconds'] = dict(durations)
        progress.update(values, updatedAtUtc=datetime.now(timezone.utc).isoformat())
        RELEASE.atomic(progress_path, progress)
    checkpoint()
    connection = None
    try:
        snapshot = SOURCE.corpus_snapshot(state, args.endpoint, args.timeout, args.max_games)
        checkpoint(sourceSnapshotCapturedAtUtc=datetime.now(timezone.utc).isoformat(),
                   sourceSnapshotPolicy='captured-promotions-with-game-read-locks')
        metadata = SOURCE.official_metadata(state)
        inventory = snapshot['inventory']['games']
        dimensions = snapshot['live']['dimensions']
        schema_key = digest([SCHEMA.read_text(encoding='utf-8'), (ROOT/'serving/metric-suite-schema.sql').read_text(encoding='utf-8')])
        database = work/('working-'+schema_key[:16]+'.sqlite')
        connection = sqlite3.connect(database, timeout=30)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        METRICS.initialize_sql(connection); DISPLAY.initialize(connection); PLAYER_RANGES.initialize(connection)
        # Physical reader index only: existing player/game calculations and
        # their producer fingerprint remain unchanged.
        connection.execute('CREATE INDEX IF NOT EXISTS dashboard_player_metric_by_player '
                           'ON dashboard_player_metric(metric_id,player,graph_iri)')
        connection.execute('CREATE INDEX IF NOT EXISTS dashboard_player_metric_coverage '
                           'ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
        connection.commit()
        calculation = METRICS.calculation_fingerprint()
        cache = SOURCE._query_cache.ServingQueryCache(serving/'query-cache.sqlite')
        products = SOURCE._metric_cache.MetricProductCache(serving/'metric-cache.sqlite', calculation)
        pending = []; expected = {}; unchanged = 0; admission_updates = 0; calculation_updates = 0; player_admissions = {}
        pending_rosters=[]
        old_dimensions = dict(connection.execute('SELECT graph_iri,season FROM game_dimension'))
        saved = dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_checkpoint'))
        checkpoint(phase='input-refresh',totalGames=len(dimensions))
        with admission_versions():
            for index,dimension in enumerate(dimensions,1):
                graph = SOURCE.lexical(dimension, 'graph'); pk = graph.rsplit('/',1)[-1]
                promotion = inventory[pk]
                with admission_reads():
                    admissions = {name: ADMISSION_EVIDENCE.load(adapter,state,promotion,name.removesuffix('_admission').replace('_','-'))
                                  for name, adapter in ADMISSIONS.items()}
                    player_admissions[graph] = ADMISSION_EVIDENCE.player_admission(state,promotion)
                values = dimension_values(dimension, promotion, metadata)
                if (values[6]=='regular_season' and not any(PLAYER_RANGES.admitted(admissions[name])
                        for name in ('batting_admission','scoring_run_admission'))
                        and not (player_admissions[graph] or {}).get('rosterComplete')):
                    pending_rosters.append(dict(graph=graph,promotion=promotion,dimension=values))
                identity = input_identity(promotion, values, admissions, calculation)
                expected[graph] = identity
                with connection:
                    reused=reuse_game(connection,graph,saved.get(graph),promotion,values,admissions,calculation)
                if reused:
                    if reused=='admissions':admission_updates+=1
                    elif reused=='calculations':calculation_updates+=1
                    else:unchanged+=1
                else:
                    pending.append(dict(graph=graph, promotion=promotion, dimension=values, identity=identity,
                                        admissions=admissions, previousSeasons=[old_dimensions[graph]] if graph in old_dimensions else []))
                if index%100==0:checkpoint(inspectedGames=index,completedGames=unchanged+admission_updates+calculation_updates)
        connection.commit()
        removed = set(old_dimensions) - set(expected)
        with connection:
            dirty_row = connection.execute("SELECT value FROM dashboard_state WHERE name='dirty-seasons'").fetchone()
            dirty = set(json.loads(dirty_row[0]) if dirty_row else [])
            for graph in removed:
                dirty.add(old_dimensions[graph]); remove_game(connection, graph)
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)', ('dirty-seasons', json.dumps(sorted(dirty))))
        completed=unchanged+admission_updates+calculation_updates
        checkpoint(phase='game-products', totalGames=len(expected), changedGames=len(pending)+admission_updates+calculation_updates,
                   admissionUpdatedGames=admission_updates,calculationUpdatedGames=calculation_updates,
                   reusedGames=unchanged, completedGames=completed)
        display_version=DISPLAY.fingerprint()
        recaptured={}
        captured_fingerprint=snapshot['fingerprint']
        def answers(item):
            query=METRICS.evidence_query([item['graph']])
            bindings=cache.query(endpoint=args.endpoint,
                query=query,slot='metric-suite-snapshot-v1',promotion=item['promotion'],
                fetch=lambda: SOURCE.sparql(args.endpoint,query,args.timeout))['results']['bindings']
            query=DISPLAY.query(item['graph'])
            labels=cache.query(endpoint=args.endpoint,query=query,slot='metric-display-snapshot-v1',promotion=item['promotion'],
                fetch=lambda:SOURCE.sparql(args.endpoint,query,args.timeout))['results']['bindings']
            return bindings,labels
        def fetch(item):
            try:return query_game_snapshot(state,item['promotion'],lambda:answers(item))
            except SOURCE.SourceSnapshotChanged as error:return error
        def store_answers(item,payload):
            bindings,labels=payload
            store_game(connection,item,bindings,products)
            DISPLAY.store(connection,item['graph'],digest([item['promotion']['authoritativeRdfSha256'],display_version]),labels)
        def recapture(item):
            updated,payload,player=refresh_changed_game(state,item,endpoint=args.endpoint,timeout=args.timeout,
                metadata=metadata,calculation=calculation,fetch=answers)
            graph=updated['graph'];promotion=updated['promotion'];pk=promotion['gamePk']
            inventory[pk]=promotion;expected[graph]=updated['identity'];player_admissions[graph]=player
            recaptured[pk]=promotion['promotionManifestSha256']
            snapshot['fingerprint']=digest(dict(capturedCorpus=captured_fingerprint,recapturedPromotions=recaptured))
            for roster in pending_rosters:
                if roster['graph']==graph:roster.update(promotion=promotion,dimension=updated['dimension'])
            store_answers(updated,payload)
            checkpoint(recapturedGames=sorted(recaptured))
        deferred=[]
        for count, (item, payload) in enumerate(bounded_fetch(pending, fetch, args.workers), 1):
            if isinstance(payload,SOURCE.SourceSnapshotChanged):deferred.append(item);continue
            store_answers(item,payload)
            checkpoint(completedGames=completed+count)
        # Finish independent game reads before revisiting an active writer.
        for item in deferred:recapture(item)
        checkpoint(completedGames=len(expected))
        checkpoint(phase='display-labels')
        saved_labels = dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_display_manifest'))
        for promotion in list(inventory.values()):
            graph = promotion['authoritativeGraph']
            if graph not in expected: continue
            identity = digest([promotion['authoritativeRdfSha256'],display_version])
            if saved_labels.get(graph) == identity: continue
            label_query = DISPLAY.query(graph)
            try:
                labels = query_game_snapshot(state,promotion,lambda:cache.query(endpoint=args.endpoint,
                    query=label_query,slot='metric-display-snapshot-v1',promotion=promotion,
                    fetch=lambda: SOURCE.sparql(args.endpoint,label_query,args.timeout)))['results']['bindings']
                DISPLAY.store(connection,graph,identity,labels)
            except SOURCE.SourceSnapshotChanged:
                recapture(dict(graph=graph,promotion=promotion,previousSeasons=[old_dimensions[graph]] if graph in old_dimensions else []))
        if pending_rosters:
            refreshed_rosters=refresh_pending_rosters(connection,state,pending_rosters,calculation,expected,player_admissions)
            checkpoint(lateRosterAdmissionGames=refreshed_rosters)
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
            # Individual B1 proofs can complete a season reference without
            # changing a whole-game admission or its graph checkpoint.
            saved_players=dict(connection.execute('SELECT graph_iri,proof_sha256 FROM dashboard_player_admission'))
            dirty.update(year for graph,year in connection.execute('SELECT graph_iri,season FROM game_dimension')
                if saved_players.get(graph,'') != (METRICS._hash(METRICS._json(player_admissions[graph]))
                    if player_admissions.get(graph) else ''))
            checkpoint(phase='reference-ranks', affectedSeasons=sorted(dirty))
            reference_version = REFERENCES.fingerprint()
            prepared = connection.execute("SELECT value FROM dashboard_state WHERE name='reference-version'").fetchone()
            if not prepared or prepared[0] != reference_version:
                dirty.update(r[0] for r in connection.execute('SELECT DISTINCT season FROM game_dimension'))
            references = REFERENCES.prepare(METRICS,connection,seasons=dirty,checkpoint=checkpoint,
                player_admissions=player_admissions)
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('reference-version',reference_version))
            connection.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)', ('dirty-seasons','[]'))
        checkpoint(phase='player-ranges')
        player_ranges = PLAYER_RANGES.prepare(METRICS,connection,checkpoint=checkpoint,player_admissions=player_admissions)
        input_set = digest(dict(games=expected, coverage=coverage_sha, calculation=calculation,
                               playerAdmissions={g:dict(players=p.get('proofSha256'),
                                   resolutions=(p.get('paResolutions') or {}).get('proofSha256'))
                                   for g,p in player_admissions.items() if p},
                               playerRanges=PLAYER_RANGES.fingerprint()))
        checkpoint(phase='season-ranges')
        prepared_seasons=SOURCE._reader._range_query.prepare_seasons(METRICS,PLAYER_RANGES,connection,input_set)
        checkpoint(preparedSeasonRanges=prepared_seasons)
        checkpoint(phase='publication',publicationStep='source-check')
        if dict(connection.execute('SELECT graph_iri,input_sha256 FROM dashboard_checkpoint')) != expected:
            raise ValueError('Dashboard checkpoints do not match the selected source snapshot')
        missing_rosters=default_roster_gaps(connection)
        if missing_rosters and old_pointer and not publication_issue:
            # A prior usable publication can legitimately use an older metric
            # implementation. Validate it with its own paired reader.
            prior_root=RELEASE.resolve_pointer_release(state,old_pointer)
            prior_reader=(module(prior_root/'scripts/pipeline/query-serving-layer.py','prior_dashboard_reader')
                          if prior_root else SOURCE._reader)
            with prior_reader.dashboard_database(state,old_pointer) as (previous,_):
                prior_rosters_complete=not default_roster_gaps(previous)
            if prior_rosters_complete:
                checkpoint(status='waiting-for-source',reason='Captured game roster checks are pending',
                           pendingRosterGames=missing_rosters,publicationBuildId=old_pointer['buildId'])
                return progress
        # The prepared snapshot enforces SQL constraints during copying and
        # receives the integrity check below. Do not also scan build-only raw
        # bindings and duplicated results on every small publication update.
        # Every fetched game was fenced against its captured promotion while
        # holding the existing source writer lock. Reused SQL is already bound
        # to those exact inputs. Publish this consistent captured inventory;
        # subsequent promotions trigger the next incremental NiFi build instead
        # of starving publication by invalidating unrelated completed products.
        release = RELEASE.own_descriptor(ROOT)
        if (not args.force and not args.max_games and not args.no_promote and not publication_issue
                and old_pointer.get('inputSetSha256') == input_set
                and old_pointer.get('corpusFingerprint') == snapshot['fingerprint']
                and old_pointer.get('runtimeRelease') == release
                and old_pointer.get('dataRuntimeRelease',old_pointer.get('runtimeRelease')) == release):
            # A new receipt is a reason to inspect inputs, not to copy identical
            # reader products. Keep the original publication identity and time.
            # Exact data/reader release equality also covers reference and
            # display changes outside the game-calculation input set. Attaching
            # a new reader alone does not certify its prepared SQL products.
            try:
                RELEASE.resolve_pointer_release(state, old_pointer)
                with SOURCE._reader.dashboard_database(state, old_pointer): pass
            except (OSError, ValueError, sqlite3.Error) as error:
                checkpoint(previousPublicationIssue=str(error))
            else:
                checkpoint(status='unchanged', publicationStep='retained-publication',
                           publicationBuildId=old_pointer['buildId'])
                RELEASE.atomic(pointer_path, dict(old_pointer, notificationKey=notification))
                return progress
        with connection:
            connection.execute('INSERT OR REPLACE INTO dashboard_build VALUES (1,?,?,?,?)',
                               (build_id,snapshot['fingerprint'],input_set,'validated'))
        # The older report builder's retention job cannot touch this product.
        (work/'builds').mkdir(exist_ok=True)
        published = work/'builds'/(build_id+'.sqlite')
        checkpoint(publicationStep='prepared-snapshot')
        publication=publish_snapshot(database,published,checkpoint)
        checkpoint(publicationStep='snapshot-digest',publication=publication)
        sha = SOURCE.sha256_file(published)
        SOURCE._reader.write_database_verification_cache(
            SOURCE._reader.database_verification_cache_path(serving,sha), sha, published, SOURCE._reader.file_identity(published))
        pointer = dict(artifactType='baseballo-dashboard-serving-pointer', contractVersion=1, buildId=build_id,
                       databasePath=str(published), databaseSha256=sha, corpusFingerprint=snapshot['fingerprint'],
                       inputSetSha256=input_set, metricSuiteSha256=METRICS.fingerprint(), schemaSha256=SOURCE.sha256_file(SCHEMA),
                       runtimeRelease=release, notificationKey=notification,
                       sourceSnapshotCapturedAtUtc=progress['sourceSnapshotCapturedAtUtc'],
                       sourceSnapshotPolicy=progress['sourceSnapshotPolicy'],
                       recapturedPromotions=recaptured,
                       gameCount=len(expected), promotedAtUtc=datetime.now(timezone.utc).isoformat())
        # Save the complete candidate evidence before changing the reader's
        # pointer. A storage failure here must preserve the prior publication.
        checkpoint(status='ready-for-promotion', databasePath=str(published))
        evidence = dict(progress, durationSeconds=round(time.perf_counter()-started,2), publication=publication, queryCache=cache.stats,
                        metricProductCache=products.stats, references=references, playerRanges=player_ranges, pointer=pointer)
        evidence_path = serving/'evidence'/(build_id+'.json')
        RELEASE.atomic(evidence_path, evidence)
        if args.max_games or args.no_promote: return evidence
        RELEASE.atomic(pointer_path,pointer)
        # The atomic pointer is the commit point. Bookkeeping errors cannot
        # undo it or truthfully turn the already readable build into a failure.
        warnings = []
        try: retain_snapshots(published.parent,published)
        except OSError as error: warnings.append('Snapshot retention: '+str(error))
        try: checkpoint(status='published', postPublicationWarnings=warnings)
        except OSError as error: warnings.append('Progress record: '+str(error))
        evidence.update(progress, durationSeconds=round(time.perf_counter()-started,2))
        try: RELEASE.atomic(evidence_path, evidence)
        except OSError as error: warnings.append('Publication evidence status: '+str(error))
        # NiFi receives these warnings even if local status writes are blocked.
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
    # Per-game locks and recapture handle ongoing promotions. A global quiet
    # window starves SQL while the independent repair lanes keep progressing.
    parser.add_argument('--quiet-seconds',type=int,default=0)
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
