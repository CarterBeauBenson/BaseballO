# Boundary association: temporal vocabulary and category

Status: **design investigation; no new ontology term is proposed or accepted**.

The user has accepted recognized runner/Base association at an evidenced Game
boundary, distinguished from continuous physical contact and uninterrupted
persistence. A particular touching process may remain unknown when the
recognized association is supported. These decisions identify the intended
fact; its exact world-side category and identity remain to be settled.

## Existing temporal vocabulary

The pinned [CCO/BFO dependency](../../../ontology/CommonCoreOntologiesMerged.ttl)
already supplies the following terms, inspected locally on 2026-09-08:

| Term | Declared meaning relevant here | Consequence |
| --- | --- | --- |
| `obo:BFO_0000108` exists at | A particular exists at a Temporal Region; domain Entity, range Temporal Region. | An accepted association entity could have evidenced existence at a Temporal Instant without asserting an entire interval of persistence. No new generic existence-at-time property is needed. |
| `obo:BFO_0000145` Relational Quality | A Quality specifically depending on multiple non-identical relata. | A possible category to review, requiring the actual runner and particular Base as independent-continuant relata. Naming a relation does not automatically establish that its reification is a Quality. |
| `obo:BFO_0000195` specifically depends on | Specifically dependent continuant dependency on an appropriate continuant. | Available for the relata if a Relational Quality interpretation is justified. It does not express Game context, recognized status or a source observation. |
| `obo:BFO_0000199` occupies temporal region | Applies to a Process or Process Boundary. | Do not use it to timebox a Quality. |
| `cco:ont00000850` Stasis of Quality | A Quality remains unchanged during a Temporal Interval. | Stronger than one boundary observation; not licensed by matching endpoint observations alone. |

`base:BaseballEventTemporalInstant` is already defined as a first or last
instant of a Temporal Region occupied by a Process within a Baseball Game.
Selecting that instant for the metric still requires the correct Process and
boundary evidence. A timestamp or source-row index does not select it by itself.

## Category question for the ontologist

One candidate is a **Relational Quality** specifically depending on the runner
and particular Base. Under that candidate, `exists at` could state its existence
at an evidenced boundary while leaving persistence between observations open.

This candidate is not admitted yet. It must independently explain what makes
the association a Quality, rather than merely reifying a relation because RDF
needs temporal qualification. Its institutional differentia and Game context
must be expressed with reviewed vocabulary, not hidden in a label or an ICE.
The prior recognition and contact decisions do not select this BFO category.

Identity is a separate unresolved requirement. One source observation cannot
be equated with one new Quality, and matching observations cannot prove one
continuous Quality episode. A named identity policy or reviewed treatment of
unidentified instances is needed before any instances can be mapped.

Consequently this file declares no class IRI, new object property, executable
shape or RML. The existing source fields, accepted act origins and adjudicated
destinations remain as reviewed. The first unresolved gate is the world-side
category and independent differentia, followed by identity and boundary evidence.
