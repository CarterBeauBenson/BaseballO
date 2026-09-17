# Shared dashboard blockers: September 16

The published SQL build `20260916T214621Z-70f29a436fd8` serves HTTP 200 and
contains 2,732 games and 207,021 PAs. This fixes SQL availability, not player
ranking completeness. On the August 25 selection, the one available scoped
review aggregate is **not** a populated player leaderboard. All 19 player
leaderboards were empty in this diagnostic.

## Repairs

- The movement query now consumes the existing, particular runner-record
  Passed Ball/Wild Pitch process, judgment and decision pattern. Previously
  it recognized independent steals only. Same-PA association alone cannot
  supply the classification. Conflicting batting/running channels stay withheld.
- Existing runners receive their supported independent contribution; the
  batter receives no positive credit from it. A scored runner's actual end
  still removes remaining erosion. The accepted strikeout example remains
  exactly -1/4. A batter's HOME-to-first uncaught-third-strike entry is outside
  the accepted existing-runner advance weights and remains unresolved.
- A1's contact selector now includes the already recognized
  `fielders_choice_out` classification. It retains the exact terminal contact
  and same-classification runner tests.
- The accepted intentional-walk award selector now recognizes the complete
  four-`VB` virtual-ball representation: four nonpitch events, counts 1 through
  4, no strikes, unchanged outs, plus all existing award/runner checks. This
  does not create four actual ball judgments or count four pitches.
- Run Contributors no longer requires positive contact causation merely to
  apply the accepted zero-positive-credit policy to an error/FC batter's own
  entry. Other runners still require their own contribution evidence.
- The existing NiFi source recovery component accepts an idempotent queued
  date-range refresh. It preserves active work, archives completed plans,
  reruns the normal current full proof and uses the existing backfill and SQL
  stages. This allows the complete season reference to follow the selected-day
  repair without Codex repeatedly dispatching jobs.

These changes implement existing accepted decisions. No object property,
ontology term, identity policy, source lane or metric formula was added.
Only the existing context implementation pin changed in the unratified
runtime manifest; the named accepted award decision remains the authority.

## Focused evidence

Both unchanged final feeds were transformed through current RML and passed
the authoritative Jena source SHACL gate. Jena then evaluated the canonical
metric query; SQLite retained the calculated results exactly.

| Game | Complete progress PA inputs before these selectors | After | Remaining PAs |
| --- | ---: | ---: | --- |
| 823585 | 79/82 | 81/82 | 81 |
| 823826 | 86/90 | 87/90 | 49, 78, 79 |

The before column already includes the new PB/WP query, isolating the contact
and intentional-walk selector repairs. In 823826, the PB query itself closes
the independent scoring advance during PA 73: zero batting reach and one
positive runner contribution. Scoring History Length resolves all 15 runs
across these two games. Run Contributors resolves 13/15. Neither isolated
proof claims a complete selected-day or reference-season population.

[Machine-readable results](focused-results.json) retain source/RDF hashes,
exact unresolved entities, and the SQL comparison. Focused unit tests cover
wrong record, missing judgment, conflicting channel, wrong PA, excluded batter
entry, existing-runner credit, actual-end-state erosion, strict virtual-ball
selection, and queued recovery without overwriting active or failed work.

## Exact remaining dependencies

| Dependency | Concrete evidence and required work |
| --- | --- |
| Current source admissions | Only 1 of 2,732 games had the current B1/run/resolution/boundary/count proof in the published build. August 25's 15 games had stale proofs. The existing NiFi refresh, followed by the reference-season refresh, owns regeneration and publication. This is an admission-version problem, not missing MLB records. |
| Mixed error/contact attribution | 823585 PA 81 names a throwing error during a fielder's choice. The three existing-runner rows say `error`; the batter row says `fielders_choice`. A1/B2 currently admit matching contact classifications and bounded `other_out` continuations, not this extra mixed-label case. Reusing the existing parthood shape needs an explicit extension of that bounded selection contract. |
| Independent event classification | 823826 PA 49 has `pickoff_error_2b`; PA 79 has `defensive_indiff`. Their movements are present in the personal histories. The current graph does not classify these as an admitted independent contribution channel. Neither may silently become a stolen base or batting credit. |
| Wild-pitch companion movements | In 823826 PA 78, the scoring runner and runner advancing to third carry `strikeout` labels, while the batter's separate reach record carries `wild_pitch`. The existing WP process is present. Classifying the companion movements needs reconciled event-specific evidence; copying the classification across a whole PA is invalid. The batter's reach is a separate unresolved contribution case. |
| Percentile references | PAQ, adjusted PAQ, two-strike rank and PAQ with Tie-Breakers need every eligible game and independently covered calendar day from January 1 through cutoff. The selected-day refresh alone cannot admit these references. |
| Defensive populations | D1 currently proves specific intentional performances, not a complete act inventory for every contact. Its real 566279 proof contains 20 supported acts, with 13 of 107 contact plays complete. Counting assist-array positions as throws would violate the accepted D1 contract. Complete performances and order remain an evidence-reconciliation task. |
| Review players | The affected-batter pitch-review query and exact SQL retention exist. Complete review inventory, explicit mechanism, additional affected subjects and decision-time eligibility are not yet connected to the two player reducers. A scoped aggregate is not evidence that this work is finished. |

Research confirms the distinction behind the last two rows. An assist can
result from a deflection, so it does not by itself prove a throw
([MLB assist definition](https://www.mlb.com/glossary/standard-stats/assist)).
ABS eligibility includes remaining challenges and technical availability,
and excludes a position player pitching; pitch type alone is insufficient
([MLB ABS metrics documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)).
These are bounded constraints, not claims that usable defensive or review
source evidence is absent.

The first failed gate for each dependent population remains visible. This
report does not approve an extension, omit inconvenient events, or replace
unresolved values with zero.
