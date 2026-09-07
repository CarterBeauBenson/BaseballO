# MLB Game pipeline components

This directory owns the source-specific executable stages used by the clean
NiFi `MLB Game` process group. NiFi supplies the scheduling, FlowFile
dependency order, bounded retries, quarantine routing, and provenance.

`stage.ps1` exposes the accepted per-game lifecycle as separate actions:

`rml -> shacl -> promote -> materialize -> cleanup`

The API response is written only to the transient MLB-game directory. A failed
run retains that payload in the lane quarantine. A bounded proof materializes
and promotes SQLite immediately. A schedule-driven corpus game instead records
its successful graph-pair promotion against a compact batch manifest; the
NiFi-owned pending-batch stage promotes one SQLite build only after every
expected game is current. Transient payload and serialized-RDF cleanup follows
the applicable stage contract. Persistent manifests, promotion evidence, the
authoritative TDB2 graph, the rebuildable indexed graph, and promoted analytical
databases remain.

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
is written to the shared dataset, by one promotion task. The existing
authoritative/index row-equivalence gate still runs for every game before the
graph-pair transaction commits and cleanup becomes eligible.
