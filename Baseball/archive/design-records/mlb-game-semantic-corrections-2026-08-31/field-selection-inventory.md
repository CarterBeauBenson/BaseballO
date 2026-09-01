# Accepted field consequences

| Evidence | Accepted consequence |
| --- | --- |
| pitch-code `buntAttemptStatus` | Bunt Act gate; takes priority over broad `swingStatus`. |
| in-play `bunt_grounder`, `bunt_popup`, `bunt_line_drive` | Bunt Act evidence independent of sacrifice result. |
| PA structure and `about.isComplete` | Separate existence from completed-result eligibility. |
| terminal baseball event plus final/game-over state | Candidate game endpoint. |
| runner `movement.end` | Institutional runner state only. |
| `wild_pitch`, `passed_ball` | Institutional event and scorer adjudication; no automatic physical failure. |
| `reviewDetails.isOverturned` | Original Decision existence with unresolved content. |
| Statcast `outs_when_up`, `on_1b/2b/3b` | Multi-source PA-start evidence after independent promotion only. |
| attack angle/direction | Local sweet-spot direction geometry at contact or reviewed crossing. |
| arm angle | Shoulder-to-ball line plus shoulder-ground-parallel line at release. |
| plate/zone fields | Era-qualified: through 2025 versus 2026+ semantics. |
| projected distance | Projection/Estimate ICE, not actual traveled distance. |
| launch speed/angle | Provider-reported value with tracked/estimated status only when evidenced. |
| `hc_x`, `hc_y` | Block world geometry pending reference-system evidence. |

