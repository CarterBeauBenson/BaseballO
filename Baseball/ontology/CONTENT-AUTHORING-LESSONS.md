# BaseballO ontology and semantic-ingestion lessons learned

This document records failure patterns that must remain visible after their
implementations are removed. [`AUTHORING-RULES.md`](AUTHORING-RULES.md) states
the binding workflow; this file explains why those gates exist.

The recurring root causes are:

1. treating ontology construction as source-schema translation;
2. replacing reality with information about reality;
3. collapsing a measurement with the entity measured;
4. inventing field-specific classes before searching accepted vocabulary;
5. mapping duplicate or derivable data as new evidence;
6. skipping visual and ontologist review before implementation;
7. confusing successful execution with semantic correctness; and
8. allowing an early modeling error to propagate into RDF, SQL, and the UI;
9. inferring the kind of a whole from a part, plan, context, or provider label;
   and
10. distributing a missing differentia across a circular cluster of new names.

## Reality and information about reality

1. An ICE is about an entity; it is not that entity. Keep source records,
   data-element ICEs, measurement ICEs, estimates, classifications, and
   decisions distinct from their world-side referents.
2. Do not “embezzle” the semantics of a missing quality, relation, geometry, or
   process profile into a long ICE class name or definition.
3. A provider-specific record class may identify the grain and provenance of a
   record. It does not license provider-specific versions of every measured
   phenomenon.
4. Preserve source terminology as information. Assert a normalized world-side
   entity only when its identity criteria and differentiae are reviewed.
5. Keep physical history, institutional adjudication, source classification,
   analytical estimate, and downstream decision-support result distinct.
6. A successful transformation that produces syntactically valid triples can
   still be ontologically wrong.

## Measurements, qualities, and geometry

7. A measurement ICE is not speed, velocity, angle, distance, acceleration,
   trajectory, or contact quality.
8. A measurement must terminate at an accepted measured quality, relation,
   spatial entity, temporal entity, process, or process profile—not merely at
   the nearest Pitch Act, Swing Act, Plate Appearance, or ball motion.
9. Identify the bearer or relata of a measured entity and its temporal scope.
   Measurements at contact, release, or plate crossing cannot silently inherit
   the entire enclosing event interval.
10. Angle semantics belong to the geometric relation among the relevant fiat
    points, fiat lines, artifacts, and time. The numeric ICE reports that
    angle; it does not create it.
11. Distance semantics belong to an extent, path, sites, or relata. A projected
    distance estimate must remain distinct from an actually traversed path.
12. Preserve units, precision, method, and whether a value is observed,
    calculated, adjusted, or estimated.
13. Do not invent a field-specific measurement subclass when the generic CCO
    measurement pattern plus an accepted measured entity expresses the truth.
14. If the measured world-side referent is missing from accepted vocabulary,
    record a gap and stop that field.

## Source selection and de-duplication

15. Compare a proposed source against the authoritative raw MLB payload and
    accepted MLB coverage before ontology or RML work. A field omitted by the
    current RML is mapping-coverage debt in the owning lane, not novelty in a
    later endpoint.
16. Exclude assertions already supplied by the authoritative MLB feed, even
    when another provider uses different column names or exposes a wider
    population or historical range.
17. Keep deterministically derivable values downstream unless preserving a
    separately reviewed source assertion is itself important.
18. Use join identifiers for identity and provenance without automatically
    turning them into domain RDF.
19. Similar labels across providers do not prove semantic identity; different
    labels do not prove new evidence.
20. Missing data never proves that an entity, act, process, quality, or event
    did not exist. Negative claims require a completeness contract.

Source, provider, grain, and provenance normally differentiate ICE instances,
not universals. A provider-specific record class requires an independent
intensional differentia needed for reasoning; provider code systems normally
remain Reference System individuals.

## Classes, axioms, and identity

21. Do not create one class per API field, CSV column, source enumeration,
    provider category, or analytical output.
22. Search BaseballO, BFO, and CCO by definition and superclass before
    proposing vocabulary.
23. A class proposal begins with the world-side universal and its parent, not
    with the column that motivated the search.
24. Every accepted class has one named parent and a singular Aristotelian
    genus-and-differentia definition. Restrictions state reviewed universal
    truths rather than source conveniences.
25. Never introduce a new object property merely to make a mapping easy.
26. Encode identity policy before IRI templates. A stable-looking string is not
    automatically the identity of the entity it describes.
27. Keep persistent roles, game-scoped roles, acts, processes, and the persons
    or organizations bearing or participating in them distinct.
28. Use taxonomy for kinds, parthood for components, and precedence for order.
    Do not use subclassing or causal language as a shortcut.
29. Parthood does not transmit taxonomy. A Process is not an Act because it has
    Acts as parts, and a part does not inherit the class of its containing Game
    or Season.
30. Admit an Act only when at least one Agent plays a causative role in that
    Act. Admit a Planned Act only when a Directive Information Content Entity
    held by at least one of its Agents prescribes it. Objective or other
    intentional structure is required only where the selected subclass
    requires it. Governance, prescription of a larger Process, affiliation,
    and benefit do not establish agentivity in that Process.
