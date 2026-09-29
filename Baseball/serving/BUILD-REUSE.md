# NiFi serving build reuse and checkpoints

## Immutable code and database releases

Help Without Advancing prepares its own binary eligibility and answer when an
otherwise unresolved PA has a complete B1 and runner-resolution census. It
reuses the existing progress reducer with every segment and history member of
the batter, then the batter plus each other runner. A known batter positive
excludes that PA from Help's denominator; a known teammate positive settles
Help only when the batter's own progress is known to be zero. Unknown batter
progress or only unknown teammate progress remains withheld. Certain positive
contributions also settle non-emptiness, without completing reach, contribution
amounts, channel diversity or independent-running credit.

NiFi reads the retained SQL evidence only for affected player partitions. The
preceding exact player version migrates partitions with no admissible unresolved
progress by retaining their values. Source admissions, whole-game calculations,
RDF and RML remain unchanged. Qualification still applies to the whole selected
range. The September 29 read-only repair of game 823580 / PA 55 supplies Daulton
Varsho's missing Help observation: his season result is 14 successful eligible
PAs / 368 eligible PAs = 7/184, with all 526 official PAs accounted for. This is
a checked repair result, pending NiFi publication, not a live-card claim.

The NiFi source-snapshot stage retains artifact byte hashes between invocations
in a local cache separated by Python runtime. Each reuse checks the file's
device, identity, size and timestamps; replaced, edited or missing files cannot
reuse the prior hash. Cache misses also check the open handle and pathname
around hashing. A missing, damaged or unwritable cache uses normal file reads.
This retains hashes only: promotion ordering, manifest ownership, source/index
consistency and the final live graph check still execute. Bounded eviction drops
one old entry instead of clearing the entire cache. No admission is renewed and
no graph or SQL value changes through this optimization.

NiFi prepares the default full-season range responses after player and reference
products are ready. `dashboard_prepared_range` retains the exact result for each
regular-season year through its latest loaded date. An unchanged input set and
range-reader/player version reuse the result. Publication copies that small
SQL table alongside the prepared player products. Dashboard and metric detail
reads use it only for an exact date range, code version and published input-set
match; other ranges continue to aggregate prepared player/game rows. No graph
query, PA reconstruction, source acquisition or changed eligibility occurs on
that path. Unavailable metrics remain unavailable in the prepared response.

Dashboard publication copies the prepared SQL tables into an immutable reader
snapshot. `metric_suite_evidence` and the duplicated `metric_suite_result` stay
in the existing working database for incremental repairs; the reader uses their
prepared scope, input and shell products. They are absent from the snapshot so
an accidental fallback to raw bindings fails explicitly. All dashboard cards
and expanded metric responses are checked for equality in the component test.
The snapshot keeps SQL constraints and indexes; mutable producer triggers remain
in the working database. Publication records both logical file sizes. No source,
graph, retained binding or existing working checkpoint is rebuilt or removed.
The SQL integrity scan explicitly names `main.quick_check` and
`main.foreign_key_check`. Unqualified `quick_check` also inspects the attached
working database; that was extending publication by scanning the large excluded
intermediate tables. The component regression keeps an invalid CHECK value in
an excluded fixture table and verifies that the reader's own constraints still
hold. Copying enforces the snapshot's SQL constraints,
while each changed calculation keeps its existing binding/checksum checks.
Publication progress distinguishes the source check, snapshot copy and digest.

Independent PA admission reuses the existing C1/C2 constraints with one target
per PA. Each target still requires every runner history in its half-inning;
unknown history scope blocks all dependent PAs. A failed start boundary blocks
that PA. Original whole-game proof outcomes remain unchanged. The player proof
retains the separate boundary proof and checksums for its census, shapes and
report. Earlier identical roster/player checks remain usable during rollout.

The player projector invokes the existing contribution calculator only for
affected games, using retained SQL evidence and these independent admissions.
It excludes a player's entire selected-range record if any required PA remains
unresolved. The default game calculator is unchanged. Its exact compatible
version transition preserves existing game results and unchanged player
partitions; it triggers neither RDF extraction nor a database rebuild.

Empty Game Damage can also retain an independently complete player when another
runner's play is unresolved. The admitted C2 runner census bounds the affected
players. Completed PA contributions already certify no separate damaging running
episode; unresolved turns and unattributed episodes exclude their possible runners.
Missing runner identity or census withholds this isolation. This does not score
independent outs or repair their missing attribution. Full selected-range player
completeness and the original whole-game proof outcomes are preserved.

