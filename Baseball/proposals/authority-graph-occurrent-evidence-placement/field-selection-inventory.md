# Entity and graph-placement inventory

| Entity or evidence family | Ontology category | Option A placement | Option B placement |
| --- | --- | --- | --- |
| Person | persistent independent continuant | Source authority graph | Source authority graph |
| Team, League, Division | persistent Organizations | Source authority graph | Source authority graph |
| Venue and Field Site | persistent continuants | Source authority graph | Source authority graph |
| Height or Distance Quality | specifically dependent continuant | Source authority record under its accepted source contract | Product selected by explicit evidence policy; not retyped as event |
| Name, Identifier, Measurement, Date, response, and Plan ICEs | generically dependent continuants | Source authority record | Explicit single home required; no convenience duplication |
| Birth | one-time Process | Source authority record alongside its Person evidence | Source-owned event/evidence graph |
| Baseball Season | Process | Organization authority record | Source-owned event/evidence graph |
| Baseball Season Phase | Process | Organization authority record | Source-owned event/evidence graph |
| transaction Death | one-time Process | Already outside reference authority scope | Existing transaction event/evidence graph |
| query-index RDF | derived acceleration | Rebuildable graph | Rebuildable graph |
| SQL serving rows | derived analytical product | Rebuildable serving store | Rebuildable serving store |

This inventory does not authorize moving existing promoted RDF or changing an
IRI. Any migration requires provenance-preserving, idempotent graph promotion
and query-equivalence evidence.
