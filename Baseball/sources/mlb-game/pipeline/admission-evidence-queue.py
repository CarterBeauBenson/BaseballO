"""Resume interrupted admission checks before the regular maintenance sweep.

This is execution order only. The existing evidence producer owns validation,
receipts and fingerprints; moving a job must not invalidate completed history
inspections. NiFi's wrapper holds the shared evidence-writer lease.
"""
import argparse
import hashlib
import importlib.util
import json
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('queued_admission_evidence', HERE/'admission-evidence.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def missing_player_games(state):
    """Published exclusions select work; the source owner still decides it."""
    pointer = Path(state)/'serving/dashboard-current.json'
    if not pointer.is_file():
        return set()
    database = Path(E.read(pointer)['databasePath']).resolve()
    if not database.is_relative_to((Path(state)/'serving/dashboard/builds').resolve()):
        raise ValueError('Dashboard priority database escaped its owner')
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as db:
        missing={row[0] for row in db.execute('''SELECT g.game_pk FROM game_dimension g
            JOIN metric_suite_admission b USING(graph_iri)
            LEFT JOIN dashboard_player_admission a USING(graph_iri)
            WHERE g.game_set IN ('regular_season','all_star')
              AND json_extract(b.proof_json,'$.status')!='admitted' AND a.graph_iri IS NULL''')}
        implementation=E.PLAYER_PARTICIPATION.fingerprint()
        missing.update(game for game,text in db.execute('''SELECT g.game_pk,a.proof_json
            FROM dashboard_player_admission a JOIN game_dimension g USING(graph_iri)
            WHERE g.game_set IN ('regular_season','all_star')
              AND EXISTS (SELECT 1 FROM dashboard_player_game p
                WHERE p.graph_iri=a.graph_iri AND p.plate_appearances IS NULL)''')
            if E.PLAYER_PARTICIPATION.needs_compound_refresh(json.loads(text),implementation=implementation))
        return missing


def tick(state, java, classpath, endpoint='http://127.0.0.1:3031/baseball-dev/query'):
    control = Path(state)/'pipeline/control/mlb-game/admission-evidence'
    excluded = E.module(HERE/'work_scope.py', 'queued_work_scope').excluded_games(state)
    missing = missing_player_games(state) - set(excluded)
    pending = {}
    for path in control.glob('*.json'):
        if not path.stem.isdigit() or path.stem in excluded:
            continue
        previous = E.read(path)
        if path.stem in missing or previous.get('status') in {'waiting-for-memory', 'partial-refreshed', 'failed'}:
            pending[path.stem] = (previous.get('checkedAtUtc', ''), path, previous)
    for game in missing - pending.keys():
        pending[game] = ('', control/(game+'.json'), {})
    if pending:
        versions = {family:E.module(HERE/(family+'-admission.py'), 'queued_'+family).fingerprint()
                    for family in E.FIELDS}
        version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()+E.fingerprint().encode()).hexdigest()
        inventory = E.module(E.ROOT/'scripts/pipeline/game_promotion_inventory.py', 'queued_inventory')
        outcomes = []; started = time.monotonic()
        for _, destination, previous in sorted(pending.values(), key=lambda row:(row[1].stem not in missing, row[0], row[1])):
            game = destination.stem
            owner = Path(state)/'pipeline/evidence/nifi/game-promotion'/game
            markers = [(E.read(p).get('promotedAtUtc', ''), p.name, p) for p in owner.glob('*.json')]
            if not markers:
                continue
            path = max(markers)[2]
            marker_sha = E.sha(path)
            same_input = (previous.get('promotionManifestSha256') == marker_sha
                          and previous.get('implementationSetSha256') == version)
            # SQL can still show a missing proof until the next publication.
            # Continue staged refreshes, but do not redo a terminal check.
            if same_input and previous.get('status') not in {'waiting-for-memory', 'partial-refreshed', 'refreshed', 'failed'}:
                continue
            failures = previous.get('failureAttempts', 0) if same_input else 0
            if failures >= 2:
                continue
            result = dict(gamePk=game, promotionManifestSha256=marker_sha,
                          implementationSetSha256=version, checkedAtUtc=datetime.now(timezone.utc).isoformat(),
                          rdfChanged=False, attempts=(previous.get('attempts', 0) if same_input else 0)+1,
                          failureAttempts=failures)
            try:
                promotion = inventory.validated_promotion_record(Path(state), path, game,
                                                                 inventory.query_index_contract_admission())
                preserved = E.preserve_interrupted_refresh(state, promotion, previous)
                if preserved:
                    result['preservedInterruptedEvidence'] = preserved
                result.update(E.refresh_game(state, promotion, java, classpath, endpoint))
                if result['status'] != 'waiting-for-memory':
                    result['failureAttempts'] = 0
            except (OSError, ValueError, RuntimeError) as error:
                result.update(status='failed', error=str(error), failureAttempts=failures+1)
            E.atomic(destination, result)
            outcomes.append(result)
            if (result['status'] in {'failed', 'waiting-for-memory'} or len(outcomes) >= 10
                    or time.monotonic()-started >= 300):
                break
        if outcomes:
            summary = dict(status='processed', processedGames=len(outcomes), resumedGame=outcomes[-1]['gamePk'],
                           resumedGames=[r['gamePk'] for r in outcomes],
                           refreshedGames=sum(bool(r.get('refreshed')) for r in outcomes),
                           outcomes={status:sum(r['status']==status for r in outcomes)
                                     for status in sorted({r['status'] for r in outcomes})})
            E.atomic(control/'latest.json', summary)
            return summary
    return E.tick(state, java, classpath, endpoint=endpoint)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('state-root', 'java', 'jena-classpath'):
        parser.add_argument('--'+key, required=True, type=Path)
    parser.add_argument('--endpoint', default='http://127.0.0.1:3031/baseball-dev/query')
    args = parser.parse_args()
    print(json.dumps(tick(args.state_root, args.java, args.jena_classpath, args.endpoint)))
