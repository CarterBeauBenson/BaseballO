# Metric completion decisions, September 15, 2026

Carter Beau Benson answered the nine consolidated questions below. This record
precedes implementation. Questions 1 and 3–9 were accepted; question 2 was
challenged and remains unresolved. No new object property, ontology class,
global semantic ratification, or additional source lane was requested or
authorized. Existing source-owned engineering follows the accepted decisions.

## Exact answers

1. "Yes"
2. "Not necessarily, it could have been a hit and run if the batter struck out swining."
3. "Yes. Batter interference should not prevent an empty game."
4. "Yes, separate"
5. "YEs. Balls and strikes get called on clock violations\""
6. "Yes"
7. "yes"
8. "yes"
9. "yes"

## Accepted scope

| Question | Named decision presented and accepted |
| --- | --- |
| 1 — B2 | All six supported movements in game 824315 PA 6 may belong to the existing contact play under the bounded [continuation contract](../contact-play-continuation-membership/README.md), using existing BFO parthood. Reuse existing resolutions, episodes and personal Processes. Terminal batter out supplies no positive trajectory; Offensive Reach is 2. |
| 3 — Catcher interference | No positive batter credit for advancement awarded through catcher interference. Preserve official PA eligibility and actual runner states. The award alone does not prevent an Empty Game. The question expressly concerned catcher interference; the answer's phrase "Batter interference" is retained above, without treating it as an additional approval about offensive interference. |
| 4 — Substituted batting participation | One PA may contain separate existing Batter Acts, one for each batter's uninterrupted participation, linked to that player's actual actions and persistent Batter Role. This expressly accepts the participation-act identity criterion. Official statistical PA attribution remains separate from actual agency. |
| 5 — Non-pitch awards | Existing Ball Process / Strike Process and their judgment pattern may represent evidenced automatic awards, including clock violations, without an invented Pitch Act. The existing phrase "pitch-related history" includes these awards. An operative automatic second strike establishes the two-strike count; the award itself contributes zero pitches to Recovery Quality. |
| 6 — Defensive acts | Explicit MLB descriptions reconciled with structured play evidence may establish particular Fielding Attempt, Throw, Catch Attempt and Tag Attempt Acts, actual agents and supported order. Separate performances have separate identities; repeated throws count separately; superclass typing does not count a catch twice. Complete depth requires a complete supported sequence, not assist credits alone. |
| 7 — Review eligibility | A decision is eligible when a review could legally have been initiated at that moment under that season's rules and available routes, rather than category membership alone. For ball/strike challenges count a pitch decision once if either side could legally challenge it; preserve affected-batter display attribution. Challenge inventory and operational exceptions must be evidenced. Traditional replay and ball/strike mechanisms remain separate. |
| 8 — Walk-off | Evaluate at the supported game-ending boundary, retain only officially counted advances and outs, and add no erosion merely because the game ended. Do not infer further running or completed advances for every participant. |
| 9 — Qualification | Adopt the exact selected-range observation minima below, retain the existing batting minimum where applicable, and retain minima when fewer than five players qualify. Explain that state on cards; the expanded view may show smaller samples marked unqualified. These are dashboard thresholds, not MLB standards or statistical reliability claims. |

For question 9, `G` is the player's complete applicable team-game exposure in
the selected range. Fractional observation requirements round upward.

| Metric group | Minimum observations |
| --- | --- |
| Independent running | max(3 episodes, ceil(G / 10)) |
| Defensive depth/breadth | max(3 participating resolutions, ceil(G / 10)) |
| Run construction | max(2 runs scored, ceil(G / 5)) |
| Review overturn rate | max(3 completed reviews, ceil(G / 40)), separately per mechanism |
| Traditional Review Dependence | max(3 eligible decisions, ceil(G / 2)) |
| Ball/strike Review Dependence | max(10 eligible decisions, G) |
| Recovery Quality / PAQ-2.1 | Existing batting minimum plus max(3 applicable PAs, ceil(G / 5)) |

## Question 2 was not accepted

The proposed case had runners on first and third with one out, a strikeout and
runner out at second, and third stranded. The proposal would split erosion
equally between batter and independent-running channels, giving batter TFS
−3/4. The user identified a possible called hit-and-run, particularly on a
swinging strikeout. This does not accept the equal split or establish that
either observed outcome proves an independent steal or a called hit-and-run.

Do not implement the proposed shared-out allocation. Preserve previously
accepted ordinary and no-independent-out erosion policies. A follow-up asks
who bears runner-out damage when a called hit-and-run is explicitly evidenced.
Evidence sufficiency, causal attribution and the resulting allocation remain
distinct requirements; a swing alone does not prove the called strategy.

## Implementation boundary

These answers settle the named choices, not completeness of any game or
population. Existing vocabulary and source-owned SHACL must express accepted
graph constraints. Proof must precede corpus promotion and serving exposure.
Unreviewed act identities or additional ontology vocabulary are not admitted
by these answers. No semantic freeze is globally ratified by this record.
