# Change inventory

| Ontology content | Disposition | Accepted treatment |
| --- | --- | --- |
| `BaseballSeasonPhase rdfs:subClassOf BFO Process` | redundant direct parent | Remove. |
| `BaseballSeasonPhase rdfs:subClassOf BaseballSeasonSegment` | identity-bearing accepted parent | Retain. |
| `BaseballSeasonSegment rdfs:subClassOf BFO Process` | accepted hierarchy | Retain. |
| Baseball Season Phase restrictions in the axioms overlay | accepted axioms | Retain unchanged. |
| Labels, definition, comment, and example | accepted annotations | Retain unchanged. |
| Descendant season-phase classes | accepted hierarchy | Retain unchanged. |

No API field, RML mapping, SHACL shape, SPARQL query, or serving contract is
changed by this repair.
