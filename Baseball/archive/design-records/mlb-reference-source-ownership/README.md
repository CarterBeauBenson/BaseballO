# MLB reference-source ownership decision

Status: **accepted by the ontologist on 2026-08-29**

This record preserves the approved ownership split between the existing MLB
game lane and the dedicated MLB reference-source modules. It is an integration
and detachability decision, not approval of source-specific RDF shapes.

The MLB game module owns game and event facts and retains canonical identity
links. Organizations, people, venues, and transactions own their respective
reference facts in independently validated and promoted graphs. The
authoritative triple store remains the integration boundary.

Existing promoted MLB-game RDF is not deleted by this decision. Reference
graphs must be populated before any coordinated game-mapping cutover, and
affected SPARQL, indexed RDF, and serving products must demonstrate equivalence
before reference assertions are removed from future game graphs.

This decision authorizes source-module ownership metadata. Executable RML,
source SHACL, NiFi groups, graph promotion, and query cutover remain gated by
approved source-specific Mermaid contracts.
