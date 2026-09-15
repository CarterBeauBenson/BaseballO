#!/usr/bin/env python3
"""Advance one queued MLB proof/refresh through existing NiFi processors.

Called by the source's periodic batch worker. A tick never waits for a job to
finish, manufactures stage evidence, or retries an ambiguous RUN_ONCE request.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler


MODULE_ROOT = Path(__file__).resolve().parents[1]
BASEBALL_ROOT = MODULE_ROOT.parents[1]
CONTRACT = MODULE_ROOT / "nifi" / "flow-contract.json"
CHECKER = BASEBALL_ROOT / "scripts" / "pipeline" / "check-source-proof-release.py"
ARTIFACT = "baseballo-mlb-game-deferred-recovery"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False, suffix=".partial") as stream:
            name = stream.name
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def plan_path(state_root):
    return state_root / "pipeline" / "control" / "mlb-game" / "metric-source-recovery.json"


@contextmanager
def lock(path):
    """OS releases the lock on crashes; no stale lease files to clear manually."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("NiFi recovery requests must not redirect")


class NiFi:
    def __init__(self, endpoint):
        parsed = urlparse(endpoint)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.path != "/nifi-api" or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ValueError("recovery requires the configured loopback NiFi API")
        self.endpoint = endpoint
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(self.endpoint + path, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=20) as response:
            return json.load(response)

    def processor(self, identifier, group, name, kind):
        entity = self.call("GET", "/processors/" + identifier)
        component = entity["component"]
        if (component.get("id") != identifier or component.get("parentGroupId") != group
                or component.get("name") != name
                or component.get("type") != "org.apache.nifi.processors.standard." + kind):
            raise ValueError(f"NiFi processor ownership/configuration changed: {name}")
        return entity

    def source_processors(self, group):
        flow = self.call("GET", "/flow/process-groups/" + group)["processGroupFlow"]
        breadcrumb = flow.get("breadcrumb", {})
        if (breadcrumb.get("breadcrumb", {}).get("name") != "MLB Game"
                or breadcrumb.get("parentBreadcrumb", {}).get("breadcrumb", {}).get("name") != "BaseballO"):
            raise ValueError("recovery target is not the MLB Game source group")
        result = {}
        for name, kind in (("Proof Request", "GenerateFlowFile"),
                           ("Backfill Schedule Request", "GenerateFlowFile"),
                           ("Materialize SQL", "ExecuteStreamCommand")):
            matches = [item for item in flow["flow"]["processors"]
                       if item["component"]["name"] == name]
            if len(matches) != 1:
                raise ValueError(f"expected one source processor: {name}")
            result[name] = self.processor(matches[0]["id"], group, name, kind)
        return result

    def run_once(self, entity):
        return self.call("PUT", "/processors/" + entity["id"] + "/run-status", {
            "revision": {"version": entity["revision"]["version"]},
            "state": "RUN_ONCE", "disconnectedNodeAcknowledged": False,
        })

    def configure_request(self, entity, payload):
        return self.call("PUT", "/processors/" + entity["id"], {
            "revision": {"version": entity["revision"]["version"]},
            "component": {"id": entity["id"], "config": {"properties": {
                "Custom Text": json.dumps(payload, separators=(",", ":"))}}},
        })


def active(entity):
    # Missing status must not be treated as an idle processor.
    return int(entity["status"]["aggregateSnapshot"]["activeThreadCount"]) > 0


def request_idle(entity):
    return entity["component"]["state"] == "STOPPED" and not active(entity)


def proof_release(state_root):
    result = subprocess.run([sys.executable, "-B", str(CHECKER), "--state-root",
                             str(state_root), "--contract", str(CONTRACT)],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            encoding="utf-8", timeout=45, check=False)
    if result.returncode != 0:
        return None
    value = json.loads(result.stdout)
    if value.get("released") is not True or value.get("sourceModule") != "mlb-game":
        raise ValueError("unexpected source proof release result")
    return value


def names(path, pattern):
    return sorted(str(item.relative_to(path)) for item in path.glob(pattern))


