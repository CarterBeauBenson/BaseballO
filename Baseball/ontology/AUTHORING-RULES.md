# BaseballO content authoring rules

These rules govern ontology and semantic-ingestion work in BaseballO. The
project owner is the ontologist. Source availability, a convenient column
name, or a working transformation does not authorize an ontological decision.

## 1. Start with questions and evidence

Write the decision-support or research questions before proposing classes or
mappings. For each source family, record:

- provider, product, endpoint or file contract, version, and observation date;
- observed paths or columns, types, enumerations, units, null behavior, and
  correction behavior;
- identifiers and the scope in which each is unique;
- one positive example and the closest negative or ambiguous example;
- whether each value is observed, estimated, classified, adjudicated, or
  deterministically derived; and
- the source terminology separately from any normalized BaseballO meaning.

Unknown or ambiguous fields do not license a class, relation, IRI template,
SHACL constraint, RML condition, or reasoning rule.

## 2. De-duplicate before modeling

Compare every candidate field against the authoritative MLB feed, accepted
BaseballO RDF, and downstream derivations. Assign exactly one review status:

| Status | Meaning | Mapping consequence |
| --- | --- | --- |
| authoritative duplicate | The same assertion is already supplied by an accepted source | Exclude from the new source mapping |
| deterministically derivable | Complete accepted inputs already determine it | Derive downstream; do not ingest it as new domain truth |
| identity or join only | It links records but adds no domain assertion | Use only in execution and provenance policy |
| genuinely additional | It supplies evidence not otherwise available | Continue to semantic modeling |
| unresolved | Meaning, identity, unit, or referent is not established | Defer and record the gap |

Similar labels do not prove identical meanings. Conversely, a differently
named provider field does not become new evidence when it duplicates an
accepted MLB assertion.

## 3. Model reality before information about reality

One source row may evidence several distinct entities. Never collapse them
because they occur in one JSON object or CSV record.

| Diagnostic question | Candidate category |
| --- | --- |
| Who or what persists? | person, organization, team, artifact |
| What dependent characteristic exists? | quality, role, disposition, or function |
| What intentional performance occurred? | act |
| What physical change or motion occurred? | process |
| What spatial or geometric entity exists? | site, fiat point, fiat line, fiat surface, or relational quality |
| What was institutionally counted or decided? | rule-governed process, adjudication, or decision |
| What source object describes it? | record ICE and data-element ICEs |
| What number and unit describe it? | measurement ICE about a measured entity |
| What model output was produced? | estimate or classification ICE with method provenance |
| When did it occur? | temporal region, distinct from a time-value ICE |

An ICE is about something; it is not the thing itself. A record ICE does not
replace the baseball event it describes. A classification ICE does not become
the classified process. A measurement ICE does not become the speed, angle,
distance, trajectory, quality, or process profile it measures.

Classify each occurrent at the level whose differentia are actually present.
The fact that a Plan or Rule prescribes, governs, schedules, or describes a
process does not make that process a Planned Act. A temporally extended whole
may be a BFO Process whose occurrent parts include intentional Planned Acts,
physical processes, and institutional processes. Test agentive and objective
structure at the level of the candidate Act rather than inheriting it from the
whole process or from an information artifact about the whole.

Parthood does not transmit taxonomy in either direction. The presence of an
Act as a part does not make the whole an Act, and occurrence inside a larger
Process does not make every part a Planned Act. Admit an Act only when at least
one Agent plays a causative role at that Act's own level. Admit a Planned Act
only when, additionally, a Directive Information Content Entity held by at
least one of its Agents prescribes that Act. Require an Objective or other
intentional structure only where the selected subclass requires it. `agent
in` and `has agent` likewise require actual agentive participation; governing,
prescribing, hosting, benefiting from, or being affiliated with a Process is
not enough.

Before proposing a membership, status, assignment, or affiliation Role, test
whether an accepted Occupation Role or other existing Role already carries the
intended fact through `has organizational context`. Represent the interval of
that context with the accepted Stasis of Role and Temporal Interval pattern
when evidence supports boundaries. A different grounding relation, source
label, roster name, or temporal scope does not by itself establish a distinct
Role universal; a new Role requires its own realizability and identity
conditions.

Do not replace that Role pattern with an intrinsic primitive kind of the
bearer. A Person, Baseball Team, or Organization is queried through the Role
it bears, the Role's organizational context, its realization, and its bounded
Stasis. A contextual bearer class is permissible only as an explicitly
reviewed defined query view equivalent to that full pattern; it must not erase
the particular Game or time scope.

