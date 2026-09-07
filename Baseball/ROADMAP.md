# BaseballO roadmap

This is the current ordered work queue. Completed implementation detail belongs
in subsystem documentation and archived design records, not in this file.

## Fixed architecture

```text
transient API payloads
  -> persistent authoritative source-owned RDF
  -> rebuildable indexed RDF
  -> persistent derived SQL serving builds
  -> Explorer
```

- Authoritative RDF is the semantic research record and remains available for
  arbitrary historical SPARQL.
- Indexed RDF and SQL are derived, replaceable, and reproducible from RDF.
- NiFi owns scheduling, source isolation, validation gates, promotion, retry,
  quarantine, and provenance.
- Every source owns separate schema, RML, SHACL, and NiFi boundaries. The
  triple store is the first shared integration space.
- Routine Explorer families move to validated SQL grains only after their
  end-to-end equivalence is accepted. Live SPARQL remains for new research,
  definitions, audits, backfills, and unmigrated questions.

## Implemented baseline and runtime-status boundary

- MLB game mapping: 345 triples maps and 98 logical sources. The generated
  Mermaid catalog is the authoritative current coverage count.
- Query library: 51 canned, 17 advanced, and 19 reviewed
  authoritative/index equivalence pairs.
- Explorer: shared grains for routine families can be materialized, but only
  PAQ/Good At Bat is admitted as the visible SQL-backed slice. Advanced,
  Simple Explore, Empty Games, and Derived remain on their authoritative
  SPARQL paths until family-specific equivalence is demonstrated. The current
  materializer has source-corpus, row-preservation, and SQLite integrity gates.
- NiFi: the clean runtime contains seven independent source-owned lanes for
  Games, Teams, Leagues, Divisions, People, Venues, and Transactions. Their
  bounded proofs passed RML, source SHACL, promotion, and cleanup; the Game
  proof also passed index promotion and SQL materialization. Daily 05:00
  Eastern triggers are enabled. Proof and corpus operations are explicit
  one-shot submissions rather than recurring schedules.
- Shared downstream NiFi: every source lane now emits an immutable promoted-
  graph event before cleanup. `Analytical Serving` consumes declared authority
  dependencies into an immutable SQLite build, `Repository Evidence` runs the
  aggregate repository gate daily at 06:30 Eastern without controlling source
  lanes, and `Serving Equivalence` owns manual pre-admission family proofs.
- MLB reference/event modules: Teams, Leagues, Divisions, People, Venues, and
  Transactions have approved semantic contracts with no open modeling blockers.
  Each owns an endpoint-specific connector, source-owned NiFi process group,
  proof-gated corpus request, retry/quarantine path, and bounded proof evidence.
- Statcast: rejected implementation removed; no Statcast RML or authoritative
  graph is accepted. Fresh process-profile, geometry, expectancy, and alignment
  Mermaids are under ontologist review.
- Semantic governance: the pinned MLB-game and reference-module executable
  surfaces are accepted and frozen against unreviewed extension. Exact known
  ontology debt and unresolved future-source work remain machine-readable; new
  debt or an unreviewed protected-file change fails.

Live graph counts, active queues, quarantines, submitted batches, and current
SQL build IDs are intentionally absent from this roadmap. Read those facts from
NiFi's terminal evidence, the graph store, and the machine-local serving
pointers. A submitted request is never documented as completed work.

## Immediate. Complete the corpus lifecycle and downstream serving

Do not describe BaseballO as ready for ingestion merely because an individual
mapping, source lane, or control primitive passes. Ingestion readiness means
the complete accepted lifecycle is unattended, recoverable, evidence-producing,
and proven through the first bounded live run:

```text
API -> RML -> source SHACL -> authoritative Fuseki promotion
    -> indexed RDF -> approved SPARQL -> SQL serving build -> UI
```

### A. Clean runtime and common lifecycle

- [x] Remove the abandoned NiFi flow and its runtime state without migrating,
  snapshotting, or reconciling it.
- [x] Reconfigure the local NiFi runtime on loopback and prove that the new
  canvas starts empty.
- [x] Implement the first source-owned lifecycle in `sources/mlb-game/`:
  acquire -> RML -> source SHACL -> recoverable authoritative/index promotion
  -> approved SQL materialization -> transient cleanup.
- [x] Give the Game lane bounded retry and source-local quarantine without
  recreating a repository-wide control plane.
- [x] Submit one bounded Game proof asynchronously.
- [x] Review only the proof's completed or quarantined evidence and repair any
  defect it actually reports.

