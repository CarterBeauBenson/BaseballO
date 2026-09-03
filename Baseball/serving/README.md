# Analytical serving layer

This directory defines BaseballO's rebuildable SQL serving contract. SQLite was
selected for the first release because it ships with the installed Python
runtime, has no server lifecycle, and supports immutable versioned files. DuckDB
is not installed on the deployment host; the versioned contract keeps a later
engine change possible if columnar workloads demonstrate a benefit.

The analytical fact rows are derived from persistent authoritative RDF. The
database is operationally persistent but is never a source of truth.
`materialize-serving-layer.py`
queries bounded authoritative game graphs, validates promotion evidence, live
graph-pair identity, SQLite integrity, foreign keys, and retained binding
hashes. It also round-trips every directly materialized source row through
SQLite and requires exact source/stored row counts and streaming row-sequence
hashes before recording evidence-schema version 2. It records timing evidence
and only then atomically replaces the local
`serving/current.json` pointer. Those checks establish integrity, not
end-to-end SPARQL-to-SQL result equivalence. A failed build leaves the prior
pointer unchanged.

Reference authority facts use a separate immutable SQLite product and pointer
under `%LOCALAPPDATA%\BaseballO\state\serving\authority`. Immutable promoted-
graph events identify the exact source graph and promotion evidence. The
authority materializer executes only query specifications that declare that
source as a dependency, replaces a corrected graph's complete SQL partition,
validates every retained RDF binding hash, and atomically promotes
`authority/current.json`. It never changes the game serving pointer.

Before the final pointer swap, the materializer retains at most three database
files: the candidate, the prior current build, and the newest remaining
rollback build. Compact evidence is retained. Use `--retain-builds` to raise
the limit, never below two.

There is one explicit authority gap before RDF-only rebuildability can be
claimed: `game_dimension.game_set` currently comes from compact acquisition
provenance for new runs and checked schedule evidence for the historical corpus
because the authoritative MLB-game RDF has no accepted game-type
classification. The materialized baseball facts remain RDF-derived, but
reconstructing the current regular-season/All-Star partition also requires that
evidence. Do not infer the partition from team IDs, dates, labels, or absence.
The MLB-game ontology/RML must model the source-supported distinction after
ontologist review; fixture membership must remain a separate corpus-provenance
concern. Until that migration and backfill are complete, the serving contract
records this dependency instead of claiming complete RDF-only recovery.

Contract 5 materializes shared grains for every routine Explorer family and
the complete approved static DSQ surface: 17 reviewed Advanced questions plus
39 non-option canned questions. [`dsq-materializations.json`](dsq-materializations.json)
is the exact machine-readable inventory. Each question has its own physical
`dsq_*` SQLite table, its own query hash, reducer contract, projected-variable
manifest, binding count, graph index, and dimension indexes. Rows retain exact
SPARQL JSON terms and the authoritative game graph from which they came, so a
question can be filtered, rebuilt, or equivalence-tested without traversing
the full RDF corpus in front of the user. The older `advanced_result_fact`
table remains temporarily as a compatibility copy for the existing Advanced
candidate reader.

The authoritative SPARQL file remains the semantic identity of every DSQ.
Fourteen canned DSQs currently execute through the indexed query selected by
`operational-query-routing.json`; each has preserved equivalence evidence and
the same projected-variable contract. The remaining 42 execute against the
authoritative graph. Both the semantic query and selected execution query are
hash-pinned in `dsq_query_manifest` and the immutable build evidence.

Materialization is not
route admission. The rollout gate admits the shared reusable grains and exposes
only Plate Appearance Quality/Good At Bat as the visible SQL-backed vertical
slice. Advanced Questions, Simple Explorer families, Empty Games, and Derived
remain pending until each has reviewed end-to-end SPARQL-to-SQL equivalence.
Option lookup is admitted only as support for the PAQ/Good At Bat slice.
Every DSQ runs against one authoritative game graph at a time; its exact
bindings are retained with graph scope and hashes. SQL applies date, game,
season, venue, team, and declared result filters, then uses the versioned
[`advanced-query-reducers.json`](advanced-query-reducers.json) contract to
recombine additive results and preserve the reviewed ordering. This is a
reusable per-game analytical grain, not a cache of rendered pages.

The 12 option lookups are not DSQs. They remain derived from the shared SQL
dimensions and facts, rather than receiving redundant per-question result
tables.

New additive DSQs should use the guarded
[`sparql/query-modules/`](../sparql/query-modules/) contract. It compiles
reviewable indexed-RDF queries from accepted fact grains and records the SQL
merge rule alongside the question. NiFi executes those queries in disjoint
game batches; SQLite sums the sufficient statistics and derives corpus-wide
rates only after all partitions are combined. The first compiler version does
not admit cross-fact joins or averages, so those require an explicit reviewed
module/reducer extension rather than ad hoc query text.

Reusable authority dimensions use the separate
[`authority/catalog.json`](../sparql/query-modules/authority/catalog.json).
Those nodes read only independently promoted source graphs and return complete
evidence grains: for example, a Person name includes the Name ICE, while a
height includes the Height quality, Measurement ICE, value, and unit. They are
materialized separately from event aggregates and keyed by `authorityGraph`.
When an authority graph changes, SQL replaces that graph's partition rather
than treating corrected evidence as an append. Presentation rules such as
choosing one display name belong in SQL/UI views and do not erase the retained
name evidence.

