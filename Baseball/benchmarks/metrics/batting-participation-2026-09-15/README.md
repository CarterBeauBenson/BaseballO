# Batting participation and qualification evidence

The [captured comparison](result.json) uses the hash-pinned M1/M2 output for
game 824315. The canonical query in Jena extracts 77 PA observations with one
batting-role bearer each, covering 20 players. The evidence survives the exact
SQL round trip. Each observed player count matches that player's official
boxscore total; the team totals are 41 and 36. Offensive substitutions occur
at event index zero with a 0–0 count in turns 53 and 55.

This is a source/graph comparison, not admission of official-credit identity,
the complete selected-period exposure, or any metric score. The report is
never read as a serving data source. `tests/prove_batting_participation.py`
consumes the focused Jena/SQL proof and verifies its source and RDF hashes.
No raw evidence is changed or acquired; no graph or SQL build is promoted.

## A real counterexample to counting every mapped PA

The existing source `data/raw/samples/2026-08-25/822693.json` has SHA-256
`c2701c7de786df80013b21b36d74e8c5d6f6b1d0063bfab86d83ce6f5fb5fe02`.
Harry Ford (695670) appears as the matchup batter in five records, at indexes
12, 31, 49, 53 and 71, but his official boxscore PA total is four.

Index 49 ends with Daylen Lile caught stealing second for the third out while
Ford's count is 2–0. The record says `type=atBat` and `about.isComplete=true`.
Neither provider field therefore certifies a completed statistical PA for the
batter. The unchanged mapping creates its broad Plate Appearance/Batter Act
structure for this record. The new query correctly observes that participation
but must not label the fifth observation as official PA credit.

An inning-ending baserunning out can leave a batter without a statistical PA.
See [MLB's PA definition](https://www.mlb.com/glossary/standard-stats/plate-appearance).
For substitutions, rule 9.15(b) separately allocates strikeouts and at-bats
between original and replacement batters; the player who finishes the turn
does not always receive the official credit. See [MLB's published rulebook](https://content.mlb.com/documents/2/2/4/305750224/2019_Official_Baseball_Rules_FINAL_.pdf).

## What the implementation closes

The PA participation query and its SQL/API evidence transport are implemented.
The independent exact PA-mean reducer preserves official qualification counts,
score observation counts and team-game exposures separately. Eight Python
regressions cover missing/conflicting scores, zero-PA exclusion, duplicate
observations, missed games, team changes, doubleheaders and ambiguous batting
participation. A Python-to-JavaScript regression verifies that the largest
synthetic mean is excluded when its player falls below the PA minimum.

Official-credit graph representation, complete PA scoring and applicable
team-game exposure remain open. This proof does not produce a real leaderboard.