### B. Independent MLB API connectors and lanes

Every item below is a peer acquisition lane. Games do not acquire, trigger, or
own the reference/event APIs. Each connector may run on its own appropriate
schedule and may be disabled without stopping any other connector.

- [x] MLB Games: retain the source-owned proof lane; after it passes, add the
  authorized daily 05:00 Eastern schedule and completed-game discovery.
- [x] MLB Teams: add its own API connector, transient staging, accepted RML,
  source SHACL, authority-graph promotion, retry, quarantine, and provenance.
- [x] MLB Leagues: add its own API connector and complete independent authority
  lifecycle.
- [x] MLB Divisions: add its own API connector and complete independent
  authority lifecycle.
- [x] MLB People: add its own API connector and complete independent person
  authority lifecycle.
- [x] MLB Venues: add its own API connector and complete independent venue
  authority lifecycle, including the accepted dimensions coverage.
- [x] MLB Transactions: add its own API connector and complete independent
  event-evidence lifecycle.
- [x] Give each lane one deterministic first-record or smallest-valid-response
  proof. Review only completed/quarantined evidence; do not continuously watch
  running processors.

### C. Shared work begins only after promotion

- [x] Emit immutable promoted-graph events from each successful source lane.
- [x] Trigger single-source or multi-source approved SPARQL only from declared
  promoted-graph dependencies; do not couple acquisition lanes to one another.
- [x] Build and validate persistent SQL serving candidates from those query
  outputs, then promote the serving build atomically.
- [x] Keep serving failure isolated from authoritative RDF and every source
  acquisition lane.
- [x] Rebuild the aggregate repository-validation/evidence stage after the
  source-owned lanes exist; it is an asynchronous observer/gate, not their
  controller.

### D. Activation

- [ ] Run one bounded unattended multi-lane proof through independent API
  acquisition, source-owned semantic gates, RDF promotion, approved SPARQL,
  SQL, and the UI.
- [x] Mark each lane active only after its own proof passes; one failed lane
  must not block activation of an unrelated proven lane.
- [x] Submit the season/corpus run only after the relevant lanes and downstream
  materialization lifecycle have passed their bounded proofs.
- [ ] For the next activation proof, review terminal promotion, cleanup,
  quarantine, and batch-materialization evidence after NiFi completes; do not
  poll it continuously.

## 0. Close discovered correctness gaps

- [ ] Replace the retired port-8443 NiFi liveness probes in
  `scripts/infra/migrate-rdf-storage.ps1` with the replacement runtime's shared
  port configuration, then prove stop/restart behavior without moving the
  already configured RDF store.
- [ ] Resolve the three frozen structural findings for
  `GroundedIntoDoublePlayProcess` only after its source-independent
  institutional and ground-ball differentiae are reviewed. The obsolete six
  release-metadata findings are no longer present in the current 0.6.0,
  2026-08-30 ontology documents and are not current work.
- [x] Repair the semantic-freeze manifest generator so it refreshes every
  already pinned runtime admission while rejecting any catalog module that
  lacks an explicit prior pin. The accepted 2026-08-31 measurement,
  classification, and lifecycle decision authorizes this bounded repair.
- [x] Resolve the former thirteen executable MLB-game semantic blockers. The
  corrected pinned mapping was accepted on 2026-08-31; historical findings
  remain in `sources/mlb-game/SEMANTIC-AUDIT.md` as curation evidence.
- [x] Make corrected-game authoritative/index graph-pair replacement recoverable
  as a unit. A single Graph Store `PUT` is atomic, but the two-graph sequence is
  not; preserve or restore the previously promoted pair if index construction
  fails after authoritative replacement.
- [x] Make game-promotion evidence immutable and record transient-payload
  cleanup as a separate event instead of rewriting the promotion marker.
- [x] Require each static single-source SPARQL artifact to enforce its graph
  namespace itself, or register and test the exact runtime binder that does so.
- [ ] Capture current-contract SPARQL-to-SQL result equivalence per Explorer
  family before labeling the integrity-gated routes equivalence-proven. The
  fail-closed candidate/read boundary, exact result comparator, immutable
  evidence format, complete Explore option-list comparison, and manual NiFi
  lane now exist; no pending family is admitted until its proof actually
  passes and is reviewed. Fingerprint mismatches record both compared values
  rather than only a generic failure. Submission of an equivalence run does
  not change route admission.
