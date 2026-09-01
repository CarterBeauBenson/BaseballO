# NiFi control-plane hardening handoff

## Authority and target flow

- Carter decides BaseballO semantics and major pipeline topology.
- The accepted lifecycle is `API -> RML -> SHACL -> Fuseki -> queries -> SQL -> UI`.
- Within that accepted lifecycle, Codex owns ordinary engineering decisions:
  locking, no-op reconciliation, retries, staging, manifests, fingerprints,
  indexing, physical SQL design, equivalent query optimization, tests, and UI
  plumbing.
- Do not ask for file-by-file approval after the semantic meaning and topology
  are accepted. Stop only for a new semantic assertion, a new ontology term or
  relation, or a material change to the lifecycle topology.

## Completed in the first implementation slice

1. Semantic-change protection is responsibility based. Ontology, RML, SHACL,
   SPARQL, reasoning, and declared semantic-output contracts remain protected;
   NiFi scheduling, transport, locking, retry, and reconciliation code is not
   protected merely because a filename contains `rdf`, `rml`, or `context`.
2. `scripts/infra/nifi-control.ps1` is the shared process-group reconciliation
   primitive. The dedicated RDF configurator uses it and has an in-memory
   control-plane test suite. Exact no-op reconciliation performs no stop or PUT;
   partial mutation leaves the group stopped; explicit Disable does not require
   a valid current definition.
3. Query-index semantic compatibility is separated from implementation-byte
   provenance. `sparql/query-index/semantic-contract.json` is the semantic
   contract; current builds carry its ID and hash. Only five explicitly listed
   historical implementation hashes remain admitted through a fixed bridge.
4. Game promotion and source-lane admission use the source-neutral
   `game_promotion_inventory.py`, not the Explorer serving materializer.
5. The `game-team-season-v1` consumer grain requires exactly one home and one
   away assignment, distinct canonical Team IRIs, and authoritative Team
   typing. The requirement exists in query-index SHACL, live promotion checks,
   and the Teams preflight before acquisition.
6. Semantic-freeze validation runs inside the game-stage failure boundary at
   `assess` and again at `promote`. The assessed semantic-contract identity is
   pinned through `index` and `promote`; failures release the game lock and
   produce quarantine evidence.
7. Two stale benchmark routes fail closed to authoritative/rebenchmark-required
   rather than inheriting performance evidence from obsolete query text.

## Current next task for High

Complete one prerequisite slice: migrate
`scripts/infra/configure-nifi-source-lanes.ps1` to the existing shared
`scripts/infra/nifi-control.ps1` reconciler. Commit and push that migration,
then stop. Do **not** implement the dependency outbox in the same slice.

This comes first because the six source-lane groups are the destinations for
the coming Game batch -> Teams -> Leagues/Divisions automation. The current
configurator has no process-safe lock or bounded fresh-revision conflict retry,
rewrites every existing processor and connection, and can stop a healthy lane
during a configure-only rerun. Each lane is a separately owned dedicated group
and is therefore a direct fit for the shared closed-inventory reconciler.

### Required implementation scope

1. Reconcile one selected module group at a time under a process-safe source-
   lane configuration lock. Use one
   `Invoke-NiFiProcessGroupReconciliation` call per group.
2. Preserve the existing six groups, processor and connection names, 13-stage
   order, retry/quarantine graph, stopped-default creation behavior, 10-object
   and 10-MB backpressure thresholds, and `-Enable`/`-EnableModule` behavior.
3. Treat module selection as both mutation scope and enablement scope. An
   `-EnableModule mlb-teams` invocation must not discover, stop, validate,
   configure, or start any other source group.
4. Default Configure preserves the prior states of a valid existing group.
   Exact desired equality performs zero stop, state, processor PUT, or
   connection PUT operations.
5. Add explicit per-module Disable as `-DisableModule`. Keep it mutually
   exclusive with enable modes and never infer an all-lane disable from default
   Configure.
