# NiFi serving build reuse and checkpoints

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

The materializer records the implementation and actual loaded query/schema
hashes before acquisition, rechecks every ten completed games, and checks
again before SQL validation and promotion. A changed or removed input ends
the attempt with `failureKind: implementation-changed`. Unvalidated private
candidates are removed through the existing cleanup path; the current pointer
is untouched. Successfully cached answers remain reusable by NiFi's next
attempt because their graph/query identity is independent of metric code.

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