def advance(state_root, plan, nifi, release=proof_release):
    """Perform at most one dispatch; caller holds the source-local plan lock."""
    path = plan_path(state_root)
    phase = plan["phase"]
    if phase in ("complete", "failed") and not plan.get("awaitSqlIdle"):
        return {"status": phase, "deferMaterialization": False,
                "reason": plan.get("reason")}
    sql = nifi.processor(plan["sqlProcessorId"], plan["sqlGroupId"],
                         "Materialize All DSQs", "ExecuteStreamCommand")
    processors = nifi.source_processors(plan["sourceGroupId"])
    sql_busy = active(sql) or active(processors["Materialize SQL"])
    if phase in ("complete", "failed"):
        plan["awaitSqlIdle"] = sql_busy
        save(path, plan)
        return {"status": phase, "deferMaterialization": sql_busy, "reason": plan.get("reason")}
    proof_pk = str(read(CONTRACT)["proofGamePk"])
    proof_root = state_root / "pipeline" / "evidence" / "mlb-game" / proof_pk
    quarantine_root = state_root / "pipeline" / "quarantine" / "mlb-game" / proof_pk
    batch_root = state_root / "pipeline" / "control" / "mlb-game" / "batches"

    def finish(status, reason, defer=True):
        plan.update(phase=status, reason=reason, checkedAtUtc=now())
        if status in ("complete", "failed"):
            plan["awaitSqlIdle"] = sql_busy
        save(path, plan)
        return {"status": status, "reason": reason, "deferMaterialization": defer}

    def dispatch(entity, next_phase):
        # Persist BEFORE sending: an HTTP timeout is not permission to repeat it.
        plan.update(phase=next_phase, dispatchedAtUtc=now(), dispatchOutcome="uncertain")
        save(path, plan)
        try:
            nifi.run_once(entity)
        except (OSError, ValueError) as error:
            return finish(next_phase, f"Dispatch outcome uncertain; awaiting evidence: {error}")
        plan["dispatchOutcome"] = "accepted"
        return finish(next_phase, "Request accepted by NiFi; awaiting pipeline evidence")

    if phase == "waiting-serving":
        pointer_file = state_root / "serving" / "current.json"
        pointer = read(pointer_file) if pointer_file.exists() else {}
        if sql_busy or pointer.get("buildId") != plan["requiredBuildId"]:
            return finish(phase, "Waiting for the prerequisite SQL build to promote and become idle")
        if not Path(pointer.get("databasePath", "")).is_file():
            raise ValueError("promoted SQL pointer has no database")
        proof = processors["Proof Request"]
        if not request_idle(proof):
            return finish(phase, "Waiting for the proof request processor to become idle")
        payload = json.loads(proof["component"]["config"]["properties"]["Custom Text"])
        if payload != {"gamePk": proof_pk, "materializeMode": "immediate", "scheduleEvidencePath": "none"}:
            raise ValueError("existing proof request differs from the accepted source contract")
        plan["priorProofRuns"] = names(proof_root, "*")
        plan["priorProofFailures"] = names(quarantine_root, "*/failure.json")
        return dispatch(proof, "waiting-proof")

    if phase == "waiting-proof":
        # The existing checker owns the current RML/SHACL/full-stage proof gate.
        released = release(state_root)
        if released and released["proofRunId"] not in plan["priorProofRuns"]:
            if sql_busy:
                return finish(phase, "Proof released; waiting for SQL work to finish")
            plan["proofRelease"] = released
            return finish("ready-refresh", "Current source proof completed")
        failures = set(names(quarantine_root, "*/failure.json")) - set(plan["priorProofFailures"])
        if failures:
            plan["proofFailureEvidence"] = sorted(failures)
            return finish("failed", "Proof reached quarantine; retained evidence requires a focused fix", sql_busy)
        return finish(phase, "Waiting for actual RML, SHACL, promotion, materialization and cleanup evidence")

    if phase == "ready-refresh":
        if sql_busy:
            return finish(phase, "Waiting for SQL work before refreshing the source")
        released = release(state_root)
        if not released or released["proofRunId"] != plan["proofRelease"]["proofRunId"]:
            return finish("failed", "Source proof changed before refresh dispatch", False)
        request = processors["Backfill Schedule Request"]
        if not request_idle(request):
            return finish(phase, "Waiting for the backfill request processor to become idle")
        payload = {"startDate": plan["startDate"], "endDate": plan["endDate"], "requestKind": "backfill"}
        plan["priorBatchManifests"] = names(batch_root, "*.json")
        plan.setdefault("previousBackfillRequest", request["component"]["config"]["properties"]["Custom Text"])
        save(path, plan)
        nifi.configure_request(request, payload)
        request = nifi.processor(request["id"], plan["sourceGroupId"],
                                 "Backfill Schedule Request", "GenerateFlowFile")
        if not request_idle(request) or json.loads(request["component"]["config"]["properties"]["Custom Text"]) != payload:
            raise ValueError("backfill processor changed during request preparation")
        return dispatch(request, "waiting-batch")

    if phase == "waiting-batch":
        matches = []
        for name in set(names(batch_root, "*.json")) - set(plan["priorBatchManifests"]):
            batch = read(batch_root / name)
            if (batch.get("artifactType") == "baseballo-mlb-game-schedule-batch"
                    and batch.get("contractVersion") == 1
                    and batch.get("requestKind") == "backfill"
                    and batch.get("requestedStartDate") == plan["startDate"]
                    and batch.get("requestedEndDate") == plan["endDate"]):
                matches.append(batch)
        if len(matches) > 1:
            return finish("failed", "Multiple matching refresh batches; cannot attribute completion", sql_busy)
        if not matches:
            return finish(phase, "Waiting for the dispatched schedule batch manifest", sql_busy)
        batch = matches[0]
        plan["batchId"] = batch["batchId"]
        if batch["status"] in ("materialized", "complete-empty"):
            plan["servingBuildId"] = batch.get("servingBuildId")
            return finish("complete", "Refresh batch completed through the normal source pipeline", sql_busy)
        if batch["status"] != "pending":
            return finish("failed", f"Unexpected batch status: {batch['status']}", sql_busy)
        return finish(phase, "Batch dispatched; awaiting game promotions and normal SQL materialization", sql_busy)
    raise ValueError(f"unknown deferred recovery phase: {phase}")


