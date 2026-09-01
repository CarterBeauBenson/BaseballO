# Source evidence

Checked-in immutable evidence:

- `sources/mlb-game/schema/mlb-feed-rml-source-schema.yaml`
- `sources/mlb-game/schema/mlb-feed-live-observed.schema.json`
- `data/raw/game-566279.json`
- `sources/mlb-game/mapping/mapping-coverage.yaml`
- `sources/mlb-game/SEMANTIC-AUDIT.md`

The observed fixture contains 282 pitch-data records and 60 hit-data records.
Speed, extension, plate time, strike-zone, coordinate, vector, break, and most
spin values are populated on every observed pitch; spin rate is occasionally
absent. Launch angle, launch speed, and projected distance are absent on some
hit records. Corpus presence establishes field occurrence only—not units,
reference frame, evaluation scope, observation method, or realist identity.

The current audit explicitly defers all measurements and freezes extension of
the RML pending ontologist-approved world-side patterns.

The accepted 2026-08-31 decision further requires source-specific evaluation
semantics. Savant documents a pre-2026/2026+ plate and strike-zone boundary,
but that definition is not evidence that MLB Games `pX`, `pZ`,
`strikeZoneTop`, or `strikeZoneBottom` denote the same evaluations. Those
Games fields therefore remain unresolved pending feed-specific evidence.
Projected distance remains projection evidence, and tracked-versus-estimated
launch status is asserted only when row-level evidence supports it.

MLB's public Savant CSV documentation describes `hc_x` and `hc_y` only as hit
coordinate X and Y. It does not state an origin, axes, orientation, scale,
physical unit, terrestrial CRS, or transform to field geometry. No equivalent
authoritative definition was found for MLB Games `coordX` and `coordY`.
Accordingly, checked occurrence and value ranges support only a provider-frame
display-coordinate interpretation. They do not support feet, latitude/
longitude, or physical Distance Qualities. A field polygon may be queried with
Jena only after the polygon and coordinates are explicitly represented in the
same provider frame.

Source: <https://baseballsavant.mlb.com/csv-docs>

The feed's `details.type.code` and `details.type.description` occur on all 282
observed pitch events in the checked fixture. Their reuse across events supports
a reusable provider classification rather than an identifier unique to one
pitch. The ontologist has directed that labels such as `Slider` be modeled as
reusable Nominal Measurement ICEs. The focused class proposal applies those
pitch classifications to Pitch Acts. It separately proposes batted-ball
trajectory classifications for Batted-Ball Motion Processes, not Swing or
Bunt Acts.

The ontologist rejected use of CCO Spatial Region and its Coordinate System
Axis subclasses for BaseballO coordinates. The revised candidate therefore
uses world-side Fiat Lines meeting at an origin Fiat Point, an Angle Quality
for the axes' perpendicularity, Distance Qualities for component magnitudes,
and provider/reference ICEs about that geometry.
`BaseballFieldCoordinateReferenceSystemICE` now inherits from the generic CCO
Reference System and describes the reviewed Fiat Line, Fiat Point, and Angle
Quality frame. This repairs the ontology dependency but does not supply the
provider origin, orientation, sign, scale, projection, polygon, or literal
contract required for executable coordinates.

Consequently, provider-frame containment remains information-space evidence.
It does not license a `designates` assertion to a Batted-Ball Location Site or
minting that world-side Site. Those steps remain blocked until the provider
frame is grounded to the Baseball Field.

MLB describes the traditional rulebook zone as a three-dimensional space over
Home Plate, bounded vertically relative to the batter. For the 2026 ABS
challenge system, MLB instead evaluates a two-dimensional rectangle at the
midpoint of Home Plate, 8.5 inches from either edge. These are distinct
world-side structures and method eras. That public distinction does not by
itself prove which structure the similarly named MLB Games feed values measure
on a particular pitch.

Sources:

- <https://www.mlb.com/glossary/rules/strike-zone>
- <https://www.mlb.com/interactive/mlb-abs-system-explainer>
