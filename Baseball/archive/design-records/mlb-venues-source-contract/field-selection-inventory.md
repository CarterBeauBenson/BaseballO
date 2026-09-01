# Field-level selection and de-duplication inventory

This inventory compares the standalone venue endpoint with the authoritative
MLB game payload and applies the accepted reference-source ownership migration.
"Migration target" means the reference graph may be populated before a later
equivalence-proven cutover; it does not reclassify a duplicate as genuinely
new.

| Endpoint field or family | Gate disposition | Proposed consequence |
| --- | --- | --- |
| `id` | identity/join-only | Required. Normalize the provider integer lexically and reuse the canonical `venue/{id}` entity; the identifier ICE uses the MLB venue-ID Reference System. |
| `link` | deterministically derivable | Exclude navigation metadata. The acquisition manifest already preserves the exact request URI. |
| `name` | authoritative duplicate; approved migration target | Emit or reuse a Proper Name ICE keyed by canonical Venue IRI, MLB official-name kind, and SHA-256 of the exact decoded lexical name. It designates the canonical Venue and may be part of each matching response DICE. Do not use `rdfs:label` as a substitute for the ICE. |
| `active` | unresolved | Exclude. Provider availability/status does not establish a physical venue state or temporal interval. |
| request/response `season` | identity and provenance context only | Preserve it in the evidence manifest and response-dependent IRIs. Do not designate a Baseball Season or assert season-long validity. |
| implied facility design | accepted vocabulary; source-specific inference under review | Type the identified resource as Baseball Venue and assert its stable, named Baseball Game Hosting Function. Do not assert a realization event. |
| implied baseball field | authoritative duplicate; approved migration target | Emit the stable canonical Baseball Field Site described by `fieldInfo`; do not add a direct Venue-to-Field relation. |
| `fieldInfo.leftLine` | authoritative duplicate; approved dimension migration | For each non-null positive number, emit selector identifier, selected boundary Fiat Point, Distance Quality, and Measurement ICE using Foot. |
| `fieldInfo.leftCenter` | authoritative duplicate; approved dimension migration | Same shape; "left center" does not entail a fence, wall, or undocumented bearing. |
| `fieldInfo.center` | authoritative duplicate; approved dimension migration | Same shape; designate the provider-selected center field-boundary Fiat Point. |
| `fieldInfo.rightCenter` | authoritative duplicate; approved dimension migration | Same shape; "right center" does not entail a fence, wall, or undocumented bearing. |
| `fieldInfo.rightLine` | authoritative duplicate; approved dimension migration | Same shape; designate the provider-selected right-line field-boundary Fiat Point. |
| missing or JSON `null` dimension | resolved absence policy | Emit no selector-specific point, Distance Quality, or Measurement ICE. |
| present nonnumeric or nonpositive dimension | invalid source assertion | Do not silently omit or coerce it. Pre-mapping input validation fails and NiFi quarantines the input evidence before RML. |
| `fieldInfo.capacity` | unresolved | Exclude. Counted entity, venue configuration, and effective time are not established. |
| `fieldInfo.turfType` | unresolved | Exclude. The classified world-side referent and status/configuration semantics are not established. |
| `fieldInfo.roofType` | unresolved | Exclude. Do not infer a roof artifact, design, open/closed state, or temporal validity. |
| `location.defaultCoordinates.latitude`, `longitude` | unresolved | Exclude. The exact located physical point and coordinate reference system are not established. |
| `location.azimuthAngle` | unresolved | Exclude. The two directions/Fiat Lines, shared Fiat Point, frame, unit, and method are not established. |
| `location.elevation` | unresolved | Exclude. Bearer, unit, vertical datum, and measurement semantics are not established. |
| `location.address1`, `address2`, `city`, `state`, `stateAbbrev`, `postalCode`, `country`, `phone` | authoritative duplicate but outside admitted surface | Exclude. Strings alone do not establish geographic entities, address structure, organizational identity, or phone-number semantics. |
| `timeZone.id`, `tz`, `offset`, `offsetAtGameTime` | unresolved | Exclude. Identifier system and offset temporal scope are not established. |

## Emission cardinality

- One canonical Venue, venue-ID identifier, hosting Function, and Field Site per
  normalized MLB venue ID.
- One content-addressed response DICE per venue ID, requested season, and
  canonical response SHA-256.
- Zero or one Proper Name reference per nonempty response `name`; identical
  decoded lexical names reuse the same ICE across snapshots.
- Zero or one dimension subgraph per each of the five selectors. Each emitted
  subgraph contains one selector identifier, one provider-selected boundary
  Fiat Point, one Distance Quality, and one Measurement ICE. The snapshot
  origin Fiat Point is shared by the emitted dimensions in that response.
- No array position participates in any identity.

## Future input-validation and SHACL obligations

The owning lane's pre-mapping input validator must distinguish missing/null
selectors from present invalid values and quarantine nonnumeric or nonpositive
values before RML. It must not depend on SHACL to discover a bad input that RML
could omit.

After RML and before promotion, the owning `mlb-venues` SHACL profile must
enforce the RDF contract: canonical Venue/identifier identity,
Venue-versus-Field distinction, no direct Venue-to-Field edge, exactly two
distinct Fiat Point bearers for each admitted Distance Quality, exactly one
Foot unit and positive decimal value per emitted measurement,
selector/reference-system designation, and response-local cardinality.
Analytical equivalence and later graph-owner cutover remain SPARQL regression
work rather than source SHACL.
