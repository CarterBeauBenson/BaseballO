# Mermaid views of implemented semantic patterns

These diagrams describe the active [MLB game RML](../sources/mlb-game/mapping/mlb-game.rml.ttl). The detailed [generated pattern catalog](patterns/README.md) is the canonical non-regression review of implemented RML. Its boundaries are maintained in the source module's [RML Mermaid manifest](../sources/mlb-game/review/rml-mermaid-manifest.json), while its nodes and relations are regenerated from the actual RML.

The catalog has two synchronized views:

- [source-independent ontology patterns](patterns/ontology/README.md), which omit MLB JSON and RML mechanics; and
- [MLB game mapping patterns](patterns/mlb-game/README.md), which expose logical sources, triples maps, explicit joins, and matching IRI templates.

Run `python Baseball/scripts/generate_rml_mermaid.py` from the repository root after changing the RML or manifest. Repository validation fails when any triples map is unassigned or generated review page is stale.

For a new source family, this generated catalog is not the first design step.
Create review-only source-independent diagrams in
[`proposals/`](../proposals/README.md), resolve de-duplication and ontology gaps,
and obtain ontologist approval before writing RML. Once implemented, add the
source-specific view and generated coverage so the approved proposal and
actual emitted graph can be compared.

## Reading sequence

1. [Pipeline and repository](01-pipeline-and-repository.md)
2. [Logical sources](02-logical-sources.md)
3. [Triples-map families](03-triples-map-families.md)
4. [Joins and identities](04-joins-and-identities.md)
5. [Event process chain](05-event-process-chain.md)
6. [Implemented shape and retained gaps](06-evaluation-findings.md)
7. [Guarded external acquisition](07-daily-game-acquisition.md)
8. [Direct game import fallback](08-manual-game-import.md)
9. [Generated discrete event patterns](patterns/README.md)

## Current structural snapshot

| Measure | Revised mapping |
| --- | ---: |
| Logical sources | 98 |
| Triples maps | 345 |
| Referencing-object-map joins | 0 |
| BaseballO classes used | 145 |
| Undeclared BaseballO classes | 0 |
| Review patterns | 60 |
| Generated pattern pages | 120 |

The generated [pattern catalog](patterns/README.md) records the current mapping
fingerprint and triples-map assignment and is the authority when this summary
and generated evidence disagree. Event and triple counts for individual
fixtures belong in generated validation evidence rather than this hand-edited
index.

The end-to-end pinned RML processor and generated-RDF validator both pass on game 566279.
The checked-in eight-game 2026-08-03 corpus also passes repository validation.
Intentional walks follow the complete walk-process pattern. Terminal pickoff
and caught-stealing outcomes that lack sufficient performer evidence stay in
the explicit generic terminal-result pattern; the diagrams do not imply a more
specific act than the RML creates.

## Review-only proposals

Proposal diagrams that are not generated from or implemented by active RML are
kept in the single [review-only catalog](../proposals/README.md).
