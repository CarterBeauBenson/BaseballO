# Deferred MLB proof and refresh

## Scope restriction: September 17

This helper runs source proof and full per-game replacement over a date range.
It is not a targeted RDF-addition mechanism or the entry point for SQL/metric
changes over the existing graph. Do not enqueue source recovery merely because
serving code, a calculation, or a validation fingerprint changed. Diagnose the
affected layer and keep the work there. If targeted source execution is needed,
implement it within the accepted lifecycle rather than substituting this broad
replacement path. See the [operating policy](../../../../AGENTS.md#incremental-work-and-minimal-manual-validation).

The user authorized completion of the already running September 17 batch
`2e0062c6ccff4630840108858425ed4f` after identifying the scope error. That is a
one-batch exception, not standing authorization for future season refreshes.
The mechanics below describe the existing implementation and remain relevant
to explicitly authorized source recovery; they are not a manual checklist.

## Existing recovery mechanics

The user restored the 15-minute `Check Pending Batch Materialization` trigger
on 2026-09-16 after its temporary shutdown. Its live state is running and the
source contract sets `batchMaterialization.periodicChecksEnabled` to true.
Provisioning preserves the explicit setting. Daily 05:00 Eastern acquisition
remains enabled.

`resume-metric-source.py` advances a queued recovery when the existing
`Materialize Ready Schedule Batches` worker is invoked. The periodic trigger
checks pending recovery and deferred batch materialization; a check does not
necessarily start a rebuild. Stopping it pauses those timer-driven checks.

The worker waits for an explicitly named SQL build to appear in the promoted
serving pointer and for both known SQL processors to be idle. It then submits
the existing `Proof Request` once. After the existing source-proof checker
verifies a new completed run against current RML, context builder and SHACL, the worker submits
the existing `Backfill Schedule Request` for the queued date range. Batch
completion comes from the normal batch manifest after promotion and SQL
materialization; submission is never reported as completion.

Only for an explicitly authorized source-recovery range, submit with the
configured runtime Python:

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

`--proof-rebuilds-serving` belongs to an already authorized source recovery,
not an ordinary scoring correction. It waits for the known SQL processors to become
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

Within an existing source-recovery request, an independently recorded SQL
implementation-change failure has a recovery path. It requires one new,
uniquely attributable quarantined proof,
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
When the previous plan is complete, `--enqueue` preserves its exact bytes in
`recovery-history/<sha256>.json` under the same plan lock before atomically
writing the new request. The new plan references that archive. Retrying the
archive step is idempotent; a corrupt archive or any pending/failed prior plan
is rejected without replacing it.
The worker changes only the stopped backfill request's date payload and retains
its previous payload in the audit. It does not change the daily 05:00 Eastern
schedule or the normal two-attempt source-stage retry/quarantine policy.

This automates accepted source recovery. It does not implement missing player
score adapters, admit a new source, infer defensive acts, or turn a bounded
metric result into a complete player leaderboard.

## Schedule qualification correction

The batch worker also invokes `schedule-qualification.py` when SQL is idle.
It repairs at most one retained incomplete schedule range per invocation using
the existing MLB schedule endpoint. A postponed occurrence can carry its later
makeup game's `officialDate`; the schedule parser now retains that explicitly
unplayed occurrence on its returned schedule date. It remains excluded from
played-game counts. Transport totals and all other completeness checks remain.

The worker selects only incomplete ranges that still own the latest retained
coverage for a date. It preserves the original batch, game requests and all
promotions. Successful coverage snapshots live separately under
`pipeline/control/mlb-game/schedule-coverage/<sha256>.json`, bound to the owning
batch, source-response hash and parser implementation. The SQL builder merges
current snapshots by observation time and preserves the snapshot hash in SQL.
An older successful snapshot cannot mask newer incomplete batch evidence.

The operation is idempotent per batch and implementation. Two failed transport
attempts stop acquisition for that batch/version; failed response bytes and
diagnostics remain in source-local quarantine. One quarantined range does not
prevent correction of unrelated ranges. The worker reports `scheduleCoverage`
in its normal result. No additional trigger or game refresh is created, and
the daily acquisition and 15-minute batch-check schedules remain in force.
