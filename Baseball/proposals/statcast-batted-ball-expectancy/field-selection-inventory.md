# Field selection inventory

| Field or evidence | Accepted classification | Draft treatment |
| --- | --- | --- |
| `estimated_ba_using_speedangle` | genuinely additional | Retain for review; block mapping until the possible Process target and model version are accepted. |
| `estimated_woba_using_speedangle` | genuinely additional | Retain for review; block until the expected-value target, outcome distribution, and season weights are modeled. |
| `launch_speed`, `launch_angle` | already supplied by MLB-game | Exclude from Statcast; they may support later post-promotion explanation queries. |
| batter, pitcher, game, pitch, PA identifiers | already supplied or join-only | Use only to resolve canonical identities; emit no duplicate names or event structure. |
| actual `events` / outcome | already supplied by MLB-game | Exclude; do not use the actual outcome as the possible target. |
| sprint speed/model inclusion flag | model input evidence; not exposed completely here | Do not infer from year alone beyond versioned provider documentation. |
| model version, training/comparable population | genuinely required provenance; incomplete | Block timeless Algorithm identity and preserve any later version evidence. |
| per-outcome xwOBA probabilities and seasonal weights | required explanatory input; not present in these scalar fields | Record as a blocker; do not fabricate a distribution. |
| null/untracked value | missingness | Emit no estimate and retain missingness reason when available. |

No new ontology IRI is proposed. Model-output ICE identity must include the
canonical event join, output kind, method/version, and source response hash;
the world event keeps its MLB identity.
