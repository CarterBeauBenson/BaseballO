# Remaining metric questions, September 30, 2026

Status: questions prepared; answers pending. Recommendations below are not
accepted decisions. The user's separate [narrow RML repair authorization](../../archive/design-records/metric-repair-scope-2026-09-30/README.md)
is effective now. This document changes no executable artifact or semantic pin.

The season diagnostics report overlapping failures and missing/stale checks,
not one unanswered semantic question per code. Existing decisions already
settle most meanings. Answers to these questions can close the identified
policy/scope choices; implementation and actual source evidence are still
required. This is not a claim that every recorded failure has been diagnosed.

## Questions

1. **Fetch only the source responses needed for a targeted repair?** Some
   original MLB responses were retired after successful ingestion. May NiFi
   fetch the same existing MLB endpoint only for specifically identified games
   on a repair manifest when retained inputs cannot support the repair? The
   first concrete set is K1's five games: 823327, 823489, 824301, 824302 and
   824866. Each new response keeps its own hash and is checked against the
   existing identities; only the selected affected facts enter RML. No season
   reacquisition or whole-game graph replacement. **Recommendation: yes.**
   The [K1 package](../mlb-game-strikeout-double-play/README.md) contains the
   exact PAs and proposed three-triple compound-result correction. This
   question concerns missing input acquisition, not repeat approval of ordinary
   narrow RML repairs.

2. **Use independently established game-state order when header clocks
   overlap?** MLB sometimes starts a PA's recorded clock just before the
   previous PA's recorded end. May a complete reconciliation of distinct play
   identities, runner transitions, counted outs, substitutions, operative
   review effects and boundary states establish the analytical before/after
   boundary despite that clock overlap? Require agreement of those independent
   facts; array position alone is insufficient. Preserve the clock conflict,
   invent no timestamp or strict BFO precedence, and withhold a boundary whose
   placement still has more than one supported interpretation.
   **Recommendation: yes, for calculations that do not need an exact clock.**
   Example: game 823580 has recorded PA-header overlaps of about three seconds
   and three-tenths of a second. These are candidates for diagnosis, not proof
   that the other evidence already reconciles. C1/C2 remain accepted; this
   asks specifically about evidence sufficiency in the conflicting-clock case.
   It does not authorize a new location, stasis or personal-history identity.

3. **What is sufficient confirmation of a called hit-and-run?** If a final
   MLB play description explicitly identifies a called hit-and-run, and its
   batter, runner and events reconcile with structured records, should that
   suffice to apply your existing rule assigning the failed attempt's damage
   to the batter? **Recommendation: yes.** A swinging strikeout plus caught
   stealing alone remains insufficient. With no explicit confirmation or
   independently supported independent-steal classification, responsibility
   remains unresolved; this does not default the damage to either player.
   No inspected example is claimed to contain such confirmation. The question
   settles the evidence threshold, not the already accepted responsibility
   rule, and does not create a strategy Act or infer its agent in RDF.

4. **How should two genuinely independent outs share stranded-runner
   erosion?** Assume the runner's attempted steal is independently confirmed,
   rather than a called hit-and-run. With runners on first and third and one
   out, the batter strikes out and the runner from first is caught on the
   same play, ending the inning. Each keeps the destruction cost of their own
   out. Should the third-base runner's total lost opportunity of 1 be split
   equally: 1/2 charged to the batter and 1/2 to the running channel?
   **Recommendation: yes; allocate the shared erosion in proportion to each
   channel's attributed outs, once in total.** Here that gives batter damage
   1/4 + 1/2 = 3/4 and runner damage 1/3 + 1/2 = 5/6. Scope this policy to
   independently established shared-play consequences; it does not combine
   separate sequential plays. A confirmed failed hit-and-run retains your
   existing all-to-batter decision. Your earlier objection identified exactly
   that distinction; it did not accept a split for the independent case.

Question 1 is separate because [AGENTS.md](../../../AGENTS.md) says a metrics
request "does not authorize API reacquisition". Questions 2-4 concern specific
unsettled evidence/metric assumptions. The RML approval is already recorded;
routine SHACL, SQL and NiFi repairs require no further vote.

## Coverage of every recorded blocker family

| Recorded family | Remaining decision versus authorized work |
| --- | --- |
| PA classification, substitutions and official totals | Narrow existing-pattern mapping/qualification repairs are authorized. Preserve accepted actual-actor versus official-PA separation. Q1 covers retired inputs such as K1's five responses. Do not guess conflicting totals. |
| Fouls, automatic awards, count transitions and ordering | Existing M3/M4 and automatic Ball/Strike decisions apply. Diagnose each transition, complete the selected missing pattern, and refresh count checks. Q1 applies if its needed response is retired; Q2 applies only if clock overlap is the actual dependency. No invented pitches or counts. |
| Runner boundaries, histories, substitutions, placement and review effects | C1/C2, C3, placement adjudication, T1 and Q7 already govern the accepted patterns. Q2 addresses the specific clock-overlap case. Other known mapping and projection defects are engineering; missing movements remain unknown. |
| Offensive attribution, independent running and continuous consequences | Implement accepted contact/award links and complete-history rules. Q3 supplies the proposed strategy-confirmation criterion; Q4 supplies the remaining independent shared-out allocation. Error/FC exclusions and actual-end-state erosion stay settled. |
| Scoring histories and run contributors | Complete existing personal histories and supported contributor paths. The scoring runner's own batting/running contributions already count; replacement starts another person's history. No new policy question. |
| Defensive acts, participants and order | D1 and the four-act policy are accepted. Expand coverage of supported descriptions within accepted identities, extract separately established order, and isolate affected players. Scoring credits alone do not establish every act. Diagnose unrepresented source cases before declaring evidence unavailable; approval cannot manufacture an unrecorded performance. |
| Review outcomes and eligible populations | Implement accepted affected-player attribution, final operative outcomes, decision-time eligibility, challenge availability and separate mechanisms. Review occurrence alone cannot supply the denominator. The two unfinished player producers are engineering work, not another policy vote. |
| Percentiles | The full accepted season reference, exact arithmetic and display-only rounding are settled. Repair their upstream inputs and rebuild affected derived references. Do not substitute an observed subset to fill the cards. |
| Stale checks, overly broad exclusions, memory and SQL | Repair proof refresh/consumption, scoped player exclusions, resource scheduling and prepared SQL through their current NiFi owners. A stale fingerprint alone does not justify RDF regeneration. No new validation framework or user approval is needed. |

## Decisions not reopened

Full selected-range player records and participation minimums remain required;
an unresolved observation cannot silently disappear from a player's average.
Empty Games remains a count. Known inapplicability stays distinct from unknown
evidence. The backend-only role metric does not become a public card. No metric
is renamed, relaxed or reported complete merely because a narrow repair passes.

The supporting decisions include [September 15](../../archive/design-records/metric-completion-decisions-2026-09-15/user-decision.md),
the [hit-and-run follow-up](../../archive/design-records/metric-completion-decisions-2026-09-15/followup-user-decision.md),
[D1](../../archive/design-records/mlb-game-defensive-acts/README.md),
the [C1/C2 source contract](../../sources/mlb-game/review/runner-continuity-source-contract.md),
and [complete selected-range players](../../archive/design-records/player-metric-presentation-2026-09-15/complete-player-ranges-2026-09-28.md).
