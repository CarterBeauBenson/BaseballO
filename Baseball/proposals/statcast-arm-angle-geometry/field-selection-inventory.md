# Field selection inventory

| Field or evidence | Accepted classification | Draft treatment |
| --- | --- | --- |
| `arm_angle` | genuinely additional | Retain for this review; block mapping until shoulder/ball points, reference line, release scope, and degree semantics are accepted. |
| game/pitch/pitcher identifiers | already supplied or identity/join-only | Join to canonical MLB-game entities; no duplicate Person or Pitch facts. |
| release position fields | unresolved duplicates of MLB-game trajectory data | Exclude from this mapping pending their own equivalence/geometry review. |
| `release_speed`, velocity, acceleration components | unresolved or already supplied | Exclude; they do not substitute for arm-angle geometry. |
| provider shoulder landmark metadata | required evidence, not currently complete | Block anatomical point identity until documented. |
| release evaluation/method era | required provenance | Persist version and evaluation semantics; do not encode only in an IRI. |
| null/untracked value | missingness | Emit no Angle Quality or measurement and preserve the coverage reason when supplied. |

No new IRI is proposed. A future source-specific mapping may use only
independently identified generic Fiat Points/Lines or a separately accepted
specialized class; it may not mint an `arm_angle` ICE class as a shortcut.
