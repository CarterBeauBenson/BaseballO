# NiFi serving build reuse and checkpoints

## Immutable code and database releases

The NiFi materializer launcher captures one committed Git revision before
loading calculation or admission modules. `serving_release.py` writes its
declared runtime dependencies and byte hashes under
`serving/releases/<manifest-sha256>/Baseball/`, then executes the materializer
from that directory. Working-tree edits and subsequent commits cannot alter
an active build. Commit a change before submitting it to NiFi; uncommitted
edits are deliberately excluded. No ontology, mapping, or source contract is
changed by this operational packaging.

The release includes pipeline components, serving code and schemas, analytical
queries, the MLB-game module, shared mapping policies and SHACL, and historical
schedule evidence used by the existing partition logic. Developer fixtures and
documentation are excluded. The manifest records the source commit, exact file
inventory and every file hash. Release creation is atomic and idempotent;
existing releases are verified, never overwritten. Python bytecode is disabled
inside releases. Missing, added or changed files fail verification.

Candidate evidence and the published `current.json` contain the same
`runtimeRelease` descriptor. Each request captures that pointer once, verifies
the associated release, and executes its query adapter and calculation code
against that pointer's database. Publication during a request cannot mix old
code with a new database. Subsequent checkout changes do not make a published
pair stale. All existing code fingerprints, database identity/hash checks,
source admission checks and final promotion gates remain enforced against the
captured release. Source graph drift can still invalidate a build.

NiFi may pair a pre-release database through a separate legacy sidecar only
when all thirteen recorded runtime fingerprints match captured Git history.
The old pointer and database are never rewritten. Unmatched historical code
remains unavailable until a new candidate passes the normal gates; in
particular, a mixture of uncommitted versions or historical mixed line endings
does not justify bypassing hashes. Non-matches are cached by pointer and HEAD
so the 15-minute worker does not repeat the same scan. Migration failure does
not prevent a normal replacement build. The worker records its result in
`serving/runtime-preparation.json` independently of long SQL builds.

Release directories are retained independently of database retention so an
active request or rollback never loses its reader. They are small code products,
not duplicate databases. There is currently no automatic release-directory GC.

The database's full checksum is calculated by NiFi before publication using
the reader's handle-based file identity checks. NiFi writes a verified receipt
under `serving/database-verifications/<database-sha256>.json` before swapping
the pointer and rechecks file identity immediately before that swap. The first
HTTP request can reuse the receipt instead of streaming the entire database
within its 30-second worker deadline. Receipts are separate per database so a
request pinned to an older build cannot evict the newly published verification.
Missing receipts still require full verification; changed size, timestamps,
device or inode invalidate them. This preserves the reader's existing integrity
contract and moves repeatable preparation into the NiFi build.

Immutable code releases also retain per-file identity receipts. The manifest,
exact inventory and paths are checked on each open; unchanged files reuse their
verified hashes. A changed file requires hashing again and must still match
its original manifest. Reader edits do not silently update captured releases.

`test_serving_release` exercises committed subprocess launch, working-copy
edits, new commits, publication during a request, exact legacy pairing,
negative-result reuse and corruption rejection. This is engineering coverage;
only a successful NiFi candidate and atomic promotion establish live readiness.

## Query reuse and unchanged validation

The materializer retains disposable per-game SPARQL SELECT answers in
`serving/query-cache.sqlite`. NiFi still runs the accepted full candidate
validation and atomic pointer promotion. This cache is not an admission proof,
a source input, a materialized score, or a replacement for authoritative RDF.

A cache identity contains the endpoint, exact query bytes, and the IRIs and
promoted RDF hashes of the graphs that query actually reads. An authoritative
query does not depend on an unread index; an index-only query does not depend
on unread authoritative RDF. Queries joining both retain both dependencies.
Variable graph queries retain every graph in their explicit named dataset.
It is usable only after the normal promotion inventory and live graph-pair
preflight succeed. Changing a read graph, endpoint, or query invalidates that
answer. Reissuing promotion evidence for identical graph contents does not.
An unrelated game's answers remain reusable. Each graph/query slot retains one
version; version-1 cache keys receive one cold read after this update.

## Published artifacts and later ingestion attempts