Apply the same discipline to historically scoped institutional assertions,
including affiliation, membership, status, assignment, and home-venue
assignment, when the dataset represents their validity across time. Use an
accepted temporalized relation, Stasis/history pattern, or explicitly scoped
intermediary. A clearly documented snapshot assertion may use an accepted
binary relation when that relation's semantics support the snapshot. An
assertion is not made temporal by adding "during season" to its prose label or
Mermaid edge. If the accepted ontology has no adequate pattern for the
intended historical claim, record the gap and withhold it.

Never embed a missing world-side structure in a field-specific ICE class. A
class name such as “measurement of provider field X” is not a substitute for
identifying the measured quality or relation and its bearer or relata.

Provider, source, record grain, and provenance normally distinguish ICE
instances, not ontology universals. Reuse generic Descriptive ICE,
Measurement ICE, Estimate ICE, Algorithm, and Reference System patterns.
Create a specialized ICE class only when it has a source-independent
intensional differentia needed for reasoning. Provider code systems are
normally Reference System individuals rather than one class per provider.

## 4. Measurements and geometry

The minimum reviewed measurement pattern identifies:

```text
measured entity, quality, relation, or process profile
  <- is about or measures - Measurement ICE
Measurement ICE
  -> has measurement value -> literal
  -> uses or designates unit -> accepted unit
  -> is generated by or sourced from -> measurement/provenance context
```

Also record the available precision and whether the value is directly
observed, calculated, or estimated. Do not attach a measurement generically to
a Pitch Act, Swing Act, Plate Appearance, or motion merely because that is the
nearest event in the source record.

Angle and distance semantics remain in reality. An angle requires the reviewed
geometric entities and relation at the relevant time. A distance requires the
reviewed spatial extent, path, sites, or relata. The information artifact only
carries information about that structure.

BaseballO does not use BFO or CCO Spatial Region classes for domain geometry.
Field-relative frames use reviewed Fiat Points, Fiat Lines, Fiat Surfaces,
Sites, Relational Qualities, and generic Reference System ICEs. Removing a
Spatial Region from an imported pattern does not authorize a convenient
replacement: if the remaining world-side referent cannot be stated with
accepted vocabulary, record the gap and stop.

A Relational Quality proposal identifies the multiple non-identical
independent continuants on which it specifically depends and the time at which
the quality exists. Where fiat or frame-relative relata are used, identify the
continuant wholes or reference frame required by the identity account. A
Process Profile proposal identifies the Process it profiles and the dependent
pattern of change that distinguishes that profile. If accepted relations
cannot connect the quality, relata, Process, and changing entity, leave the
term unresolved; prose cannot supply the missing axiom.

## 5. Reuse BFO, CCO, and BaseballO first

Search the accepted ontology and dependency snapshots by IRI, label,
definition, and superclass before proposing vocabulary. Prefer:

1. an exact accepted term;
2. an existing accepted pattern composed from several terms;
3. a BaseballO subclass of the closest correct BFO or CCO class, proposed for
   ontologist review; and
4. a new relation only after explicit approval and documented failure of
   existing BFO/CCO relations.

Do not copy dependency classes into the BaseballO namespace. Inspect a
relation's definition, direction, domain, range, characteristics, and temporal
interpretation rather than trusting its label.

## 6. Class and axiom authoring

Every accepted BaseballO class has one English `rdfs:label`, one singular
Aristotelian `skos:definition`, exactly one direct named `rdfs:subClassOf`
parent, and a `skos:example` or an editorial note explaining why a verified
example is unavailable. Add comments for exclusions, evidence limits, source
ambiguity, and institutional meaning.

The definition begins with the class label and states genus and differentia.
It says what the entity is, not which provider field emits it. Do not create
one class per column, source code, provider category, or analytical result.

Every ontologically load-bearing class and object property named in a
differentia must resolve to accepted vocabulary or to a proposal term in the
same named review package. The candidate OWL must express the same relation
directions and restrictions as the definition. Do not use an undefined
technical phrase as a hidden class, quality, relation, or identity criterion.

