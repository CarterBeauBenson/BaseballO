# Field selection inventory

| Field or evidence | Accepted classification | Draft treatment |
| --- | --- | --- |
| `attack_angle` | genuinely additional | Retain for this review; block mapping until vertical tangent/reference geometry and evaluation scope are accepted. |
| `attack_direction` | genuinely additional | Retain for this review; block mapping until horizontal tangent/home-to-center geometry and evaluation scope are accepted. |
| `swing_path_tilt` | genuinely additional | Retain for review; block until the fitted final-40-ms world-side target and Algorithm are accepted. |
| game/pitch/batter identifiers | already supplied or identity/join-only | Join to canonical MLB-game entities; emit no duplicate identity/name facts. |
| Baseball Bat and Swing Act | owned by MLB-game | Reuse canonical IRIs after graph promotion; Statcast does not remap their source facts. |
| bat sweet-spot tracking identifier | genuinely required but semantics unresolved | Use only after the point-selection Reference System and identity are reviewed. |
| contact/path-intersection marker | evaluation evidence; unresolved | Distinguish contact from swing-and-miss and never invent contact. |
| launch speed/angle and batted-ball facts | already supplied by MLB-game | Exclude from this Statcast mapping. |
| final-40-ms observations/model metadata | genuinely required for `swing_path_tilt`; incomplete | Preserve method/version provenance; do not infer a plane from the output label alone. |
| null/untracked values | missingness | Emit no geometry or measurement; retain coverage reason when available. |

No new class or property is proposed. A later source-specific contract must key
world geometry independently of response order and version Measurement ICEs by
source, method, evaluation, and payload hash.