Admission maintenance processes games serially for up to 45 seconds or ten
expensive refreshes per scheduled invocation, finishing its current game before
yielding. It retains the one-minute NiFi schedule, one JVM at a time, and the
existing memory reservation. Source acquisition schedules are unchanged.

Within one immutable dashboard input batch, each shared code-compatibility
version tuple is checked once. Producer fingerprints and the compatibility
record are rechecked when the batch ends. Every game's distinct receipts,
promotion identity and validation artifacts still receive their existing checks.

Within one game's input loading, the admission reader shares evidence bytes
between checksum and JSON reads. Every reuse checks the current file identity,
size and timestamps; replacement, mutation or deletion invalidates reuse.
The cache is limited to 32 MiB / 128 files and discarded after that game.
It creates no persistent receipts and changes no admission outcomes. A focused
check preserved the full admission outputs for games 822680, 823648 and 823004;
the regression also exercises replacement, deletion and reader restoration.

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
under `serving/database-verifications/<database-sha256>-<python-cache-tag>.json` before swapping
the pointer and rechecks file identity immediately before that swap. The first
HTTP request on the same Python runtime can reuse the receipt instead of streaming
the entire database within its 30-second worker deadline. A different runtime
verifies once and retains its own receipt because Windows file identities differ
between Python versions. Receipts are separate per database and runtime so a
request pinned to an older build cannot evict the newly published verification.
Missing receipts still require full verification; changed size, timestamps,
device or inode invalidate them. This preserves the reader's existing integrity
contract and moves repeatable preparation into the NiFi build.

Immutable code releases also retain per-file identity receipts. The manifest,
exact inventory and paths are checked on each open; unchanged files reuse their
verified hashes. A changed file requires hashing again and must still match
its original manifest. Reader edits do not silently update captured releases.

The Dashboard SQL launcher can publish a new reader against the same immutable
database when every captured producer, schema, source and query dependency is
byte-identical. Only the query adapter, its separate `player_range_query.py`
reader and the release launcher may differ. It takes the dashboard writer lock
and applies the existing database checks before swapping the runtime descriptor.
`dataRuntimeRelease` retains the original producer; `readerUpdatedAtUtc` records
the reader deployment. The database hash, build ID, data publication time and
pending input notification remain intact. This avoids copying or recalculating
SQL for a reader correction without suppressing queued source/admission updates.

Range reads require the exact season and graph-set key for a saved reference.
The existence of an unrelated earlier-cutoff reference cannot trigger a scan of
all season histories. Missing selected references remain unavailable. Range
participation coverage is read from prepared SQL and reports the exact affected
games; a missing roster does not silently shorten the user's selection.

The player reader defers aggregate JSON decoding until a player's entire selected
range passes its existing completeness checks. A failed game discards that
player's buffered values; missing metric rows also prevent decoding. SQL still
supplies the full selected range and all exclusion reasons. Exact fractions,
zero-observation records, qualification and pooled results are unchanged. This
reader-only change requires no new SQL products or RDF work.
Dashboard reads fetch the requested player metrics together in game order,
avoiding a separate season scan for each card. The existing unique game/player/
metric key supports counting matched games; any unexpected game is still an
explicit completeness failure, even when the counts match. The same query
supports expanded single-metric details without changing their period.

After checking completeness, indexed aggregate reads explicitly traverse
eligible metric/player pairs before joining their games. `CROSS JOIN` and the
player index prevent the production SQLite planner from placing every game
outside all eligible pairs. On September 29 the incorrect plan made 7,773
eligible pairs participate in probes across 2,429 games and pushed custom-season
requests past the HTTP deadline. The corrected aggregate scan read the same
10,055 rows in 8.66 seconds in the live SQL diagnostic; the three focused
comparisons also pass using the dashboard's actual Python/SQLite runtime.
Default season responses continue to use NiFi's prepared range table.

Known zero-PA games contribute no observations to Offensive Reach and Help
Without Advancing. They do not require runner-resolution evidence for those
batting averages. The player producer repairs matching previous partitions
directly from verified SQL participation and preserves all other aggregates.
Unknown PA counts and running metrics keep their own requirements. The migration
reports `repairedZeroPARows` and does not reread RDF or recalculate game kernels.

The independent player admission refresh validates existing B1/E1 roster and B1
player constraints against the promoted graph without rerunning RML. Original
whole-game admissions are retained. Its separate proof is stored in
`dashboard_player_admission`; its digest participates only in that game's player
partition and the publication input set. Metric values still come from retained
RDF query bindings. Deployment migrates unchanged player partition identities
without recalculating their rows. A new or changed individual proof recalculates
that game's player projections, leaving game kernels and evidence untouched.
When a retained raw response is available, the same bounded graph export can
also run the unchanged six source admission profiles in one Jena session.
Receipts bind the current promotion and are committed only after its final
identity/count check. Proofs retain `sourceSha256` for the validation response,
`promotionSourceSha256` for the original ingest and `validationExportSha256`
separately from the original RDF hash. Passing checks feed the existing
admission-only refresh path; failed checks remain withheld. No source/RDF
identity is rewritten to make a later response look like the original input.