The MLB NiFi lane retains exact RML/index manifests and the derived index
artifact before reusing per-game staging paths and before publishing a new
promotion. Copies are content-addressed under each game's promotion evidence;
identical artifacts are retained once. They contain neither raw API responses
nor another copy of authoritative RDF. SQL resolves the exact hashes named by
the promotion marker against these retained artifacts, so a later failed
attempt or staging cleanup cannot invalidate the published graph's evidence.
Official date and game type prefer that published manifest when available;
newer unpromoted metadata cannot replace them. Fixture scoping is unchanged.

Existing markers remain supported. A previously lost manifest is not invented
or silently certified: only exact matching bytes can be retained. Corrupt copies,
missing promotion authority, and live graph drift still fail the existing checks.
This change requires no reingestion or new batch; the owning NiFi stages retain
artifacts as already scheduled work runs. Existing published SQL releases adopt
the new reader on their next normal SQL publication.

For legacy promotions whose mutable RML manifest was overwritten by a later
failed attempt, the existing staged-replacement check also follows that exact
run's quarantine record. Both the retained input and staged RDF must still match
their recorded hashes. Moving an input into quarantine does not revoke the
earlier published graph or certify the failed replacement.

An unrecognized derived-index contract is repaired from the existing authoritative
graph using `sources/mlb-game/pipeline/repair-query-index.ps1`, run by NiFi for
explicit game IDs. It runs the existing index builder and its checks, reconciles
promotion evidence, and preserves metric proofs tied to the same RML artifact.
On failure it restores only that game's previous index and mutable index files.
No acquisition, RML transformation, or authoritative graph replacement occurs.
SQL-only publication can then use the existing DSQ request independently of an
unfinished acquisition batch.

The batting-result SQL table retains one row per result and actual batting
participant, matching the accepted index's substituted-batter support. Team and
season totals count distinct result identities; weighted total bases use those
same distinct hit counts. Participation rows do not establish official batting
credit. The separate metric-suite admission rules still determine qualification.
The legacy PAQ-1 table withholds ambiguous shared-batter scores independently;
that limitation must not prevent other SQL tables or dashboard metrics from building.

## Query execution and checkpoints

The parsed query algebra must confine every graph read to that graph pair.
A variable GRAPH requires an explicit FROM NAMED dataset containing only the
pair. Default-graph reads, other graphs, SERVICE, volatile functions, and
unrecognized extension functions bypass the cache. Standard XSD scalar casts
and the four existing XPath duration-component functions are deterministic
and allowed. Unknown syntax also uses the existing executor.

Exact SPARQL JSON terms, row order, duplicates, language/datatype tags, and
unbound variables survive the compressed cache. Every stored payload has a
checksum and a 64 MiB uncompressed limit. Corruption or cache I/O failure
causes a fresh query; invalid SELECT responses and failed requests are never
cached. Concurrent DSQ workers use separate, explicitly closed SQLite
connections. Returned objects cannot mutate the stored answer.

The released materializer records the implementation and actual loaded query/schema
hashes before acquisition, rechecks every ten completed games, and checks
again before SQL validation and promotion. A changed or removed input ends
the attempt with `failureKind: implementation-changed`. Unvalidated private
candidates are removed through the existing cleanup path; the current pointer
is untouched. Successfully cached answers remain reusable by NiFi's next
attempt because their graph/query identity is independent of metric code.
These checkpoints now examine the captured files rather than the moving
working tree; release corruption still terminates the attempt.

Each build has `serving/builds/<build-id>.progress.json` with the completed
game count, phase, process ID, implementation hashes, and a running, failed,
invalidated, validated, or ready-for-promotion status. This is diagnostic
progress, not a completion certificate. `ready-for-promotion` precedes the
final atomic pointer swap; only the normal pointer and build evidence prove
promotion. The materializer performs no fallible progress write afterward.

The report builder retains completed game SQL partitions in
`serving/report-cache.sqlite`. A partition includes parameterized SQL writes,
ordered source rows and result counts. It is keyed by current admission
outcomes, authoritative/index hashes, dimensions and construction inputs.
Tables are created before processing games, so partition reuse is independent
of game order. A failed game is never checkpointed. After interruption, the
next NiFi attempt creates a fresh candidate and replays completed partitions;
the existing candidate-wide integrity and ordered-row checks still run.
Corrupt/unavailable cache data falls back to the ordinary extraction path.
Three versions per game are retained; each decompressed partition is limited
to 128 MiB. Warm builds report cache reuse separately from query timing and
do not invent SPARQL durations for replayed games.

