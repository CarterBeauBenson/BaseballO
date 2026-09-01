# MLB venues source-specific graph contract

Status: **accepted by the ontologist on 2026-08-29**

This package proposes the exact RDF shape for the detachable `mlb-venues`
reference-source lane. It follows the accepted ownership decision in which the
venue lane owns venue reference and physical-field facts while the `mlb-game`
lane continues to own games and game-event facts. The authoritative triple
store is the only integration boundary.

The proposed first executable surface is deliberately narrow:

- the canonical MLB Venue identity and Proper Name;
- the Baseball Game Hosting Function borne by a Baseball Venue;
- the Baseball Field Site described by the endpoint, without inventing a
  direct Venue-to-Field relation;
- the five non-null field-dimension values as measurements of realist Distance
  Qualities between two Fiat Points; and
- the provider selector that designates each selected field-boundary Fiat
  Point.

The ontologist has already established that baseball stadium dimensions are
in feet. Every admitted dimension measurement therefore directly uses CCO
`Foot Measurement Unit` (`cco:ont00001714`). A JSON number is not a Distance
Quality: it is the decimal value borne by a Measurement Information Content
Entity that measures a Distance Quality in reality.

## Decisions requested in this review

Approval of this named package would accept all of the following as one
source-specific contract:

1. MLB venue `id` keys the persistent Baseball Venue, its stable venue-ID
   identifier, its Baseball Game Hosting Function, and its canonical Baseball
   Field Site. A Proper Name ICE is keyed by the canonical Venue IRI, the
   reviewed MLB official-name kind, and the SHA-256 of the exact decoded
   lexical name; an unchanged name is reused across nightly responses.
2. The field-dimension origin is the Fiat Point selected at the intersection
   of the first-base and third-base lines at home base.
3. Each of `leftLine`, `leftCenter`, `center`, `rightCenter`, and `rightLine`
   identifies a provider-selected Fiat Point on the field boundary. The shape
   does **not** claim that every selected point is on a fence or wall.
4. A Distance Quality inheres in the origin and the selected boundary point.
   A generic Measurement Information Content Entity measures that quality,
   carries the source number as `xsd:decimal`, and uses CCO Foot.
5. The requested `season` is response-snapshot context recorded in evidence
   and identity. It is not an assertion that a dimension held throughout a
   Baseball Season or any inferred validity interval.
6. The endpoint supplies no Measurement Process, method, or measuring agent,
   so none is minted.
7. Missing or null selectors emit no selector-specific point, quality, or
   measurement. A present nonnumeric or nonpositive dimension fails
   pre-mapping input validation and goes to quarantine before RML. Source
   SHACL separately enforces the positive decimal and cardinality contract on
   RDF that RML emits.
8. Coordinates, azimuth, elevation, capacity, turf, roof, time-zone, address,
   phone, and provider-status fields remain blocked.

The identity and null policies are specified in
[`source-specific-mermaid.md`](source-specific-mermaid.md). The governance
schema still calls its Mermaid artifact bucket `sourceIndependentMermaid`;
this package uses that historical bucket for the required pre-RML
source-specific diagram.

## Detachable runtime boundary

Implementation belongs entirely under
`Baseball/sources/mlb-venues/`: source contract, pre-mapping input validation,
RML, source SHACL, fixtures, and its own NiFi process groups. API JSON remains
transient. NiFi records the request URI, requested season, retrieval time,
response SHA-256, mapping version, validation report, and promoted graph pair.
Raw bytes are removed only after successful promotion and retained only in
quarantine after failure.

The lane will be submitted asynchronously. A healthy NiFi run is not polled or
watched continuously. Existing promoted MLB-game RDF is not deleted; any
future reference-assertion cutover requires population of this graph and
equivalence checks first.

This proposal declares no new ontology class or property. It does not itself
authorize RML, SHACL, NiFi changes, RDF promotion, SQL materialization, or UI
exposure.
