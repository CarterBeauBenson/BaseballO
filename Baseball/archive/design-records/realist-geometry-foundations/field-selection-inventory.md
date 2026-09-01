# Geometry selection inventory

| Candidate | Disposition | Reason |
| --- | --- | --- |
| `AngleQuality` | genuinely additional ontology class | BFO supplies Relational Quality and Fiat Lines but no general class with the required angle differentia. |
| `DistanceQuality` | genuinely additional ontology class | BFO supplies Relational Quality and Fiat Points but no class matching the ontologist's distance account. |
| New angle relation | rejected | `inheres in` and `has continuant part` express the reviewed necessary structure; the shared-point constraint remains in the definition and review pattern. |
| New distance relation | rejected | `inheres in` already relates the quality to each Fiat Point. |
| Angle Measurement ICE | already supplied | Reuse CCO Measurement Information Content Entity or an accepted measurement subclass; the ICE is about Angle Quality. |
| Distance Measurement ICE | already supplied | CCO already has Distance Measurement Information Content Entity, but its current definition should be checked against the accepted two-point target during implementation. |
| Signed axis displacement | unresolved | A signed component relative to a Coordinate System Axis is not identical to nonnegative distance; no honest existing-property account has yet been established. |
| Provider-specific angle class | rejected | Arm, attack, and swing fields must first identify their lines, points, bearers, and time. |
| Provider-specific distance class | rejected | Venue and intercept columns do not define the world category. |

## Proposed IRIs

- `https://baseballontology.org/AngleQuality`
- `https://baseballontology.org/DistanceQuality`