- [ ] Migrate `game_dimension.game_set` serving extraction from compact
  acquisition provenance to the accepted authoritative season-phase RDF, prove
  historical equivalence, and rebuild the serving layer. Fixture membership
  remains a separate corpus-provenance classification.
- [ ] Split source-specific checks out of the shared NiFi evidence group as new
  source modules arrive; shared orchestration may depend on source outputs but
  must not own their semantics.

## 1. Finish the MLB game API module

- [ ] Inventory useful feed/live fields not represented by the current graph.
- [ ] Mark every candidate as already represented, deterministically derived,
  identity/join-only, genuinely additional, or unresolved.
- [ ] Group genuinely additional fields by real-world referent rather than JSON
  location.
- [ ] Create source-independent Mermaid in the canonical proposal catalog and
  obtain ontologist approval before changing ontology or RML.
- [ ] Add accepted source-specific Mermaid, RML, and SHACL only inside
  `sources/mlb-game/`.
- [ ] Prove each coherent extension on one record and one complete game before
  bounded corpus promotion.
- [ ] Preserve existing graph identities and query contracts unless an explicit
  migration is reviewed.

## 2. Add the remaining MLB APIs as separate modules

Create independent modules for:

- [x] teams, leagues, and divisions;
- [x] people and players;
- [x] transactions; and
- [x] venues.

Shared MLB identifiers support joins in RDF; they do not justify shared RML,
SHACL, staging, or failure handling. Each module must be independently
disconnectable and independently promotable.

- [x] Let NiFi run each admitted module's deterministic first-unit proof and
  release bulk/daily acquisition only after successful RML, SHACL, graph
  promotion, and cleanup with the current mapping and SHACL hashes. Do not make
  an attended Codex session the proof/backfill gate.
- [ ] Review the independently packaged field gaps in `proposals/`; implement
  only those explicitly accepted in a later change.

## 3. Restart Statcast from zero

- [x] Build a fresh non-duplicative field inventory against all accepted MLB
  API coverage.
- [x] Identify candidate world-side qualities, processes, geometry, units,
  estimates, and measurement-process evidence before defining information
  artifacts; do not invent a measuring Act from a reported result.
- [ ] Reuse accepted BFO, CCO, and BaseballO terms; record ontology gaps instead
  of creating field-shaped ICE classes.
- [x] Produce review-only Mermaid for process profiles, bat/arm geometry,
  expectancy outputs, and defensive alignment.
- [ ] Obtain explicit ontologist decisions on those active packages and resolve
  every blocker before writing Statcast RML.
- [ ] After approval, create a standalone Statcast module with its own RML,
  SHACL, NiFi lane, graph namespace, and one-game proof.
- [ ] Do not restore or imitate rejected Statcast artifacts.

## 4. Later source families

- [ ] Weather observations and forecasts.
- [ ] Travel, rest, time-zone, and circadian derived evidence.

Each begins as a separate source module and joins existing knowledge only in
the triple store through explicitly multi-source SPARQL.

## 5. Serving and performance follow-through

- [ ] With no corpus work active and after recording terminal evidence,
  reorganize the NiFi canvas without changing runtime behavior. Keep the root view limited to
  the seven detachable source lanes and shared downstream work; show each
  source lane as `Acquire -> Map -> Validate -> Promote -> Materialize`, with
  retry, failure, quarantine, cleanup, proof, and provenance processors
  encapsulated in nested process groups. Preserve every connector, schedule,
  queue, relationship, retry limit, evidence contract, and source-isolation
  boundary, and prove the reorganized flow against the existing terminal
  evidence before replacing the current canvas.
- [ ] With no corpus work active and after recording terminal evidence, remove
  the MLB-game promotion bottleneck by splitting parallel, isolated query-index
  preparation from the single-writer graph-pair promotion stage. Keep the accepted RML,
  source SHACL, query-index CONSTRUCT queries, graph identities, retry policy,
  and RDF semantics unchanged.
- [ ] Run query-index construction, query-index SHACL, and authoritative/index
  row-equivalence against each validated per-game RDF artifact before promotion,
  using two bounded Jena workers. Produce a hashed immutable index artifact and
  manifest for the writer to consume.
- [ ] Keep one short serialized promotion writer with a per-game lock. It must
  verify artifact hashes, recoverably promote the authoritative/index graph
  pair, perform combined post-write verification, record immutable evidence,
  and only then release cleanup.
