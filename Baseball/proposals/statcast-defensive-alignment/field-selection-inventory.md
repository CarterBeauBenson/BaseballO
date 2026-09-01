# Field selection inventory

| Field or evidence | Accepted classification | Draft treatment |
| --- | --- | --- |
| `if_fielding_alignment` | genuinely additional | Retain as a nominal classification candidate; block until infield Sites, Stasis interval, and category scheme are accepted. |
| `of_fielding_alignment` | genuinely additional | Retain separately; block until outfield Sites, Stasis interval, and category scheme are accepted. |
| `fielder_2` through `fielder_9` | deterministically derivable from MLB-game lineup/substitution history | Exclude from Statcast after equivalence validation. |
| game/pitch/team/player IDs | already supplied or identity/join-only | Resolve canonical entities; emit no duplicate identities or names. |
| player coordinate/Site evidence | genuinely required but not present in the two category tokens | Block actual configuration identity unless another reviewed tracking field/source supplies it. |
| official category values/rules/version | genuinely required Reference System evidence; incomplete | Do not create an unversioned scheme or infer rules from labels. |
| pitch-relative evaluation window | required temporal evidence; unresolved | Do not encode scope only in classification IRI. |
| null/untracked value | missingness | Emit no nominal measurement and retain reason when available. |

No ontology IRI is proposed. If the source cannot supply actual player-Site
structure, the provider classification may remain information-layer evidence
without a complete world-side target and may not be promoted as a conformance-
ready nominal measurement.
