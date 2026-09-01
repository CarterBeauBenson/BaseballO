# Field selection inventory

## Response and row fields

| Field | Disposition | Source-specific treatment |
| --- | --- | --- |
| request bounds and retrieval time | provenance only | Persist in the run manifest; exclude from row identity and domain RDF. |
| response byte hash | provenance only | Persist before transient JSON removal and bind to the promoted graph pair. |
| `copyright` | source metadata not selected | Do not map as a baseball assertion. |
| `id` | identity and join only | Create a generic Non-Name Identifier using the MLB transaction-identifier Reference System; it designates the stable grouping DICE. |
| `person.id` | identity and join only | Conditionally join the row to the canonical Person IRI; include the value or JSON `null` in the row hash. |
| `person.fullName` | owned by the independent future MLB people module; diagnostic only here | Use transiently for join/Unicode diagnostics; this lane emits no name assertion and does not require the people graph to exist. |
| `person.link` | navigation metadata | Do not map. |
| `fromTeam.id` | identity and join only | Conditionally make the row about the canonical Baseball Team; include the value or JSON `null` in the row hash. No movement or role inference. |
| `fromTeam.name` | owned by the independent future MLB organizations module; diagnostic only here | Use transiently to diagnose a mismatched identifier; this lane emits no Proper Name and does not require the organizations graph to exist. |
| `fromTeam.link` | navigation metadata | Do not map. |
| `toTeam.id` | identity and join only | Conditionally make the row about the canonical Baseball Team; include the value or JSON `null` in the row hash. No movement or role inference. |
| `toTeam.name` | owned by the independent future MLB organizations module; diagnostic only here | Use transiently to diagnose a mismatched identifier; this lane emits no Proper Name and does not require the organizations graph to exist. |
| `toTeam.link` | navigation metadata | Do not map. |
| `date` | genuinely additional | Emit a Calendar Date Identifier that designates the corresponding Day; distinguish the field with a generic provider-field identifier. Do not bind a process boundary. |
| `effectiveDate` | genuinely additional | Emit a Calendar Date Identifier that designates the corresponding Day; distinguish the field with a generic provider-field identifier. Do not bind a process boundary. |
| `resolutionDate` | genuinely additional when non-null | Emit a Calendar Date Identifier that designates the corresponding Day; distinguish the field with a generic provider-field identifier. Do not bind a process boundary. |
| `typeCode` | genuinely additional | Emit a generic Nominal Measurement ICE that is a nominal measurement of the row, uses the MLB transaction-type Reference System, and has the exact code as text value. |
| `typeDesc` | code-list validation evidence | Include in the row hash and require consistency with the pinned transaction-type code list; do not treat it as a second type or world class. |
| `description` | genuinely additional when non-null | Emit a generic Descriptive Information Content Entity about the row with the exact Unicode text value. Never parse it into world assertions in this release. |

## Record and child identity

| Entity | Identity policy |
| --- | --- |
| grouping DICE | MLB transaction identifier-system IRI plus provider `id`; stable across repeated rows and acquisitions. |
| row/leg DICE | lowercase SHA-256 of the RFC 8785 canonical selected-content object specified in `source-evidence.md`; never array position. |
| transaction identifier ICE | deterministic child of the grouping IRI. |
| type classification ICE | deterministic child of the row-version IRI with fixed role token `type`. |
| description DICE | deterministic child of the row-version IRI with fixed role token `description`; absent when source value is null. |
| date identifier ICEs | deterministic children of the row-version IRI with fixed role tokens `date`, `effective-date`, and `resolution-date`. |
| provider-field identifiers | stable generic identifiers for those three fixed source keys using an MLB transactions field Reference System; each designates its corresponding date identifier. |
| Person and Baseball Team | existing canonical source-neutral identity policy; this lane does not mint source-local duplicates. |
| CCO Death | deterministic child of the row-version IRI only after the exact reviewed Death-code gate passes with a non-null Person. |

## Type-family disposition

| Type family | Release disposition | Reason |
| --- | --- | --- |
| exact reviewed Death code | conditional world mapping | May emit CCO Death only with a pinned exact code-list match and non-null canonical Person. |
| Trade | information layer only | Accepted Trade class exists, but persistent team-scoped Player Role/stint identity and supported Gain/Loss of Role parts are unresolved. |
| Number Change | information layer only | Accepted Uniform Number Assignment class exists, but the assigned number is only prose and has no structured identifier bearer. |
| every other provider type | information layer only | The source classification and description do not independently establish a precise world-side process structure. |

## Null, correction, and detachment policy

- A missing or JSON-null optional field emits neither an entity nor a literal.
- Empty strings, if supplied, fail source validation for fields whose contract
  requires non-empty text; they are not converted to null silently.
- Before RML, input/code-list validation quarantines malformed required
  provider identifiers, malformed required dates or a malformed present
  `resolutionDate`, unknown `typeCode` values, and `typeCode`/`typeDesc`
  mismatches. RML receives only admitted rows. A missing sibling graph does
  not fail this gate: canonical Person and Team IRIs follow the shared identity
  policy and can join after independent promotion.
- After RML, source-owned SHACL validates the emitted RDF graph. It does not
  inspect the raw JSON or substitute for input validation. A one-record fixture
  and source-to-RDF regression must prove that RML emits every selected
  required and conditionally present source value before activation.
- Re-observing the same selected semantic content reuses the row IRI. Changed
  content creates another version associated with its own acquisition
  provenance; it does not overwrite historical authoritative RDF.
- Successful promotion persists the RDF, manifest, source/code-list hashes,
  SHACL report, and provenance, then permits removal of the transient JSON.
  Failed input remains quarantined for bounded retry.
- Stopping or rebuilding this lane has no operational dependency on MLB games,
  organizations, people, venues, Statcast, or future source modules.

## Vocabulary decision

This contract proposes no class, object property, or data property. It uses
accepted BaseballO/BFO/CCO vocabulary plus source-specific individuals for MLB
identifier and code systems. Those provider systems are Reference System
instances, not one-off ontology classes.
