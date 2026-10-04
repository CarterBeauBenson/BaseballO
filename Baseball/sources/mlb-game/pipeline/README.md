# MLB Game pipeline components

This directory owns the source-specific executable stages used by the clean
NiFi `MLB Game` process group. NiFi supplies the scheduling, FlowFile
dependency order, bounded retries, quarantine routing, and provenance. Each
game work stage quarantines after two total failed attempts.

`stage.ps1` exposes the accepted per-game lifecycle as separate actions:

`rml -> shacl -> promote -> materialize -> cleanup`

Targeted award, runner, compound, foul, defensive and history repair workers
share the existing resource lease around selection and execution, then take
their source-game lock. This prevents another repair from retiring a selected
input while its consumer waits. Award retry limits bind the exact source hash
and implementation. The one-game `award-input-recovery.json` resumes a recorded
retirement race through this same owner; it does not trigger full-game mapping.
See the [October 2 audit](../review/rml-audit-2026-10-02.md). The existing runner
owner also executes the explicitly inventoried P1 participation and game-end
clock corrections. Those corrections remove only their named erroneous triples
and add their verified replacements; they do not replace whole games.

The RML harness counts pitch classifications from the identifiers selected in
its reviewed execution context, keeping multiple runner rows for one pitch
from inflating the count. Targeted completion compares the current selected
RML output with the existing graph; empty output cannot count as completion.
Award and defensive input inventories reconsider previously unpromoted games
when their promotion appears and retain malformed-input diagnostics without
blocking independent candidates.

Recorded defensive failures receive priority over successful-input rechecks,
with the same exact-source retry limit. History discovery keeps a separate
request for each approved selector and reuses the original acquisition only
when its remaining scope and hashes match. RML context and manifest readers
explicitly decode UTF-8. Discovery reuses the owning current or explicitly
compatible admitted boundary proof before opening another source request;
withheld and stale proofs cannot take that shortcut. Existing selected jobs
retain their original finalization and cleanup. See the [October 3 audit](../review/rml-audit-2026-10-03.md)
for the recorded failures and focused regressions.

The shared RML runner snapshots the mapping and its execution dependencies,
executes those copies, and checks for changes before publishing its manifest.
Normal context assembly and clock admission share the terminal selector; D1
uses the accepted Q6 distinction between supported acts and complete populations.
The [October 4 repair record](../review/rml-audit-2026-10-03.md#six-item-repair-implementation-october-4)
records these generic changes and their focused recurrence checks.

Before invoking the RML, the `rml` action calls
`reconcile-metric-source.py`. It retains a source-revision/input-hash-bound
inventory in the run's `metric-source-reconciliation.json`, with its path,
digest and consistency result in the stage evidence. The inventory survives
transient cleanup. NiFi's existing source lane owns invocation and retries;
no additional processor, mapping, source lane or ontology term is introduced.

The check reconciles unfiltered play membership, inning/scoring indexes,
movement-to-event links, explicit pitch membership and inning/team run totals.
MLB `pitchIndex` also contains non-pitch events, so its length is not used as
a pitch count. Event and PA count fields retain their separate scopes.
Missing post-base fields remain absent observations. Identical inputs produce
identical reports for the same reconciler version.

This is mechanical consistency evidence, not exhaustive-history authority,
graph coverage or metric eligibility. All three admission flags remain false.
An inconsistency is retained for review and does not change the currently
pinned ingester's semantic admission; failure to create the durable inventory
uses the existing stage failure/retry route. New full metric results cannot
be released from this report. Source authority, operative effects/boundaries,
source-to-graph reconciliation and population reconciliation remain separate
requirements. The user's conditional direction does not authorize filling
missing graph assertions through new RML or raw-source SQL calculations.

The API response is written only to the transient MLB-game directory. A failed
run retains that payload in the lane quarantine. A bounded proof materializes
and promotes SQLite immediately. A schedule-driven corpus game instead records
its successful graph-pair promotion against a compact batch manifest; the
NiFi-owned pending-batch stage promotes one SQLite build only after every
expected game is current. Transient payload and serialized-RDF cleanup follows
the applicable stage contract. Persistent manifests, promotion evidence, the
authoritative TDB2 graph, the rebuildable indexed graph, and promoted analytical
databases remain.

That batch dependency belongs to the full report builder. The independent
`Dashboard SQL` owner checks promoted game changes and prepares its own SQL
product; it does not wait for a whole acquisition batch to be declared complete.
Player and schedule completeness still govern which results it can publish.
See [serving ownership](../../../serving/METRIC-SUITE-IMPLEMENTATION.md).

Quarantine replay is hash-bound and NiFi-owned. The first replay proves the
five configured representative games before releasing its remainder. Later
replays verify that immutable proof, then require up to five exact current
quarantine payloads to promote before releasing any new remainder. Successfully
resolved proof inputs do not need to remain quarantined merely to authorize a
future replay.

Compact batch and RML manifests retain each game's MLB `officialDate` and
`gameType` after the transient response is removed. The serving materializer
uses that evidence to keep regular-season (`R`), preseason (`S`), exhibition
(`E`), postseason (`F`, `D`, `L`, `W`, `C`, `P`), and All-Star (`A`) games in
separate query pools. Explorer requests default to the regular-season pool;
the other pools remain available explicitly.

For a postponed completed game, the schedule request also carries the path to
its compact revision evidence into the RML stage. That evidence is validated
against the game identity, fingerprinted in the RML manifest, and never mixed
into another source lane.

This stage component does not decide ontology meaning. It invokes the accepted
RML, current source SHACL, graph-pair promotion, query-index components, and
serving materializer.

The MLB Game lane executes the unchanged source SHACL profile with Apache Jena
and permits two validation tasks. Query-index construction also uses Apache
Jena, but against the validated per-game RDF in an isolated in-memory dataset;
the checked-in CONSTRUCT queries are unchanged. Only the completed index graph
is written to the shared dataset. Two promotion tasks share the existing NiFi
queue; the existing graph-store write lock serializes writes. `game-lock.ps1`
excludes simultaneous stages for the same game while allowing different games
to proceed together. Windows releases the lock handle when a worker exits,
including after a crash. Before a new promotion, the existing graph-pair
recovery routine restores an uncommitted pair or completes a marked promotion.
The existing
authoritative/index row-equivalence gate still runs for every game before the
graph-pair transaction commits and cleanup becomes eligible.
