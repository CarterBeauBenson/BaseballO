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
- What team role did a person have in this particular game?
- Did an event not happen, or is the source record incomplete or not yet
  recognized?
- Can two measurements be combined into a percentage without mixing different
  kinds of counts?

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

## A current example: Empty Games

BaseballO currently includes an **Empty Games** measurement: games in which a
player appeared as a batter but recorded no qualifying offensive contribution.

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
- Empty Games and Empty Games percentage;
- compatible numerator/denominator combinations in the Derived view;
- official-game-date ranges for one day, seven days, 30 days, season to date,
  or a custom range;
- filters for season, game, player, team, and venue where the filter has one
  clear meaning;
- click-to-sort result columns and CSV export; and
- inspection of the generated query used to produce a result.

The checked-in research corpus contains 288 completed games dated July 14
through August 6, 2026, plus a separate development fixture. It is a test
corpus, not a complete season or historical database.

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
model. Completed-game files can move through one repeatable workflow and become
connected, checked, queryable game data.

```mermaid
flowchart LR
    A["Completed-game JSON"] --> B["Repeatable NiFi processing"]
    B --> C["Connected game events and roles"]
    C --> D["Structure and coverage checks"]
    D --> E["Complete game store"]
    E --> F["Local BaseballO Explorer"]
    E --> G["Rebuildable query summaries"]
    G --> H["Exact-result comparison"]
    H --> F
```

Today that system includes:

- 288 completed games in the checked-in raw corpus
- 48 standard queries and 17 advanced queries with reproducible test results
- 18 complete-versus-summary query comparisons with identical results
- a local read-only Explorer with date scoping, filters, derived measurements,
  sortable results, CSV export, and generated-query inspection
- a repeatable NiFi workflow for mapping, checking, loading, indexing, and
  testing games

The implementation uses Apache NiFi for the repeatable game-processing
workflow, RML to map source records, SHACL to check graph structure, and Apache
Jena Fuseki/TDB2 to store and query the games. A baseball user does not need to
know those technologies to use the Explorer.

## A possible product end state

The product opportunity is a research layer between raw game feeds and fixed
leaderboards. Instead of commissioning a new data pipeline for every unusual
question, a baseball organization could build, save, compare, and share new
measurements from the same connected game data.

```mermaid
flowchart LR
    A["Authorized live and historical feeds"] --> B["Continuous game processing"]
    B --> C["Connected multi-season baseball data"]
    C --> D["Baseball question builder"]
    D --> E["Custom statistics and ratios"]
    D --> F["Replay and play-chain research"]
    D --> G["Coverage and data-quality reports"]
    E --> H["Saved and shareable research"]
    F --> H
    G --> H
    H --> I["Web product, API, notebooks, and partner tools"]
```

A mature version could add full-season and historical coverage, continuous
updates, saved definitions, result-to-play drill-down, team workspaces, and an
API for partner products. Those are possible product capabilities, not claims
about the current prototype.

## Why an organization would pay for it

- **Less one-off data engineering:** new cross-event questions can reuse the
  existing game connections instead of starting with a new table and pipeline.
- **More useful custom statistics:** analysts can combine compatible
  measurements, including percentages and ratios, while the system checks that
  the units and groupings make sense.
- **Faster investigation:** researchers can move between pitches, calls,
  reviews, contact, fielding, runners, and scoring without manually stitching
  separate exports together.
- **Definitions people can inspect and reuse:** a result can travel with its
  measurement definition and generated query instead of living only in an
  analyst's private code.
- **One foundation for several products:** the same connected data can support
  an internal research tool, broadcast preparation, data-quality reporting,
  notebooks, and partner-facing APIs.

The likely buyers are teams, baseball data providers, media and broadcast
groups, research organizations, and companies building baseball products. The
value is not the underlying database technology; it is answering expensive,
custom baseball questions with less repeated data work.

## Run the Explorer locally

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/start-fuseki.ps1
Set-Location Baseball/web
npm start
```

Open <http://127.0.0.1:4173/>.

See the [Explorer guide](Baseball/web/README.md) for more detail.

## Technical documentation

The active implementation is under [`Baseball/`](Baseball/README.md).

- [Explorer and query builder](Baseball/web/README.md)
- [query library](Baseball/sparql/README.md)
- [game-data mapping](Baseball/mappings/README.md)
- [graph checks](Baseball/shacl/README.md)
- [NiFi and Fuseki infrastructure](Baseball/infra/README.md)
- [selective reasoning](Baseball/reasoning/README.md)
- [current continuation plan](Baseball/NEXT-PHASE.md)

Run the complete repository check with:

```powershell
python Baseball/scripts/validate_repository.py
```