31. Do not turn temporary context into an intrinsic primitive bearer kind.
    Query a Person, Team, or Organization through its Role, organizational
    context, realization, Stasis, and Temporal Interval. A contextual bearer
    class is only a reviewed defined query view over that full pattern, never
    a substitute for it.
32. Historically scoped institutional assertions such as affiliation,
    membership, status, assignment, and home-venue assignment require an
    accepted temporalized relation, Stasis/history pattern, or scoped
    intermediary when their validity across time is represented. A documented
    snapshot may use an accepted binary relation whose semantics support it.
    Prose such as “during season” does not temporalize an OWL assertion.
33. Every load-bearing term in a differentia must be an accepted class or
    object property, or an explicitly reviewed proposal term, and the axioms
    must express the same structure.
34. Do not define a closed group of proposal terms only through one another.
    An independent accepted anchor must supply the identity-bearing
    differentia, not merely occur somewhere else in the restriction graph.
35. A comment admitting that the distinguishing quality, relation, or profile
    remains unmodeled does not make the class safe. Block it until the
    world-side structure is expressible.
36. A Relational Quality identifies the multiple non-identical independent
    continuants on which it specifically depends and its temporal scope. Fiat
    or frame-relative relata additionally require the continuant wholes or
    reference frame needed by the identity account. A Process Profile
    identifies both the profiled Process and the dependent pattern of change
    that distinguishes the profile.
37. A CCO Artifact Function requires evidence that its Material Artifact
    bearer was designed for Processes requiring the Function. Mere selection,
    assignment, or historical participation does not establish an Artifact
    Function; use an accepted Role or another reviewed pattern when design is
    absent.
38. A Stasis represents persistence or lack of the relevant change. It does
    not realize a Role, Disposition, or Function. Participation of a Role and
    bearer in a Stasis of Role is distinct from realization by another
    Process.
39. Keep a persistent Role's identity separate from the identities of its
    realization Processes. A reviewed generic Process or Act may provide a
    stable counting grain while more specific Acts additionally realize the
    same Role.
40. Translate accepted competency-question answers into executable SHACL when
    they constrain graph conformance. Run that SHACL in the source's NiFi lane
    before promotion; do not duplicate the semantic review in Python.

The general lesson is that relational context must not be turned into a class
differentia without argument. A process does not become a Planned Act merely
because a Rule or Plan prescribes it; the temporally extended whole and its
intentional Act parts must each be classified at their own level. Likewise, a
Person does not need a new membership Role merely because an existing
Occupation Role has a particular Organization as its context or persists over
a bounded interval. Reuse the Role, organizational-context relation, Stasis of
Role, and Temporal Interval pattern unless a genuinely distinct realizability
and identity condition is established.

## RML and Mermaid review

41. RML is not a row converter. One row can evidence several information-side
    and world-side individuals connected by an accepted semantic pattern.
42. Start from a source-independent Mermaid shape, then bind source fields to
    it. The shape of a JSON object or CSV row must not dictate the graph.
43. Review-only Mermaid comes before RML for a new source family. Generated
    Mermaid after implementation is necessary but cannot retroactively approve
    the design.
44. Mermaid must expose relation directions, identity scope, temporal context,
    measurements and their targets, null behavior, exclusions, and unresolved
    gaps.
45. Never draw an unresolved or dashed edge as though executable RML emits it.
46. Every implemented triples map must trace back to an approved pattern.
47. A mapping that appears implausibly fast or dramatically flatter than the
    established MLB graph should be stopped and inspected before execution.

## Staged proof and containment

48. Prove one representative record before transforming one game.
49. Inspect one complete game semantically before touching a corpus.
50. SHACL proves an executable constraint contract; it does not replace human
    review of whether the graph represents the right things.
51. Do not expose a new source in SPARQL contracts, SQL, or the UI until the
    authoritative RDF pattern has passed the earlier gates.
52. When a foundational pattern is rejected, remove its classes, axioms,
    mappings, SHACL, fixtures, graphs, derived stores, UI dependencies, and
    evidence before restarting. Partial reuse can preserve the same bad
    assumptions under new names.
53. Derived SQL and indexed RDF are semantically disposable. Authoritative RDF
    is not; this makes semantic review before promotion especially important.
54. Preserve useful benchmark evidence, but do not retain rejected semantic
    artifacts as active baselines.

## Required audit before acceptance language

Before describing a content family as complete:

- verify the source-field de-duplication inventory;
- inspect every ICE and state exactly what it is about;
- inspect every measurement target, bearer or relata, unit, precision, method,
  and temporal scope;
- verify that all world-side classes have source-independent identity criteria;
- confirm that every local class has one BFO/CCO-grounded named parent and a
  reviewed Aristotelian definition;
- confirm that proposal vocabulary appears nowhere in executable artifacts;
- compare approved source-independent Mermaid, source-specific Mermaid, RML,
  emitted RDF, SHACL, and fixtures;
- inspect the one-record and one-game output before corpus execution;
- verify that serving and UI work began only after authoritative acceptance;
  and
- run the repository validator while separately recording semantic questions
  that automation cannot decide.
