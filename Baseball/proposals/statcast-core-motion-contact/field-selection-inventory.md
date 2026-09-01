# Field selection and de-duplication inventory

## Complete-inventory dependency

The accepted inventory at
`Baseball/archive/design-records/statcast-nonduplicate/field-selection-inventory.md`
accounts for all 113 distinct field semantics in the current official CSV
documentation. A transient check on 2026-08-30 found 115 documentation cards:
113 semantics plus repeated provider headings for pitcher, catcher, and one
velocity component. No new field was found.

This package does not reopen the accepted classifications. It selects the
motion/contact fields needed for the first source-independent Mermaid review.

| Field or family | Accepted classification | Consequence for this review |
| --- | --- | --- |
| `game_pk`, batter, pitcher, pitch and plate-appearance keys | already supplied or identity/join-only | Resolve canonical MLB-game entities transiently; emit no competing Games, Persons, Plate Appearances, or Processes. |
| `pitch_type`, event descriptions, counts and outcomes | already supplied or deterministically derivable | Exclude from Statcast RML. |
| `release_speed` | unresolved duplicate of MLB-game `startSpeed` | Use only to review the generic Speed Process Profile shape; mapping remains blocked pending evaluation and corpus equivalence. |
| `release_pos_x`, `release_pos_y`, `release_pos_z` | unresolved overlap with MLB trajectory evidence | Block until point, origin, axes, release plane, era, and equivalence are reviewed. |
| `vx0`, `vy0`, `vz0`, `ax`, `ay`, `az` | already supplied by MLB-game | Exclude; they may inform later MLB-owned Velocity/Acceleration coverage. |
| `pfx_x`, `pfx_z`, `plate_x`, `plate_z`, `spin_axis` | unresolved overlaps | Block pending unit, sign, axis, origin, and equivalence evidence. Preserve Savant's front-of-plate evaluation through 2025 and middle-of-plate/ABS evaluation from 2026; never project that boundary onto MLB Games fields by name similarity. |
| `effective_speed` | unresolved provider-derived value | Do not model as observed Speed; requires a separate Algorithm/Estimate review. |
| `release_spin`, `release_extension`, zone and strike-zone bounds | already supplied by MLB-game | Exclude from Statcast RML. Preserve as source evidence that Savant `sz_top`/`sz_bot` are operator-set through 2025 and ABS-defined from 2026; do not transfer those semantics to the MLB Games fields. |
| `hit_distance`, `launch_speed`, `launch_angle`, batted-ball type and coordinates | already supplied by MLB-game | Exclude; reuse the canonical Batted-Ball Motion Process after promotion. |
| `arm_angle` | genuinely additional | Retain as release-time Angle Quality between the shoulder-to-ball Fiat Line and a ground-parallel Fiat Line through their shared shoulder Fiat Point. |
| `attack_angle` | genuinely additional | Retain as local vertical sweet-spot direction geometry at contact or the documented bat/ball path crossing. |
| `attack_direction` | genuinely additional | Retain as local horizontal sweet-spot direction relative to a translated Fiat Line through the evaluation point parallel to home-to-center-field direction. |
| `swing_path_tilt` | genuinely additional | Retain for review, but block mapping until the fitted final-40-ms world-side target is identified. |
| signed intercept X/Y components | unresolved | Block; the provider calls them distances while the names imply signed subtraction, and the points/frame/sign semantics remain incomplete. |
| expected batting/wOBA, run/win expectancy | genuinely additional analytical outputs | Outside this physical foundation; keep in separate analytical-model reviews. |
| infield/outfield alignment | genuinely additional provider classifications | Outside this physical foundation; keep in the defensive-configuration review. |
| null, untracked, estimated, not applicable | missingness/method evidence | Do not mint placeholder world entities or zero measurements; preserve the evidenced reason in provenance. |

## Candidate identity policy after later approval

| Entity | Candidate identity policy |
| --- | --- |
| Game, Plate Appearance, Pitch Act, Swing Act, contact and ball-motion Processes | Reuse canonical MLB-game world identities after independent graph promotion and an explicit join. |
| Baseball and Baseball Bat | Reuse the accepted event-scoped identities when established by MLB-game; do not assert cross-event artifact persistence. |
| Process Profile | Key by the profiled Motion plus a reviewed world-side evaluation scope; never by source column alone. |
| Fiat Point and Fiat Line | Key by the particular bearer/geometry, selection Reference System, and supported temporal scope. |
| Angle Quality | Key by its two particular Fiat Lines and their shared Fiat Point at the reviewed scope. |
| Measurement ICE | Key by measured entity, output kind, source response, method/version, evaluation scope, and payload hash. |
| Source record ICE | Content-versioned Statcast evidence distinct from every world entity it describes. |
