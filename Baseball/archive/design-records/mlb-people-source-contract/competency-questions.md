# Competency questions and proposed answers

| ID | Competency question | Proposed answer and graph consequence |
| --- | --- | --- |
| PEOPLE-CQ-01 | How is a Person identified independently of a response version? | The Person IRI is keyed by `(MLB person resource kind, person ID)`. A Non-Name Identifier designates the Person and uses the MLB person-ID Reference System. No array index or response hash identifies the Person. |
| PEOPLE-CQ-02 | Which names are mapped? | A non-null `fullName` becomes a Proper Name and a non-null `nickName` becomes a Nickname. Each designates the Person and carries the exact once-decoded Unicode text. Other name parts and presentation variants remain blocked or derived. |
| PEOPLE-CQ-03 | What does `height` describe? | A valid feet/inches string supports a Height quality inhering in the Person and a generic Measurement ICE that measures that quality. The strict parse is converted to strictly positive total inches, asserted as a decimal, and uses CCO Inch. |
| PEOPLE-CQ-04 | Is a Height Measurement Process asserted? | No. The endpoint reports a measurement result but does not identify the measuring event, method, instrument, time, or agent. The RML emits no invented Measurement Process. |
| PEOPLE-CQ-05 | What does the bare integer `weight` describe? | Nothing executable yet. The likely target is Mass rather than CCO Weight, but the response value has no explicit unit and this package has no official evidence proving pounds. No Mass, measurement, value, or pound unit triple is emitted from `weight`. |
| PEOPLE-CQ-06 | How is `birthDate` represented? | A Birth Process has the Person as participant. The response is about that Birth and has a Calendar Date Identifier part whose date value designates a Day. No Birth-to-Day localization or boundary edge is asserted. |
| PEOPLE-CQ-07 | What happens for null, absent, or malformed selected values? | Null or absent optional fields are permitted and emit no node or triple. Before RML, a source-contract input validator quarantines a present malformed ID, date, or height string, including any height whose computed total inches is not strictly positive. |
| PEOPLE-CQ-08 | How is source evidence versioned? | A generic Descriptive ICE represents each people response and is keyed by request scope plus response SHA-256. Measurement and date-evidence ICEs are response-versioned; the Person, Height quality, and Birth Process are not. |
| PEOPLE-CQ-09 | How is text encoding proven? | HTTP bytes are decoded as UTF-8 exactly once. The literal is never mojibake-repaired or replacement-decoded. The one-record proof must preserve `Eugenio Suárez` through source decoding, Turtle/RDF parsing, SPARQL result serialization, and any serving row used in the proof. |
| PEOPLE-CQ-10 | Does a person response establish batting side, pitching hand, primary position, current team, or uniform number? | No. Those fields lack a complete accepted world-side target or historical institutional pattern and remain absent from executable RDF. |
| PEOPLE-CQ-11 | Can the source module be disconnected independently? | Yes. Its endpoint inputs, mapping, SHACL, staging, quarantine, promotion, provenance, and graph namespace are module-owned. Game-event participation remains in `mlb-game`; integration occurs only in the authoritative triple store. |
| PEOPLE-CQ-12 | What survives deletion of successful raw JSON? | Request metadata, response hash, mapping version, validation report, promoted graph hash, promotion result, and graph provenance persist. Failed inputs remain quarantined for retry. |

## Required pre-mapping input checks after approval

- Before RML, validate every present selected person ID, ISO date, and height
  string. A height must match the reviewed grammar and compute to total inches
  greater than zero. A malformed present value sends the input to quarantine.
- Null and absent optional fields are allowed and follow the RML no-emission
  policy.
- This gate validates the transient source payload. It must not be replaced by
  RDF SHACL, because a value omitted by RML is not visible in the graph.

## Required source-SHACL consequences after approval

Source SHACL runs only after RML and validates emitted RDF cardinality,
datatypes, values, and prohibited edges. It cannot prove that every present
source field was emitted.

- Every emitted MLB person identifier designates exactly one Person, has one
  non-empty provider value, and uses the MLB person-ID Reference System.
- Every emitted Proper Name or Nickname designates the record Person and has
  exactly one uncorrupted text value.
- Every emitted Height Measurement ICE measures one Height inhering in that
  Person, has exactly one strictly positive decimal value, and uses CCO Inch.
- A valid birth record has one Birth Process participating the Person and one
  response-part Calendar Date Identifier designating a Day.
- The source graph contains no measurement process, mass/weight measurement,
  Birth-to-Day temporal edge, laterality classification, position
  classification, team affiliation, or uniform-number assignment from these
  fields.
- The Unicode fixture must compare the exact scalar sequence
  `Eugenio Suárez`; `Eugenio Su�rez`, `Eugenio SuÃ¡rez`, and replacement
  characters fail validation/test promotion.

Cross-source identity and query equivalence remain SPARQL regression checks,
not constraints imposed by people-source SHACL on another module's graph.
