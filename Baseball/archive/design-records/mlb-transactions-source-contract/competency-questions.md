# Competency questions

## Information-layer questions

1. Which provider transaction identifier designates each stable transaction
   grouping Descriptive Information Content Entity?
2. Which content-versioned row/leg records are continuant parts of that
   grouping?
3. Which canonical Person, optional from-Team, and optional to-Team is each row
   about, without inferring movement, agency, affiliation, or a role change?
4. Which MLB transaction type code classifies a row, and which provider
   Reference System supplies that code?
5. What exact provider description text describes a row?
6. Which Days are designated by the row's `date`, `effectiveDate`, and optional
   `resolutionDate` Calendar Date Identifiers?
7. Can repeated observations of unchanged semantic content resolve to the same
   row IRI while a corrected row resolves to a new content version?
8. Can every row be traced to the request and payload hash that supplied it
   after the raw JSON has been removed?

## Pipeline-gate question

9. Before RML receives a row, has input/code-list validation rejected malformed
   required identifiers or dates, unknown `typeCode` values, and a
   `typeCode`/`typeDesc` mismatch?

## Narrow world-side question

10. Which row supports a CCO Death involving the identified Person when, and
   only when, a pinned MLB transaction-type code-list snapshot proves an exact
   Death-code match and `person.id` is non-null?

## Negative and conformance questions

- A transaction grouping record is not a transaction act or process.
- A provider type classification does not by itself type a world-side entity.
- A repeated provider `id` does not collapse distinct participant rows.
- A repeated `(id, person.id)` pair does not collapse distinct semantic rows.
- Array order never contributes to an IRI.
- Missing `person`, `fromTeam`, `toTeam`, `resolutionDate`, or `description`
  emits no placeholder entity, empty literal, or invented `unknown` IRI.
- A from-Team or to-Team mention does not entail agency, affiliation, transfer,
  gain of role, loss of role, or temporal membership.
- `date`, `effectiveDate`, and `resolutionDate` identify source date values;
  none is asserted as a process boundary or temporal extent in this release.
- `typeDesc` is not a second transaction type and does not override `typeCode`.
- Trade rows do not instantiate `BaseballPersonnelTradeAct` until persistent
  Player Role/stint identity and the supported Gain/Loss of Role structure are
  reviewed.
- Number Change rows do not instantiate `UniformNumberAssignmentAct` until a
  structured number identifier and its bearer are supplied.
- Descriptive prose is never parsed into an unreviewed world-side assertion.
- SHACL validates the RDF emitted by RML; it is not expected to inspect raw
  source values or discover a source value that the mapping omitted.
- One-record source-to-RDF regression must prove the mapping of every selected
  required and conditionally present field before the lane is activated.
- A Death assertion is prohibited when the exact code-list evidence is absent,
  the code does not match, or the Person identifier is null.
- Disconnecting this lane does not stop MLB games or any other source lane and
  does not delete already promoted authoritative RDF.
