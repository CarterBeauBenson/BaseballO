# BaseballO

**BaseballO lets you query baseball as connected game events instead of isolated
statistics rows.**

A normal statistics table is good at questions such as:

- How many hits did a player have?
- How many pitches were called strikes?
- How many games did a team win?

BaseballO is for questions that cross the boundaries between those rows:

- Which called strikes followed a swing, contact, review, or changed decision?
- Who initiated a replay review, what was the original call, and what call
  became final?
- Which pitch, swing, contact, fielding play, and runner movement belong to the
  same play?
- Which players recorded hits for more than one team in the selected games,
  and how many came with each team?
- Which games are excluded from Empty Games analysis because their play-by-play
  contains an unrecognized plate-appearance result?
- Which players had the highest Empty Games percentage over a selected stretch
  of games?

BaseballO keeps the pitch, batter, pitcher, swing, contact, ball movement,
umpire call, replay review, runner movement, and scoring result connected. That
makes it possible to ask across the whole play instead of relying only on the
columns chosen when a statistics table was created.

## What is different from a normal stat table?

| Normal baseball stat table | BaseballO |
| --- | --- |
| Stores a prepared result such as `1 hit` | Stores the game events that can be queried to calculate the hit |
| Has a fixed set of columns | Allows questions across pitches, swings, contact, calls, reviews, runners, teams, venues, and officials |
| Usually treats a player-team relationship as one field | Represents the role a player had for a team in a specific game |
| Often requires a custom table or ETL change for a new statistic | Builds new measurements from reviewed event patterns at query time |
| Can make missing data and zero look the same | Can exclude a game when the required source records are incomplete or unrecognized |
| Returns an aggregate with its definition hidden in code | Shows the measurement definition and generated query with the result |
| Uses the summary table as the data being queried | Keeps the complete game representation and treats faster summaries as rebuildable copies |

A relational database could reproduce many of these features with enough
tables, joins, rules, and custom code. The point is not that tables are
incapable. The point is that BaseballO makes the connections and baseball
meanings part of the shared model instead of rebuilding them separately for
every new analysis.

## A reviewed prototype: Empty Games

BaseballO includes an **Empty Games** prototype: games in which a player
appeared as a batter but recorded no qualifying offensive contribution under
the current completeness-gated policy. The calculation is still being refined;
it must not be presented as a final published statistic.

This is not simply "games with zero hits." The current definition checks for:

- singles, doubles, triples, and home runs;
- walks;
- sacrifice flies;
- fielder's choices; and
- explicitly recorded stolen bases.

If a game contains a plate-appearance result that the current mapping does not
recognize, BaseballO excludes that game instead of automatically calling it
empty.

The Explorer can also calculate:

```text
Empty Games / Offensive Games Played
```

Because both counts refer to player-games from the same reviewed set of games,
the result can be labeled as a percentage. Reversing the measurements produces
a ratio instead. The server rejects arbitrary formulas and measurements that
do not use compatible units and groupings.

## What the Explorer can do now

The local read-only Explorer supports:

- batting, pitching, baserunning, game, team, venue, umpire, and scorer
  questions;
- 17 advanced questions involving connected plays, replay reviews, unusual
  event structures, and incomplete records;
- the versioned PAQ-1.0/Good At Bat rating from `.000` to `1.000`, with
  individual plate appearances and sortable player averages;
- Empty Games and Empty Games percentage;
- compatible numerator/denominator combinations in the Derived view;
- separate Regular season and 2026 All-Star Game query sets, with regular play
  selected by default;
- official-game-date ranges for one day, seven days, 30 days, season to date,
  or a custom range;
- filters for season, game, player, team, and venue where the filter has one
  clear meaning;
- click-to-sort result columns and CSV export; and
- inspection of the generated query used to produce a result.

PAQ-1.0 is retained for reproducibility, but its game-context input and formula
are under review. Empty Games, Derived, Simple Explore, and the non-PAQ
Advanced questions still use authoritative SPARQL and can be slow on the full
corpus until their SQL routes pass exact equivalence. See the
[offensive analytics redesign](Baseball/web/OFFENSIVE-ANALYTICS-REDESIGN.md)
for the current design boundary.

The checked-in evidence corpus contains 546 distinct completed games dated
July 14 through August 25, 2026, including one separately scoped All-Star Game.
A development fixture and a bounded eight-game regression set remain separate.
This is a fixed repository fixture, not the live datastore count. Current
ingestion, quarantine, cleanup, graph, and serving-build status comes from
NiFi's terminal evidence and machine-local serving pointers, not this README.

## Questions this structure supports

BaseballO is being developed for questions such as:

- How do pitch calls relate to swings, contact, balls in play, and runner
  outcomes?
- How often was an original replay call affirmed or overturned?
- Were reviews initiated by a challenge or by an umpire?
- Which players had the highest Empty Games percentage under the stated
  definition?
- Which games contain broken or incomplete event chains?
- Do faster query summaries return exactly the same rows as the complete game
  representation?
- How should rare baseball events be counted without forcing them into the
  wrong category?

