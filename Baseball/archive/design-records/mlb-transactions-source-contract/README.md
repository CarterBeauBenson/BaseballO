# MLB transactions source-specific contract

Status: **accepted by the ontologist on 2026-08-29**

This package proposes the source-specific RDF shape for a detachable MLB Stats
API transactions lane. It applies the already accepted generic transaction
record pattern without proposing ontology vocabulary. The normal output is an
information-layer graph: a stable provider grouping record, content-versioned
row records, identifiers, classifications, descriptions, dates, and links to
canonical Persons and Baseball Teams.

The provider collection is heterogeneous and does not license a generic
transaction act. An exact, independently captured MLB transaction-type code
list is a mandatory acquisition and pre-RML input. Only a row whose `typeCode`
exactly matches the reviewed Death code and whose `person.id` is non-null may
support a CCO Death instance. Every other type remains at the information
layer in this release.

`BaseballPersonnelTradeAct` and `UniformNumberAssignmentAct` are accepted
classes, but this source-specific contract deliberately does not instantiate
them. A Trade row does not yet identify the career- or tenure-persistent
team-scoped Player Roles and stint boundaries needed to assert the role
changes. A Number Change row supplies the number only in prose, not as a
structured identifier value.

The proposed identity contract is:

- one stable grouping Descriptive Information Content Entity per provider
  transaction `id`;
- one row/leg Descriptive Information Content Entity per SHA-256 digest of its
  canonical semantic content;
- no array position in any identity;
- canonical source-neutral Person and Baseball Team IRIs for joins; and
- content-derived child IRIs for the row classification, description, and
  calendar-date identifiers.

The lane will own its eventual acquisition, pre-mapping input/code-list
validation, RML, RDF SHACL validation, promotion, retry, quarantine, and
provenance artifacts under
`Baseball/sources/mlb-transactions/`. API JSON remains transient. This review
package creates no source module, RML, SHACL, NiFi process group, graph
namespace, or RDF.

Validation has two explicit stages. Before RML, the input gate inspects the
transient source values and pinned code list, rejecting malformed required
identifiers or dates, unknown `typeCode` values, and `typeCode`/`typeDesc`
mismatches. After RML, source-owned SHACL validates the emitted RDF contract.
SHACL does not inspect the discarded source structure and is not used as a
substitute for pre-mapping validation or source-to-RDF mapping regression.

The accepted package answers four decisions:

1. Is the provider `id` correctly treated as the identity of an information
   grouping rather than a world-side act?
2. Is the canonical-content hash the correct row/leg identity policy?
3. Is the narrow Death gate sufficient while all other world-side mappings
   remain blocked?
4. Do the information-layer shapes retain the useful source content without
   asserting unsupported role changes or process boundaries?
