# Field selection inventory

## Fields

| Field | Disposition | Treatment |
| --- | --- | --- |
| `id` | identity or join only | Candidate identity for overall provider grouping; repeated IDs require separate row identity proof. |
| `person.id` | identity or join only | Join to canonical Person; record is about that Person. |
| `person.fullName` | authoritative duplicate | Use only as validation evidence; canonical Person/name comes from accepted identity/name sources. |
| `fromTeam.id` | identity or join only | Joins a Team to a record; the type and description must independently support any prior-context or agent claim. |
| `toTeam.id` | identity or join only | Joins a Team to a record; the type and description must independently support any resulting-context or agent claim. |
| team names | authoritative duplicate | Validate joined Team identity; do not duplicate Proper Names. |
| team links | identity or join only | Navigation metadata only. |
| `date` | genuinely additional | Date Identifier for source record date; not automatically event time. |
| `effectiveDate` | genuinely additional | Date Identifier for an effective boundary only after the affected process/role is identified. |
| `resolutionDate` | genuinely additional | Date Identifier candidate for a resolution boundary; optionality and type determine whether the binding is licensed. |
| `typeCode`, `typeDesc` | genuinely additional | Use generic Nominal Measurement ICE and a provider Reference System instance; the classification does not determine a world class. |
| `description` | genuinely additional | Text value on the generic Descriptive ICE; structured world claims require independently reviewed extraction rules. |

## Type-family semantic dispositions

| Type family | Disposition | World-side treatment |
| --- | --- | --- |
| Trade | genuinely additional | Proposed Baseball Personnel Trade Act; group repeated participant rows under one supported act. |
| Signed / Signed as Free Agent | unresolved | Reuse Act of Contract Formation and Act of Employment only when parties and meaning are supported. |
| Assigned / Recalled / Optioned / Outrighted / Selected | unresolved | May support the start or end of a Stasis of an existing team-scoped Occupation Role; exact role type and effective boundary are required. |
| Released / Declared Free Agency / Retired | unresolved | May support Loss of Role, contract termination, or retirement act; do not conflate them. |
| Claimed Off Waivers / Designated for Assignment | unresolved | Multi-stage institutional procedures; source code alone does not establish every role change. |
| Number Change | genuinely additional | Proposed Uniform Number Assignment Act, but only structured evidence may create identifier assignment claims. |
| Suspension | unresolved | May restrict realization without ending Player Role; needs a suspension/regulation account. |
| Status Change | unresolved | Provider umbrella with no sufficient world-side differentia. |
| Acquired / Obtained | unresolved | Outcome wording does not identify the causative act. |
| Death | genuinely additional | Reuse CCO Death; explicitly not a transaction act. |

## Proposed ontology vocabulary

| Class | Direct parent | Purpose |
| --- | --- | --- |
| `BaseballPersonnelTradeAct` | CCO Planned Act | Multi-agent act with supported Gain/Loss of Role parts involving team-scoped Occupation Roles. |
| `UniformNumberAssignmentAct` | CCO Act of Declarative Communication | Act assigning a number Code Identifier to a team-scoped Player Role. |

Generic CCO Descriptive Information Content Entity, Nominal Measurement ICE,
and Reference System instances cover the information side. No generic Baseball
Personnel Transaction Act, roster-membership role, field-specific ICE class,
reference-system class, or new object property is proposed. Existing
Occupation Roles, `has organizational context`, Stasis of Role, and Temporal
Intervals carry team membership and its temporal scope.
