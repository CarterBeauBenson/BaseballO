#!/usr/bin/env python3
"""Materialize SQL once all games in a pending MLB schedule batch promoted."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_ROOT = Path(__file__).resolve().parents[1]
BASEBALL_ROOT = MODULE_ROOT.parents[1]
INVENTORY_SCRIPT = BASEBALL_ROOT / "scripts" / "pipeline" / "game_promotion_inventory.py"
MATERIALIZER = BASEBALL_ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py"
RECOVERY_SCRIPT = MODULE_ROOT / "pipeline" / "resume-metric-source.py"
_schedule_spec = importlib.util.spec_from_file_location('batch_schedule_qualification',
    MODULE_ROOT/'pipeline/schedule-qualification.py')
_schedule_qualification = importlib.util.module_from_spec(_schedule_spec)
_schedule_spec.loader.exec_module(_schedule_qualification)
_budget_spec = importlib.util.spec_from_file_location('batch_serving_budget',
    BASEBALL_ROOT/'scripts/infra/serving-budget.py')
_budget = importlib.util.module_from_spec(_budget_spec)
_budget_spec.loader.exec_module(_budget)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    return parser.parse_args()


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def timestamp(value: object) -> datetime:
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def promotion_inventory(state_root: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("game_promotion_inventory", INVENTORY_SCRIPT)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load the game promotion inventory")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.promotion_inventory(state_root,
        excluded_game_pks=_schedule_qualification.PARSER.SCOPE.excluded_games(state_root))


def maintain_serving_storage(state_root):
    """Run the existing retention policy before another build needs space.

    Promotion-only cleanup never runs when candidates repeatedly fail. Keep
    the current reader's database and newest rollback candidates; leave the
    separately owned dashboard, RDF, source inputs and evidence untouched.
    """
    store=state_root/'serving';pointer=store/'current.json'
    if not pointer.is_file() or len(list((store/'builds').glob('*.sqlite')))<=3:return
    current=Path(json_object(pointer)['databasePath']).resolve()
    if current.parent!=(store/'builds').resolve() or not current.is_file():
        raise ValueError('Retention requires the existing current serving database')
    spec=importlib.util.spec_from_file_location('batch_storage_owner',MATERIALIZER)
    owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    result=owner.enforce_build_retention(store,current,3)
    atomic_json(store/'build-retention.json',dict(result,checkedAtUtc=datetime.now(timezone.utc).isoformat()))
    return result


def resume_replay_workers(state_root, request=None, proof_release=None):
    """Finish a requested deployment, including a proof-held RML queue."""
    path = state_root/'pipeline/control/mlb-game/replay-readiness-resume.json'
    if not path.is_file(): return
    def http(method, route, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request('http://127.0.0.1:8080/nifi-api'+route, data=data,
            method=method, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=15) as response: return json.load(response)
    request = request or http
    pending = json_object(path)
    for processor, resume in list(pending.items()):
        name = resume.get('name') if isinstance(resume, dict) else resume
        if name not in {'Plan Quarantine Replay', 'Emit Quarantine Remainder Retry', 'RML'}:
            raise ValueError('Unexpected deferred replay processor')
        if name == 'RML':
            if (not isinstance(resume, dict) or not resume.get('afterProofRunId')
                    or not resume.get('groupId') or resume.get('concurrentTasks') not in (1, 2)):
                raise ValueError('RML resume requires its exact proof and prior worker configuration')
            if proof_release is None:
                spec = importlib.util.spec_from_file_location('resume_queue_proof', RECOVERY_SCRIPT)
                recovery = importlib.util.module_from_spec(spec); spec.loader.exec_module(recovery)
                proof_release = recovery.proof_release
            released = proof_release(state_root)
            if not released or released.get('proofRunId') != resume['afterProofRunId']:
                continue
        entity = request('GET', '/processors/'+processor)
        if entity['component']['name'] != name: raise ValueError('Replay worker identity changed')
        if name == 'RML' and (entity['component']['parentGroupId'] != resume['groupId']
                or entity['component']['type'] != 'org.apache.nifi.processors.standard.ExecuteStreamCommand'):
            raise ValueError('RML worker ownership changed')
        if entity['component']['state'] == 'RUNNING':
            del pending[processor]
        elif entity['status']['aggregateSnapshot']['activeThreadCount'] == 0:
            if name == 'RML':
                entity = request('PUT', '/processors/'+processor, dict(revision=entity['revision'],
                    component=dict(id=processor, config=dict(
                        concurrentlySchedulableTaskCount=resume['concurrentTasks']))))
            request('PUT', '/processors/'+processor+'/run-status', dict(revision=entity['revision'],
                state='RUNNING',disconnectedNodeAcknowledged=False))
            del pending[processor]
    if pending: atomic_json(path, pending)
    else: path.unlink()


def main() -> int:
    args = parse_args()
    state_root = args.state_root.resolve()
    with _budget.reserve(state_root,'report') as reason:
        if reason:
            print(json.dumps({'status':'waiting-serving','reason':reason}))
            return 0
        return materialize_pending(state_root)


def materialize_pending(state_root) -> int:
    process_spec = importlib.util.spec_from_file_location('mlb_worker_state', BASEBALL_ROOT/'scripts/pipeline/process_state.py')
    process_state = importlib.util.module_from_spec(process_spec)
    process_spec.loader.exec_module(process_state)
    builds = process_state.reconcile_builds(state_root)
    # An external SQL process can survive a NiFi restart. Its durable progress
    # and OS liveness, rather than a new processor's zero thread count, own the
    # in-flight build. Leave the pending batches for a later tick.
    active_reports = [build for build in builds
                      if build['status'] == 'running'
                      and Path(build['path']).parent == state_root / 'serving' / 'builds']
    if active_reports:
        print(json.dumps({'status': 'waiting-serving',
                          'reason': 'Existing report SQL worker is still running',
                          'activeBuilds': [Path(build['path']).name for build in active_reports]}))
        return 0
    resume_replay_workers(state_root)
    recovery_spec = importlib.util.spec_from_file_location("mlb_metric_source_recovery", RECOVERY_SCRIPT)
    if recovery_spec is None or recovery_spec.loader is None:
        raise ValueError("cannot load the MLB source recovery worker")
    recovery_module = importlib.util.module_from_spec(recovery_spec)
    recovery_spec.loader.exec_module(recovery_module)
    recovery = recovery_module.tick(state_root)
    if recovery["deferMaterialization"]:
        print(json.dumps({"status": "deferred", "sourceRecovery": recovery}, separators=(",", ":")))
        return 0
    schedule_refresh = _schedule_qualification.refresh_incomplete_batches(state_root)
    batch_root = state_root / "pipeline" / "control" / "mlb-game" / "batches"
    batch_root.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[datetime, Path, dict[str, Any]]] = []
    excluded = _schedule_qualification.PARSER.SCOPE.excluded_games(state_root)
    for path in sorted(batch_root.glob("*.json")):
        batch = json_object(path)
        if (
            batch.get("artifactType") != "baseballo-mlb-game-schedule-batch"
            or batch.get("contractVersion") != 1
        ):
            raise ValueError(f"unsupported game batch manifest: {path}")
        if batch.get("status") == "pending":
            expected = {str(pk) for pk in batch.get('expectedGamePks', [])}
            if expected and expected <= set(excluded):
                continue  # Retain the old batch; it no longer requests work.
            pending.append((timestamp(batch.get("createdAtUtc")), path, batch))
    if not pending:
        print(json.dumps({"status": "idle", "pendingBatchCount": 0,
                          "scheduleCoverage":schedule_refresh}, separators=(",", ":")))
        return 0

    inventory = promotion_inventory(state_root)
    games = inventory["games"]
    ready: list[tuple[Path, dict[str, Any]]] = []
    waiting: list[dict[str, Any]] = []
    for created, path, batch in sorted(pending, key=lambda item: (item[0], item[1].name)):
        missing: list[str] = []
        stale: list[str] = []
        for game_pk in batch.get("expectedGamePks", []):
            if str(game_pk) in excluded:
                continue
            record = games.get(str(game_pk))
            if record is None:
                missing.append(str(game_pk))
            elif timestamp(record.get("promotedAtUtc")) < created:
                stale.append(str(game_pk))
        if missing or stale:
            waiting.append(
                {
                    "batchId": batch.get("batchId"),
                    "missingPromotionCount": len(missing),
                    "stalePromotionCount": len(stale),
                }
            )
        else:
            ready.append((path, batch))
    if not ready:
        print(
            json.dumps(
                {"status": "waiting", "pendingBatchCount": len(pending), "batches": waiting,
                 "scheduleCoverage":schedule_refresh},
                separators=(",", ":"),
            )
        )
        return 0

    maintain_serving_storage(state_root)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(MATERIALIZER),
            "--state-root",
            str(state_root),
            "--retain-builds",
            "3",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"serving materialization failed: {result.stdout[-4000:]}")
    pointer_path = state_root / "serving" / "current.json"
    pointer = json_object(pointer_path)
    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for path, batch in ready:
        batch["status"] = "materialized"
        batch["materializedAtUtc"] = completed_at
        batch["servingBuildId"] = pointer.get("buildId")
        batch["servingCorpusFingerprint"] = pointer.get("corpusFingerprint")
        batch["servingGameCount"] = pointer.get("gameCount")
        atomic_json(path, batch)
    print(
        json.dumps(
            {
                "status": "materialized",
                "materializedBatchCount": len(ready),
                "waitingBatchCount": len(waiting),
                "buildId": pointer.get("buildId"),
                "corpusFingerprint": pointer.get("corpusFingerprint"),
                "gameCount": pointer.get("gameCount"),
                "scheduleCoverage":schedule_refresh,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Pending MLB game batch materialization failed: {error}", file=sys.stderr)
        raise SystemExit(2)
