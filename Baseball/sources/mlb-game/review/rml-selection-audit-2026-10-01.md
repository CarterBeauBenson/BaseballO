# RML failure-family diagnostic: October 1, 2026

This is a diagnostic report, not a semantic decision, executable inventory or promotion admission.

Coverage: 2,404 current staging manifests; 60,405 selected histories; 2,429 regular-season SQL games.

The combined repair has 209 inventoried games and 752 missing histories. The
user accepted H3 and it was activated in `9b4d192`. The counts below describe
the pre-repair snapshot; they are not a live count of remaining failures. See
the [H3 review and execution notes](rml-selection-repair-2026-10-01.md).

Accepted patch SHA-256: `c90b77d00bf84db10de6f104ff8951ec2c963f204a8ead50d3a8a776659b89c8`.

| Recorded family | Games | Example games |
| --- | ---: | --- |
| `withheldFouls:NO_SECOND_STRIKE_INCREMENT` | 2401 | 822678 |
| `withheldReviews:NOT_EXPLICIT_COMPLETED_AFFIRMATION` | 1947 | 822678, 822679 |
| `withheldFouls:SUBSTITUTION_IN_PREFIX` | 1736 | 822678 |
| `withheldFouls:UNEXPLAINED_COUNTER_TRANSITION` | 1626 | 822678, 822679 |
| `history:UNRESOLVED_REVIEW_EFFECT` | 619 | 822679, 822683, 822685, 822688 |
| `withheldAutomaticAwards:AUTOMATIC_AWARD_KIND_NOT_ADMITTED` | 431 | 822685 |
| `withheldFouls:UNRESOLVED_PA_REVIEW` | 285 | 822688 |
| `history:UNSUPPORTED_EVENT_TIME_ORDER` | 237 | 822683, 822691, 822700 |
| `history:ZERO_EPISODE_PERSONAL_HISTORY` | 226 | 822680, 822682, 822685, 822688 |
| `history:UNSUPPORTED_EVENT_EFFECT:game_advisory` | 134 | 822679, 822686, 822699, 822703 |
| `history:UNSUPPORTED_EVENT_EFFECT:ejection` | 101 | 822681, 822731, 822777, 822801 |
| `withheldFouls:UNSUPPORTED_EVENT_TIME_ORDER` | 86 | 822690, 822718, 822720 |
| `history:UNSUPPORTED_EVENT_EFFECT:pickoff_caught_stealing_2b` | 81 | 822683, 822685, 822689, 822749 |
| `withheldReviews:CONFLICTING_OR_UNSUPPORTED_CALL` | 62 | 822700, 822737, 822741 |
| `history:UNSUPPORTED_EVENT_EFFECT:error` | 34 | 822705, 822738, 822754, 822762 |
| `history:MISSING_STABLE_MOVEMENT_ANCHOR` | 25 | 822694, 822732, 822842, 823144 |
| `history:UNSUPPORTED_THIRD_OUT_ANCHOR` | 24 | 822694, 822805, 822842, 823144 |
| `history:UNSUPPORTED_EVENT_EFFECT:forced_balk` | 22 | 822715, 822818, 822931, 822955 |
| `history:UNSUPPORTED_RUNNER_ENTRY` | 17 | 823087, 823286, 823332, 823448 |
| `withheldAutomaticAwards:UNRESOLVED_COUNT_REVIEW` | 17 | 823192, 823427, 823480 |
| `history:POST_BASE_RECONCILIATION_FAILED` | 16 | 822749, 823087, 823286, 823332 |
| `history:UNSUPPORTED_EVENT_EFFECT:umpire_substitution` | 16 | 822886, 823569, 823806, 823867 |
| `history:UNSUPPORTED_EVENT_EFFECT:other_out` | 16 | 823127, 823213, 823343, 823588 |
| `history:UNSUPPORTED_EVENT_EFFECT:pickoff_caught_stealing_3b` | 13 | 822921, 823439, 823440, 823546 |
| `history:UNSUPPORTED_C3_ADMINISTRATIVE_BOUNDARY` | 11 | 823286, 823569, 823847, 824022 |
| `history:UNSUPPORTED_EVENT_EFFECT:injury` | 10 | 822745, 822854, 822858, 822871 |
| `history:UNSUPPORTED_EVENT_EFFECT:runner_placed` | 9 | 823286, 823847, 824022, 824031 |
| `history:UNSUPPORTED_EVENT_EFFECT:pitcher_switch` | 9 | 824184, 824575, 824727, 824955 |
| `withheldAutomaticAwards:UNSUPPORTED_EVENT_TIME_ORDER` | 7 | 823226, 823666, 824125 |
| `history:UNSUPPORTED_EVENT_EFFECT:offensive_substitution` | 7 | 823286, 823569, 823847, 824022 |
| `history:UNSUPPORTED_HALF_TERMINATION` | 6 | 822805, 823847, 824031, 824125 |
| `history:UNSUPPORTED_RUNNER_EPISODE` | 6 | 823087, 823332, 823448, 823712 |
| `history:UNSUPPORTED_EVENT_EFFECT:pickoff_caught_stealing_home` | 5 | 823059, 823134, 824213, 824611 |
| `history:PRE_EVENT_OUT_COUNT_MISMATCH` | 5 | 823847, 824031, 824125, 824327 |
| `history:POST_PA_OUT_COUNT_MISMATCH` | 5 | 823847, 824031, 824125, 824327 |
| `history:DISTINCT_OUT_RECONCILIATION_FAILED` | 5 | 823847, 824031, 824125, 824327 |
| `history:CONFLICTING_BASE_OCCUPANCY` | 3 | 822749, 824125, 825049 |
| `withheldFouls:SOURCE_RECONCILIATION_FAILED` | 2 | 824295 |
| `history:UNSUPPORTED_EVENT_EFFECT:other_advance` | 1 | 822681 |
| `history:AMBIGUOUS_RUNNER_SEGMENT_CHAIN` | 1 | 822749 |
| `history:UNSUPPORTED_PA_CLOCK_PAIR` | 1 | 823631 |
| `history:POST_ACTION_OUT_COUNT_MISMATCH` | 1 | 824031 |

Counts overlap across families. Two-strike held fouls and reviews outside the affirming-review mapping are expected exclusions, not whole-game failures. Repairability and unresolved cases are explained in the [combined H3 review](rml-selection-repair-2026-10-01.md).

The following 25 games have legacy additive manifest stubs. All retain defensive source censuses; their promotion receipts lack the original history, resolution and pitch-count censuses. This does not establish that their RDF is absent.

822864, 822918, 822972, 822991, 823023, 823028, 823031, 823048, 823052, 823062, 823070, 823082, 823116, 823128, 823200, 823350, 823363, 823375, 823385, 823398, 823471, 823589, 823648, 823668, 823682.

Source-revision exclusion: game 823433. The candidate cannot align its retained sample with the current history census.
