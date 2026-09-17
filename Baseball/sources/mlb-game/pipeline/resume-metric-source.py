#!/usr/bin/env python3
"""Advance one queued MLB proof/refresh through existing NiFi processors.

Called by the source's periodic batch worker. A tick never waits for a job to
finish, manufactures stage evidence, or retries an ambiguous RUN_ONCE request.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
import re
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


def event_time(value):
    """Compare timezone-qualified timestamps without losing .NET's seventh digit.

    Python 3.10's fromisoformat rejects that precision. Keep arbitrary decimal
    fractions exact instead of rounding or dropping the timestamp check.
    """
    if not isinstance(value,str):raise ValueError('Missing recovery event timestamp')
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})',value)
    if not match:raise ValueError('Unqualified recovery event timestamp')
    parsed=datetime.fromisoformat(match[1]+match[3].replace('Z','+00:00'))
    delta=parsed-datetime(1970,1,1,tzinfo=timezone.utc)
    digits=match[2] or '0'
    return Fraction(delta.days*86400+delta.seconds)+Fraction(int(digits),10**len(digits))


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


def archive_completed_plan(path):
    """Called under the plan lock; retain exact bytes before a new request.

    A completed request can be superseded. Pending or failed work still needs
    its own resolution and must never be overwritten by enqueue.
    """
    if not path.exists():
        return None
    raw = path.read_bytes()
    prior = json.loads(raw)
    if (prior.get('artifactType') != ARTIFACT or prior.get('contractVersion') != 1
            or prior.get('phase') != 'complete'):
        raise ValueError('Only a completed recovery plan can be archived for another request')
    digest = hashlib.sha256(raw).hexdigest()
    archive = path.parent / 'recovery-history' / (digest + '.json')
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        with archive.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if archive.read_bytes() != raw:
            raise ValueError('Completed recovery archive differs from its content hash')
    return dict(path=str(archive), sha256=digest, phase='complete')


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


def completed_obsolete_proofs(state_root, prior_runs):
    """Identify positively completed work invalidated by a mapping/SHACL edit.

    The existing release checker must reach its current-artifact hash check:
    missing stages, failed conformance and incomplete cleanup never qualify.
    This observes old completion; it does not release that proof or infer that
    a request with no completion evidence may be repeated.
    """
    spec = importlib.util.spec_from_file_location('mlb_completed_proof_checker', CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    contract = read(CONTRACT)
    module, scope, required = checker.proof_identity(contract)
    root = state_root/'pipeline/evidence'/module/scope
    if not root.is_dir():
        return []
    obsolete = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name in prior_runs:
            continue
        matched, reason, _ = checker.evidence_matches(path, module, scope, required, contract, CONTRACT)
        if not matched and reason.startswith('proof artifact changed after the proof: '):
            cleanup = read(path/'cleanup.json')
            # Completion must be positively recorded, not inferred from age.
            completed = cleanup.get('completedAtUtc')
            if not isinstance(completed, str):
                continue
            event_time(completed)
            obsolete.append(dict(proofRunId=path.name, proofCompletedAtUtc=completed, reason=reason,
                stageEvidenceSha256={name:hashlib.sha256((path/(name+'.json')).read_bytes()).hexdigest()
                                     for name in required}))
    return obsolete


def serving_revision():
    """Bound automatic recovery to one attempt per current scoring/build revision."""
    path=BASEBALL_ROOT/'serving/metric_suite.py'
    spec=importlib.util.spec_from_file_location('mlb_recovery_metric_fingerprint',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    paths=[BASEBALL_ROOT/'scripts/pipeline'/name for name in
           ('materialize-serving-layer.py','serving_query_cache.py','serving_preflight_queries.py','serving_build_guard.py','serving_release.py')]
    inputs={str(p.relative_to(BASEBALL_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    inputs['metric-suite']=module.fingerprint()
    return hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def serving_launcher_committed():
    """A first-deployment refusal is retryable only after the launcher is committed."""
    for name in ('serving_release.py','materialize-serving-layer.py'):
        relative='Baseball/scripts/pipeline/'+name
        result=subprocess.run(['git','-C',str(BASEBALL_ROOT.parent),'show','HEAD:'+relative],
                              capture_output=True,check=False,timeout=15)
        if result.returncode or result.stdout!=(BASEBALL_ROOT/'scripts/pipeline'/name).read_bytes():
            return False
    return True


def obsolete_sql_failure(state_root, plan, failures):
    """Recognize a terminated proof whose SQL code changed during its build.

    This never releases a source proof. A new full proof may be queued only
    from unique, positively attributed quarantine and prior successful stages.
    Other failures, active/ambiguous work and incomplete evidence do not qualify.
    """
    if len(failures)!=1 or plan.get('dispatchOutcome')!='accepted':return None
    proof_pk=str(read(CONTRACT)['proofGamePk'])
    failure_path=state_root/'pipeline/quarantine/mlb-game'/proof_pk/next(iter(failures))
    failure=read(failure_path);run=failure_path.parent.name
    if (failure.get('artifactType')!='baseballo-mlb-game-quarantine'
            or failure.get('contractVersion')!=1 or failure.get('failedStage') not in {'materialize','materialization'}
            or failure.get('pipelineRunId')!=run or str(failure.get('gamePk'))!=proof_pk
            or run in plan['priorProofRuns']):return None
    try:
        dispatched=event_time(plan.get('dispatchedAtUtc'))
        ended=event_time(failure.get('quarantinedAtUtc'))
        if ended<dispatched:return None
        root=state_root/'pipeline/evidence/mlb-game'/proof_pk
        candidates={p.name for p in root.iterdir() if p.is_dir()}-set(plan['priorProofRuns'])
        if candidates!={run}:return None
        directory=root/run
        if any((directory/(stage+'.json')).exists() for stage in ('materialize','cleanup')):return None
        hashes={}
        previous=dispatched
        for action in ('rml','shacl','promote','emit'):
            stage_path=directory/(action+'.json')
            record=read(stage_path)
            if (record.get('artifactType')!='baseballo-mlb-game-stage-result'
                    or record.get('contractVersion')!=1 or record.get('action')!=action
                    or record.get('pipelineRunId')!=run or str(record.get('gamePk'))!=proof_pk):return None
            completed=event_time(record.get('completedAtUtc'))
            if not previous<=completed<=ended:return None
            previous=completed
            if action=='shacl' and record.get('conforms') is not True:return None
            hashes[action]=hashlib.sha256(stage_path.read_bytes()).hexdigest()
        log=directory/'materialize.log'
        if log.stat().st_size>1024*1024:return None
        raw=log.read_bytes()
        output=json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
        if not isinstance(output,dict) or output.get('status')!='failed':return None
        failure_kind='implementation-changed'
        if output=={'status':'failed','error':'Commit the serving release launcher before deploying it',
                    'failureKind':'release-preparation-failed'}:
            if not serving_launcher_committed():return None
            failure_kind='release-not-committed'
        elif (output.get('failureKind')!='implementation-changed'
                and output!={'status':'failed','error':'Metric implementation changed during materialization'}):return None
    except (OSError,ValueError,KeyError):return None
    return dict(proofRunId=run,quarantinedAtUtc=failure['quarantinedAtUtc'],
        quarantineEvidence=str(failure_path.relative_to(state_root)),
        quarantineSha256=hashlib.sha256(failure_path.read_bytes()).hexdigest(),
        materializeLogSha256=hashlib.sha256(raw).hexdigest(),stageEvidenceSha256=hashes,
        failureKind=failure_kind)


def advance(state_root, plan, nifi, release=proof_release):
    """Perform at most one dispatch; caller holds the source-local plan lock."""
    path = plan_path(state_root)
    phase = plan["phase"]
    if phase == 'complete' and not plan.get('awaitSqlIdle') and plan.get('pendingRefreshes'):
        # A queued reference-season refresh follows the existing full proof
        # and backfill lifecycle. Archive completion before replacing a plan;
        # never overwrite pending/failed work or dispatch two requests per tick.
        previous=archive_completed_plan(path)
        request,*remaining=plan['pendingRefreshes']
        pointer=read(state_root/'serving/current.json')
        fresh={k:plan[k] for k in ('sourceGroupId','sqlGroupId','sqlProcessorId','nifiApi')}
        fresh.update(artifactType=ARTIFACT,contractVersion=1,phase='waiting-serving',createdAtUtc=now(),
            requiredBuildId=pointer['buildId'],proofRebuildsServing=True,
            startDate=request['startDate'],endDate=request['endDate'],refreshRequest=request,
            pendingRefreshes=remaining,previousCompletedPlan=previous)
        plan.clear();plan.update(fresh);save(path,plan)
        return dict(status='waiting-serving',deferMaterialization=True,
                    reason='Queued refresh advanced after prior batch completion; NiFi will run the current full proof')
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
        promoted = pointer.get("buildId") == plan["requiredBuildId"]
        if sql_busy or (not promoted and not plan.get("proofRebuildsServing", False)):
            return finish(phase, "Waiting for the prerequisite SQL build to promote and become idle")
        if promoted and not Path(pointer.get("databasePath", "")).is_file():
            raise ValueError("promoted SQL pointer has no database")
        # The normal proof's materialize stage performs a complete validated SQL
        # build itself. When explicitly queued in this mode, an obsolete prior
        # build need only finish, not promote. No old pointer or failed build is
        # admitted as current evidence, and the full proof gate still applies.
        plan["prerequisiteResolution"] = "promoted" if promoted else "idle-proof-will-rebuild"
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
            obsolete=obsolete_sql_failure(state_root,plan,failures)
            if obsolete:
                if sql_busy or not request_idle(processors['Proof Request']):
                    return finish(phase,'Obsolete SQL proof reached quarantine; waiting for active work to finish')
                revision=serving_revision()
                if any(p['retryImplementationSha256']==revision for p in plan.get('obsoleteSqlProofs',[])):
                    return finish('failed','Current implementation already received an obsolete-SQL proof retry',sql_busy)
                plan.setdefault('obsoleteSqlProofs',[]).append({**obsolete,
                    'retryImplementationSha256':revision,'priorDispatchedAtUtc':plan['dispatchedAtUtc'],
                    'priorDispatchOutcome':plan['dispatchOutcome'],'recordedAtUtc':now()})
                plan['proofRebuildsServing']=True
                return finish('waiting-serving','Obsolete SQL proof retained in quarantine; queued a full current proof')
            return finish("failed", "Proof reached quarantine; retained evidence requires a focused fix", sql_busy)
        obsolete = completed_obsolete_proofs(state_root, set(plan['priorProofRuns']))
        if len(obsolete) > 1:
            plan['obsoleteProofCandidates'] = obsolete
            return finish('failed', 'Multiple completed obsolete proofs require dispatch attribution', sql_busy)
        if obsolete:
            if sql_busy or not request_idle(processors['Proof Request']):
                return finish(phase, 'Completed proof is obsolete; waiting for active work to finish')
            plan.setdefault('supersededProofs', []).append({**obsolete[0],
                'priorDispatchedAtUtc':plan.get('dispatchedAtUtc'),
                'priorDispatchOutcome':plan.get('dispatchOutcome'), 'recordedAtUtc':now()})
            plan['proofRebuildsServing'] = True
            # Next tick rechecks processor identity/idle state and persists a
            # new intent before dispatching. The obsolete proof never releases
            # backfill, and its original files and request audit are preserved.
            return finish('waiting-serving', 'Completed proof used older artifacts; queued a current proof')
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
    # NiFi also pairs an existing validated database with its exact historical
    # runtime. This runs independently of a long replacement SQL build.
    release_path=BASEBALL_ROOT/'scripts/pipeline/serving_release.py'
    spec=importlib.util.spec_from_file_location('mlb_serving_release',release_path)
    serving_release=importlib.util.module_from_spec(spec);spec.loader.exec_module(serving_release)
    try:
        release_result=serving_release.prepare_legacy(BASEBALL_ROOT.parent,state_root)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        # Failure cannot admit a legacy pointer; a new normal build still runs.
        release_result={'status':'failed','error':str(error)}
    serving_release.atomic(Path(state_root)/'serving/runtime-preparation.json',release_result)
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


def resume_obsolete_sql(state_root):
    """Explicitly reopen only a positively identified obsolete-code failure.

    Preserve the terminal plan and all quarantine evidence. This queues work
    for the existing NiFi worker; it neither dispatches nor releases a proof.
    """
    path=plan_path(state_root)
    with lock(path.with_suffix('.lock')):
        plan=read(path)
        if (plan.get('artifactType')!=ARTIFACT or plan.get('contractVersion')!=1
                or plan.get('phase')!='failed'):
            raise ValueError('Only a failed recovery plan can be explicitly resumed')
        proof_pk=str(read(CONTRACT)['proofGamePk'])
        failures=set(names(state_root/'pipeline/quarantine/mlb-game'/proof_pk,'*/failure.json'))-set(plan['priorProofFailures'])
        evidence=obsolete_sql_failure(state_root,plan,failures)
        if evidence is None:
            raise ValueError('Failure is not a uniquely attributable obsolete SQL implementation')
        revision=serving_revision()
        if any(p['retryImplementationSha256']==revision for p in plan.get('obsoleteSqlProofs',[])):
            raise ValueError('Current implementation already received an obsolete-SQL proof retry')
        nifi=NiFi(plan['nifiApi'])
        nifi.source_processors(plan['sourceGroupId'])
        nifi.processor(plan['sqlProcessorId'],plan['sqlGroupId'],'Materialize All DSQs','ExecuteStreamCommand')
        plan.setdefault('resumedFailures',[]).append(dict(recordedAtUtc=now(),
            priorPlanSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            priorPhase=plan['phase'],priorReason=plan.get('reason'),
            priorCheckedAtUtc=plan.get('checkedAtUtc'),evidence=evidence))
        plan.update(phase='waiting-proof',awaitSqlIdle=True,checkedAtUtc=now(),
            reason='Verified obsolete SQL failure reopened; NiFi will check idle state and queue one current proof')
        save(path,plan)
        return dict(status='queued',path=str(path),proofRunId=evidence['proofRunId'])


def queue_refresh(state_root, start_date, end_date):
    """Append bounded work to the existing source lane; no immediate dispatch."""
    start=date.fromisoformat(start_date);end=date.fromisoformat(end_date)
    if start>end or start.year<1876 or end>date.today():raise ValueError('Invalid completed-game refresh range')
    path=plan_path(state_root)
    with lock(path.with_suffix('.lock')):
        plan=read(path)
        if (plan.get('artifactType')!=ARTIFACT or plan.get('contractVersion')!=1
                or plan.get('phase') not in {'waiting-serving','waiting-proof','ready-refresh','waiting-batch','complete'}):
            raise ValueError('A refresh can follow only a valid active or completed source plan')
        identity=dict(startDate=start.isoformat(),endDate=end.isoformat(),implementationSha256=serving_revision())
        key=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (plan.get('refreshRequest',{}).get('requestId')==key
                or any(r.get('requestId')==key for r in plan.get('pendingRefreshes',[]))):
            return dict(status='already-queued',requestId=key)
        plan.setdefault('pendingRefreshes',[]).append(dict(identity,requestId=key,queuedAtUtc=now()))
        save(path,plan)
        return dict(status='queued',requestId=key,startDate=identity['startDate'],endDate=identity['endDate'],
                    waitsForCurrentPhase=plan['phase'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--enqueue", action="store_true")
    mode.add_argument("--resume-obsolete-sql", action="store_true")
    mode.add_argument('--queue-refresh',action='store_true',help='Append a bounded refresh after the current source request completes')
    parser.add_argument("--required-build-id")
    parser.add_argument("--source-group-id")
    parser.add_argument("--sql-group-id")
    parser.add_argument("--sql-processor-id")
    parser.add_argument("--nifi-api", default="http://127.0.0.1:8080/nifi-api")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--proof-rebuilds-serving", action="store_true",
                        help="After SQL becomes idle, let the normal proof rebuild serving even if the prior build did not promote")
    args = parser.parse_args()
    state_root = args.state_root.resolve()
    if args.queue_refresh:
        if not args.start_date or not args.end_date:parser.error('--queue-refresh requires --start-date and --end-date')
        print(json.dumps(queue_refresh(state_root,args.start_date,args.end_date)))
    elif args.resume_obsolete_sql:
        print(json.dumps(resume_obsolete_sql(state_root)))
    elif args.enqueue:
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
            previous_plan = archive_completed_plan(path)
            plan = {"artifactType": ARTIFACT, "contractVersion": 1, "phase": "waiting-serving",
                    "createdAtUtc": now(), "requiredBuildId": args.required_build_id,
                    "sourceGroupId": args.source_group_id, "sqlGroupId": args.sql_group_id,
                    "sqlProcessorId": args.sql_processor_id, "nifiApi": args.nifi_api,
                    "startDate": args.start_date, "endDate": args.end_date,
                    "proofRebuildsServing": args.proof_rebuilds_serving}
            if previous_plan:
                plan['previousCompletedPlan'] = previous_plan
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
