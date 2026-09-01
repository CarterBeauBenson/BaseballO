# Source evidence

## Provider endpoints

The source is the MLB Stats API transactions endpoint, requested with explicit
date bounds:

`https://statsapi.mlb.com/api/v1/transactions?startDate={MM/DD/YYYY}&endDate={MM/DD/YYYY}`

The provider's transaction-type code list is a separate required input:

`https://statsapi.mlb.com/api/v1/transactionTypes`

The code-list response must be captured, hashed, and bound to the transformation
manifest before RML may run. This package does not guess the Death code. The
code-list snapshot used by a run must supply the exact reviewed code/description
pair.

## Pre-mapping input and code-list gate

NiFi must run source validation against the transient response and pinned code
list before invoking RML. A row is not admitted to the mapper unless:

- required provider identifiers have the reviewed non-empty integer lexical
  form, and every optional identifier that is present has that form;
- required `date` and `effectiveDate`, plus `resolutionDate` when present, are
  valid calendar values in the reviewed `YYYY-MM-DD` lexical form;
- `typeCode` is non-empty and occurs in the pinned transaction-type code list;
  and
- `typeDesc` exactly matches the description paired with that code in the same
  pinned list.

A failure produces source-validation evidence and sends the input to this
lane's quarantine/retry path before any RDF is generated. RML receives only the
validated projection and its bound code-list identity.

After transformation, source-owned SHACL validates the emitted RDF types,
cardinalities, datatypes, and relations. SHACL does not inspect the raw JSON and
cannot be used to infer whether RML silently omitted a conditionally selected
source value. The required one-record fixture and source-to-RDF mapping
regression prove that completeness before lane activation.

No response JSON belongs in this proposal. Runtime responses remain transient;
their request parameters, retrieval time, byte hash, code-list hash, mapping
version, validation report, and promoted graph identifiers remain persistent.

## Observed response surface

Observed transaction rows expose:

- `id`;
- optional `person` with `id`, `fullName`, and `link`;
- optional `fromTeam` and `toTeam` with `id`, `name`, and `link`;
- `date` and `effectiveDate`;
- optional `resolutionDate`;
- `typeCode` and `typeDesc`; and
- optional `description`.

The top-level `copyright` string is provider response metadata, not a baseball
domain assertion.

## Identity and collision evidence

A transient audit of the date-bounded 2026-07-01 through 2026-08-28 response
observed 14,397 rows. Ninety-one provider `id` values appeared in more than one
row. Three `(id, person.id)` pairs also appeared more than once. Consequently:

- `id` is suitable for the provider's grouping grain, not the row grain;
- `(id, person.id)` is not a safe row key; and
- an array index would make identity depend on response ordering.

The proposed row identity is therefore the lowercase hexadecimal SHA-256 of an
RFC 8785 canonical JSON object containing exactly these selected semantic
members:

`id`, `personId`, `fromTeamId`, `toTeamId`, `date`, `effectiveDate`,
`resolutionDate`, `typeCode`, `typeDesc`, and `description`.

Absent optional members are represented as JSON `null` in that canonical
identity object; an absent value is not collapsed with an empty string. Source
strings retain their decoded Unicode code points and are not ASCII-folded,
trimmed, or case-normalized. Request dates, retrieval timestamps, pagination,
and array positions are excluded, so unchanged semantic content is stable
across acquisitions. A provider correction produces a new row version rather
than destructively changing the old record.

## Semantic evidence limits

The endpoint product name and `typeDesc` labels cover heterogeneous events,
including trades, assignments, signings, releases, status changes, number
changes, suspensions, retirement, and death. They do not establish one honest
world-side genus.

The accepted source-independent proposal permits precise world-side classes
only when source-specific evidence satisfies their structure. This package has
only one such narrow rule:

- the current code-list snapshot proves an exact Death-code match;
- `person.id` resolves to a canonical Person; and
- the row may then be about one CCO Death that has that Person as participant.

The three source date fields still do not identify the Death boundary. The
transactions endpoint supplies no reviewed basis here for choosing a process
start, end, or temporal region.

Trade remains blocked even though `BaseballPersonnelTradeAct` is accepted.
`fromTeam` and `toTeam` do not identify the career- or tenure-persistent
team-scoped Player Roles, their stint intervals, or the supported Gain/Loss of
Role parts. Number Change remains blocked because the number occurs only in
unstructured prose rather than a structured identifier field. All other types
remain information-layer records and classifications.
