# Repository and architectural evidence

The source catalog currently assigns one authoritative graph prefix to each
reference module:

- MLB organizations uses an authority prefix and maps Baseball Season and
  Baseball Season Phase, both accepted BFO Processes;
- MLB people uses an authority prefix and maps a Birth Process; and
- MLB venues uses an authority prefix but its accepted mapped surface contains
  no one-time Process.

MLB transactions already uses an event graph prefix. Its persistent RDF is
authoritative evidence even though the graph is event-scoped. This proves that
`event` does not mean transient or disposable in the current architecture.

The user has now distinguished re-identifiable persistent entities, such as
Persons, Venues, Teams, Leagues, and Divisions, from Processes that happen once
and do not recur. That distinction does not by itself determine whether a
named graph denotes a BFO category partition or a source-owned evidence
record. Both interpretations are technically possible and lead to different
NiFi promotion contracts.

The detachable-module rule remains fixed under both options. MLB people owns
all products made from the people endpoint; MLB organizations owns all
products made from its organization endpoints. A graph split cannot move RML,
SHACL, raw payloads, or scheduling into another source module. The persistent
authoritative triple store remains the only semantic integration boundary.

The decision should be made before corpus promotion because graph naming,
SHACL targeting, provenance, atomicity, backfill, and disconnect behavior all
depend on it. It does not require a new ontology class or property.
