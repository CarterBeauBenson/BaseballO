# SPARQL

Statistical totals and absence-based classifications belong here, not in RML-generated instance data.

## Query families

The library is organized by the mapped domain rather than by one statistic:

| Family | Examples |
| --- | --- |
| [`batting/`](batting/) | Outcome distributions, plate appearances, home runs, extra-base hits, total bases, multi-hit games, three true outcomes, and hitless games |
| [`pitching/`](pitching/) | Pitch totals, ball/strike processes, plate appearances faced, pitches per plate appearance, swings, and batted balls |
| [`baserunning/`](baserunning/) | Runs, runner event types, stolen bases, outs, and safe/out/run resolution totals |
| [`games/`](games/) | Games by season/venue/team, home-away splits, matchups, umpires, official scorers, and timelines |
| [`options/`](options/) | Discovery queries that populate UI select boxes from loaded values |

These are additive to the cross-cutting hit queries below. The UI-facing
[`analytics-query-builder`](../web/query-builder/analytics-query-builder.js)
can compile the same four domains from selected dimensions, metrics, and
filters.

## Hit query catalog

The active mapping preserves each plate-appearance `eventType`, connects its
result to the plate appearance, identifies the batter through `BatterAct`, and
locates the result at a venue's baseball-field site. These links support the
following executable queries across the per-game named graphs in Fuseki:

| Query | Result |
| --- | --- |
| [`hits-by-season.rq`](hits-by-season.rq) | Total hits and games containing a hit for each season |
| [`hits-by-season-and-venue.rq`](hits-by-season-and-venue.rq) | Hit totals for each venue and season |
| [`hits-by-player-and-season.rq`](hits-by-player-and-season.rq) | Player hit leaderboard for each season |
| [`hits-by-player-and-venue.rq`](hits-by-player-and-venue.rq) | Player hit totals at each venue and season |
| [`hit-types-by-season.rq`](hit-types-by-season.rq) | Singles, doubles, triples, and home runs by season |
| [`hits-by-game.rq`](hits-by-game.rq) | Hit total and venue for each loaded game |

The [`options/`](options/) directory contains the smaller discovery queries
used to populate season, venue, player, hit-type, and game select boxes. The UI
component catalog links each dimension to its corresponding options query.

For these queries, a hit is a distinct plate-appearance result whose preserved
MLB `eventType` is `single`, `double`, `triple`, or `home_run`. The queries use
the source identifier rather than OWL subclass inference, so they remain
correct when Fuseki is running without a reasoner and include triples even
before a sample containing a triple has been reviewed for a specific RML type
map.

The source season field is not currently emitted as RDF. `?season` is therefore
derived with `YEAR` from the mapped first-pitch timestamp. This is an explicit
query-layer convention, not a stored statistic.

### Restricting a query

The grouped queries return every loaded season, venue, or player. A caller can
add `VALUES` clauses inside the `GRAPH` block to request a specific slice. For
example:

```sparql
VALUES ?venue { <https://baseballontology.org/data/venue/2680> }
VALUES ?player { <https://baseballontology.org/data/player/545361> }
```

Place a season filter after the query's `BIND` expression:

```sparql
FILTER(?season = 2019)
```

Against the checked-in game 566279 fixture, the hit queries report 21 hits at
Petco Park in 2019: 13 singles, 6 doubles, and 2 home runs. This is a one-game
development check, not a season dataset.

## UI composition

The complete `.rq` files are reviewable canned queries. The future web
interface can also compile equivalent queries from fixed select-box components
using the allowlisted [`web/query-builder`](../web/query-builder/README.md)
module. The general compiler covers batting, pitching, baserunning, and game
queries; the original hit-only compiler remains available as a focused
compatibility layer. Its dimensions, metrics, and filters are code-owned
components, while user input is limited to validated selections and values
rather than raw SPARQL.

## Empty Games prototype

[`empty-games-prototype.rq`](empty-games-prototype.rq) is an executable review query, not yet the final product definition. It uses the source-backed `BatterAct` for offensive participation and treats the following mapped evidence as a contribution:

- single, double, home run, or walk;
- sacrifice fly or fielder's choice;
- a baserunning event whose source identifier begins with `stolen_base`.

The query excludes entire games containing a plate-appearance result type outside the mapping's current eleven-value completeness profile. That prevents an unknown result from silently becoming an empty game.

One important limitation remains: runner records are not explicitly linked to their enclosing plate appearance. The prototype therefore cannot attribute an ordinary batter out that moves another runner to that batter. Its output must be treated as candidates for review, not a published statistic.

The project owner is needed before promotion to a canned UI query to approve the contribution policy: productive outs, reach-on-error, hit-by-pitch, fielder's choice, sacrifice types, steals/caught stealing, pinch runners, and any minimum offensive-participation threshold.
