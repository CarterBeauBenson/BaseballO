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

`test_serving_release` exercises committed subprocess launch, working-copy
edits, new commits, publication during a request, exact legacy pairing,
negative-result reuse and corruption rejection. This is engineering coverage;
only a successful NiFi candidate and atomic promotion establish live readiness.

## Query reuse and unchanged validation

The materializer retains disposable per-game SPARQL SELECT answers in
`serving/query-cache.sqlite`. NiFi still runs the accepted full candidate
validation and atomic pointer promotion. This cache is not an admission proof,
a source input, a materialized score, or a replacement for authoritative RDF.

A cache identity contains the endpoint, exact query bytes, authoritative and
query-index graph IRIs, promotion-manifest hash, and both promoted RDF hashes.
It is usable only after the normal promotion inventory and live graph-pair
preflight succeed. Changing a graph pair, its promotion, endpoint, or query
invalidates that answer. An unrelated game's answers remain reusable. Each
graph/query slot retains one version.

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
defensive, contribution, recovery and PAQ-2.1 inputs. The candidate still writes
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