6. Use a fresh-revision REST adapter with bounded 409 retry. Reject duplicate or
   stale closed inventory before mutation. Reject a topology rewire while its
   connection has queued FlowFiles. A partial mutation or validation failure
   leaves only that selected group stopped.
7. Keep the desired-contract builder reusable by an offline fake-adapter test;
   do not copy the 32-processor/70-connection topology into the test as a
   second implementation.

Expected files are:

- `scripts/infra/configure-nifi-source-lanes.ps1`;
- optionally one small source-lane definition-builder helper under
  `scripts/infra/`;
- new `scripts/pipeline/test-nifi-source-lane-control.ps1`;
- `scripts/pipeline/test-source-lane-orchestration.py`;
- `infra/nifi/README.md`; and
- `scripts/validate_repository.py` only as needed for Stage 91 to own the new
  focused test.

Do not modify `nifi-control.ps1` unless the offline state machine proves a
source-neutral defect in the shared primitive. Do not change lane JSON, source
schemas, ontology, RML, SHACL, SPARQL, SQL, or UI in this slice.

### Required offline proof

- All six desired contracts contain exactly 32 processors and 70 connections.
- A healthy running exact match is a true zero-mutation no-op.
- Selecting Teams leaves all five unselected groups completely unobserved.
- Drift causes a stable whole-group stop, minimal repair, validation, and exact
  prior-state restoration under Configure.
- Enable finishes with every selected processor running; explicit Disable can
  stop a stale or invalid selected group without first validating it.
- Duplicate/stale inventory, queued topology rewiring, partial update failure,
  and validation failure all fail closed before any hybrid group can run.
- A 409 refreshes revisions and retries within the shared bound.
- Lock contention fails within its bound.
- Existing 13 source-lane fixture tests and the RDF shared-reconciler control-
  plane suite still pass.

Use fake adapters and temporary state only. Do not contact NiFi, Fuseki, MLB, or
the SSD. Do not configure, enable, retry, or monitor a live flow. Do not run the
aggregate repository validator manually. After the focused checks pass, commit
all in-scope changes, push `dev`, report the commit and evidence, and stop.

This is ordinary engineering already authorized by the accepted
`nifi-control-plane-hardening` design. Do not create another proposal or ask
for renewed semantic approval.

## Subsequent slices; do not start in the current task

1. Implement durable source-completion evidence plus an idempotent dependency
   outbox dispatcher. Teams completion should drive Leagues and Divisions.
   Dispatch failure must not invalidate a successful upstream completion.
2. Add typed trigger pointers and hashes so an automated Teams run consumes its
   exact completed Game batch and automated League/Division runs consume their
   exact Teams completion. Global backfill must remain an explicit mode.
3. Add the bounded lifecycle proof:
   promoted game evidence -> exact Teams preflight -> Teams completion ->
   durable downstream dispatch. Component tests alone do not prove this phase.
4. Let NiFi own aggregate repository validation and all repeatable runtime work.
   Do not start or continuously watch a live flow merely to finish this handoff.

## Review and testing rules

- Review evidence produced by NiFi; do not turn Codex back into the scheduler.
- Use focused developer tests for the component being changed. Stage 91 remains
  the aggregate repository gate.
- Never weaken ontology, RML, or SHACL to make an operational test green.
- The former People, Venues, and Transactions fixture failures were stale
  source-owned SHACL contracts and were repaired in `a8ec24e`; the full
  source-lane fixture suite passes. Their RML graph semantics were already
  accepted. Aligning an owning module's SHACL profile, fixtures, and byte pins
  to an accepted RML contract is ordinary engineering under the existing
  authorization. Do not create a new semantic proposal unless a repair would
  introduce genuinely new meaning.
- `Baseball/ontology/catalog-v001.xml` is a local Protege import catalog. It is
  user-owned and must not be staged, discussed as a pipeline artifact, or
  altered by this work.
