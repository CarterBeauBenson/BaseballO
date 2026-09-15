# B1 source evidence and field selection

The owning source is the existing `mlb-game` module. No additional API or
provider is proposed. Raw checked-in bytes remain unchanged.

| Field / existing graph path | Selection | Use and limit |
| --- | --- | --- |
| `gamePk`, revision, final status | Identity/join-only; already supplied | Bind all proofs to one immutable source revision and promoted graph. |
| `allPlays` + `playsByInning` | Already supplied | Independent unfiltered membership; existing E1 reconciliation remains required. |
| `about.atBatIndex`, `matchup.batter.id` | Identity/join-only | Join existing PA/Batter Act/Role/bearer. Final matchup cannot overwrite earlier batting. |
| Existing adjudicated result Process, Judgment and Decision | Already mapped | Identify recognized completed batting outcomes; retain unknowns. |
| Player and team `stats.batting.plateAppearances` | Already supplied; no duplicate mapping | Independently verify RDF-derived counts, including zero totals. Does not create per-event official-credit identity. |
| Offensive substitution events, indexes, pitch/count context | Already supplied | Verify uninterrupted batter attribution. Before-turn replacement differs from replacement during the turn. Unknown boundaries block admission. |
| Boxscore player roster, team IDs | Already supplied and mapped | Existing game realization of team-context Player Roles includes players without a PA. |
| Home/Away Team Role + game realization | Already mapped | Validate each roster team's game context, without institutional parthood or inferred continuity. |
| Selected-game/schedule coverage | Existing upstream evidence; verification required | A loaded subset does not automatically represent every selected game. |

## Positive observation

The [retained proof](../../benchmarks/metrics/batting-participation-2026-09-15/README.md)
checks game 824315: 77 graph observations, 20 batting players, all player
boxscore counts equal, team totals 41 and 36. The two offensive substitutions
are at event index zero and 0–0 counts. This is evidence to test B1, not an
admission certificate. Its RDF comes from the previously passed M1/M2 proof.

## Counterexample to unrestricted participation counting

In game 822693, Harry Ford (695670) has five matchup records and four official
PAs. At index 49, Daylen Lile is caught stealing for the third out while Ford's
count is 2–0. Both `type=atBat` and `about.isComplete=true` are present. The
existing broad PA and Batter Act preserve participation, not an extra official
PA. The source hash and exact indexes are retained in the proof above.

An inning-ending baserunning out can leave no statistical PA for the batter.
See [MLB's PA definition](https://www.mlb.com/glossary/standard-stats/plate-appearance).
Rule 9.15(b) separately addresses original/replacement batter credit after a
two-strike substitution. See [MLB's published rulebook](https://content.mlb.com/documents/2/2/4/305750224/2019_Official_Baseball_Rules_FINAL_.pdf).
B1 withholds that substitution case rather than treating the final matchup
as the universally credited batter.

## Required focused proof

After acceptance: the positive game, the interrupted-turn counterexample,
synthetic two-strike replacement, mismatching player totals with matching team
totals, a missed game, team change, doubleheader and missing selected game.
All source-conformance decisions belong in the source-owned SHACL profile;
supporting code may construct parameterized shapes and verify serialization,
but cannot replace semantic conformance with a second imperative graph review.
Only after source/graph proof may NiFi release qualification into scoring,
exact SQL summaries, the live API and the top-five dashboard.