The shared metric cache likewise retains three calculation versions per game.
Concurrent immutable report and dashboard releases therefore do not evict
each other's current product on every game. Legacy cache entries remain
readable while older running workers finish.

Build evidence contains input hashes and cache hit/miss/bypass/discard counts.
The final corpus snapshot still performs fresh promotion-inventory and live
graph checks. Cache reuse cannot authorize promotion after source drift.

Focused regressions in `test_serving_query_cache` and
`test_serving_materializer` cover cold/warm equivalence, every graph-version
key, unsafe queries, real materializer query shapes, corrupt payloads,
concurrency, source drift, and implementation drift. An offline one-game
second build reuses all 62 graph queries while making all six fresh preflight
queries; exact SQL row-preservation hashes match the cold build. This verifies
rebuild behavior, not live corpus completion or population eligibility.

## Calculated metric product reuse

`serving/metric-cache.sqlite` holds one calculated product per game. The
materializer first runs all six current `promoted_admission` readers, which
validate proofs against the current promotion and producer implementations.
It then normalizes the current graph-query evidence. Only after these steps
can an exact cache hit skip `metric_suite.game_products`.

The key includes the graph IRI, every normalized evidence binding, all six
validated admission outputs in full, and a calculation fingerprint covering
the metric implementation, schema, catalogs, policies and analytical queries.
Any change invalidates that game's product. Unrelated games remain reusable.
The source admission producers have a separate responsibility: their code
hash alone does not invalidate a pure calculation when the validated inputs
are identical. The broader serving fingerprint, build guard, release pairing
and SQL reader checks remain in force.

The cached product contains all twenty game-scope calculations and their
defensive, contribution, recovery, progress and PAQ-2.1 inputs. The candidate still writes
current evidence and current proofs, retains normalized exact fractions, and
checks every result's SQL round trip. Selected-period schedules, qualification
and season reference populations are evaluated by the reader as before;
game-product reuse cannot admit any of those populations.

Payloads are checksum-verified, compressed and limited to 64 MiB uncompressed.
Corruption causes recalculation. Cache I/O failure falls back to calculation;
calculation failures are not cached. One row per graph prevents accumulation
of superseded versions. Connections close after each operation. Build evidence
records `benchmark.metricProductCache` hits, misses, bypasses and discards
separately from the SPARQL cache statistics.

Focused tests in `test_serving_metric_cache`, `test_metric_suite_serving` and
`test_serving_materializer` prove exact cold/warm equality, invalidation of
every proof input, evidence and calculation identity, corruption recovery,
unchanged-game reuse and successful retry after a failed calculation. The
materializer integration test checks that a warm build calls all six admission
readers again, makes both fresh live graph snapshots, preserves every metric
SQL row, and never invokes the cached calculation. This is a developer proof,
not a claim about full-corpus speed or dashboard population readiness.

## Indexed inputs and reference preparation

Each candidate projects cached or newly calculated game products into the
indexed tables owned by `serving/metric_blocks.py`. Scope facts retain their
distinct source identities. Each observation retains its exact reducer record,
checksum and matching scalar SQL columns. The build verifies every input family
against its calculated product and records `buildingBlocksRoundTrip` per game.
Missing observations, changed columns, incorrect hashes and incomplete row
counts fail the reader; they cannot silently shrink a denominator.

After all games are stored, the `metric-reference-ranks` stage prepares admitted
season ranks for PAQ, Situation-Adjusted PAQ, Two-Strike Extension Rank and PAQ
with Tie-Breakers. `metricReferencePopulations` in build evidence records each
metric's cutoff, completeness and gaps. Incomplete populations remain withheld.
This stage uses the existing independent schedule and source admission checks.

Rank keys include the exact reference graph set. Stored observation changes
invalidate prepared ranks. Direct changes to raw evidence invalidate that
game's block manifest; direct changes to canonical game results invalidate the
corresponding compact result. Immutable publication, database checksums and
matching code releases remain the production boundary. These database triggers
also prevent stale projections during focused tests or candidate construction.

The selected-period reader reuses compact inputs and performs the final exact
math in Python. It no longer reconstructs graph patterns, runs SPARQL kernels,
or reads whole-game calculation JSON for a normal dashboard request. Historical
reference populations not prepared by NiFi are ranked from their own stored
observations, without updating the read-only database.
