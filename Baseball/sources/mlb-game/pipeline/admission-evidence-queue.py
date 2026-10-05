"""Resume interrupted admission checks before the regular maintenance sweep.

This is execution order only. The existing evidence producer owns validation,
receipts and fingerprints; moving a job must not invalidate completed history
inspections. NiFi's wrapper holds the shared evidence-writer lease.
"""
import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('queued_admission_evidence', HERE/'admission-evidence.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def tick(state, java, classpath, endpoint='http://127.0.0.1:3031/baseball-dev/query'):
    control = Path(state)/'pipeline/control/mlb-game/admission-evidence'
    excluded = E.module(HERE/'work_scope.py', 'queued_work_scope').excluded_games(state)
    pending = []
    for path in control.glob('*.json'):
        if not path.stem.isdigit() or path.stem in excluded:
            continue
        previous = E.read(path)
        if previous.get('status') in {'waiting-for-memory', 'partial-refreshed', 'failed'}:
            pending.append((previous.get('checkedAtUtc', ''), path, previous))
    if pending:
        versions = {family:E.module(HERE/(family+'-admission.py'), 'queued_'+family).fingerprint()
                    for family in E.FIELDS}
        version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()+E.fingerprint().encode()).hexdigest()
        inventory = E.module(E.ROOT/'scripts/pipeline/game_promotion_inventory.py', 'queued_inventory')
        for _, destination, previous in sorted(pending):
            game = destination.stem
            owner = Path(state)/'pipeline/evidence/nifi/game-promotion'/game
            markers = [(E.read(p).get('promotedAtUtc', ''), p.name, p) for p in owner.glob('*.json')]
            if not markers:
                continue
            path = max(markers)[2]
            marker_sha = E.sha(path)
            same_input = (previous.get('promotionManifestSha256') == marker_sha
                          and previous.get('implementationSetSha256') == version)
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
            summary = dict(status='processed', processedGames=1, resumedGame=game,
                           refreshedGames=int(bool(result.get('refreshed'))), outcomes={result['status']:1})
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
