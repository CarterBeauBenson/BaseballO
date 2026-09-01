# Statcast non-duplicate semantic extension

Status: **accepted by the ontologist on 2026-08-29; ontology implementation only**

This package applies BaseballO's source-extension gate to the documented
Baseball Savant Statcast Search CSV surface. It does not authorize ontology,
RML, SHACL, SPARQL, serving, UI, source-module, or NiFi changes.

The inventory covers 113 unique documented field semantics. The official page
repeats `pitcher` and `fielder_2`; those headings are counted once. It also
labels the z-velocity field `vy0` a second time even though its definition says
z-dimension; this proposal records that semantic field as `vz0` and preserves
the documentation defect as evidence.

The strict selection result is:

- 38 fields already supplied directly by the MLB games feed;
- 41 fields deterministically derivable from MLB games or
  other retained analytical facts;
- 16 unresolved overlaps, meanings, or insufficiently specified derivatives that must not be treated as additional until
  record-level equivalence is proved;
- 7 deprecated fields that are excluded;
- 1 non-unique join-only identifier that is excluded from semantic mapping;
- 10 genuinely additional Statcast candidates.

The 10 additional candidates are:

- `estimated_ba_using_speedangle`;
- `estimated_woba_using_speedangle`;
- `if_fielding_alignment`;
- `of_fielding_alignment`;
- `delta_run_exp`;
- `home_win_exp`;
- `arm_angle`;
- `attack_angle`;
- `attack_direction`;
- `swing_path_tilt`.

The two signed intercept fields are nonduplicative but remain in the
`unresolved` bucket because their subtraction names conflict with distance
prose and the official axis/sign convention is not established.

None is implementation-ready. The diagrams keep actual qualities,
configurations, process profiles, game states, generic CCO model calculations,
measurement ICEs, classification ICEs, and source records distinct. Only three
Only `BaseballBatSweetSpotFiatPoint` is proposed. Generic CCO classes cover
records, measurements, classifications, estimates, algorithms, calculations,
and reference systems.

The sweet-spot Process Profile remains an ontology gap. BFO defines Process
Profile intensionally, but the pinned vocabulary does not connect the proposed
profile to the profiled Swing, the Fiat Point, and the point's changing
Location. `occurrent part of Swing Act` alone cannot distinguish that profile
from other Process Profiles, so no class or candidate axiom is proposed. No
new object property is invented to make the OWL look stronger than it is.

No class is proposed for the provider's defensive-alignment fields. A set of
fielder Persons plus a Baseball Field Site and interval does not yet represent
the relative player Sites and spatial relations that constitute an alignment.
The two fields remain genuinely additional evidence but are blocked from
mapping until that world-side configuration is modeled.

## Dependency on geometry review

The active `realist-geometry-foundations` proposal already owns the proposed
IRIs `AngleQuality` and `DistanceQuality`. This package does not duplicate
them. Acceptance of the relevant geometry is a prerequisite for angle and
nonnegative-distance mappings. Signed intercept components remain blocked:
they must not be asserted as ordinary Distance Qualities.

## Dependency on direct ICE values, units, and reference systems

The diagrams place literal values, measurement units, and reference systems on
Information Content Entities, as required by the project owner. The pinned CCO
snapshot currently places those properties on Information Bearing Entity. The
separate `ice-direct-values-and-units` proposal must therefore be accepted and
implemented first; otherwise the proposed edges would infer an ICE to be an
IBE. A material carrier may still carry the content, but it is not the detour
through which values or units are attached.

## Barrel and `launch_speed_angle`

The full `launch_speed_angle` field is classified as unresolved because the
official evidence does not provide complete decision rules for all six values.
It is excluded from Statcast ingestion. The Barrel subset remains analytically
valuable: a versioned Act of Data Transformation can derive a generic Nominal
Measurement ICE after authoritative MLB launch measurements are present and
after the Barrel rule and boundary behavior are reviewed.

The value `6` / Barrel is not a new physical process or a special kind of
Baseball. It is provider-defined nominal information classifying an actual
`BattedBallMotionProcess` under a batted-ball physical-profile reference
system. The official Barrel definition uses comparable outcomes and expanding
launch-angle windows beginning at 98 mph. The full six-zone rule set is not
completely specified on the CSV documentation page, so only the Barrel rule
may be implemented after its version and boundary behavior are reviewed; the
remaining five categories stay unresolved until equally authoritative rules
are captured.

## Hard stops

RML must not be written until the ontologist explicitly accepts a named review
decision and that decision is archived in a prior commit. In particular:

- no angle value may be attached directly to a Swing Act, Pitch Act, ball, or
  bat as a literal;
- no model score may be asserted as a physical quality;
- no probability may be mapped until its possible-process target and
  conditioning context are accepted;
- no alignment token may be turned into a world class;
- no sweet-spot Process Profile may be proposed until accepted relations state
  the profiled Process and the dependent pattern of location change;
- no defensive-configuration class may be proposed until the player Sites,
  spatial relations, field reference, and temporal identity are modeled;
- no signed intercept component may be mapped as a Distance Quality;
- no proposal IRI in this directory may enter executable artifacts.

## Package contents

- `competency-questions.md`: questions that the design must answer;
- `source-evidence.md`: official and repository evidence plus uncertainties;
- `field-selection-inventory.md`: one disposition for every documented field;
- `source-independent-mermaid.md`: world-first review diagrams;
- `proposed-ontology.ttl`: the remaining defensible review-only class using
  BFO/CCO/BaseballO relations only;
- `review.json`: draft governance envelope with no ontologist decision.
