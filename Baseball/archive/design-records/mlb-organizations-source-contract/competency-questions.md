# Competency questions and proposed answers

These answers constrain the future `mlb-organizations` RML and source SHACL.
Approval applies only to the explicit answers below.

| ID | Competency question | Proposed answer and graph consequence |
| --- | --- | --- |
| ORG-CQ-01 | How is a team identified independently of a response version? | A Baseball Team has one MLB team Non-Name Identifier that designates it and uses the MLB team-ID Reference System. The world entity IRI is keyed by the provider resource kind and team ID, never by an array position or response hash. |
| ORG-CQ-02 | How are leagues and divisions represented without inventing weak universals? | Each is an instance of the accepted generic CCO Organization. Its MLB league or division Non-Name Identifier designates it and uses the corresponding Reference System. No `BaseballLeague` or `BaseballDivision` class is introduced. |
| ORG-CQ-03 | Which names are asserted? | A non-null canonical `name` produces a Proper Name with the exact decoded Unicode text and designation of the identified Organization. Alternate, short, presentation, and code fields remain blocked or excluded. |
| ORG-CQ-04 | Does nesting a team beneath a league or division establish a season-scoped affiliation triple? | No. The response is evidence that mentions both Organizations, but the accepted vocabulary does not yet express the historically scoped institutional assertion. No affiliation edge is emitted. |
| ORG-CQ-05 | Does a nested league on a division establish a timeless division-to-league relation? | No. Both Organizations may be identified and named, but the relation remains blocked until an accepted temporalized or snapshot relation is reviewed. |
| ORG-CQ-06 | How are a Season and its Plan identified? | A Baseball Season and Baseball Season Plan are each keyed by the pair `(MLB league ID, season code)`. The league ID is an identity scope, not an unasserted affiliation edge. The Plan prescribes that Season. |
| ORG-CQ-07 | Which Season Phases are instantiated? | A regular-season phase is keyed by `(plan, regular-season)` when both regular-season boundary fields are non-null. A postseason phase is keyed by `(plan, postseason)` when both postseason boundary fields are non-null. Each is prescribed by the Plan and is an occurrent part of the Season. No offseason phase is created. |
| ORG-CQ-08 | How are provider date fields represented without inventing a boundary relation? | Every valid, non-null `seasonDateInfo.*Date` value becomes a Calendar Date Identifier that is a continuant part of the Plan, has its `xsd:date` value, and designates a Day. A field-key Non-Name Identifier designates that Date Identifier and uses an MLB season-date-field Reference System. No Date-to-Phase or Day-to-Phase relation is asserted. |
| ORG-CQ-09 | What happens when a selected field is null, absent, or malformed? | Null or absent selected values are permitted and emit no node or triple. A Phase is not minted from a partial boundary pair. A pre-RML input-contract validator quarantines a present malformed identifier or date rather than allowing RML to omit or convert it silently. |
| ORG-CQ-10 | How is source evidence versioned? | A generic Descriptive Information Content Entity represents each response and is keyed by endpoint family, request scope, and response SHA-256. Identifier-bearing world entities are not response-versioned. The response is about the entities evidenced in that response and has the record-level ICEs as continuant parts. |
| ORG-CQ-11 | Does the source assert an acquisition or measurement process? | No. HTTP and NiFi provenance belongs in the lane manifest. The RML does not invent a planning, measurement, affiliation, or other world-side Process absent from the response evidence. |
| ORG-CQ-12 | Can this module be disconnected? | Yes. Its acquisition, RML, SHACL, staging, quarantine, promotion, provenance, and graph namespace are module-owned. The persistent authoritative triple store is the only semantic integration boundary. |
| ORG-CQ-13 | What must survive deletion of transient JSON? | The request metadata, response hash, mapping version, validation report, promoted graph hash, promotion result, and graph provenance survive. Successful raw JSON is removed only after validated graph-pair promotion; failures remain quarantined for retry. |

## Required pre-mapping input checks after approval

- Before RML, validate the shape and lexical form of every present selected
  provider ID and date. A malformed present value sends the input to the
  module quarantine.
- Null and absent optional values are allowed and remain available to the RML
  null policy; they are not treated as malformed values.
- This gate operates on the transient source payload. It must not be
  implemented as RDF SHACL because a field omitted by RML is no longer
  observable in the generated graph.

## Required source-SHACL consequences after approval

Source SHACL runs only after RML and validates emitted RDF cardinality,
datatypes, values, and prohibited edges. It does not claim to validate a
present source value that RML failed to emit.

- An emitted team, league, or division identifier must have exactly one
  non-empty provider value, designate exactly one expected Organization, and
  use exactly the matching MLB Reference System.
- A canonical Proper Name must preserve the decoded source text, designate the
  same Organization as the record identifier, and never be emitted for null.
- Every emitted Season Plan must prescribe its keyed Season and at least one
  emitted reviewed Phase.
- Every Phase must be prescribed by that Plan and be an occurrent part of that
  Season.
- Every emitted Calendar Date Identifier must have exactly one valid date,
  designate a Day, and be a continuant part of the keyed Plan.
- The graph must contain no source-asserted team/league/division affiliation
  edge and no Date-to-Phase boundary edge.

Analytical checks that compare reference identities with existing MLB-game
identities are SPARQL regression checks, not source conformance constraints.