`test_serving_release` exercises committed subprocess launch, working-copy
edits, new commits, publication during a request, exact legacy pairing,
negative-result reuse and corruption rejection. This is engineering coverage;
only a successful NiFi candidate and atomic promotion establish live readiness.

## Query reuse and unchanged validation

The shared report/dashboard corpus snapshot also retains a completed live
graph check. Reuse requires the same validated promotion inventory, query
definitions, local Fuseki restart identifier and write-capable endpoint
counters. Counters are read before and after reuse; in-flight writes, changed
counters, restarts, unknown endpoints, corrupt cache data or unavailable
server statistics use the original live graph scan. Read-only requests do
not invalidate it. This uses Fuseki's documented
[server statistics](https://jena.apache.org/documentation/fuseki2/fuseki-server-info.html).
The final publication check still re-reads the promotion inventory and server
state. No HTTP dashboard request performs this work.

For dashboard games whose RDF, dimensions and calculation version match their
checkpoint, changed admission proofs refresh only the affected contribution,
recovery, defense and joined PAQ inputs. The existing calculators consume
checksum-verified SQL evidence; unchanged game kernels, observations and scope
facts remain intact. Updated inputs use the existing SQL round-trip checks,
and affected seasons have their reference products prepared again. Each game
commits atomically. Evidence, math or dimension changes still use the ordinary
game materializer. `admissionUpdatedGames` distinguishes these updates from
fully unchanged games. A focused regression compares every game table against
a complete calculation and rejects missing retained evidence.

The September 28 shortened-fraction timestamp fix has one exact old/new
calculation-fingerprint migration in the dashboard builder. With unchanged RDF,
dimensions and retained proof inputs, it refreshes contribution, runner-boundary,
recovery and joined PAQ products through their existing calculators. Unaffected
game kernels and evidence stay intact. `calculationUpdatedGames` reports these
updates; unrecognized calculation changes still use the normal materializer.

`player_ranges.py` separately prepares per-player, per-game sufficient statistics
and completeness flags. Its own fingerprint invalidates only those derived
partitions. HTTP range selection pools their exact sums and counts, excluding a
player if any applicable selected-game record is incomplete. It does not repeat
SPARQL, reconstruct PA histories or average a player's known subset. This does
not alter admission proofs or relax season-reference requirements.

Dashboard input loading hashes each shared admission producer before and after
the batch, instead of reopening identical code files for every game. A changed
producer aborts before publication. Each game's proof, promotion identity and
retained evidence hashes are still checked individually. Progress distinguishes
source capture from input refresh so saved calculation work remains visible.

Promotion inventory also reuses each artifact's hash within the same process
while its open-file identity, size and timestamps match. Replacements or edits
require hashing again. The cache is bounded and expires when the NiFi command
exits; the next invocation verifies the bytes afresh. This avoids rereading
unchanged index files for both inventory captures and final publication checks.

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

Contribution arithmetic also has a bounded in-process cache of 4,096 exact
numerical consequences. It runs the unchanged canonical TFS SPARQL kernel on
a miss. The key includes every numerical input, participant multiplicity,
and the query/catalog contract; it excludes person and evidence identities.
All input checks still run before lookup, and each result receives its own
evidence and fresh fraction/component objects. No admission or source evidence
is cached this way. A change to the canonical kernel invalidates the entry.

For retained game 823979's 86 PAs, exact results and evidence matched before
and after this change: 6.574 seconds previously, 3.864 seconds with an empty
cache and 0.078 seconds with those numerical cases cached. The empty-cache run
already reused 38 repeated cases. This is a bounded component timing, not a
projection of full-corpus runtime.

`serving/metric-cache.sqlite` retains up to three calculated versions per game. The
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
calculation failures are not cached. The versioned table keys rows by graph and
calculation identity and prunes beyond three versions per game. The old
single-version table remains readable by older immutable releases; it is not
the current retention policy. Connections close after each operation. Build evidence
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

Dashboard update notifications include admission refresh receipts, but the
brief pre-build quiet window considers only RDF promotion and independent
schedule events. A receipt produced every minute must not keep resetting a
one-minute wait. Refreshed admissions still invalidate their affected game
inputs; the existing final source-snapshot check still protects publication.

After a changed notification, the dashboard builder still inspects the inputs
and performs its final source check. When the resulting input set, source
snapshot and exact runtime release match the current readable publication, it
retains that publication and acknowledges the notification. It does not copy,
index and checksum identical SQL again. The build ID, database hash and original
publication time remain unchanged. Changed proofs or code produce a new
publication; a missing or damaged snapshot is repaired from retained SQL work.
An explicit forced build still publishes normally.

Admission maintenance yields on a memory deferral below its smallest existing
JVM reservation instead of inspecting dozens more games that cannot run. A
deferral at the larger reservation can still allow smaller checks to proceed.
The next NiFi tick retries deferred work; no admission threshold is reduced.

Atomic metadata replacement retries transient Windows access/sharing/lock
errors for at most six attempts (1.55 seconds of delay). Readers continue to
see the old complete file until replacement succeeds. Persistent errors still
fail; the writer never substitutes an in-place partial update. This covers
status-file readers as well as publication pointers.

Each candidate projects cached or newly calculated game products into the
indexed tables owned by `serving/metric_blocks.py`. Scope facts retain their
distinct source identities. Each observation retains its exact reducer record,
checksum and matching scalar SQL columns. The build verifies every input family
against its calculated product and records `buildingBlocksRoundTrip` per game.
Missing observations, changed columns, incorrect hashes and incomplete row
counts fail the reader; they cannot silently shrink a denominator.

After games are stored, NiFi prepares admitted ranks for PAQ,
Situation-Adjusted PAQ, Two-Strike Extension Rank and PAQ with Tie-Breakers.
The full report builder prepares the latest cutoff per season in its
`metric_suite_reference` tables, with `metricReferencePopulations` evidence. The independent dashboard
builder uses `reference_products.py` to prepare every supported historical
date cutoff in `dashboard_reference`. After the existing population reducer
passes, it also saves exact player/game totals, eligible counts, official PA
counts and team-game exposure in `dashboard_reference_players`. These compressed
products retain the full reference graph set, including games with no eligible
observations. Both paths use existing schedule and source admission checks;
incomplete populations remain withheld. A rank table without its prepared player
product cannot trigger request-time reconstruction.

Rank keys include the exact reference graph set. Stored observation changes
invalidate prepared ranks. Direct changes to raw evidence invalidate that
game's block manifest; direct changes to canonical game results invalidate the
corresponding compact result. Immutable publication, database checksums and
matching code releases remain the production boundary. These database triggers
also prevent stale projections during focused tests or candidate construction.

The dashboard reader combines prepared player/game totals over the selected
period. For the four percentile metrics it selects the exact season-through-
cutoff reference product, checks its checksum and independent schedule, and
pools its saved fractions. It does not decode PA inputs, reconstruct graph
patterns, run SPARQL kernels or rank a season on a request. Known ineligible
observations stay out of the denominator; missing reference products remain
unavailable. The older full report reader's stored-observation ranking fallback
is a separate behavior, not the dashboard contract. Changing the independent
reference producer refreshes those SQL products through NiFi without rerunning
unchanged game calculations or modifying RDF.

Dashboard publication copies only the reader's products and provenance. Raw
bindings, intermediate observation rows, game-result shells and per-PA rank
tables remain in the working SQL database; they are not copied and scanned
again in every immutable reader snapshot. Prepared reference-player products
remain available. The publication retains its existing SQL integrity and
foreign-key checks and reports the table-copy, index and integrity phases.
The focused roundtrip compares every metric's dashboard and detail results
before and after this projection. No RDF or game calculation changes.
The reader snapshot also adds an index covering the range-completeness scan.
The reader first checks the entire range, then fetches aggregate JSON only for
complete player records. Older snapshots retain the prior reader path until
NiFi publishes the index; neither path shortens the range or changes values.
The working database now receives that coverage index too, so NiFi's season
preparation uses the same compact read. A separate metric/player/game index
allows SQLite to seek eligible player records directly. Exact empty aggregate
payloads need not cross into Python, but their games remain in the coverage
check. Zero-valued observations, eligible games and independent running exposure
are retained. These physical indexes do not invalidate player calculations.

The web layer reads only small prepared player/team/game rows from the same
immutable, worker-verified dashboard snapshot for participation minimums. It
counts each represented team's full selected-period schedule, not merely the
games in which the candidate appears. Multiple-team candidates use the largest
team total, never less than their evidenced game exposure. This conservative
threshold cannot be reduced by switching teams. No SPARQL, scoring, source
refresh or SQL rebuild is performed by this display qualification step.