def tick(state_root):
    path = plan_path(state_root)
    if not path.exists():
        return {"status": "idle", "deferMaterialization": False}
    try:
        with lock(path.with_suffix(".lock")):
            plan = read(path)
            if plan.get("artifactType") != ARTIFACT or plan.get("contractVersion") != 1:
                raise ValueError("unsupported MLB recovery plan")
            return advance(state_root, plan, NiFi(plan["nifiApi"]))
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        # Read/configuration failures cannot release a dependent build or submit
        # another request. The next normal tick can retry this read-only check.
        return {"status": "recovery-error", "reason": str(error), "deferMaterialization": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--enqueue", action="store_true")
    parser.add_argument("--required-build-id")
    parser.add_argument("--source-group-id")
    parser.add_argument("--sql-group-id")
    parser.add_argument("--sql-processor-id")
    parser.add_argument("--nifi-api", default="http://127.0.0.1:8080/nifi-api")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()
    state_root = args.state_root.resolve()
    if args.enqueue:
        for field in ("required_build_id", "source_group_id", "sql_group_id", "sql_processor_id", "start_date", "end_date"):
            if not getattr(args, field):
                parser.error(f"--enqueue requires --{field.replace('_', '-')}")
        if date.fromisoformat(args.start_date) > date.fromisoformat(args.end_date):
            raise ValueError("refresh start date follows end date")
        nifi = NiFi(args.nifi_api)
        nifi.source_processors(args.source_group_id)
        nifi.processor(args.sql_processor_id, args.sql_group_id,
                       "Materialize All DSQs", "ExecuteStreamCommand")
        path = plan_path(state_root)
        with lock(path.with_suffix(".lock")):
            if path.exists():
                raise ValueError("recovery plan already exists; preserve its audit before queuing another")
            plan = {"artifactType": ARTIFACT, "contractVersion": 1, "phase": "waiting-serving",
                    "createdAtUtc": now(), "requiredBuildId": args.required_build_id,
                    "sourceGroupId": args.source_group_id, "sqlGroupId": args.sql_group_id,
                    "sqlProcessorId": args.sql_processor_id, "nifiApi": args.nifi_api,
                    "startDate": args.start_date, "endDate": args.end_date}
            save(path, plan)
        print(json.dumps({"status": "queued", "path": str(path)}))
    else:
        print(json.dumps(tick(state_root)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"MLB source recovery failed: {error}", file=sys.stderr)
        raise SystemExit(2)
