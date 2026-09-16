from __future__ import annotations

import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "pipeline" / "resume-metric-source.py"
SPEC = importlib.util.spec_from_file_location("metric_source_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def entity(name, identifier, kind="GenerateFlowFile"):
    return {"id": identifier, "revision": {"version": 1},
            "component": {"id": identifier, "name": name, "parentGroupId": "source",
                          "state": "STOPPED", "type": "org.apache.nifi.processors.standard." + kind,
                          "config": {"properties": {"Custom Text": "{}"}}},
            "status": {"aggregateSnapshot": {"activeThreadCount": 0}}}


class FakeNiFi:
    def __init__(self):
        self.sql = entity("Materialize All DSQs", "sql", "ExecuteStreamCommand")
        self.proof = entity("Proof Request", "proof")
        self.backfill = entity("Backfill Schedule Request", "backfill")
        self.materialize = entity("Materialize SQL", "materialize", "ExecuteStreamCommand")
        self.proof["component"]["config"]["properties"]["Custom Text"] = json.dumps({
            "gamePk": str(recovery.read(recovery.CONTRACT)["proofGamePk"]),
            "materializeMode": "immediate", "scheduleEvidencePath": "none"})
        self.calls = []
        self.fail_dispatch = False
        self.before_dispatch = None

    def processor(self, identifier, *args):
        return {"sql": self.sql, "backfill": self.backfill}[identifier]

    def source_processors(self, group):
        return {"Proof Request": self.proof, "Backfill Schedule Request": self.backfill,
                "Materialize SQL": self.materialize}

    def run_once(self, value):
        self.calls.append(("run", value["id"]))
        if self.before_dispatch:
            self.before_dispatch()
        if self.fail_dispatch:
            raise TimeoutError("response lost")
        return {}

    def configure_request(self, value, payload):
        self.calls.append(("configure", value["id"]))
        value["component"]["config"]["properties"]["Custom Text"] = json.dumps(payload)
        return value


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.nifi = FakeNiFi()
        self.plan = {"artifactType": recovery.ARTIFACT, "contractVersion": 1,
                     "phase": "waiting-serving", "requiredBuildId": "new-build",
                     "sourceGroupId": "source", "sqlGroupId": "serving", "sqlProcessorId": "sql",
                     "nifiApi": "http://127.0.0.1:8080/nifi-api",
                     "startDate": "2026-08-25", "endDate": "2026-08-25"}
        self.release = None
        self.path = recovery.plan_path(self.root)
        self.proof_root = self.root / "pipeline/evidence/mlb-game/566279"
        self.failure_root = self.root / "pipeline/quarantine/mlb-game/566279"
        self.batch_root = self.root / "pipeline/control/mlb-game/batches"
        self.database = self.root / "new.sqlite"
        self.database.touch()
        recovery.save(self.root / "serving/current.json", {
            "buildId": "new-build", "databasePath": str(self.database)})

    def step(self):
        return recovery.advance(self.root, self.plan, self.nifi, lambda _: self.release)

    def test_waits_for_promotion_not_candidate_existence(self):
        recovery.save(self.root / "serving/current.json", {"buildId": "old-build"})
        self.assertTrue(self.step()["deferMaterialization"])
        self.assertEqual(self.nifi.calls, [])

    def test_waits_for_active_sql_even_after_promotion(self):
        self.nifi.sql["status"]["aggregateSnapshot"]["activeThreadCount"] = 1
        self.assertTrue(self.step()["deferMaterialization"])
        self.assertEqual(self.nifi.calls, [])

    def test_proof_can_rebuild_after_obsolete_sql_job_finishes(self):
        self.plan['proofRebuildsServing'] = True
        recovery.save(self.root / 'serving/current.json', {'buildId': 'old-build'})
        self.nifi.sql['status']['aggregateSnapshot']['activeThreadCount'] = 1
        self.assertEqual(self.step()['status'], 'waiting-serving')
        self.assertEqual(self.nifi.calls, [])
        self.nifi.sql['status']['aggregateSnapshot']['activeThreadCount'] = 0
        self.assertEqual(self.step()['status'], 'waiting-proof')
        self.assertEqual(self.plan['prerequisiteResolution'], 'idle-proof-will-rebuild')
        # An obsolete build has not satisfied any proof stage or released a
        # refresh. The ordinary full source proof must still complete.
        self.assertNotIn('proofRelease', self.plan)
        self.assertEqual(self.step()['status'], 'waiting-proof')
        self.assertEqual(self.nifi.calls, [('run', 'proof')])

    def test_waits_for_active_source_materializer(self):
        self.nifi.materialize["status"]["aggregateSnapshot"]["activeThreadCount"] = 1
        self.assertEqual(self.step()["status"], "waiting-serving")
        self.assertEqual(self.nifi.calls, [])

    def test_missing_promoted_database_blocks_dispatch(self):
        self.database.unlink()
        with self.assertRaisesRegex(ValueError, "no database"):
            self.step()
        self.assertEqual(self.nifi.calls, [])

    def test_request_must_be_stopped(self):
        self.nifi.proof["component"]["state"] = "RUNNING"
        self.assertEqual(self.step()["status"], "waiting-serving")
        self.assertEqual(self.nifi.calls, [])

    def test_different_proof_payload_blocks_dispatch(self):
        self.nifi.proof["component"]["config"]["properties"]["Custom Text"] = '{}'
        with self.assertRaisesRegex(ValueError, "differs"):
            self.step()
        self.assertEqual(self.nifi.calls, [])

    def test_intent_persisted_before_request_and_not_repeated(self):
        def check_intent():
            saved = recovery.read(self.path)
            self.assertEqual(saved["phase"], "waiting-proof")
            self.assertEqual(saved["dispatchOutcome"], "uncertain")
        self.nifi.before_dispatch = check_intent
        self.assertEqual(self.step()["status"], "waiting-proof")
        self.step()
        self.assertEqual(self.nifi.calls, [("run", "proof")])

    def test_http_timeout_does_not_resubmit_after_restart(self):
        self.nifi.fail_dispatch = True
        self.step()
        self.plan = recovery.read(self.path)
        self.step()
        self.assertEqual(self.plan["dispatchOutcome"], "uncertain")
        self.assertEqual(self.nifi.calls, [("run", "proof")])

    def test_old_completed_proof_does_not_release_refresh(self):
        (self.proof_root / "old-run").mkdir(parents=True)
        self.step()
        self.release = {"released": True, "proofRunId": "old-run"}
        self.assertEqual(self.step()["status"], "waiting-proof")

    def test_no_completed_proof_does_not_dispatch_backfill(self):
        self.step()
        self.assertTrue(self.step()["deferMaterialization"])
        self.assertEqual(self.nifi.calls, [("run", "proof")])

    def obsolete_proof(self, run='completed-obsolete'):
        path=self.proof_root/run
        mapping=self.root/'mapping.ttl';mapping.write_text('current mapping')
        shape=self.root/'shape.ttl';shape.write_text('current shape')
        manifest=self.root/'manifest.json'
        context=recovery.BASEBALL_ROOT/'scripts/pipeline/prepare-rml-context.py'
        recovery.save(manifest,dict(mappingPath=str(mapping),mappingSha256='older-hash',
            shaclShapePath=str(shape),shaclShapeSha256=hashlib.sha256(shape.read_bytes()).hexdigest(),
            contextBuilderPath=str(context),contextBuilderSha256=hashlib.sha256(context.read_bytes()).hexdigest()))
        for action in ('rml','shacl','promote','materialize','cleanup'):
            recovery.save(path/(action+'.json'),dict(action=action,pipelineRunId=run,gamePk='566279',
                rmlManifest=str(manifest),conforms=True,authoritativeRdfRemainsInGraphStore=True,
                completedAtUtc='2026-09-15T19:00:00Z'))
        return path

    def test_completed_obsolete_proof_queues_fresh_work_without_releasing_backfill(self):
        self.step();path=self.obsolete_proof()
        self.assertEqual(self.step()['status'],'waiting-serving')
        self.assertEqual(self.nifi.calls,[('run','proof')])
        self.assertNotIn('proofRelease',self.plan)
        old=self.plan['supersededProofs'][0]
        self.assertEqual(old['proofRunId'],path.name)
        self.assertEqual(set(old['stageEvidenceSha256']),{'rml','shacl','promote','materialize','cleanup'})
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(self.nifi.calls,[('run','proof'),('run','proof')])
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(len(self.nifi.calls),2)
        self.assertTrue((path/'cleanup.json').exists())

    def test_obsolete_mapping_without_completed_proof_never_retries(self):
        self.step();path=self.obsolete_proof()
        (path/'cleanup.json').unlink()
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(self.nifi.calls,[('run','proof')])

    def test_completed_obsolete_proof_waits_for_idle_and_rejects_multiple_candidates(self):
        self.step();self.obsolete_proof()
        self.nifi.sql['status']['aggregateSnapshot']['activeThreadCount']=1
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.nifi.sql['status']['aggregateSnapshot']['activeThreadCount']=0
        self.obsolete_proof('second-completion')
        self.assertEqual(self.step()['status'],'failed')
        self.assertEqual(self.nifi.calls,[('run','proof')])

    def test_failed_conformance_cannot_be_relabelled_as_obsolete_completion(self):
        self.step();path=self.obsolete_proof()
        shacl=recovery.read(path/'shacl.json');shacl['conforms']=False
        recovery.save(path/'shacl.json',shacl)
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(self.nifi.calls,[('run','proof')])

    def test_new_quarantine_fails_and_preserves_evidence(self):
        old = self.failure_root / "old-run/failure.json"
        recovery.save(old, {"failedStage": "materialize"})
        self.step()
        self.assertEqual(self.step()["status"], "waiting-proof")
        new = self.failure_root / "new-run/failure.json"
        recovery.save(new, {"failedStage": "shacl"})
        self.assertEqual(self.step()["status"], "failed")
        self.assertTrue(new.is_file())
        self.assertTrue(old.is_file())
        self.assertEqual(self.nifi.calls, [("run", "proof")])

    def obsolete_sql(self,run='a'*32,legacy=False,stage='materialization'):
        directory=self.proof_root/run
        for action in ('rml','shacl','promote','emit'):
            recovery.save(directory/(action+'.json'),dict(artifactType='baseballo-mlb-game-stage-result',
                contractVersion=1,action=action,pipelineRunId=run,gamePk='566279',
                conforms=True,completedAtUtc=recovery.now()))
        output=dict(status='failed',error='Metric implementation changed during materialization')
        if not legacy:output.update(error='Serving implementation changed during materialization: metric-suite',
                                    failureKind='implementation-changed')
        (directory/'materialize.log').write_text(json.dumps(output),encoding='utf-16' if legacy else 'utf-8')
        failure=self.failure_root/run/'failure.json'
        recovery.save(failure,dict(artifactType='baseballo-mlb-game-quarantine',contractVersion=1,
            pipelineRunId=run,gamePk='566279',failedStage=stage,quarantinedAtUtc=recovery.now()))
        return directory,failure

    def test_obsolete_sql_failure_queues_full_proof_and_preserves_quarantine(self):
        self.step();directory,failure=self.obsolete_sql()
        before=failure.read_bytes()
        self.assertEqual(self.step()['status'],'waiting-serving')
        self.assertNotIn('proofRelease',self.plan)
        self.assertEqual(len(self.nifi.calls),1)
        audit=self.plan['obsoleteSqlProofs'][0]
        self.assertEqual(audit['proofRunId'],directory.name)
        self.assertEqual(audit['quarantineSha256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(set(audit['stageEvidenceSha256']),{'rml','shacl','promote','emit'})
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(len(self.nifi.calls),2)
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(failure.read_bytes(),before)

    def test_exact_legacy_materializer_error_is_recognized_from_windows_log(self):
        self.step();self.obsolete_sql(legacy=True)
        self.assertEqual(self.step()['status'],'waiting-serving')

    def test_both_historical_and_nifi_stage_names_are_recognized(self):
        for stage in ('materialize','materialization'):
            with self.subTest(stage=stage):
                self.setUp();self.step();self.obsolete_sql(stage=stage)
                self.assertEqual(self.step()['status'],'waiting-serving')

    def test_windows_timestamp_precision_and_timezones_remain_exact(self):
        first=recovery.event_time('2026-09-15T14:40:14.4841705Z')
        self.assertEqual(first,recovery.event_time('2026-09-15T10:40:14.4841705-04:00'))
        self.assertLess(first,recovery.event_time('2026-09-15T14:40:14.4841706Z'))
        with self.assertRaisesRegex(ValueError,'Unqualified'):
            recovery.event_time('2026-09-15T14:40:14.4841705')

    def test_real_windows_stage_timestamp_format_allows_obsolete_code_recovery(self):
        self.step();directory,failure=self.obsolete_sql(legacy=True)
        self.plan['dispatchedAtUtc']='2026-09-15T14:39:34.749367Z'
        for i,action in enumerate(('rml','shacl','promote','emit')):
            path=directory/(action+'.json')
            recovery.save(path,{**recovery.read(path),'completedAtUtc':f'2026-09-15T14:40:{i:02}.4841705Z'})
        recovery.save(failure,{**recovery.read(failure),'quarantinedAtUtc':'2026-09-15T23:10:28.1685713Z'})
        self.assertEqual(self.step()['status'],'waiting-serving')

    def test_explicit_resume_preserves_failed_plan_and_queues_without_dispatch(self):
        self.step();directory,failure=self.obsolete_sql(legacy=True)
        self.plan.update(phase='failed',reason='Proof reached quarantine')
        recovery.save(self.path,self.plan);before=self.path.read_bytes();quarantine=failure.read_bytes()
        with patch.object(recovery,'NiFi',return_value=self.nifi):
            result=recovery.resume_obsolete_sql(self.root)
        self.assertEqual(result['status'],'queued')
        saved=recovery.read(self.path)
        self.assertEqual(saved['phase'],'waiting-proof')
        self.assertEqual(saved['resumedFailures'][0]['priorPlanSha256'],hashlib.sha256(before).hexdigest())
        self.assertEqual(failure.read_bytes(),quarantine)
        self.assertEqual(self.nifi.calls,[('run','proof')])
        self.plan=saved
        self.assertEqual(self.step()['status'],'waiting-serving')

    def test_explicit_resume_rejects_unrelated_failure_without_mutating_audit(self):
        self.step();directory,failure=self.obsolete_sql()
        (directory/'materialize.log').write_text(json.dumps(dict(status='failed',error='other failure')))
        self.plan.update(phase='failed');recovery.save(self.path,self.plan);before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'not a uniquely attributable'):
            recovery.resume_obsolete_sql(self.root)
        self.assertEqual(self.path.read_bytes(),before)

    def test_one_automatic_obsolete_sql_retry_per_implementation(self):
        self.step();self.obsolete_sql()
        self.assertEqual(self.step()['status'],'waiting-serving')
        self.step();self.obsolete_sql(run='b'*32)
        self.assertEqual(self.step()['status'],'failed')
        self.assertIn('already received',self.plan['reason'])
        self.assertEqual(len(self.nifi.calls),2)

    def test_obsolete_sql_quarantine_waits_for_both_sql_processors_to_be_idle(self):
        self.step();self.obsolete_sql()
        self.nifi.materialize['status']['aggregateSnapshot']['activeThreadCount']=1
        self.assertEqual(self.step()['status'],'waiting-proof')
        self.assertEqual(len(self.nifi.calls),1)
        self.nifi.materialize['status']['aggregateSnapshot']['activeThreadCount']=0
        self.assertEqual(self.step()['status'],'waiting-serving')

    def test_incomplete_failed_ambiguous_or_unattributed_proofs_cannot_auto_retry(self):
        def write_bad_shacl(directory):
            record=recovery.read(directory/'shacl.json');record['conforms']=False
            recovery.save(directory/'shacl.json',record)
        mutations=[lambda d,f:(d/'emit.json').unlink(),
                   lambda d,f:write_bad_shacl(d),
                   lambda d,f:self.plan.update(dispatchOutcome='uncertain'),
                   lambda d,f:(self.proof_root/'unrelated-new-run').mkdir(),
                   lambda d,f:recovery.save(d/'cleanup.json',{}),
                   lambda d,f:(d/'materialize.log').write_text(json.dumps({'status':'failed','error':'Database corruption'})),
                   lambda d,f:recovery.save(f,{**recovery.read(f),'gamePk':'different'}),
                   lambda d,f:recovery.save(f,{**recovery.read(f),'quarantinedAtUtc':'2020-01-01T00:00:00Z'})]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                # Each case gets its own dispatched intent and complete fixture.
                self.setUp()
                self.step();directory,failure=self.obsolete_sql();mutate(directory,failure)
                self.assertEqual(self.step()['status'],'failed')
                self.assertNotIn('obsoleteSqlProofs',self.plan)
                self.assertEqual(len(self.nifi.calls),1)

    def ready_refresh(self):
        self.step()
        self.release = {"released": True, "proofRunId": "new-run"}
        self.assertEqual(self.step()["status"], "ready-refresh")

    def test_checks_proof_again_before_backfill(self):
        self.ready_refresh()
        self.release = None
        self.assertEqual(self.step()["status"], "failed")
        self.assertEqual(self.nifi.calls, [("run", "proof")])

    def test_end_to_end_requires_matching_materialized_batch(self):
        self.ready_refresh()
        recovery.save(self.batch_root / "old.json", self.batch("old", "materialized"))
        self.assertEqual(self.step()["status"], "waiting-batch")
        self.assertEqual(self.step()["status"], "waiting-batch")
        unrelated = self.batch("other", "materialized")
        unrelated["requestedStartDate"] = "2026-08-24"
        recovery.save(self.batch_root / "other.json", unrelated)
        self.assertEqual(self.step()["status"], "waiting-batch")
        recovery.save(self.batch_root / "new.json", self.batch("new", "pending"))
        self.assertFalse(self.step()["deferMaterialization"])
        self.assertEqual(self.plan["batchId"], "new")
        recovery.save(self.batch_root / "new.json", self.batch("new", "materialized"))
        self.assertEqual(self.step()["status"], "complete")
        self.step()
        self.assertEqual(self.plan["servingBuildId"], "refreshed-build")
        self.assertEqual(self.nifi.calls, [("run", "proof"), ("configure", "backfill"), ("run", "backfill")])

    def batch(self, identifier, status):
        return {"artifactType": "baseballo-mlb-game-schedule-batch", "contractVersion": 1,
                "batchId": identifier, "status": status, "requestedStartDate": "2026-08-25",
                "requestedEndDate": "2026-08-25", "requestKind": "backfill",
                "servingBuildId": "refreshed-build"}

    def test_backfill_timeout_does_not_repeat_config_or_request(self):
        self.ready_refresh()
        self.nifi.fail_dispatch = True
        self.step()
        self.plan = recovery.read(self.path)
        self.step()
        self.assertEqual(self.nifi.calls, [("run", "proof"), ("configure", "backfill"), ("run", "backfill")])

    def test_ambiguous_batches_do_not_claim_completion(self):
        self.ready_refresh()
        self.step()
        for name in ("a", "b"):
            recovery.save(self.batch_root / (name + ".json"), self.batch(name, "materialized"))
        self.assertEqual(self.step()["status"], "failed")

    def test_failure_keeps_sql_guard_until_active_job_finishes(self):
        self.step()
        self.nifi.sql["status"]["aggregateSnapshot"]["activeThreadCount"] = 1
        recovery.save(self.failure_root / "new-run/failure.json", {"failedStage": "shacl"})
        self.assertTrue(self.step()["deferMaterialization"])
        self.assertTrue(self.step()["deferMaterialization"])
        self.nifi.sql["status"]["aggregateSnapshot"]["activeThreadCount"] = 0
        self.assertFalse(self.step()["deferMaterialization"])

    def test_no_plan_preserves_existing_batch_behavior(self):
        self.assertEqual(recovery.tick(self.root), {"status": "idle", "deferMaterialization": False})

    def test_read_failure_defers_dependent_work(self):
        recovery.save(self.path, self.plan)
        with patch.object(recovery.NiFi, "processor", side_effect=OSError("NiFi offline")):
            result = recovery.tick(self.root)
        self.assertEqual(result["status"], "recovery-error")
        self.assertTrue(result["deferMaterialization"])
        self.assertEqual(recovery.read(self.path)["phase"], "waiting-serving")


class NiFiBoundaryTests(unittest.TestCase):
    def test_rejects_nonlocal_or_redirect_targets(self):
        for endpoint in ("http://example.org/nifi-api", "http://user@localhost/nifi-api",
                         "http://localhost/nifi-api?redirect=1", "http://localhost/elsewhere"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                recovery.NiFi(endpoint)
        with self.assertRaises(ValueError):
            recovery.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_ownership_change_rejected(self):
        nifi = recovery.NiFi("http://127.0.0.1:8080/nifi-api")
        correct = entity("Proof Request", "proof")
        for key, value in (("parentGroupId", "other-source"), ("name", "Other Request"),
                           ("type", "other.Type"), ("id", "different")):
            wrong = copy.deepcopy(correct)
            wrong["component"][key] = value
            with patch.object(nifi, "call", return_value=wrong), self.assertRaises(ValueError):
                nifi.processor("proof", "source", "Proof Request", "GenerateFlowFile")

    def test_missing_active_status_is_not_idle(self):
        with self.assertRaises(KeyError):
            recovery.active({"status": {"aggregateSnapshot": {}}})

    def test_proof_gate_failure_is_not_a_release(self):
        with patch.object(recovery.subprocess, "run", return_value=SimpleNamespace(returncode=2, stdout="")):
            self.assertIsNone(recovery.proof_release(Path("unused")))

    def test_other_source_release_is_rejected(self):
        output = json.dumps({"released": True, "sourceModule": "mlb-people"})
        with patch.object(recovery.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output)):
            with self.assertRaises(ValueError):
                recovery.proof_release(Path("unused"))


class BatchIntegrationTests(unittest.TestCase):
    def test_recovery_error_stops_batch_before_inventory_or_sql_work(self):
        spec = importlib.util.spec_from_file_location("recovery_batch_test", SCRIPT.with_name("materialize-pending-batches.py"))
        batch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(batch)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recovery.save(recovery.plan_path(root), {"artifactType": "unknown", "contractVersion": 1})
            with patch.object(batch, "parse_args", return_value=SimpleNamespace(state_root=root)), \
                    patch.object(batch, "promotion_inventory") as inventory, \
                    patch.object(batch.subprocess, "run") as materialize, \
                    patch("builtins.print") as output:
                self.assertEqual(batch.main(), 0)
            inventory.assert_not_called()
            materialize.assert_not_called()
            result = json.loads(output.call_args.args[0])
            self.assertEqual(result["status"], "deferred")
            self.assertEqual(result["sourceRecovery"]["status"], "recovery-error")


if __name__ == "__main__":
    unittest.main()
