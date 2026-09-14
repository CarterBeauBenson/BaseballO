# Metric dashboard naming review

The dashboard names should say what is counted or compared. A short label and
a precise subtitle work better than an ontology term or an unexplained acronym.
Names must not imply runs produced, scoring probability, success, or defensive
skill when the calculation does not estimate those things.

These are editorial recommendations for dashboard labels. They do not rename
ontology terms, change metric IDs or formulas, or resolve missing evidence.
The existing names remain searchable aliases if these labels are adopted.

## Primary recommendation

Replace **Trajectory Fulfillment Score** with **Plate Appearance Contribution**.

Suggested explanation: "Credit for advancing the batter and other runners,
minus the cost of outs and lost scoring opportunity."

"Trajectory" suggests a physical path or tracked ball flight. "Fulfillment"
does not explain the signed score, the cost of outs, or opportunity erosion.
The calculation measures normalized attributed progress and loss. It is not
expected runs, a probability of scoring, or the fraction of a physical route
traveled. The internal ID `tfs` can remain unchanged.

"Plate Appearance Impact" is a shorter alternative, but "contribution" is more
explicit about attributing the result to the batter. "Offensive Contribution
Score" is broader and could be confused with independent baserunning.

## Whole-suite recommendations

| Current name | Recommended dashboard label | Essential explanation |
| --- | --- | --- |
| Trajectory Fulfillment Score | Plate Appearance Contribution | Attributed progress minus direct loss and lost opportunity; signed and normalized. |
| Plate Appearance Quality | Plate Appearance Quality | Keep the established name; show its season percentile and explain its dependence on the contribution score. |
| Opportunity-Adjusted PAQ | Situation-Adjusted PAQ | Compare within the same immediate base/out situation; not the PA-start situation after an intervening event. |
| Offensive Reach | Offensive Reach | Keep for now. Explain that it counts distinct runner histories advanced, not bases gained or movement events. "Runners Advanced" is attractive but must not silently replace trajectory count with person count. |
| Hidden Help Rate | Help Without Advancing | Among PAs with no batter progress, the share advancing another runner. No inference about whether the batter reached base. |
| Rally Kill Rate | Runner Out Rate | Among PAs starting with runners aboard, the share directly putting an existing runner out. It does not establish that a rally was underway or ended. |
| Rally Kill Severity | Runner Loss per PA | Weighted direct loss of existing runners per PA starting with runners aboard, including PAs without such a loss. It is not severity conditional on a runner being put out. |
| Opportunity Erosion | Scoring Opportunity Lost | Remaining opportunity removed by attributed outs. This is the accepted opportunity measure, not an estimated scoring probability. |
| Empty Game Rate | Empty Game Rate | Keep; define an eligible game and the absence of qualifying positive contribution. It does not mean hitless or scoreless. |
| Empty Game Damage | Empty Game Damage | Keep; explain the negative contributions counted during an eligible Empty Game. |
| Contribution Path Diversity | Contribution Mix | Balance across advancing oneself through batting, helping other runners through batting, and independent running. The entropy is not a simple count of contribution types. |
| Recovery Quality | Two-Strike Extension Rank | Percentile of nonterminal pitches after reaching two strikes. It does not measure whether the batter recovered to get a hit or reach base. |
| Defensive Resolution Depth | Longest Defensive Sequence | Length of the longest supported sequence of intentional defensive acts, not all defensive acts added together. |
| Defender Breadth | Defenders Involved | Distinct supported defensive agents, not fielding positions or credited touches. |
| Run Construction Depth | Scoring History Length | Count of state-changing episodes in one complete scoring history. Episodes are not necessarily separate pitches or PAs; held-base observations add nothing. |
| Run Construction Breadth | Run Contributors | Distinct offensive contributors to that run, including the runner when supported. |
| Adjudication Volatility | Replay Overturn Rate | Overturns divided by explicitly resolved mapped replay reviews. It does not measure variation over time or the accuracy of all calls. |
| Review Dependence Rate | Outcomes Changed by Review | Review-dependent outcomes over all eligible decisions, including unreviewed ones. Show the review mechanism separately. |
| Role Realization Breadth | Roles Played | Count Batter, Baserunner, Pitcher and Fielder roles actually realized in that game; not defensive positions or roster eligibility. |
| PAQ with Process Tie-Breakers | PAQ with Tie-Breakers | Contribution first, then two-strike extension and defensive sequence length, within the accepted applicable population. |

## Presentation details

- Show the returned result's actual scope next to its value: an individual
  award play, a complete scoring history, or a stated review population.
- Keep familiar metric names where they are useful. Removing terminology is
  not a reason to replace every label or invent another set of acronyms.
- For weighted contribution and loss, explain the normalization in the formula
  disclosure. Do not relabel those units as runs, bases, or probability points.
- Replace technical "breadth" and "depth" labels with the counted thing when
  that preserves the precise count. Keep the technical alias in detailed docs.
- Distinguish an implemented formula from a result supported by current data.

The name review is separate from the remaining operational work. Renaming a
metric cannot supply complete histories, attribution, or eligible populations.
