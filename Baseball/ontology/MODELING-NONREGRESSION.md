# BaseballO semantic non-regression rules

These are binding review rules for future ontology and semantic-ingestion
changes. Automated checks cover structural portions; the project ontologist
decides the semantics.

## Realist separation

1. World-side entities are modeled before information about them.
2. An ICE is about an entity and never substitutes for that entity.
3. Keep source records, data elements, identifiers, measurements, estimates,
   classifications, judgments, decisions, and their referents distinct.
4. Keep physical history, institutional adjudication, provider analysis, and
   downstream decision-support results distinct.
5. An Act requires at least one Agent playing a causative role at that Act's
   own level. A Planned Act additionally requires a Directive Information
   Content Entity held by at least one of its Agents to prescribe it. Require
   an Objective or other intentional structure only where the selected
   subclass requires it. Do not infer any of these from successful outcome,
   legality, a provider result label, or an enclosing Process; otherwise use
   the correct Process class or leave the candidate unresolved.
6. Prescription, governance, scheduling, or description by a Plan or Rule is
   a relation and does not entail that the prescribed occurrent is a Planned
   Act.
7. Classify each occurrent level independently: a temporally extended whole
   may be a Process with intentional Planned Acts, physical processes, and
   institutional processes as occurrent parts. Parthood does not transmit
   taxonomy from part to whole or whole to part.
8. Before proposing a membership, status, assignment, or affiliation Role,
   test whether an accepted Role plus organizational context and a Stasis of
   Role already expresses the fact. A new grounding context does not by itself
   license a new Role universal. Do not create a contextual Person, Team, or
   Organization as a primitive kind. A contextual bearer class is permitted
   only as a reviewed defined query view over the full Role/context/time
   pattern and must not replace that pattern.
9. Use taxonomy for kinds, parthood for components, and BFO precedence for
   sequence. Do not assert causation from array order. `has agent` or `agent
   in` additionally requires actual agentive participation; governance,
   prescription, affiliation, hosting, or benefit is not enough.
10. Missing source data does not establish nonexistence. Negative claims
    require an explicit completeness contract. Historically scoped
    institutional assertions such as affiliation, membership, status,
    assignment, and home-venue assignment require an accepted temporalized
    relation, Stasis/history pattern, or scoped intermediary when validity
    across time is represented. A documented snapshot may use an accepted
    binary relation whose semantics support it; prose such as “during season”
    cannot temporalize an OWL assertion.

## Measurements and geometry

11. A Measurement ICE is not the measured Quality, relation, spatial extent,
   Process, or Process Profile.
12. Every measurement pattern identifies its measured target, value, unit when
   applicable, provenance or method, available precision, and temporal scope.
   A Relational Quality also identifies the multiple non-identical independent
   continuants on which it specifically depends and its temporal scope; fiat
   or frame-relative relata additionally identify the continuant wholes or
   reference frame needed by the identity account. A Process Profile identifies
   the profiled Process and the dependent pattern of change it profiles.
13. Do not attach a measurement generically to an enclosing act or process
    when the actual measured target is more specific.
14. Speed, velocity, acceleration, angle, distance, trajectory, and other
    physical semantics remain on the world side.
15. An angle value requires a reviewed angle relation and its relevant fiat
    geometry; a distance value requires a reviewed extent, path, sites, or
    relata.
16. Keep direct observations, calculated values, adjusted values, projections,
    and model estimates explicitly distinct.
17. If an accepted measured referent is unavailable, defer the field instead
    of creating a provider-specific ICE that hides the gap.
18. Do not use BFO or CCO Spatial Region classes in BaseballO domain models.
    Ground field-relative geometry in reviewed Fiat Points, Fiat Lines, Fiat
    Surfaces, Sites, Relational Qualities, and a generic Reference System ICE.
    If that pattern cannot express the referent, leave the field unresolved.

## Vocabulary and identity

19. Do not create one class per source field, column, code, provider category,
    or analytical output.
20. Reuse accepted BaseballO, BFO, and CCO vocabulary before proposing a class.
21. Every accepted BaseballO class has one direct named parent grounded in BFO
    or CCO and a singular Aristotelian genus-and-differentia definition.
22. Definitions state what an entity is, not which source field reports it.
    Every load-bearing class and object property in the differentia resolves
    to accepted vocabulary or an explicitly reviewed proposal term, and the
    axioms express the same structure.
23. Restrictions express reviewed universal truths, never implementation
    convenience. A closed cluster of new terms cannot define itself only by
    circular reference; an independent accepted anchor must supply the
    identity-bearing differentia. Comments admitting missing semantics do not
    make the class safe.
24. New object properties require explicit ontologist approval.
25. Encode reviewed identity policy before constructing IRIs. Mutable labels,
    classification strings, and random identifiers are not domain identity.
26. Roles, dispositions, and functions may remain unrealized; their existence
    must not entail an actual realization. A CCO Artifact Function also
    requires evidence that its Material Artifact bearer was designed for
    Processes requiring the Function; selection, assignment, or historical
    participation alone does not establish it.
27. Keep persons, persistent roles, game-scoped roles, acts, processes, teams,
    sites, temporal regions, and artifacts distinct.

## Source boundaries

28. Before modeling a new provider, classify every field as an authoritative
    duplicate, deterministic derivative, identity/join-only value, genuinely
    additional evidence, or unresolved. Compare against the authoritative raw
    payload, not only the current mapping; omitted RML coverage is debt in the
    owning source lane.
29. Do not remap authoritative duplicates as new domain assertions.
30. Keep deterministic derivatives downstream unless a separately reviewed
    source assertion is itself the research object.
31. Join-only identifiers may support execution and provenance without
    becoming domain RDF.
32. Preserve provider terminology as information until normalization criteria
    are accepted. Provider, source, grain, and provenance normally distinguish
    ICE instances, and provider code systems normally remain Reference System
    individuals; neither automatically licenses a subclass.
33. Similar source labels do not prove identical meaning, and different labels
    do not prove independent evidence.

## Review and implementation order

34. Competency questions and source evidence precede ontology design.
35. The de-duplication inventory precedes Mermaid modeling.
36. Source-independent review-only Mermaid precedes ontology and RML changes
    for a new source family.
37. The project ontologist approves shapes, identity, classes, axioms, and any
    new relation before implementation.
38. Proposal terms never appear in executable RML, SHACL, SPARQL, reasoning,
    authoritative RDF, serving schemas, or UI code.
39. RML binds source evidence to an accepted pattern; it is not a mechanical
    JSON/CSV serializer.
40. Generated Mermaid derived from RML is a post-implementation non-regression
    check and does not replace prior design review.
41. Every triples map traces to one approved source-independent pattern and one
    source-specific pattern.
42. One-record execution precedes one-game execution; one-game SHACL and human
    semantic inspection precede any corpus run.
43. Corpus promotion precedes SQL materialization and UI exposure.
44. Successful execution, high triple count, or unusually fast implementation
    is not evidence of semantic correctness.
45. Stop at the first unresolved gate; do not carry an assumption forward to a
    later layer for convenience.
46. If a foundational pattern is rejected, remove every active and derived
    artifact that depends on it before restarting from the source evidence and
    Mermaid stages.
