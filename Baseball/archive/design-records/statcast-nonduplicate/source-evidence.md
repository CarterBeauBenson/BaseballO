# Source evidence

Evidence was inspected transiently on 2026-08-28. No external payload was
added to the repository.

## Official Statcast documentation

### Baseball Savant CSV documentation

- URL: <https://baseballsavant.mlb.com/csv-docs>
- Authority: MLB Baseball Savant.
- Use: field names, field-level descriptions, units, deprecated flags,
  documented classification labels, and documented method-era changes.

Important evidence from this page:

- release velocity is PitchFX-derived and adjusted for 2008-2016, while 2017+
  values are Statcast out-of-hand values;
- `plate_x` and `plate_z` use front-of-plate through 2025 and middle-of-plate
  beginning in 2026;
- `sz_top` and `sz_bot` are operator-set through 2025 and ABS-defined beginning
  in 2026;
- some `launch_speed` and `launch_angle` values are estimates for untracked
  batted balls;
- `launch_speed_angle` defines six provider categories: Weak, Topped, Under,
  Flare/Burner, Solid Contact, and Barrel;
- attack angle, attack direction, swing path tilt, and intercept fields refer
  to bat sweet-spot or bat/ball geometry rather than merely to a source column;
- the page repeats `pitcher` and `fielder_2` headings;
- the z-velocity description is under a second `vy0` heading, an apparent
  documentation typo;
- deprecated fields are explicitly marked and are not candidates for new
  semantic coverage.

### Expected Batting Average

- URL: <https://www.mlb.com/glossary/statcast/expected-batting-average>
- Use: xBA meaning and model history.
- Evidence: xBA is a likelihood assigned from comparable batted balls. Since
  2019, seasonal sprint speed contributes for some topped or weakly hit balls.

This evidence prevents defining `estimated_ba_using_speedangle` as a timeless
two-input calculation merely because of its column name.

### Expected weighted on-base average

- URL: <https://www.mlb.com/glossary/statcast/expected-woba>
- Use: outcome distribution and season-weight semantics.
- Evidence: batted balls receive probabilities for multiple hit types, and
  the result uses wOBA-style season-adjusted outcome weights. Sprint speed is
  included for some batted-ball types beginning in 2019.

### Perceived velocity

- URL: <https://www.mlb.com/glossary/statcast/perceived-velocity>
- Use: interpretation of the CSV `effective_speed` derivative.
- Evidence: the metric normalizes actual velocity using release extension and
  an average Major League extension. It is not a second observed physical
  Speed inhering in the pitch.

### Barrel

- URL: <https://www.mlb.com/glossary/statcast/barrel>
- Use: `launch_speed_angle` value 6.
- Evidence: Barrel is a provider classification of batted-ball events based on
  exit velocity, launch angle, and comparable historical outcomes. The
  guaranteed window begins at 98 mph and expands as exit velocity increases.

The CSV page does not give the complete decision boundaries for all six
`launch_speed_angle` categories. The non-Barrel categories therefore remain
unresolved even though the underlying launch measurements are already
available from MLB games.

### Attack angle and attack direction

- URLs:
  - <https://www.mlb.com/glossary/statcast/attack-angle>
  - <https://www.mlb.com/glossary/statcast/attack-direction>
- Use: evaluation geometry and historical availability.
- Evidence: both metrics use sweet-spot motion at contact or at the point where
  bat and ball paths cross for a swing-and-miss. Bat-tracking data is described
  as available back to the 2023 All-Star break.

Pinned BFO evidence: Process Profile is defined at
`Baseball/ontology/CommonCoreOntologiesMerged.ttl:3581-3588` as an occurrent
part of a Process by virtue of a rate, pattern, or amplitude of change in an
attribute of process participants. The pinned vocabulary supplies `occurrent
part of` but no named `process profile of` object property. The proposal
therefore exposes the parthood, participating Baseball Bat, and Sweet-Spot Fiat
Point structure while leaving the intensional profile differentia for explicit
ontologist review.

## MLB games evidence used for de-duplication

- `Baseball/sources/mlb-game/schema/mlb-feed-path-inventory.csv`
- `Baseball/sources/mlb-game/mapping/mapping-coverage.yaml`
- `Baseball/sources/mlb-game/mapping/ontology-coverage-gaps.yaml`

The inventory demonstrates that the games response already supplies:

- game, team, person, handedness, inning, plate-appearance, and pitch identity;
- ordered pitch events, result descriptions, counts, runner movements,
  substitutions, and scoring state;
- pitch type, zone, start and end speed, extension, spin rate and direction,
  movement, initial position, velocity, acceleration, plate location, and
  strike-zone bounds;
- batted-ball launch speed, launch angle, projected distance, trajectory,
  fielder location code, and X/Y hit coordinates.

The current RML defers most physical measurements because the accepted
measurement vocabulary is incomplete. That is MLB-game semantic backlog. It
does not make the duplicate Statcast columns genuinely additional.

## Ontology evidence

- `Baseball/ontology/BaseballO.ttl`
- `Baseball/ontology/BaseballO-axioms-overlay.ttl`
- `Baseball/ontology/CommonCoreOntologiesMerged.ttl`
- `Baseball/ontology/ModalRelationOntology.ttl`
- `Baseball/governance/ontology-curation-debt.json`
- user-supplied angle and distance precedent:
  <https://github.com/CarterBeauBenson/ProvisionalFootballOntology-Soccer-/blob/main/FootballOntology.ttl>

Existing reusable coverage includes `PitchAct`, `PitchBallMotionProcess`,
`SwingAct`, `BatBallContactProcess`, `BattedBallMotionProcess`, `Baseball`,
`BaseballBat`, `BaseballFieldSite`, `HitProcess`, `RunProcess`, BFO Process
Profile and Relational Quality, and CCO measurement, estimate, probability,
nominal-classification, algorithm, data-transformation, coordinate-system,
center-of-mass, speed, velocity, and acceleration classes.

The active `realist-geometry-foundations` proposal owns the unaccepted
`AngleQuality` and `DistanceQuality` IRIs. They are dependencies, not accepted
vocabulary and not duplicated here.

`BaseballEventRecord` is too narrow for a generic tracking row because its
definition concerns institutionally counted baseball processes. The dangling
`BaseballInformationContentEntity` parent is frozen known debt and is not used
as a parent in this proposal.

## Unresolved evidence that blocks fields

- exact release-plane reconstruction for `release_pos_x/y/z`;
- unit, sign, and era equivalence for `pfx_x/z`, `plate_x/z`, and `spin_axis`;
- the anatomical landmark used as the pitcher's shoulder location;
- the physical/fiat identity rule for the tracked bat sweet spot;
- the fitting method used to create the swing-path plane;
- sign and origin conventions for the two intercept components;
- official value sets and decision rules for infield and outfield alignment;
- accepted player-Site and relative-location structure for an actual defensive
  configuration;
- the versioned algorithms and conditioning populations for run and win
  expectancy;
- the appropriate modal target for xBA and home win expectancy;
- complete rules for Weak, Topped, Under, Flare/Burner, and Solid Contact.

No unresolved item licenses an executable placeholder.

The absence of an accepted relation connecting a sweet-spot Process Profile to
the Swing, Fiat Point, and changing Location blocks that class. Likewise, a
fielder aggregate, field Site, and interval do not independently distinguish a
Defensive Fielding Configuration. Both former class proposals are removed
rather than leaving their differentiae only in prose.