Definitions require an independent semantic anchor. A set of new classes may
not receive its meaning only by referring around a closed cycle to one another.
An accepted term mentioned elsewhere in the restrictions is not an anchor
unless it supplies the identity-bearing differentia. If the axioms state only
necessary structure, the definition and review record must not claim that the
unmodeled differentia has been captured; the class remains blocked.

Named taxonomy and annotations belong in `BaseballO.ttl`. Reviewed
restrictions belong in `BaseballO-axioms-overlay.ttl`. The overlay declares no
new named domain vocabulary. Use `owl:equivalentClass` only for reviewed
necessary-and-sufficient conditions; otherwise state honest necessary
conditions. New object properties require explicit ontologist approval.

Roles, dispositions, and functions may remain unrealized. Do not add an
existential realization restriction that falsely entails an occurrence.

A Stasis describes persistence or the absence of a relevant change. It does
not realize a Role, Disposition, or Function. A Role and its bearer may
participate in a Stasis of Role during an evidenced interval, but that pattern
does not replace the distinct Process that realizes the Role.

Keep the identity of a persistent Role separate from the identities of the
Processes that realize it. Reuse a career- or tenure-persistent Role across
supported events instead of minting a Role per event. A generic Process or Act
used as a common event grain requires explicit review; once accepted, it is not
invalid merely because more specific event subclasses are also represented.

A CCO Artifact Function additionally requires evidence that its Material
Artifact bearer was designed for Processes requiring that Function. Mere
selection, assignment, or historical participation does not establish an
Artifact Function; use an accepted Role or another reviewed pattern when
design is absent.

## 7. Mermaid is a design gate, not decoration

Before executable RML for a new source family, create review-only Mermaid that
shows:

- source-independent world-side entities and relation directions;
- distinct information artifacts and what each is about;
- identity boundaries and temporal scope;
- measurement targets, units, estimates, and provenance;
- duplicate, derivable, identity-only, and rejected fields;
- unresolved gaps and intentionally withheld claims; and
- positive and nearby negative examples.

The ontologist must approve those shapes before ontology or RML implementation.
Generated Mermaid produced from existing RML is required later as a
non-regression check, but it does not satisfy the prior design gate.

For each accepted competency-question answer, state whether it is an RDF
conformance invariant or an analytical question. Put conformance invariants in
the owning source module's SHACL profile and run that profile in NiFi after RML
and before promotion. Put genuinely analytical answers in version-controlled
SPARQL regression checks. Do not recreate the same semantic decision as
imperative Python graph-review logic.

Every novel BaseballO class, object property, or data property declared in a
proposal Turtle file is enumerated exactly in that package's `review.json`
`proposedIris`. A restatement of an already accepted class for repair is not a
novel IRI. Every artifact hash recorded in a draft review matches the current
package-relative file; leave an artifact list empty while its file is changing
rather than retaining a stale pin.

## 8. RML implements an accepted account

RML is not a mechanical JSON/CSV serializer. Begin from the approved
source-independent pattern, then bind source fields to it. Preserve record
ICEs, data-element ICEs, identifiers, measurements, classifications, estimates,
and world-side entities as distinct individuals when supported.

Encode identity policy before IRI templates. Do not use mutable labels,
provider classifications, array positions without an approved structural
scope, or random UUIDs as substitutes for identity.

Every triples map must be assigned to one approved ontology pattern and one
source-specific Mermaid pattern. Source-specific review shows logical-source
filters, triples-map names, IRI templates, joins, conditions, units, and null
behavior. A dashed or proposed Mermaid edge must never be presented as emitted
RDF.

## 9. Prove the smallest unit before scaling

The required execution sequence is:

1. one representative source record;
2. one complete game;
3. procedural validation and SHACL;
4. human semantic inspection against the approved Mermaid;
5. positive and negative regression fixtures;
6. only then a bounded corpus run; and
7. only after equivalence and promotion evidence, serving or UI integration.

An unexpectedly fast mapping pass is a reason to inspect whether the semantic
structure was flattened. Transformation speed and triple count are not
evidence of correctness.

## 10. Acceptance boundary

Proposal terms are never imported, mapped, queried as accepted content,
admitted to reasoning, loaded into authoritative RDF, materialized into SQL,
or exposed in the UI. Stop at the first unresolved gate.

A content family is complete only when competency questions, source evidence,
de-duplication decisions, accepted ontology terms, identity policy, both
Mermaid views, RML, SHACL, positive and negative fixtures, semantic inspection,
deterministic regeneration, and ontologist decisions all agree.
