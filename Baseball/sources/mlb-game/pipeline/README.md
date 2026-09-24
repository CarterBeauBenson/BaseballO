# MLB Game pipeline components

This directory owns the source-specific executable stages used by the clean
NiFi `MLB Game` process group. NiFi supplies the scheduling, FlowFile
dependency order, bounded retries, quarantine routing, and provenance.

`stage.ps1` exposes the accepted per-game lifecycle as separate actions:

`rml -> shacl -> promote -> materialize -> cleanup`

Before invoking the unchanged RML, the `rml` action now calls
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
