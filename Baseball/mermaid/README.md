# Mermaid views of the implemented direct RML

These diagrams describe the active [mlb-direct.rml.ttl](../mappings/direct/mlb-direct.rml.ttl). The detailed [event-pattern catalog](patterns/README.md) is the canonical design view: the RML was revised first, and every pattern diagram reflects generated RDF.

## Reading sequence

1. [Pipeline and repository](01-pipeline-and-repository.md)
2. [Logical sources](02-logical-sources.md)
3. [Triples-map families](03-triples-map-families.md)
4. [Joins and identities](04-joins-and-identities.md)
5. [Event process chain](05-event-process-chain.md)
6. [Implemented shape and retained gaps](06-evaluation-findings.md)
7. [Parked daily acquisition](07-daily-game-acquisition.md)
8. [Manual game import](08-manual-game-import.md)
9. [Discrete event patterns](patterns/README.md)

## Current snapshot

| Measure | Revised mapping |
| --- | ---: |
| Logical sources | 56 |
| Triples maps | 249 |
| Referencing-object-map joins | 57 |
| BaseballO classes used | 113 |
| Undeclared BaseballO classes | 0 |
| Sample generated triples | 27,163 |
| Sample plate appearances | 79 |
| Sample pitches and pitch motions | 282 each |
| Sample bat-ball contacts and batted-ball motions | 112 each |

The end-to-end pinned RML processor and generated-RDF validator both pass on game 566279.
