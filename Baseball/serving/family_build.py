"""Independent NiFi dashboard publications over one resumable working store.

Each tick handles one family under the existing writer/resource locks. Published
families retain their own immutable snapshot and reader, so partial work or a
failed sibling cannot leak into a previously published result.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def publications(pointer, families):
    if pointer.get('families') is not None:return dict(pointer['families'])
    # The previous combined publication remains readable during migration.
    return {family:dict(pointer) for family in families} if pointer else {}


def composition(published, attempts):
    primary=published.get('offense') or next(iter(published.values()))
    return dict(primary,families=published,familyBuildStatus={family:dict(
        status=value.get('status','running'),attemptedAtUtc=value.get('attemptedAtUtc'))
        for family,value in attempts.items()})


def choose(families, published, attempts, notification, requested, force):
    if requested!='auto':return requested
    pending=[f for f in families if force or published.get(f,{}).get('familyNotificationKey')!=notification]
    ready=[f for f in pending if attempts.get(f,{}).get('notification')!=notification or
           attempts[f].get('attempts',0)<3]
    # Round robin prevents a continuously changing offensive inventory or a
    # repeatedly failing family from starving the other independently ready work.
    return min(ready,key=lambda f:(attempts.get(f,{}).get('attemptedAtUtc',''),list(families).index(f))) if ready else None


def retained_rows(d, db, graph, promotion, dimension, query_sha, calculation):
    m=d.METRICS
    saved=db.execute('SELECT rdf_sha256,query_sha256,row_count FROM dashboard_evidence_checkpoint WHERE graph_iri=?',(graph,)).fetchone()
    if saved is None:
        # Adopt exact retained SQL evidence from a recognized earlier producer.
        # Matching the prior input identity proves RDF, dimensions and proofs;
        # it does not relabel the previous metric calculations as new ones.
        legacy=db.execute('SELECT input_sha256,proof_json FROM dashboard_checkpoint WHERE graph_iri=?',(graph,)).fetchone()
        previous={}
        for name,table in d.ADMISSION_TABLES.items():
            row=db.execute(f'SELECT proof_json,proof_sha256 FROM {table} WHERE graph_iri=?',(graph,)).fetchone()
            if row is None:return None
            previous[name]=m._blocks.decode(m._block_api(),*row)
        # These recent versions changed only the progress reducer. Older
        # versions may have used a different query; let the query cache decide
        # their reuse instead of assigning new extraction provenance to them.
        versions={calculation,*d.ISOLATED_PROGRESS_CALCULATIONS}
        if not legacy or not any(legacy[0]==d.input_identity(promotion,dimension,previous,v,legacy=old)
                                for v in versions for old in (False,True)):return None
        saved=(promotion['authoritativeRdfSha256'],query_sha,json.loads(legacy[1])['evidenceRows'])
    if saved[:2]!=(promotion['authoritativeRdfSha256'],query_sha):return None
    rows=[m._blocks.decode(m._block_api(),text,sha) for text,sha in db.execute(
        'SELECT binding_json,binding_sha256 FROM metric_suite_evidence WHERE graph_iri=?',(graph,))]
    if len(rows)!=saved[2]:raise m.EvidenceError('Retained dashboard evidence is incomplete')
    rows.sort(key=m._json)
    return rows


def retain(d, directory, published):
    active={Path(p['databasePath']).resolve() for p in published.values()}
    snapshots=sorted(directory.glob('*-dashboard-*.sqlite'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    # Keep every active family plus two rollback snapshots, all in this owner.
    rollback=0
    for path in snapshots:
        if path.resolve() in active:continue
        rollback+=1
        if rollback>2 and path.resolve().parent==directory.resolve():
            try:path.unlink()
            except OSError:pass


def roster_gaps(db, family):
    if family not in {'offense','defense','combined','other'}:raise ValueError('Unknown metric family')
    table=(f"(SELECT * FROM dashboard_family_player_game WHERE family='{family}')"
           if family!='offense' else 'dashboard_player_game')
    return [r[0] for r in db.execute('SELECT g.graph_iri FROM game_dimension g '
        f'LEFT JOIN {table} p USING(graph_iri) '
        "WHERE g.game_set='regular_season' AND g.season=(SELECT MAX(season) FROM game_dimension WHERE game_set='regular_season') "
        'GROUP BY g.graph_iri HAVING MAX(COALESCE(p.roster_complete,0))=0')]


def build(d, args, state, serving, work):
    f=d.module(d.ROOT/'serving/metric_families.py','dashboard_metric_families')
    m=d.METRICS;release=d.RELEASE.own_descriptor(d.ROOT)
    pointer_path=serving/d.POINTER
    old=d.RELEASE.read(pointer_path) if pointer_path.is_file() else {}
    published=publications(old,f.FAMILIES)
    notification,latest=d.notification_key(state)
    notification=d.digest([notification,d.SOURCE.sha256_file(Path(__file__)),d.SOURCE.sha256_file(Path(f.__file__))])
    attempts_path=work/'family-attempts.json'
    attempts=d.RELEASE.read(attempts_path) if attempts_path.is_file() else {}
    family=choose(f.FAMILIES,published,attempts,notification,args.family,args.force)
    if family is None:return dict(status='unchanged',families=list(published),failures={k:v for k,v in attempts.items() if v.get('error')})
    if time.time_ns()-latest<args.quiet_seconds*1_000_000_000:return dict(status='waiting-for-source',family=family)
    selected=f.FAMILIES[family]
    previous_attempt=attempts.get(family,{})
    attempt=dict(notification=notification,attemptedAtUtc=now(),attempts=
        previous_attempt.get('attempts',0)+1 if previous_attempt.get('notification')==notification else 1)
    attempts[family]=attempt;d.RELEASE.atomic(attempts_path,attempts)
    build_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-dashboard-'+family+'-'+uuid.uuid4().hex[:8]
    progress=dict(artifactType='baseballo-dashboard-build-progress',buildId=build_id,family=family,
        status='running',phase='source-snapshot',processId=os.getpid(),startedAtUtc=now(),completedGames=0)
    def checkpoint(**values):
        progress.update(values,updatedAtUtc=now())
        d.RELEASE.atomic(work/'progress.json',progress)
        d.RELEASE.atomic(work/('progress-'+family+'.json'),progress)
    db=None
    try:
        checkpoint()
        snapshot=d.SOURCE.corpus_snapshot(state,args.endpoint,args.timeout,args.max_games)
        captured=now();metadata=d.SOURCE.official_metadata(state)
        checkpoint(sourceSnapshotCapturedAtUtc=captured,sourceSnapshotPolicy='captured-promotions-with-game-read-locks')
        schema_key=d.digest([d.SCHEMA.read_text(encoding='utf-8'),(d.ROOT/'serving/metric-suite-schema.sql').read_text(encoding='utf-8')])
        database=work/('working-'+schema_key[:16]+'.sqlite')
        db=sqlite3.connect(database,timeout=30)
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        db.executescript(d.SCHEMA.read_text(encoding='utf-8'))
        m.initialize_sql(db);d.DISPLAY.initialize(db);d.PLAYER_RANGES.initialize(db);f.initialize(db)
        db.execute('CREATE INDEX IF NOT EXISTS dashboard_player_metric_coverage ON dashboard_player_metric(graph_iri,metric_id,player,complete,reason)')
        db.commit()
        calculation=m.calculation_fingerprint()
        cache=d.SOURCE._query_cache.ServingQueryCache(serving/'query-cache.sqlite')
        saved=dict(db.execute('SELECT graph_iri,input_sha256 FROM dashboard_family_checkpoint WHERE family=?',(family,)))
        dirty_row=db.execute('SELECT value FROM dashboard_state WHERE name=?',('dirty-'+family,)).fetchone()
        expected={};players={};dirty=set(json.loads(dirty_row[0]) if dirty_row else []);changed=0;reused=0
        checkpoint(phase='game-products',totalGames=len(snapshot['live']['dimensions']))
        with d.admission_versions():
            for dimension in snapshot['live']['dimensions']:
                graph=d.SOURCE.lexical(dimension,'graph');promotion=snapshot['inventory']['games'][graph.rsplit('/',1)[-1]]
                values=d.dimension_values(dimension,promotion,metadata)
                with d.admission_reads():
                    admissions={name:d.ADMISSION_EVIDENCE.load(d.ADMISSIONS[name],state,promotion,
                        name.removesuffix('_admission').replace('_','-')) for name in f.ADMISSIONS[family]}
                    individual=d.ADMISSION_EVIDENCE.player_admission(state,promotion)
                players[graph]=individual
                identity=d.digest([family,d.input_identity(promotion,values,admissions,calculation),individual])
                expected[graph]=identity
                query=m.evidence_query([graph]);query_sha=d.digest(query)
                if saved.get(graph)!=identity:
                    rows=retained_rows(d,db,graph,promotion,values,query_sha,calculation)
                    replace_evidence=rows is None
                    if rows is None:
                        bindings=d.query_game_snapshot(state,promotion,lambda:cache.query(endpoint=args.endpoint,query=query,
                            slot='metric-suite-snapshot-v1',promotion=promotion,
                            fetch=lambda:d.SOURCE.sparql(args.endpoint,query,args.timeout)))['results']['bindings']
                        rows=m.normalize_bindings(bindings,[graph])
                    with db:
                        prior_year=db.execute('SELECT season FROM game_dimension WHERE graph_iri=?',(graph,)).fetchone()
                        if prior_year:dirty.add(prior_year[0])
                        dirty.add(values[5])
                        db.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(graph_iri) DO UPDATE SET '
                            'game_iri=excluded.game_iri,game_pk=excluded.game_pk,official_date=excluded.official_date,game_start=excluded.game_start,'
                            'season=excluded.season,game_set=excluded.game_set,venue_iri=excluded.venue_iri,venue_label=excluded.venue_label,'
                            'home_team_iri=excluded.home_team_iri,home_team_label=excluded.home_team_label,'
                            'away_team_iri=excluded.away_team_iri,away_team_label=excluded.away_team_label',values)
                        proof=m.materialize_game(db,graph,None,normalized_rows=rows,metric_ids=selected,
                            player_admission=individual,replace_evidence=replace_evidence,**admissions)
                        db.execute('INSERT OR REPLACE INTO dashboard_evidence_checkpoint VALUES (?,?,?,?)',
                            (graph,promotion['authoritativeRdfSha256'],query_sha,len(rows)))
                        db.execute('INSERT OR REPLACE INTO dashboard_family_checkpoint VALUES (?,?,?)',(family,graph,identity))
                        if family=='offense':
                            db.execute('INSERT OR REPLACE INTO dashboard_checkpoint VALUES (?,?,?)',(graph,identity,m._json(proof)))
                        db.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('dirty-'+family,json.dumps(sorted(dirty))))
                    changed+=1
                else:reused+=1
                label_identity=d.digest([promotion['authoritativeRdfSha256'],d.DISPLAY.fingerprint()])
                label=db.execute('SELECT input_sha256 FROM dashboard_display_manifest WHERE graph_iri=?',(graph,)).fetchone()
                if label!=(label_identity,):
                    label_query=d.DISPLAY.query(graph)
                    bindings=d.query_game_snapshot(state,promotion,lambda:cache.query(endpoint=args.endpoint,query=label_query,
                        slot='metric-display-snapshot-v1',promotion=promotion,
                        fetch=lambda:d.SOURCE.sparql(args.endpoint,label_query,args.timeout)))['results']['bindings']
                    d.DISPLAY.store(db,graph,label_identity,bindings)
                if (changed+reused)%100==0:checkpoint(completedGames=changed+reused,changedGames=changed,reusedGames=reused)
        with db:
            # Source-scope retirement removes only derived SQL. Active sibling
            # publications remain immutable and retain their own older scope.
            removed=set(r[0] for r in db.execute('SELECT graph_iri FROM game_dimension'))-set(expected)
            for graph in removed:
                dirty.add(db.execute('SELECT season FROM game_dimension WHERE graph_iri=?',(graph,)).fetchone()[0])
                for table in ('dashboard_family_checkpoint','dashboard_family_player_partition',
                              'dashboard_family_player_game','dashboard_evidence_checkpoint'):
                    db.execute(f'DELETE FROM {table} WHERE graph_iri=?',(graph,))
                d.remove_game(db,graph)
            coverage=d.SOURCE._schedule_qualification.merge_snapshots(state,d.SOURCE._batting_admission.schedule_coverage(state))
            coverage_key=d.digest(coverage)
            saved_coverage=db.execute('SELECT value FROM dashboard_state WHERE name=?',('coverage-'+family,)).fetchone()
            if saved_coverage!=(coverage_key,):
                dirty.update(r[0] for r in db.execute('SELECT DISTINCT season FROM game_dimension'))
                db.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('coverage-'+family,coverage_key))
            db.execute('DELETE FROM metric_suite_schedule_coverage')
            for day,proof in coverage.items():
                text=m._json(proof);db.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day,text,m._hash(text)))
            db.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('dirty-'+family,json.dumps(sorted(dirty))))
        # A resumed family still finishes reference and player preparation even
        # when every game checkpoint had already committed before interruption.
        input_set=d.digest([family,expected,coverage,d.PLAYER_RANGES.fingerprint(),d.REFERENCES.fingerprint(),
            d.SOURCE.sha256_file(Path(d.SOURCE._reader._range_query.__file__))])
        prior=published.get(family,{})
        if not args.force and prior.get('inputSetSha256')==input_set and prior.get('runtimeRelease')==release:
            prior=dict(prior,familyNotificationKey=notification);published[family]=prior
            attempt.update(status='unchanged');attempt.pop('error',None)
            d.RELEASE.atomic(attempts_path,attempts)
            if not args.no_promote and not args.max_games:
                d.RELEASE.atomic(pointer_path,composition(published,attempts))
            checkpoint(status='unchanged',publicationBuildId=prior['buildId'])
            return progress
        checkpoint(phase='reference-ranks',completedGames=len(expected),changedGames=changed,reusedGames=reused)
        reference_ids=set(d.PLAYER_RANGES.REFERENCES)&selected
        references=[]
        if reference_ids:
            with db:
                version=d.REFERENCES.fingerprint()
                saved_reference=db.execute('SELECT value FROM dashboard_state WHERE name=?',('reference-version-'+family,)).fetchone()
                if saved_reference!=(version,):dirty.update(r[0] for r in db.execute('SELECT DISTINCT season FROM game_dimension'))
                references=d.REFERENCES.prepare(m,db,seasons=dirty,checkpoint=checkpoint,player_admissions=players,metric_ids=reference_ids)
                db.execute('INSERT OR REPLACE INTO dashboard_state VALUES (?,?)',('reference-version-'+family,version))
        checkpoint(phase='player-ranges')
        player_ranges=d.PLAYER_RANGES.prepare_family(m,db,family,selected,players,checkpoint)
        missing_rosters=roster_gaps(db,family)
        if missing_rosters and prior:
            prior_root=d.RELEASE.resolve_pointer_release(state,prior)
            reader=d.module(prior_root/'scripts/pipeline/query-serving-layer.py','prior_family_reader') if prior_root else d.SOURCE._reader
            with reader.dashboard_database(state,prior) as (previous,_):
                previously_complete=not roster_gaps(previous,prior.get('family','offense'))
            if previously_complete:
                attempt['attempts']=max(0,attempt['attempts']-1)
                d.RELEASE.atomic(attempts_path,attempts)
                checkpoint(status='waiting-for-source',pendingRosterGames=missing_rosters,
                           reason='Captured game roster checks are pending',publicationBuildId=prior['buildId'])
                return progress
        checkpoint(phase='season-ranges')
        ranges=d.SOURCE._reader._range_query.prepare_seasons(m,d.PLAYER_RANGES,db,input_set,metric_ids=sorted(selected),family=family)
        with db:
            db.execute('INSERT OR REPLACE INTO dashboard_build VALUES (1,?,?,?,?)',(build_id,snapshot['fingerprint'],input_set,'validated'))
            db.execute('DELETE FROM dashboard_state WHERE name=?',('dirty-'+family,))
        checkpoint(phase='publication',preparedSeasonRanges=ranges)
        (work/'builds').mkdir(exist_ok=True)
        path=work/'builds'/(build_id+'.sqlite')
        publication=d.publish_snapshot(database,path,checkpoint,metric_ids=selected,family=family)
        sha=d.SOURCE.sha256_file(path)
        d.SOURCE._reader.write_database_verification_cache(d.SOURCE._reader.database_verification_cache_path(serving,sha),
            sha,path,d.SOURCE._reader.file_identity(path))
        pointer=dict(artifactType='baseballo-dashboard-serving-pointer',contractVersion=1,buildId=build_id,family=family,
            databasePath=str(path),databaseSha256=sha,corpusFingerprint=snapshot['fingerprint'],inputSetSha256=input_set,
            metricSuiteSha256=m.fingerprint(),schemaSha256=d.SOURCE.sha256_file(d.SCHEMA),runtimeRelease=release,
            familyNotificationKey=notification,sourceSnapshotCapturedAtUtc=captured,
            sourceSnapshotPolicy='captured-promotions-with-game-read-locks',gameCount=len(expected),promotedAtUtc=now())
        evidence=dict(progress,pointer=pointer,publication=publication,playerRanges=player_ranges,references=references)
        evidence_path=serving/'evidence'/(build_id+'.json');d.RELEASE.atomic(evidence_path,evidence)
        if args.no_promote or args.max_games:return evidence
        published[family]=pointer
        attempt.update(status='published');attempt.pop('error',None)
        d.RELEASE.atomic(pointer_path,composition(published,attempts))
        # Publication is committed. Subsequent bookkeeping is only a warning.
        warnings=[]
        try:
            attempt.update(status='published');attempt.pop('error',None);d.RELEASE.atomic(attempts_path,attempts)
            if family=='offense':
                remainder=d.module(d.ROOT/'serving/empty_game_remainder.py','family_empty_remainder').summarize(m,db,build_id)
                d.RELEASE.atomic(work/'empty-game-remainder.json',remainder)
                evidence['emptyGameRemainder']=remainder['summary']
            retain(d,path.parent,published)
            checkpoint(status='published',postPublicationWarnings=warnings)
            evidence.update(progress);d.RELEASE.atomic(evidence_path,evidence)
        except Exception as error:warnings.append(str(error))
        return dict(evidence,status='published',postPublicationWarnings=warnings)
    except d.SOURCE.SourceSnapshotChanged as error:
        # Routine source contention is not a failed calculation or retry debt.
        attempt['attempts']=max(0,attempt['attempts']-1)
        d.RELEASE.atomic(attempts_path,attempts)
        checkpoint(status='waiting-for-source',reason=str(error));return progress
    except Exception as error:
        attempt.update(status='failed',error=str(error));d.RELEASE.atomic(attempts_path,attempts)
        if published and not args.no_promote and not args.max_games:
            d.RELEASE.atomic(pointer_path,composition(published,attempts))
        checkpoint(status='failed',error=str(error))
        # The timer schedules other families before the bounded retry. Do not
        # fail/requeue the whole dashboard and starve its independent offense.
        return dict(progress,status='family-failed',retainedPublication=published.get(family,{}).get('buildId'))
    finally:
        if db is not None:db.close()
