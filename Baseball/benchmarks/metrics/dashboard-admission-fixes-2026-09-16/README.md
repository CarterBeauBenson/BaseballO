# Dashboard admission repairs, September 16

The August 25 refresh completed before this change. The live API returned all
19 public cards for its complete 15-game schedule, but **zero populated player
leaderboards**. Official plate-appearance admission covered only 9 games.
[The saved observation](dashboard-before.json) identifies the SQL build and
each metric's remaining gaps; an available review-population result is not a
player leaderboard.

## Changes and evidence

- A zero-count pinch hitter can follow an explicit pitching change or mound
  visit without becoming a mid-turn replacement. The bounded administrative
  prefix must contain no pitch, count award, out or runner movement. Player,
  team and official-PA reconciliation remain required.
- A passed-ball scoring event before a groundout can appear in `scoringPlays`
  even though the final PA header has `isScoringPlay: false`. Explicit event
  flags, scoring runner rows and inning/team totals now reconcile together.
  This does not assign the independent score to the batter.
- An all-null strikeout runner record beside an explicit safe wild-pitch or
  passed-ball reach is not a second movement. The exact companion, strike-three
  pitch and first-base post-state are required. Source-owned SHACL requires
  the existing uncaught-third-strike judgment pattern and rejects an invented
  additional Baserunning Act.

[All six affected source censuses reconcile](source-diagnostics.json).
Game **823826** also passes current RML, source SHACL, official-PA admission,
counted-run admission and runner-resolution admission. Its proof contains
39,490 triples, 90 PAs, 365 pitches and 52 player roles. The 129 source runner
records support 128 actual runner movements. See the
[RML manifest](rml-proof-manifest.json) and
[Jena-to-SQL result](qualification-result.json): all 90 official PAs and all 52
rostered players survive the canonical graph query and SQL retention exactly.

The one-game participation check deliberately has no public date-range schedule
admission. It does not certify a complete selected population, scoring-history
population, season reference, or any live player leaderboard. The other five
new game graphs are NiFi's responsibility, not claimed by this developer proof.

## Focused checks

From `Baseball/sources/mlb-game/tests`:

```powershell
python -B -m unittest test_batting_admission test_metric_source_reconciliation
python -B -m unittest test_metric_source_recovery test_reconciled_runner_histories test_runner_history_effects
python -B -m unittest test_runner_record_admission
```

These passed 23, 58 and 2 tests respectively. From `Baseball/tests`,
`python -B -m unittest test_batting_progress_players` passed another 14:
**97 focused tests passed**. The NiFi provisioner parses successfully and its
persisted periodic-check setting is enabled. The real-game proof used the
existing `run-rml.ps1 -DeveloperEvidenceRoot ... -ShaclEngine jena` route,
the three source-owned admission CLIs, the canonical metric evidence query
through Jena, and exact SQL round-trip comparison.

The only protected context-builder change updates the source reconciler's
dependency hash under the already accepted C1 operation decision. No ontology,
RML mapping, approval record, class or object property changed. The semantic
freeze remains unratified.

## Asynchronous refresh and provenance

The user-directed **15-minute pending-work check is RUNNING again**. The daily
05:00 Eastern acquisition schedule is unchanged. A completed recovery request
is now archived byte-for-byte under its content hash before another request
can be queued; pending, failed and unknown requests cannot be overwritten.

The [new recovery submission](recovery-submission.json) asks NiFi to refresh
August 25 using these corrections. Its recorded phase is `waiting-serving`,
not completed. NiFi owns validation, the 15-game refresh, promotion and serving
publication. The prior completed request remains in its audit history.

Diagnostic raw inputs were not added to the repository or used to rewrite the
checked-in corpus. Their acquisition manifests and hashes are retained in
`source-diagnostics.json`. Four exact payload hashes already have successful
graph-pair promotion evidence, permitting removal of those diagnostic copies.
The two differing payloads (823505 and 825042) are retained for retry until a
matching graph-pair promotion is established; equal game IDs alone do not
authorize raw deletion.

Remaining work includes complete player histories and boundaries, selected
population admission, season reference admission, and the five unfinished
defensive/review-dependent player adapters. The public
[readiness record](../../../serving/METRIC-READINESS.md) remains explicit about
those limitations.
