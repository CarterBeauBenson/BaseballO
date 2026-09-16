# Deferred MLB proof and refresh

The user disabled the 15-minute `Check Pending Batch Materialization` trigger
on 2026-09-16. Its live state is stopped and the source contract now sets
`batchMaterialization.periodicChecksEnabled` to false. Provisioning, including
`StartDaily` and `RunBackfill`, preserves that choice. Daily 05:00 Eastern
acquisition remains enabled. Already queued or running work is not cancelled.

`resume-metric-source.py` advances a queued recovery when the existing
`Materialize Ready Schedule Batches` worker is invoked. With the periodic
trigger stopped, there are no timer-driven checks to advance pending recovery
or deferred batch materialization. The workflow below describes the worker's
behavior when invoked; it does not authorize re-enabling the timer or replacing
it with a different recurring schedule.

The worker waits for an explicitly named SQL build to appear in the promoted
serving pointer and for both known SQL processors to be idle. It then submits
the existing `Proof Request` once. After the existing source-proof checker
verifies a new completed run against current RML, context builder and SHACL, the worker submits
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

If the existing release checker finds all required successful stages and
cleanup for a new proof, but its mapping, context-builder or SHACL hash is now obsolete, the
worker preserves that completion and its stage hashes in `supersededProofs`.
After the known processors become idle it queues a new proof on the next
tick. The obsolete proof never releases backfill. Missing completion, an
ambiguous dispatch, failed conformance or quarantine cannot take this path;
multiple new obsolete completions require attribution instead of a retry.

An independently recorded SQL implementation-change failure has a separate
recovery path. It requires one new, uniquely attributable quarantined proof,
an accepted dispatch, successful RML/SHACL/promotion/event-emission records,
ordered completion timestamps, and the materializer's terminal
`implementation-changed` result. The exact prior materializer error
`Metric implementation changed during materialization` is also recognized,
including its Windows UTF-16 command log. Missing stages, nonconformance,
ambiguous requests, unrelated errors, and multiple candidates never qualify.

After both SQL processors are idle, the worker records the quarantine,
command-log and successful-stage hashes in `obsoleteSqlProofs`, then queues a
new full proof on the next tick. The original quarantine and inputs remain
untouched. This is limited to one automatic proof per current metric/build
implementation revision. It does not release the failed proof or reset the
source stage's two-attempt retry policy. Repeated failure under the same
implementation requires a focused fix.

The classifier accepts both historical `materialize` and the actual NiFi
`materialization` stage name. Evidence ordering preserves the seventh decimal
digit emitted by Windows/.NET timestamps; parsing or rounding it to Python's
microsecond resolution must not reject or reorder valid stage evidence.

A plan already marked failed by an older classifier can be reopened with:

```text
python -B sources/mlb-game/pipeline/resume-metric-source.py
  --state-root <runtime-state-root> --resume-obsolete-sql
```

This command validates the exact obsolete-implementation failure and existing
NiFi processor ownership, retains the prior plan hash and failure in
`resumedFailures`, and queues `waiting-proof`. It does not dispatch a processor.
The normal NiFi worker waits for idle processors and owns the retry. A second
retry for the same implementation, a different error, a missing successful
stage or an ambiguous run remains rejected. The quarantine is unchanged.

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
