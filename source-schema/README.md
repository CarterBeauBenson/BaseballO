# MLB Live Feed Observed Source Schema

This package was extracted from [`../data/raw/game-566279.json`](../data/raw/game-566279.json) (`gamePk` 566279) without modifying the game log.

## Files

- `mlb-feed-live-observed.schema.json` — Draft 2020-12 JSON Schema inferred from every observed field and value type in the sample.
- `mlb-feed-rml-source-schema.yaml` — RML-oriented record schema identifying canonical iterators, reusable record shapes, identity fields, parent-scope dependencies, duplicate views, and observed controlled values.
- `mlb-feed-path-inventory.csv` — exhaustive normalized JSONPath inventory with observed types, occurrence counts, null counts, and example values.

## Direct-mapping policy

The RML will read the untouched MLB feed directly. No source field is added, flattened, renamed, or copied.

The canonical detailed play iterator is:

`$.liveData.plays.allPlays[*]`

The following are retained as source structures but must not be remapped as new detailed events:

- `$.liveData.plays.currentPlay`
- `$.liveData.plays.playsByInning[*]`
- `$.liveData.linescore`

In this completed sample, `currentPlay` is byte-for-byte equal to `allPlays[-1]`.

Boxscore, linescore, leaders, and other aggregate structures remain available for their own informational purposes. They do not replace or duplicate event-level processes.

## Sample observations

- 79 canonical play records
- 301 nested play-event records
- 282 pitch events
- 19 non-pitch action events
- 113 runner records
- 91 fielding-credit records
- 50 player records
- 2 game-team records

## Limit

This is an observed schema extracted from one game. It records what the sample supports; it does not claim that MLB never emits additional fields, missing fields, or alternative shapes.
