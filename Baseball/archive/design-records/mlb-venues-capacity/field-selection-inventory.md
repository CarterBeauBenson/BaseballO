# Field inventory and proposed terms

| Field or entity | Disposition | Consequence |
| --- | --- | --- |
| `fieldInfo.capacity` | authoritative duplicate; admitted after ownership cutover | Positive integer becomes a response-versioned measurement of the Venue's Spectator Accommodation Amount. |
| venue `id` | identity/join-only | Reuse the canonical Baseball Venue as bearer. |
| installed seats | world-side basis | Particular seats need not be enumerated by this source. |
| standing-room accommodation | world-side basis | The source total may include designed standing-room Sites without identifying each place. |
| response hash/time | evidence version | Version the measurement; do not create a validity interval. |
| null/absent value | resolved absence | Emit nothing. |
| present non-integer or nonpositive value | invalid input | Quarantine before RML. |

## Proposed class accounts

- **Spectator Seat**
  - IRI: `https://baseballontology.org/SpectatorSeat`
  - Named parent: Material Artifact (`cco:ont00000995`).
  - Definition: A Material Artifact that is a continuant part of a Baseball
    Venue and bears a Sitting Artifact Function for a spectator.
  - Necessary axioms: continuant part of some Baseball Venue; bearer of some
    Sitting Artifact Function.

- **Sitting Artifact Function**
  - IRI: `https://baseballontology.org/SittingArtifactFunction`
  - Named parent: Structural Support Artifact Function (`cco:ont00001200`).
  - Definition: A Structural Support Artifact Function that inheres in a
    Spectator Seat and is realized in a Process in which the Seat physically
    supports a seated Person.
  - Necessary axioms: inheres in some Spectator Seat; has realization some
    Process that has participant some Person.

- **Standing-Room Spectator Site**
  - IRI: `https://baseballontology.org/StandingRoomSpectatorSite`
  - Named parent: Site (`obo:BFO_0000029`).
  - Definition: A Site that is a continuant part of a Baseball Venue and is
    configured for standing spectators during events at that Venue.
  - Necessary axioms: continuant part of some Baseball Venue; is site of some
    Process that has participant some Person.

- **Spectator Accommodation Amount**
  - IRI: `https://baseballontology.org/SpectatorAccommodationAmount`
  - Named parent: Amount (`cco:ont00000768`).
  - Definition: An Amount that inheres in a Baseball Venue in virtue of the
    total spectator accommodation supplied by its Spectator Seats and designed
    Standing-Room Spectator Sites.
  - Necessary axioms: inheres in some Baseball Venue that has continuant part
    some union of Spectator Seat and Standing-Room Spectator Site.

No new object property is proposed. The RML measures the Amount without
inventing particular seats, standing places, or use Processes absent from the
source.
