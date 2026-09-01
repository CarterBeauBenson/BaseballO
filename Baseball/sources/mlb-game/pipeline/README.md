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

This stage component does not decide ontology meaning. It invokes the accepted
RML, current source SHACL, graph-pair promotion, query-index components, and
serving materializer.
