# MLB-game semantic consumer migration

Status: **accepted**

This administrative record applies the ontologist's accepted MLB-game RML
contract to its downstream SHACL, query-index, SPARQL, serving, and Explorer
consumers. It introduces no new ontology term, source interpretation, or
identity policy.

The migration has three boundaries:

1. provider routing literals are retained only in source-record Identifier or
   nominal-classification evidence and are not attached directly to real-world
   Processes with `dcterms:identifier` or `dcterms:type`;
2. authoritative graphs retain the nominal evidence, while explicit current
   pitch and batted-ball subtype assertions are materialized only in the
   rebuildable query index; and
3. routine queries consume semantic classes or indexed facts, while live
   research queries remain able to traverse the authoritative evidence.

The existing SQL schemas remain derived serving products. This decision does
not authorize Statcast work or provider-coordinate projection into the world.
