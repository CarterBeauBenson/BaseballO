# Mermaid RML Review

These diagrams make the active [`mlb-direct.rml.ttl`](../mappings/direct/mlb-direct.rml.ttl) inspectable at several levels. They describe the mapping as implemented; red or amber nodes identify review findings rather than silently changing the ontology or mapping.

## Review sequence

1. [Pipeline and repository](01-pipeline-and-repository.md) — separates the active direct workflow from archived work.
2. [Logical sources](02-logical-sources.md) — shows how 37 JSONPath logical sources partition the raw feed.
3. [Triples-map families](03-triples-map-families.md) — groups all 121 triples maps into readable functional families.
4. [Joins and identities](04-joins-and-identities.md) — exposes the `playId` join strategy and runner composite keys.
5. [Event process chain](05-event-process-chain.md) — compares the intended responsibility chain with explicit RML edges.
6. [Evaluation findings](06-evaluation-findings.md) — summarizes strengths, processor risks, and modeling decisions.

7. [Daily game acquisition](07-daily-game-acquisition.md) — shows the scheduled NiFi boundary, immutable archives, validation gates, and quarantine paths.

## Snapshot

| Measure | Current mapping |
| --- | ---: |
| Logical sources | 37 |
| Triples maps | 121 |
| Referencing-object-map joins | 44 |
| Specifically typed plate-appearance result values | 11 |
| Canonical play collection | `$.liveData.plays.allPlays[*]` |
| Raw sample plays | 79 |
| Raw sample pitches | 282 |
| Raw sample runner records | 113 |

The diagrams are maintained as Markdown Mermaid blocks so GitHub renders them without generated image files.
