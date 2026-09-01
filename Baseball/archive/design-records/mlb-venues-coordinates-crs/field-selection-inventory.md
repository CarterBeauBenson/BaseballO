# Field inventory and proposed term

| Field or entity | Disposition | Consequence |
| --- | --- | --- |
| `defaultCoordinates.latitude`, `longitude` | authoritative duplicate; admitted after ownership cutover | Create a response-versioned coordinate ICE designating the Venue Reference Point under WGS 84. |
| venue `id` | identity/join-only | Scopes the stable reference-point identity to the canonical Venue. |
| CCO WGS 84 individual | accepted Reference System | Reuse `cco:ont00001630`; create no provider CRS class. |
| request season | provenance | Does not establish season-long positional validity. |
| response hash | evidence version | Corrections create new evidence without destructive overwrite. |
| null/absent pair | resolved absence | Emit no coordinate subgraph. |
| partial, malformed, or out-of-range pair | invalid input | Quarantine before RML. |

## Proposed class account

- **IRI:** `https://baseballontology.org/BaseballVenueReferencePoint`
- **Named parent:** Geospatial Position (`cco:ont00000373`).
- **Aristotelian definition:** A Baseball Venue Reference Point is a
  Geospatial Position that is selected as the default point designated by
  geospatial coordinate information about a Baseball Venue.
- **Necessary axioms proposed for the later overlay:** continuant part of some
  Baseball Venue; designated by some Designative Information Content Entity
  that uses World Geodetic System 1984.
- **Identity:** canonical Baseball Venue plus the default-reference-point
  selection kind; coordinate values and response versions do not define the
  point's identity.
- **Example:** the WGS-84 point MLB selects as the default coordinate for a
  ballpark.

No new object property is proposed.