Plate Appearance Quality additionally has a typed plate-appearance table for
its two admitted UI views. Candidate data for Simple Explore can aggregate
batting-result, pitch, runner-event, game, and assignment grains. Candidate data
for Empty Games and Build a Metric can share a completeness-gated player-game
grain, while damage analysis can join separate failed-PA evidence. Those
candidate capabilities exist for backfill and equivalence work; they do not
admit those Explorer families to SQL serving.

The batting, pitching, and assignment extractors use reviewed-compatible
query-index facts for identities and containment whose RDF query pairs were
proven equivalent, then join only
the authoritative context omitted by index contract 1, such as offensive team
or detailed MLB pitch-call code. The measured mixed runner plan was slower, so
baserunning remains an authoritative batch extraction. A missing or stale index
causes the candidate to fail instead of silently materializing partial facts.
That RDF-layer evidence does not by itself prove the later SQL reduction or UI
result equivalent.

That shared plate-appearance grain supports two routine views without another
Fuseki traversal: individual plate appearances and player-level average PAQ.
The latter groups the same reviewed rows by batter, reports a three-decimal
average plus band counts, and can be sorted in the Explorer by player or score.
The Python read adapter emits ASCII-safe JSON escapes at the process boundary
so Node reconstructs Unicode player names consistently on Windows; names remain
Unicode in RDF, SQLite, and the browser.

PAQ-1.0 is defined by [`plate-appearance-quality-v1.json`](plate-appearance-quality-v1.json).
It produces one `.000`–`1.000` rating per plate appearance from MLB outcome,
the existing bounded grind evidence, and situational evidence. The rating
contract, query, schema, materializer, mapping, and read
adapter hashes are all recorded in each immutable build. A change to any one
of them makes the prior build stale.

## Rebuild and backfill

NiFi owns rebuild and backfill orchestration. A rebuild request enters the
promotion-driven serving lane only after its declared authoritative/index graph
pairs have matching promotion evidence. NiFi then invokes the checked-in
materializer, validates the immutable candidate, records benchmark and failure
evidence, and atomically promotes the pointer. The materializer is a pipeline
component, not the normal human-facing workflow.

For focused developer diagnosis only, `materialize-serving-layer.py --max-games
1 --no-promote` exercises one game without changing the serving pointer. It
does not replace the NiFi lifecycle or authorize a production backfill.
Promotion does not create an equivalence claim.

`serving/nifi/provision.ps1` owns incremental authority-event materialization
and explicit full RDF rebuilds. A full authority rebuild was submitted on
2026-09-03. Its terminal evidence, rather than submission, determines whether
an authority serving build was promoted.

`serving/dsq-nifi/provision.ps1 -RunFullBackfill` submits a full 56-DSQ game
backfill once and returns immediately. Normal post-ingest refresh remains in
the MLB Game pending-batch lane. The dedicated group exists so backfill and
failure handling can be changed without touching a source connector or the
authority-serving group.

## Family equivalence and admission

The manual `Serving Equivalence` NiFi group is the pre-admission gate. It starts
a token-protected loopback Explorer child process, sends the same request
through a forced authoritative path and an isolated candidate-SQL path, then
requires the exact projected variables, RDF terms,
row multiset, row sequence, corpus fingerprint, and immutable SQL build ID to
match. Evidence is written under
`%LOCALAPPDATA%\BaseballO\state\serving\equivalence`.

The candidate adapter can bypass only a route's pending status. It retains the
normal serving pointer, artifact-hash, database-hash, SQLite integrity, query
allowlist, and input validation. The proof never edits `serving/contract.json`
and therefore cannot admit itself. After a family has passing reviewed
evidence, its route status can be changed deliberately and the existing
black-box `verify-explorer-serving.py` suite can prove the admitted UI path.
The first `explore` family proof was submitted asynchronously on 2026-09-03;
only its terminal immutable evidence can establish equivalence.

## Failure, staleness, and rollback

- Candidate databases are never edited after validation. A failed candidate
  cannot replace `current.json`, so the last validated build remains live.
- The read adapter checks the contract, PAQ rating specification, full reviewed
  query set, reducer contract, schema, materializer, mapping, and validator
  hashes. A mismatch makes the build unavailable and the Explorer uses
  authoritative SPARQL.
- End-to-end SPARQL-to-SQL equivalence is not yet claimed for the current
  materializer beyond the admitted PAQ/Good At Bat slice. Each pending Explorer
  family remains on its authoritative SPARQL path until a reviewed equivalence
  capture supports changing that family's route status. Populating its shared
  SQL grains is not sufficient evidence for admission.
- NiFi preserves failed command output under its corpus-orchestration
  quarantine. Fix the version-controlled cause and build a new candidate; do
  not repair a database in place.
- Rollback means atomically restoring `current.json` metadata for a retained
  validated immutable database and its evidence. Verify all recorded hashes
  first. Until the documented game-set gap is closed, builds outside the
  retention window require authoritative RDF plus retained game-set evidence.

Runtime databases and build evidence live under
`%LOCALAPPDATA%\BaseballO\state\serving`, outside the Git repository. Compact
reviewed benchmark summaries live under `benchmarks/serving-layer/`.
