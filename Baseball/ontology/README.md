# Ontology

[`BaseballO.ttl`](BaseballO.ttl) is the active project ontology. It contains the annotated class vocabulary and named-class taxonomy. Its natural-language definitions, labels, comments, examples, and taxonomic `rdfs:subClassOf` assertions can be shared without the optional logical restrictions.

Version `0.3.0` adds the accepted replay-review model: the on-field judgment,
challenge, replay review, input and output decisions, review-result information,
and source event record remain distinct entities. Human-facing labels use
“Replay Review Result ICE”; legacy `...DispositionICE` IRIs are retained only
for identifier stability and do not denote BFO dispositions.

[`BaseballO-axioms-overlay.ttl`](BaseballO-axioms-overlay.ttl) is the optional axiom module. It imports BaseballO, the Cognitive Process Ontology, and the Modal Relation Ontology, then adds relational and cardinality restrictions derived conservatively from BaseballO's definitions. It declares no new named classes or object properties.

## Loading choices

- Load or share `BaseballO.ttl` for the annotated taxonomic backbone.
- Load or share `BaseballO-axioms-overlay.ttl` with its imports for the taxonomic backbone plus the optional axioms.
- Add, remove, or revise optional class restrictions in the overlay, not in `BaseballO.ttl`.

The repository keeps local Turtle snapshots of the Common Core Ontologies merge, Cognitive Process Ontology, and Modal Relation Ontology so overlay vocabulary can be checked offline. The import statements use the ontologies' canonical IRIs.

Run `python scripts/validate_ontology_overlay.py` from the repository root to verify that the base contains no optional restrictions, the overlay introduces no named vocabulary, every referenced class and object property occurs in the repository, and cardinality axioms do not use transitive properties. The full `python scripts/validate_repository.py` check includes this validation.

The earlier `0.2.0` snapshot is preserved in [`../archive/ontology-v0.2.0.ttl`](../archive/ontology-v0.2.0.ttl). Do not modify the active ontology merely to make a mapping convenient; unresolved coverage belongs in the direct mapping's [`ontology-coverage-gaps.yaml`](../mappings/direct/ontology-coverage-gaps.yaml).
