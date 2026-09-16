# C1 history coverage and independent event scopes

Implementation of accepted E1/C1 and B2, not a new approval record. Final-feed
authority, personal lifetime identity, episode grain and metric meanings stay intact.

| Owning source field | Selection | Use and boundary |
| --- | --- | --- |
| PA `about.startTime/endTime` | Already supplied | Overlap remains a PA-start admission issue; it does not replace independently ordered movement bounds. |
| Event times, `playId`, movement `playIndex` | Already supplied; identity/join-only where applicable | Verify event extents across PAs, unique membership, entry and termination. No exact runner timestamp or RDF precedence is added. |
| Review details, narrative, terminal in-play event | Already supplied | Completed tag/first-base effects with consistent explicit disposition. Original-call and affected-player questions remain separate. |
| Defensive-indifference and pickoff-error records | Already supplied; mapping coverage debt | Account for existing movements; no new class, stolen-base typing or batter credit. |
| On-field-delay advisory and counts/effect flags | Already supplied | Only explicitly unchanged, movement-free and review-free delays are neutral. |
| Independent prefix followed by contact continuation | Deterministically derivable after source/C1 reconciliation | Only terminal contact-result/`other_out` resolutions join B2. Earlier independent episodes stay outside contact membership. |
| Histories and PA-start admission | Separate derived validation products | Ordered personal history does not certify a PA-start boundary or selected population. |

`personal_runner_histories` retains header overlaps in `boundaryIssues`.
`runner-boundary-admission.py` turns each into an explicit withholding reason.
Its generated SHACL continues checking every admitted existing start stasis,
out count, personal membership and award. C1 independently rejects actual event
overlap across PAs. RML manifests retain both histories and unresolved bounds.

`accounted_runner_history_reviews` keeps final operative effects separate from
count-review admission. Unknown mechanisms, incomplete reviews, contradictory
dispositions and unresolved independent event reviews still withhold the half.
The helper emits no new review RDF and selects no original call or reviewed player.

B2's source SHACL reconciles exact contact membership and personal membership
separately. A preceding steal belongs to the personal history but is rejected
as an extra member of the later contact. PA identity alone cannot merge them.

The [real-game proof and source comparison](../../../benchmarks/metrics/runner-history-coverage-2026-09-16/README.md)
record 70 complete PA calculations, five complete scoring histories, exact SQL
checks and remaining gaps. They do not admit the live date or reference season.
No raw bytes or archived decisions changed.
