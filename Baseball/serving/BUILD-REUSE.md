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