- [ ] Before deploying the split flow, prove it on 50 games: authoritative RDF
  hashes, indexed row sets, and triple counts must match the current contract;
  every submitted game must terminate as promoted or quarantined; and measured
  throughput must improve. Do not deploy or reconcile promotion changes while
  corpus work is active.
- [x] Add reusable pitch and runner-resolution SQL grains for the candidate
  Explorer routes. The runner grain is keyed by one reviewed resolution and
  correlates stolen-base evidence through the resolution's Baseball Event
  Record; UI admission still waits for family equivalence.
- [x] Add a hash-pinned DSQ module catalog and safe compiler over every current
  query-index fact grain. Version 1 permits one primary fact grain, reviewed
  game dimensions, distinct counts, and additive reduction across disjoint
  game partitions; it rejects unreviewed fact-to-fact joins and batch averages.
- [x] Give all 56 approved static DSQs persistent SQL coverage: 17 reviewed
  Advanced questions and 39 non-option canned questions. Each DSQ owns a named
  graph-partitioned table, exact query and reducer hashes, projected-variable
  metadata, binding counts, and dimension indexes. This is candidate
  materialization only; each UI route still requires end-to-end equivalence.
- [x] Add a separate hash-pinned authority-RDF module catalog for reusable
  Person, Organization, Venue, Day, name, identifier, measurement, handedness,
  position, coordinate, capacity, and playing-surface evidence. Preserve the
  accepted world-side/ICE patterns, source-lane intersection, graph provenance,
  and replace-by-authority-graph SQL contract.
- [x] Add NiFi materialization stages and SQL tables for the authority specs.
  The materializer retains exact RDF bindings, proves source-graph replacement
  in focused tests, and promotes an immutable pointer. UI authority lookups
  remain future consuming features; any rebuild still requires terminal
  evidence before it is described as current.
- [ ] Add explicit, equivalence-tested bridge modules only when a DSQ needs to
  join two fact grains, then let NiFi compile and materialize that admitted
  question through the existing serving lifecycle.
- [ ] Preserve comparable authoritative RDF, indexed RDF, and SQL timing
  evidence at matching corpus fingerprints.
- [ ] Make full serving rebuilds checkpointed across disjoint game batches so a
  failed graph/query retries only its incomplete batch. Preserve the immutable
  final database, complete-corpus integrity checks, and atomic pointer swap;
  do not turn partial batch databases into UI-readable builds.
- [ ] Introduce nightly incremental serving maintenance only after full rebuild
  and corrected-game replacement behavior are proven equivalent.
- [ ] Move additional Explorer families to SQL one at a time after row, filter,
  aggregation, and date-scope equivalence is demonstrated.

## 6. Redesign the primary offensive analytics

The working category definitions and implementation boundary are recorded in
[`web/OFFENSIVE-ANALYTICS-REDESIGN.md`](web/OFFENSIVE-ANALYTICS-REDESIGN.md).
That note does not alter PAQ-1.0 or approve a replacement formula.

- [ ] Diagnose the game-context query and prove that starting base/out, inning,
  and score evidence is not contaminated by events or state produced during
  the plate appearance.
- [ ] Add focused regression examples for runner movement, inning-ending runner
  outs, two-out situations, runs scoring, and walk-offs.
- [ ] Name and define the fifth primary offensive category; four are currently
  identified: Damage, Grind, PAQ, and Empty Game.
- [ ] Define the supported plate-appearance, game, stretch, and season behavior
  for each category, including whether the result is a total, average, count,
  or ratio.
- [ ] Review PAQ-2.0 with outcome at approximately 60% and explicitly decide
  how context, Grind, and batted-ball quality share the remaining weight.
- [ ] Keep PAQ-1.0 reproducible and introduce PAQ-2.0 as a separately versioned
  analytic only after review.
- [ ] Materialize corrected reusable context and offensive grains through NiFi,
  then admit each SQL route only after exact same-corpus equivalence.

## Coding continuation

Git and GitHub operations are disabled until the user explicitly reauthorizes
them. Do not use the archived control-plane handoff as an implementation plan.
It records a discarded design.

Continue from the clean, proven seven-lane architecture. Do not monitor the
normal NiFi runs continuously. When requested, or after NiFi records a terminal
failure, review persisted evidence and repair the versioned cause.
Promoted-graph-event-driven authority SPARQL and SQL materialization and the
aggregate repository-validation observer now exist. Review their terminal
NiFi evidence when requested, then close Explorer-family equivalence one
family at a time. Do not reproduce routine pipeline work with attended
scripts.
