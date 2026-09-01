# BaseballO roadmap

This is the current ordered work queue. Completed implementation detail belongs
in subsystem documentation and Git history, not in this file.

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

## Current operational baseline (not semantic acceptance)

- MLB game mapping: 326 triples maps and 87 logical sources.
- Evidence corpus: 546 distinct completed games plus 43 schedule responses.
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
  one-shot submissions rather than recurring schedules. A 2026 season-to-date
  request for all seven lanes was submitted on 2026-09-01; its result must be
  read from terminal NiFi evidence after completion or failure.
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

## Immediate. Complete the submitted corpus lifecycle and downstream serving

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

- [ ] Emit immutable promoted-graph events from each successful source lane.
- [ ] Trigger single-source or multi-source approved SPARQL only from declared
  promoted-graph dependencies; do not couple acquisition lanes to one another.
- [ ] Build and validate persistent SQL serving candidates from those query
  outputs, then promote the serving build atomically.
- [ ] Keep serving failure isolated from authoritative RDF and every source
  acquisition lane.
- [ ] Rebuild the aggregate repository-validation/evidence stage after the
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
- [ ] Review terminal promotion, cleanup, quarantine, and batch-materialization
  evidence after NiFi completes the submitted run; do not poll it continuously.

## 0. Close discovered correctness gaps

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
- [ ] Require each static single-source SPARQL artifact to enforce its graph
  namespace itself, or register and test the exact runtime binder that does so.
- [ ] Capture current-contract SPARQL-to-SQL result equivalence per Explorer
  family before labeling the integrity-gated routes equivalence-proven.
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

- [ ] Add reusable pitch and runner-resolution SQL grains when an approved UI
  family needs them.
- [ ] Preserve comparable authoritative RDF, indexed RDF, and SQL timing
  evidence at matching corpus fingerprints.
- [ ] Introduce nightly incremental serving maintenance only after full rebuild
  and corrected-game replacement behavior are proven equivalent.
- [ ] Move additional Explorer families to SQL one at a time after row, filter,
  aggregation, and date-scope equivalence is demonstrated.

## Coding continuation

Git and GitHub operations are disabled until the user explicitly reauthorizes
them. Do not use the archived control-plane handoff as an implementation plan.
It records a discarded design.

Continue from the clean, proven seven-lane architecture. Do not monitor the
submitted corpus run continuously. When requested, or after NiFi records a
terminal failure, review its persisted evidence and repair the versioned cause.
After corpus promotion, add promoted-graph-event-driven SPARQL and SQL
materialization, close Explorer-family equivalence one family at a time, and
restore the aggregate repository-validation observer. Do not reproduce routine
pipeline work with attended scripts.
