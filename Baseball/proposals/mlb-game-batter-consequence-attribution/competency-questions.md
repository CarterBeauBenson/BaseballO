# Attribution questions for ontologist review

A1's structural contact-play addition was accepted as part of the user's
explicit approval of the targeted fix; its bounded implementation contract is
[archived separately](../../archive/design-records/mlb-game-batted-runner-resolution-containment/competency-questions.md).
The unresolved decisions below remain review candidates. A2 and the safe
destination portion of A4 now have an accepted [concrete three-relation candidate](../../archive/design-records/mlb-game-resolution-award-links/resolution-links-review.md).
The metric roadmap's six questions are retained. The
[accepted origin relation](../../archive/design-records/mlb-game-baserunning-origin/baserunning-origin-review.md) is an accepted bounded A3 slice;
[metric boundary decisions](metric-boundary-contract.md) record the accepted
defaults, error/FC exclusion and inning-ending erosion clarification.

| ID / competency question | Current limit | Decision needed |
| --- | --- | --- |
| CQ1: Which runner resolutions are consequences of the batter-linked result? | Common PA and source-event association do not prove it. | **A1 structural addition accepted:** supported resolution parthood in the particular Batted-Ball Play Process. Still specify which parts qualify for analytical contribution and how error-related secondary advances are treated. |
| CQ2: Which runner resolutions occur independently during the PA? | Steal and wild-pitch evidence can be identified, but non-contact and mixed-event cases lack a general attribution contract. | **A2:** Define the world-side relation for walk/HBP/interference awards and their consequences. Decide whether the metric means causal responsibility, institutional consequence of the batter's result, or a specifically defined contribution policy. Do not assert the batter caused HBP merely to give credit. |
| CQ3: What base/state did each relevant participant occupy immediately before the attributed consequence? | PA-start state becomes stale after independent events. Existing baserunner stasis is limited to PA start. | **A3:** Select the institutional state and temporal-boundary pattern, including prior independent events, pinch runners and simultaneous events. Identify the affected bearer and the exact before boundary. |
| CQ4: Was the terminal state safe at a base, scored, out, or unchanged? | Safe destination link is missing; absence is insufficient for unchanged. Physical location and institutional entitlement are distinct. | **A4:** Select an explicit resolution-to-institutional-state pattern with Base/Base Site grounding where appropriate. Specify how terminal states and continuous multi-row consequences are identified. Do not substitute physical Base Touching. |
| CQ5: How many outs were created by the attributed consequence? | PA-result classification, runner resolutions and adjudication can describe related facts. | **A5:** Identify distinct operative counted outs, avoid duplicate counting, exclude independent outs, and specify required completeness. Use the pre-consequence out count, with no invented order for simultaneous events. |
| CQ6: Which offensive participants remained active afterward? | Safe, unrecorded, scored and left on base are different cases. | **A6:** Define alive-after and completeness at the consequence boundary, including inning-ending outs and walk-offs. Decide whether stranded runners incur erosion when the third out ends the inning; do not both destroy and erode the same trajectory without a reviewed rule. |

## Cross-cutting adjudication requirement

For A4-A6, specify the explicit path from a review's operative decision to the
particular resolution it determines. A PA-level review does not identify every
affected runner. Preserve original and operative decisions; do not synthesize
an inverse original decision from an overturn flag. A final payload may be
insufficient to reconstruct the originally announced destination.

## Evidence and proof cases required after review

| Case | Evidence status / required distinction |
| --- | --- |
| Bases-empty double; double scoring runner from second; bases-loaded HR | Ordinary destination/count fixtures still needed for all listed contexts. The original fixture provides a double example, not all contexts. |
| Ordinary out; K with third occupied and one out; sacrifice fly | Distinct batter destruction, counted run and erosion; no outcome-label shortcut. |
| Groundout advancing second to third; FC; GIDP | Test partial advancement, distinct outs and surviving batter. Match the specified start-out count. |
| Steal then partial advance on a hit | 824315 / PA 12 and PA 64 each contain a steal first to second followed by a single advancing that same runner second to third. Exact evidence and hash are in the origin review. |
| Balk, wild pitch, passed ball, pickoff, caught stealing, defensive indifference | Independent advances must not generate batter progress; independent outs must not enter attributed out count. Some fixture coverage remains to be located. |
| Wild pitch and strikeout at the same event index | Observed in 822693 / PA 36. Resolve simultaneity before computing erosion. |
| Uncaught third strike with null placeholder and safe resolution | Observed in 823826 / PA 78. Null must not become an out; broad strikeout labels do not establish credit. |
| Walk and HBP forcing other runners; interference | Forced walk observed in 822693 / PA 6; forced HBP observed in 823016 / PA 39. Compare balk then walk in 566279 / PA 12. Interference remains outside the proposed award link. |
| Reached on error; secondary error advance; sacrifice bunt | Distinguish contribution policy from contact-play parthood. |
| Multiple runner rows; pinch runner; unchanged runner | Prove consequence continuity and bearer identity; missing rows are not absence evidence. |
| Confirmed/overturned review; unknown result; incomplete mapping | Prove operative decisions and unknown propagation. |
| Inning-ending runner out; two-out state; walk-off | Define eligibility and alive-after without pretending the inning continues. |

These are design requirements, not passing tests. Once accepted, graph
constraints belong in the owning MLB-game SHACL profile. Analytical expected
values belong in versioned SPARQL regressions, followed by SQL equivalence.
