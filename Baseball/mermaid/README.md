# Mermaid views of the implemented direct RML

These diagrams describe the active [mlb-direct.rml.ttl](../mappings/direct/mlb-direct.rml.ttl). The detailed [generated pattern catalog](patterns/README.md) is the canonical design review. Its boundaries are maintained in the [RML Mermaid manifest](rml-mermaid-manifest.yaml), while its nodes and relations are regenerated from the actual RML.

The catalog has two synchronized views:

- [source-independent ontology patterns](patterns/ontology/README.md), which omit MLB JSON and RML mechanics; and
- [MLB direct-mapping patterns](patterns/mlb-direct/README.md), which expose logical sources, triples maps, explicit joins, and matching IRI templates.

Run `python Baseball/scripts/generate_rml_mermaid.py` from the repository root after changing the RML or manifest. Repository validation fails when any triples map is unassigned or generated review page is stale.

## Reading sequence

1. [Pipeline and repository](01-pipeline-and-repository.md)
2. [Logical sources](02-logical-sources.md)
3. [Triples-map families](03-triples-map-families.md)
4. [Joins and identities](04-joins-and-identities.md)
5. [Event process chain](05-event-process-chain.md)
6. [Implemented shape and retained gaps](06-evaluation-findings.md)
7. [Parked daily acquisition](07-daily-game-acquisition.md)
8. [Manual game import](08-manual-game-import.md)
9. [Generated discrete event patterns](patterns/README.md)

## Current snapshot

| Measure | Revised mapping |
| --- | ---: |
| Logical sources | 56 |
| Triples maps | 247 |
| Referencing-object-map joins | 0 |
| BaseballO classes used | 113 |
| Undeclared BaseballO classes | 0 |
| Sample generated triples | 29,736 |
| Sample plate appearances | 79 |
| Sample pitches and pitch motions | 282 each |
| Sample pitches with complete ancestor context | 282 |
| Sample swing/bunt acts with complete ancestor context | 134 |
| Sample bat-ball contacts and batted-ball motions | 112 each |

The end-to-end pinned RML processor and generated-RDF validator both pass on game 566279.
