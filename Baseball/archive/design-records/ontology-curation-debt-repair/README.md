# Ontology curation debt repair proposal

Status: **accepted by the ontologist on 2026-08-29; implementation pending**

This package audits all 31 existing BaseballO classes named in the frozen
ontology-curation debt manifest. It supplies candidate repairs for 30 and
leaves `GroundedIntoDoublePlayProcess` explicitly blocked because its
identity-bearing institutional and physical differentiae are not yet modeled.
It does not add a new source family and does not authorize a change to the
active ontology, axiom overlay, debt manifest, RML, SHACL, SPARQL, generated
RDF, or serving layer.

The proposal has four goals:

1. give every retained class exactly one direct named parent grounded through
   BaseballO, BFO, or CCO;
2. make every definition singular and Aristotelian, using the label of the
   proposed direct parent as its genus;
3. supply an English label, definition, example, and evidence-limiting comment
   for every class; and
4. keep relational restrictions in the proposed overlay section rather than
   using multiple asserted taxonomy parents.

One supporting class, `BaseballGameHostingFunction`, is proposed as a
realizability-safe candidate differentia for `BaseballVenue`. Its acceptance
requires evidence that a Material Artifact bearer was designed for hosting
Baseball Games; selection or a historical game occurrence alone is
insufficient and requires another pattern. No object property
or datatype property is proposed. Every relation in the candidate axioms is
already present in the repository's pinned BFO or CCO vocabulary.

## Proposed repair groups

| Group | Classes | Proposed disposition |
| --- | ---: | --- |
| Teams, roles, venue, and time | 9 | Preserve all existing classes; refine two BFO temporal parents and the venue parent; use a proposed hosting Function rather than entailing an actual game; complete annotations. |
| Timestamp and field-coordinate information | 4 | Ground the information classes in existing CCO vocabulary, use the separately reviewed ICE-direct-value foundation, and withhold executable coordinate use pending source-semantic review. |
| Double-play and foul-tip structure | 5 | Repair Double Play and foul-tip terms; leave Grounded Into Double Play frozen until independent institutional and physical differentiae exist. |
| Challenges and ball motion | 5 | Keep one taxonomic parent and move intersecting classifications to reviewed overlay axioms. |
| Replay transition leaves | 8 | Use the final judgment kind as the sole parent and infer affirming or overturning grouping from existing union axioms. |

The inventory contains exactly 31 unique classes: 30 candidate repairs and one
explicit blocker. A class may address more than one frozen finding even though
it appears in only one group.

## Decisions that require the ontologist

- Whether `BaseballVenue` is always a CCO Facility rather than the broader
  Material Artifact, and whether the proposed Baseball Game Hosting Function
  supplies the correct design basis.
- Whether the proposed field-coordinate universals should remain active when
  MLB `coordX` and `coordY` semantics and value representation have not yet been
  approved. This draft gives them coherent candidate meanings but does not
  authorize mapping them.
- Which independently defined institutional criterion and world-side
  ground-ball structure distinguish `GroundedIntoDoublePlayProcess`. The
  former circular Rule/Judgment/Decision support terms have been removed and
  are not offered for approval.
- Whether the legacy IRI `FoulTipCallICE` should retain its IRI with the human
  label "Foul Tip Decision ICE," as proposed, or be replaced through a later
  migration.
- Whether the necessary-and-sufficient challenge and replay intersections in
  the proposed overlay are accepted as written.

## Files in this package

- [`competency-questions.md`](competency-questions.md) states what the repaired
  vocabulary must support.
- [`source-evidence.md`](source-evidence.md) records the repository and pinned
  ontology evidence used for the draft.
- [`field-selection-inventory.md`](field-selection-inventory.md) gives the
  complete 31-class repair matrix.
- [`source-independent-mermaid.md`](source-independent-mermaid.md) exposes the
  proposed world-side and information-side shapes before any implementation.
- [`proposed-ontology.ttl`](proposed-ontology.ttl) is a review-only candidate
  taxonomy, annotation set, and overlay section.
- [`review.json`](review.json) is a draft review record. Its artifact arrays
  bind the finalized review artifacts by canonical hash while leaving the
  package in draft status for ontologist review.

Acceptance must name this package and the accepted or rejected decisions.
General instructions to continue do not constitute acceptance. If accepted,
the decision record must be archived and committed before a later change edits
any executable or authoritative artifact.