This project is not trying to replace Baseball Reference, FanGraphs, Statcast,
or other established baseball products. Those systems are better for standard
leaderboards, player pages, standings, and historical coverage. BaseballO is
focused on custom questions that need several parts of a game connected at
once.

## Where the project is now

BaseballO is already a working local research system, not just a proposed data
model. Seven detachable MLB API lanes can independently acquire, map, validate,
and promote Games, Teams, Leagues, Divisions, People, Venues, and Transactions.

```mermaid
flowchart TD
    A["Seven independent<br/>MLB API connectors"] --> B["Source-owned NiFi lanes"]
    B --> API["Transient exact<br/>API responses"]
    API --> C["Source-owned RML"]
    C --> D["Source-owned SHACL"]
    D --> E["Persistent authoritative<br/>RDF research record"]
    E --> G["Game-only rebuildable<br/>indexed RDF facts"]
    E --> H["Approved post-batch<br/>SPARQL materialization"]
    G --> H
    H --> SQL["Persistent derived<br/>SQLite serving layer"]
    SQL --> F["Admitted materialized<br/>Explorer views"]
    E --> LIVE["Live SPARQL for<br/>novel research"]
    LIVE --> F
```

The checked-in implementation includes:

- 546 distinct completed games, including one separately scoped All-Star Game,
  in the checked-in evidence corpus
- 51 standard queries and 17 advanced queries with reproducible test results
- 19 authoritative-versus-index query comparisons with identical results
- a local read-only Explorer with date scoping, filters, derived measurements,
  sortable results, CSV export, and generated-query inspection
- seven independent NiFi source lanes with bounded proofs, daily 05:00 Eastern
  schedules, source-local retry/quarantine, and transient-payload cleanup

The implementation uses Apache NiFi for orchestration, RML to map source
records, SHACL to check source graph structure, and Apache Jena Fuseki/TDB2 to
store the authoritative RDF. The current workstation keeps the high-volume RDF
store on guarded external storage. SQLite holds rebuildable analytical grains;
only Plate Appearance Quality/Good At Bat is currently admitted to SQL-backed
Explorer serving, while pending families continue to use authoritative SPARQL.
A baseball user does not need to know those technologies to use the Explorer.

## A possible product end state

The product opportunity is a research layer between raw game feeds and fixed
leaderboards. Instead of commissioning a new data pipeline for every unusual
question, a baseball organization could build, save, compare, and share new
measurements from the same connected game data.

```mermaid
flowchart TD
    A["Authorized live and<br/>historical feeds"] --> B["Continuous game<br/>processing"]
    B --> C["Connected multi-season<br/>baseball data"]
    C --> D["Baseball question<br/>builder"]
    D --> E["Custom statistics<br/>and ratios"]
    D --> F["Replay and play-chain<br/>research"]
    D --> G["Coverage and<br/>data-quality reports"]
    E --> H["Saved and shareable<br/>research"]
    F --> H
    G --> H
    H --> I["Web product, API, notebooks,<br/>and partner tools"]
```

A mature version could add full-season and historical coverage, continuous
updates, saved definitions, result-to-play drill-down, team workspaces, and an
API for partner products. Those are possible product capabilities, not claims
about the current prototype.

## Potential uses

- New cross-event questions can reuse the existing game connections instead of
  requiring a separate table and pipeline for every analysis.
- Researchers can combine compatible measurements, including percentages and
  ratios, while checking that their units and groupings make sense.
- Pitches, calls, reviews, contact, fielding, runners, and scoring can be
  examined together without manually stitching separate exports together.
- Results can be accompanied by their measurement definitions and generated
  queries, making an analysis easier to inspect and repeat.
- The same connected data can support exploratory research, data-quality
  checks, notebooks, visualizations, and other baseball-analysis tools.

BaseballO is an independent research and development project exploring how
connected game data can support questions that are difficult to express with
fixed statistics tables.

## Run the Explorer locally

For normal use, install or refresh the desktop shortcut once:

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/install-explorer-shortcut.ps1
```

The **BaseballO Explorer** shortcut starts or reuses Fuseki, NiFi, and the
Explorer server, then opens <http://127.0.0.1:4173/>. For a one-time launch
without installing the shortcut, run:

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/launch-explorer.ps1
```

See the [Explorer guide](Baseball/web/README.md) for more detail.

## Technical documentation

The active implementation is under [`Baseball/`](Baseball/README.md).

- [Explorer and query builder](Baseball/web/README.md)
- [query library](Baseball/sparql/README.md)
- [source modules](Baseball/sources/README.md)
- [MLB game mapping](Baseball/sources/mlb-game/mapping/README.md)
- [graph checks](Baseball/shacl/README.md)
- [NiFi and Fuseki infrastructure](Baseball/infra/README.md)
- [selective reasoning](Baseball/reasoning/README.md)
- [repository layout](Baseball/REPOSITORY-LAYOUT.md)
- [current roadmap](Baseball/ROADMAP.md)

The replacement NiFi flow includes a separate daily `Repository Evidence`
observer for aggregate validation. It records evidence without controlling
source lanes, RDF promotion, or serving pointers. Local development still uses
focused component checks rather than reproducing that aggregate workflow as an
attended command chain.
