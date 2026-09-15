# Deferred MLB proof and refresh

`resume-metric-source.py` advances a queued recovery from the existing
`Materialize Ready Schedule Batches` worker. The existing `Check Pending Batch
Materialization` trigger must be running at its contract's 15-minute interval.
No additional process group or acquisition schedule is introduced.

The worker waits for an explicitly named SQL build to appear in the promoted
serving pointer and for both known SQL processors to be idle. It then submits
the existing `Proof Request` once. After the existing source-proof checker
verifies a new completed run against current RML and SHACL, the worker submits
the existing `Backfill Schedule Request` for the queued date range. Batch
completion comes from the normal batch manifest after promotion and SQL
materialization; submission is never reported as completion.

Queue a bounded request with the configured runtime Python:

```text
python -B sources/mlb-game/pipeline/resume-metric-source.py --enqueue
  --state-root <runtime-state-root>
  --nifi-api http://127.0.0.1:8080/nifi-api
  --required-build-id <candidate-build-id>
  --source-group-id <MLB-Game-group-id>
  --sql-group-id <DSQ-serving-group-id>
  --sql-processor-id <Materialize-All-DSQs-processor-id>
  --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

The arguments above are one command, wrapped for readability. Enqueue only
writes the request after validating processor identity. NiFi performs the
work on subsequent ticks. Its durable status is
`pipeline/control/mlb-game/metric-source-recovery.json` under the runtime state
root. The batch worker loads the helper on each invocation, so updating this
helper does not require restarting the source group or the active SQL build.

For a scoring correction that makes an active build obsolete, enqueue with
`--proof-rebuilds-serving`. This waits for the known SQL processors to become
idle, then starts the normal proof even if the obsolete build did not promote.
The proof's existing materialization stage builds and validates the entire
serving product itself; a prior successful SQL build is not required for that
stage. The full current source-proof release gate still controls the backfill.
The audit records `idle-proof-will-rebuild` rather than claiming promotion.

An OS lock serializes recovery ticks. Dispatch intent is saved atomically
before `RUN_ONCE`. If the response is lost, later ticks inspect evidence and
never repeat that request automatically. A proof quarantine records failure
and preserves the failed inputs. An old completed proof or an old batch cannot
satisfy the new request. Multiple matching new batches fail attribution.
Read/configuration errors defer dependent materialization and appear in the
NiFi batch result. No stage evidence or semantic approval is synthesized.

A prerequisite build that never promotes leaves the request in
`waiting-serving`; an uncertain dispatch without downstream evidence remains
pending. These are explicit diagnostic states, not permission to erase an
audit or retry a potentially accepted request. A replacement request must
preserve the previous plan and resolve the recorded failure/uncertainty first.
The worker changes only the stopped backfill request's date payload and retains
its previous payload in the audit. It does not change the daily 05:00 Eastern
schedule or the normal two-attempt source-stage retry/quarantine policy.

This automates accepted source recovery. It does not implement missing player
score adapters, admit a new source, infer defensive acts, or turn a bounded
metric result into a complete player leaderboard.
