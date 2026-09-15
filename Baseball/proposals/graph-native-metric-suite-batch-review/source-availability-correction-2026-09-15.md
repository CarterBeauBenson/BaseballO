# Correction: absent source evidence versus unfinished implementation

The user challenged the blanket claim that missing source evidence prevents
the player metrics. The challenge is supported by a fresh inspection of the
checked-in source. The assistant retracts that blanket explanation. An absent
graph assertion, incomplete live adapter, or failed materialization does not
establish that the provider lacks the underlying evidence.

This is an engineering audit, not an ontology decision or source admission.

## Concrete counterexamples in the existing MLB feed

Inspected unchanged source:
`data/raw/samples/2026-08-23/824315.json`, SHA-256
`5fcc75d37a20a516d312b3bfb3d5cefb4371ebafa639851ff16173d9b1a6607c`.

| Input previously described too broadly as missing | Evidence actually present | Correct characterization |
| --- | --- | --- |
| Official PA totals | `liveData.boxscore.teams.{away,home}.players.*.stats.batting.plateAppearances`; team totals are 41 and 36. Jo Adell's player total is 5. | PA counts are present. Mapping, joins, qualification exposure and complete player aggregation remain work; these totals do not by themselves settle every substitution's action attribution. |
| Pitch/count sequence | 413 play events, including 360 pitches. All 413 have balls, strikes and outs, plus start/end timestamps. PA 35 has eight pitches and an explicitly non-pitch batter timeout. | Source fields exist. Exact state interpretation, event reconciliation and graph-to-metric implementation must be completed. Source fields being present is not the same as their RDF coverage being implemented. |
| Runner states and outcomes | PA 34 and PA 35 both explicitly name runner 800050 in `matchup.postOnThird`. Movement rows include start/end/out base, runner identity, out number, scoring flag and event index. | Boundary reconstruction and accepted complete-history handling are implementation/coverage questions. The source is not simply devoid of runner state evidence. |
| Defensive players and order | PA 43 describes a double play from Ezequiel Tovar to Ryan Ritter to Connor Norby. Its two runner records separately retain assist/putout credits and identify the second and third outs. | Usable defender and sequence evidence exists. It is not yet established that these descriptions and credit records enumerate every intentional act for every play. Do not turn that narrower uncertainty into a claim that defensive evidence is absent. |
| Reviews and challenge state | `gameData.review`, `gameData.absChallenges`, PA 12 `reviewDetails`, and pitch-level `reviewDetails` at PA 36/event 5 and PA 43/event 0. The latter include outcome, team and player data. | Evidence exists. Challenge initiator, affected player, operative decision and eligible never-reviewed decisions require distinct interpretation and implementation. A named player in a review record is not automatically the affected player. |

The proof is deliberately bounded to this source revision. It establishes
presence, not complete season coverage or uniform availability in every game.

## What the web sources actually support

[Statcast CSV documentation](https://baseballsavant.mlb.com/csv-docs) explicitly
documents pre-pitch counts, occupied-base runner IDs, outs and first-fielder
location. The difference between pre-pitch CSV counts and the MLB event fields
must be respected; it does not establish that exact counts are unavailable.

[Retrosheet's event specification](https://www.retrosheet.org/eventfile.htm)
contains ordered fielding and runner-advance evidence, including double plays.
Its deflection example also shows why every adjacent pair of fielders cannot
automatically be translated into an intentional throw and catch. This supports
case-specific interpretation, not blanket rejection of defensive evidence.

## Revised blocker accounting

1. **Confirmed engineering debt:** the serving backend still does not produce
   complete `playerResults`. UI code and arithmetic kernels do not finish those
   adapters. That is our implementation responsibility.
2. **Present source fields, incomplete graph/metric use:** PA counts, pitch and
   non-pitch event counts/times, runner observations and multiple review inputs.
   Any protected mapping or genuinely new semantic work must be identified
   precisely; the freeze is not evidence that MLB lacks the fields.
3. **Unverified source sufficiency:** a complete inventory of intentional
   defensive acts, and all inputs needed for every review-eligibility exception
   across the selected corpus. No universal absence has been demonstrated.
4. **Coverage verification:** source reconciliation, authoritative promotion
   and complete period/season membership still need to succeed. Incomplete
   verification must be reported as such, not renamed missing provider data.

No metric is marked available by this audit. It changes the diagnosis and the
burden of proof: identify the exact unsupported assertion and inspected source
before calling something a source-evidence gap.

The subsequent [mapping completion review](../../archive/design-records/mlb-game-metric-mapping-completion/README.md)
specifies M1 (second-strike foul coverage) and M2 (affirmed pitch reviews),
with exact source observations, field inventory, world-side/source-specific
diagrams and proposed conformance conditions. M1/M2 were accepted on September 15;
implementation follows the separately published decision.
