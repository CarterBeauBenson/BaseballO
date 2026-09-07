# Ontology

[`BaseballO.ttl`](BaseballO.ttl) is the active project ontology. It contains the annotated class vocabulary and named-class taxonomy. Its natural-language definitions, labels, comments, examples, and taxonomic `rdfs:subClassOf` assertions can be shared without the optional logical restrictions.

Version `0.6.0` implements the accepted Final MLB authority and transaction
review. It adds nineteen reviewed classes for Major League free agency,
grounded roster-status declarations and their decision ICEs, player-side and
fielding dispositions, baseball-position descriptions, and persistent venue
parts, Sites, Functions, Qualities, and reference points. It adds no object
property. The overlay uses non-existential realization constraints for Roles,
Dispositions, and Functions so their existence does not imply that a realizing
Process occurred.

Version `0.5.3` retains one generic Batter Act per Plate Appearance as the
common Process that realizes the batter's career-persistent Batter Role.
Supported Swing and Bunt Acts may additionally realize that same Role. A
Stasis of Role expresses persistence through participation and never realizes
the Role; the authoritative SHACL profile enforces these competency-question
answers before NiFi promotion.

Version `0.5.1` corrects `BaseballGame` to BFO Process: the temporally extended
game has intentional Baseball Acts, physical processes, and institutional
processes as occurrent parts, but is not itself a Planned Act merely because a
Baseball Rule prescribes it.

Version `0.5.0` includes the physical-play and review extensions while
retaining the person-role identity model introduced in
`0.4.0`. Player and
Manager Roles are CCO Occupation Roles scoped to a person and Baseball Team;
batter, pitcher, fielder, catcher, baserunner, umpire, and official-scorer
roles persist by person and role type. Each mapped role participates in an open
CCO Stasis of Role with an unbounded Temporal Interval. Boundary modeling is
deferred until an authoritative tenure or retirement source is selected. The
retired Baseball Participant Role is no longer used. Fair Territory Site and
Foul Territory Site are BFO sites that are continuant parts of a Baseball
Field Site, not subclasses of Baseball Field Site.

Version `0.3.0` added the accepted replay-review model: the on-field judgment,
challenge, replay review, input and output decisions, review-result information,
and source event record remain distinct entities. Human-facing labels use
“Replay Review Result ICE”; legacy `...DispositionICE` IRIs are retained only
for identifier stability and do not denote BFO dispositions.

[`BaseballO-axioms-overlay.ttl`](BaseballO-axioms-overlay.ttl) is the optional axiom module. It imports BaseballO, the Cognitive Process Ontology, and the Modal Relation Ontology, then adds relational and cardinality restrictions derived conservatively from BaseballO's definitions. It declares no new named classes or object properties. The reviewed restriction on imported CCO Stasis states that a Stasis has zero `realizes` relations.

## Loading choices

- Load or share `BaseballO.ttl` for the annotated taxonomic backbone.
- Load or share `BaseballO-axioms-overlay.ttl` with its imports for the taxonomic backbone plus the optional axioms.
- Add, remove, or revise optional class restrictions in the overlay, not in `BaseballO.ttl`.

The repository keeps local Turtle snapshots of the Common Core Ontologies merge, Cognitive Process Ontology, and Modal Relation Ontology so overlay vocabulary can be checked offline. The import statements use the ontologies' canonical IRIs.

## Authoring and proposal gate

All new content must follow [`AUTHORING-RULES.md`](AUTHORING-RULES.md),
[`CONTENT-AUTHORING-LESSONS.md`](CONTENT-AUTHORING-LESSONS.md), and
[`MODELING-NONREGRESSION.md`](MODELING-NONREGRESSION.md), adapted to the
baseball domain. In particular, semantic ingestion begins with
source-independent entity patterns; records, data elements, world-side
entities, qualities, process profiles, measurements, classifications, and
decisions remain distinct.

The gate order is normative:

1. write the competency questions and source-evidence contract;
2. classify fields as duplicate, derivable, identity-only, genuinely
   additional, or unresolved;
3. draw source-independent Mermaid shapes showing the world-side referents,
   information artifacts, relation directions, identity boundaries, and
   intentionally withheld claims;
4. obtain ontologist approval for the shapes and every ontology or identity
   decision;
5. place accepted named classes and annotations in `BaseballO.ttl` and accepted
   logical restrictions in the overlay;
6. write source-specific Mermaid and executable RML against only accepted
   vocabulary;
7. prove one record and one game with SHACL plus human semantic inspection; and
8. only then consider corpus ingestion, SQL materialization, or UI exposure.

Generated Mermaid derived from existing RML is a non-regression artifact. It
does not replace the review-only Mermaid required before a new mapping is
written. A field that cannot reach an accepted world-side referent remains an
explicit gap; it must not be rescued by a provider-specific measurement or
record class that embeds the missing semantics in an ICE.

Unresolved modeling belongs in the single repository-level
[`proposals/`](../proposals/README.md) catalog. Proposal
terms are not imported, used by executable RML, admitted to reasoning, or
loaded into authoritative RDF. After ontologist acceptance, named-class
taxonomy and annotations go in `BaseballO.ttl`, while reviewed restrictions go
in `BaseballO-axioms-overlay.ttl`. New object properties require explicit
approval.

Run `python Baseball/scripts/validate_ontology_overlay.py` from the Git
repository root to verify that the base contains no optional restrictions, the
overlay introduces no named vocabulary, every referenced class and object
property occurs in the repository, and cardinality axioms do not use transitive
properties. The full `python Baseball/scripts/validate_repository.py` check
includes this validation.

The earlier `0.2.0` snapshot is preserved in [`../archive/ontology-v0.2.0.ttl`](../archive/ontology-v0.2.0.ttl). Do not modify the active ontology merely to make a mapping convenient; unresolved MLB game coverage belongs in that source module's [`ontology-coverage-gaps.yaml`](../sources/mlb-game/mapping/ontology-coverage-gaps.yaml).
