# Field selection and remaining mapping work

All paths below are in the existing `mlb-game` feed. None warrants a new
provider lane merely because current RML omits it. "Already supplied" means
the authoritative source provides the field; it does not mean the graph maps
it completely. Read this with the source-hashed evidence, not as a season-wide
coverage claim.

| Exact field or product | Selection | Graph coverage and disposition |
| --- | --- | --- |
| `gamePk`, `metaData.timeStamp` | Identity/join-only | Existing game/revision provenance; reuse it. |
| `about.atBatIndex`, `about.inning`, `about.halfInning` | Identity/join-only | Existing PA/half identities; no ordinal-to-BFO-precedence shortcut. |
| `playEvents[].playId`, `.index`, `.isPitch` | Identity/join-only | Existing pitch ID plus source reconciliation; absent non-pitch playId does not erase the record. M1/M2 reuse the existing pitch identity. |
| `playEvents[].details.call.code`, `.isBall`, `.isStrike` | Already supplied | Existing pitch classifications. M1 adds supported second-strike fouls; M2 gates affirming called-pitch reviews. |
| `playEvents[].count.strikes`, `.count.balls` | Already supplied | Source-local counters presently lack a general graph count-state contract. M1 consumes them as reconciled mapping gates; it does not create count ICEs. Non-pitch awards and exact recovery prefixes remain separate. |
| `playEvents[].count.outs` | Already supplied | This can differ from completed-PA outs. Never reuse the PA-start-out-count ICE for this distinct scope. |
| `allPlays[].count.outs` | Already supplied | Already used to construct later PA-start context. Actual consequence boundaries require admitted distinct outcomes and complete runner reconciliation. |
| `playEvents[].startTime`, `.endTime` | Already supplied | Existing pitch temporal mapping. Non-pitch records also have times; these do not automatically give exact runner-act or review-act extents. |
| `matchup.batter.id`, `.pitcher.id` | Identity/join-only | Existing persons and batting/pitching relations. Mid-turn substitutions require actual event attribution, not retrospective replacement by final matchup. |
| `boxscore.teams.{away,home}.players.*.stats.batting.plateAppearances` | Already supplied | Official player PA totals exist. Reconcile as source evidence; no accepted new graph pattern yet expresses each official statistical assignment when it differs from actual agency. Do not count generic Batter Acts as official attribution without reconciliation. |
| `boxscore.teams.{away,home}.teamStats.batting.plateAppearances` | Already supplied | Independent team total for membership reconciliation; not a replacement for player attribution. |
| `matchup.postOnFirst`, `.postOnSecond`, `.postOnThird` | Already supplied | Positive base observations. Accepted C1/C2 cover reconciled continuity and bounded analytical projection. Absence is not automatically an empty-base assertion. |
| `runners[].movement.originBase`, `.start`, `.end`, `.outBase`, `.outNumber`, `.isOut` | Already supplied | Existing institutional movement/origin/out/safe mappings. Exact within-PA boundaries and out identity reconciliation need complete source-to-graph support. Event index is not a runner-act timestamp. |
| `runners[].details.runner.id`, `.playIndex`, `.isScoringEvent`, `.eventType` | Already supplied / identity-join for IDs | Existing runner identity, outcome and event anchor. Full consequences must preserve independent versus batting contributions under accepted policies. |
| `runners[].credits[].player.id`, `.credit`, `.position` | Already supplied | Current role trigger is not a complete Fielder Act mapping. Credit identifies statistical participation; classify intentional acts only with sufficient particular-act evidence. |
| `result.description` | Already supplied | PA 43 supplies an ordered named defensive sequence. Parse supported narrative evidence alongside credits. A field/throw/catch/tag act census and its completeness criterion still need an exact reviewed contract; blanket absence is disproved. |
| `allPlays[].reviewDetails`, `about.hasReview` | Already supplied | Existing PA-narrative review pattern. Preserve its distinct out/safe cases; reconcile duplicate pitch-review narratives under M2. |
| `playEvents[].reviewDetails.inProgress`, `.isOverturned`, `details.hasReview` | Already supplied | M2 maps completed explicit affirmations at their actual pitch. Other dispositions remain governed by their existing or future reviewed contracts. |
| `playEvents[].reviewDetails.player.id`, `.challengeTeamId`, `.reviewType` | Already supplied | Challenger evidence and routing tokens are not affected-player identity. M2 makes no undocumented mechanism-code inference. |
| `gameData.review`, `gameData.absChallenges` | Already supplied | Final challenge inventory; historical per-decision eligibility requires reconstruction and corroboration, including applicable exceptions. Not itself a denominator census. |
| Official qualified PA totals and player summaries | Deterministically derivable after reconciliation | Existing metric policy and aggregation choice stay settled. No direct source-to-SQL shortcut. |
| Full runner lifetime and unchanged boundary projection | Deterministically derivable after prerequisites | C1/C2 already accepted and partly implemented; no new physical Site or Stasis decision requested here. |
| Every intentional defensive act and agent | Unresolved sufficiency / interpretation | Evidence exists. Repeated physical actions must not be invented from a single assist/putout or a position code. No new act identity is admitted by M1/M2. |
| Complete eligible, never-reviewed decision population | Unresolved coverage / interpretation | Reviewed outcomes alone do not enumerate this population. Do not mark the full Review Dependence metric ready after M2. |

## Specific modeling boundaries that remain

1. **Official PA credit:** the official player total is supported; the exact
   world-side pattern for the scoring assignment across substitutions is not
   specified by the accepted actual-agent pattern. A generic measurement ICE
   about a player and game would hide that unresolved relation. A Count
   Measurement ICE requires its counted aggregate; it cannot be asserted to
   measure two separate entities through a functional measurement relation.
2. **General count states and non-pitch awards:** mapping ordinary counted
   pitch outcomes does not model the full reset/correction/automatic-award
   history. No new count-state class, field-shaped ICE or invented Pitch Act
   is proposed here.
3. **Within-PA runner timing and termination:** source event linkage and a
   runner's physical act extent differ. Preserve the accepted C1 whole and C2
   analytical state projection; do not assign a source event's timestamps to
   every associated motion or make a Stasis realize a Role.
4. **Defensive action identities:** require a particular intentional act,
   actual agent, act kind and supported temporal relationship for every
   counted contribution. The next evidence proof should use the named PA 43
   sequence and distinguish what each sentence/credit actually supports.
5. **Review eligibility and mechanism:** explicit reviews can be mapped before
   a complete never-reviewed population is proven. Separate the mechanisms
   when their meaning is supported; do not treat final remaining challenges
   as historical eligibility or infer the affected batter from a catcher ID.

These are not five requests to reconsider metric formulas. They identify
the precise graph/source contracts still needed beyond the two ready changes.
