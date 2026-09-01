# Source and domain evidence

## Official MLB API surface

The reviewed request shape is:

`GET https://statsapi.mlb.com/api/v1/venues/{venueId}?hydrate=location,timezone,fieldInfo&season={season}`

Prior transient inspections of official responses found venue identity and
name plus `fieldInfo.leftLine`, `leftCenter`, `center`, `rightCenter`, and
`rightLine`. The response also exposes fields deliberately withheld by this
contract, including location, time-zone, capacity, turf, roof, azimuth, and
elevation. No raw response JSON is retained in this proposal.

Repository evidence for the same observed response members exists in
`Baseball/sources/mlb-game/schema/mlb-feed-path-inventory.csv`. Those fields
are authoritative duplicates in the current game payload, not newly
discovered semantics. The separately accepted
`mlb-reference-source-ownership` record authorizes a coordinated ownership
migration to an independent `mlb-venues` graph; it does not authorize duplicate
RML by itself.

## Official field-geometry evidence

The official sources used to ground the conservative field shape are:

- MLB, *2026 Official Baseball Rules*, Rule 2.01:
  <https://mktg.mlbstatic.com/mlb/official-information/2026-official-baseball-rules.pdf>
- MLB Glossary, *Field Dimensions*:
  <https://www.mlb.com/glossary/rules/field-dimensions>
- MLB, *The Field*:
  <https://www.mlb.com/official-information/basics/field>

Together these sources establish the home-base/foul-line field geometry and
that outfield dimensions vary among parks. They support selecting an origin at
the home-base intersection of the first-base and third-base lines and selecting
points on the outfield boundary. They do not formally define the Stats API
member names `leftLine`, `leftCenter`, `center`, `rightCenter`, and
`rightLine`. In particular, they do not justify treating every
`leftCenter`/`rightCenter` point as a fence point or assigning an undocumented
bearing. The contract therefore stops at a provider-selected field-boundary
Fiat Point.

## Accepted unit evidence

On 2026-08-29 the ontologist established the domain fact that baseball stadium
dimension measurements are in feet. The accepted decision record is
`Baseball/archive/design-records/mlb-venue-field-dimension-foot-unit/`.
BaseballO reuses the pinned CCO Foot Measurement Unit individual
`https://www.commoncoreontologies.org/ont00001714`; no local unit is needed.

## Snapshot variation evidence

Transient season-scoped checks against the official venue endpoint for Oriole
Park showed why the request season cannot be turned into timeless venue
geometry:

| Requested season | `leftLine` | `leftCenter` | `center` | `rightCenter` | `rightLine` |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 333 | 410 | 400 | 373 | 318 |
| 2024 | 333 | 398 | 400 | 373 | 318 |
| 2025 | 333 | 376 | 410 | 373 | 318 |

These observations demonstrate response variation. They do not prove exact
change instants or that a returned value held for the whole requested season.
The future evidence manifest therefore preserves the request season and
content hash, while the semantic graph makes no season-validity assertion.

## Existing accepted vocabulary

No ontology extension is needed for the admitted surface:

| Meaning | Accepted term |
| --- | --- |
| facility | BaseballO `BaseballVenue` |
| spatial playing field | BaseballO `BaseballFieldSite` |
| designed hosting capability | BaseballO `BaseballGameHostingFunction` |
| world-side distance | BaseballO `DistanceQuality` |
| geometric relata | BFO `Fiat Point` (`BFO_0000147`) |
| source record | CCO Descriptive Information Content Entity (`cco:ont00000853`) |
| source/selector ID | CCO Non-Name Identifier (`cco:ont00000649`) |
| official venue name | CCO Proper Name (`cco:ont00001014`) |
| numeric measurement content | CCO Measurement Information Content Entity (`cco:ont00001163`) |
| provider code system | CCO Reference System (`cco:ont00000398`) |
| unit | CCO Foot Measurement Unit (`cco:ont00001714`) |

Accepted BFO/CCO relations provide continuant parthood, inherence, bearing,
designation, aboutness, measurement-of, reference-system use, measurement-unit
use, text value, and decimal value. The endpoint contains no evidence for a
Measurement Process, so the absence of one is intentional rather than an
ontology gap.
