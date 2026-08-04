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
| [`advanced/`](advanced/) | Sixteen event-chain analytics with explicit positive, completeness-gated, and integrity-audit semantics |
| [`query-index/`](query-index/) | Reviewable `CONSTRUCT` components for the disposable per-game shortcut graph |

These are additive to the cross-cutting hit queries below. The UI-facing
[`analytics-query-builder`](../web/query-builder/analytics-query-builder.js)
can compile the same four domains from selected dimensions, metrics, and
filters.

The complete 48-query audit is recorded in
[`query-inventory.md`](query-inventory.md). Those canned queries still use the
authoritative patterns. The implemented acceleration layer and its operational
shortcut contract are documented in [`query-index/`](query-index/); remaining
production decisions are tracked in
[`graph-condensation-requirements.md`](graph-condensation-requirements.md).

The separate reviewed runner currently has 18 exact authoritative/indexed
corpus pairs. Fifteen use the disposable index automatically and three neutral
lookups remain authoritative. All nine queries in [`batting/`](batting/) now
have measured indexed companions. `hitless-games-by-player` is the only
negative-semantics indexed route and is permitted only after complete, current
per-game plate-appearance and hit equivalence checks.

The separate [`advanced/`](advanced/) suite adds 16 higher-order questions
without changing the original 48-query contract. Its catalog distinguishes
positive evidence from absence-based completeness claims and records four
analytics that the current mapping cannot yet support. These queries remain
authoritative and are not exposed through the UI compiler or operational query
index routes yet.

## Hit query catalog

The active mapping connects each specific institutional result to its plate
appearance, its adjudication, the batter's `BatterAct`, and the enclosing game.
The game is located through its baseball-field site and venue. These links support the
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

For these queries, a hit is a distinct plate-appearance institutional result
explicitly typed as `SingleProcess`, `DoubleProcess`, `TripleProcess`, or
`HomeRunProcess` and linked to a `HitJudgmentAct`. The queries name all four
classes directly, so they do not depend on OWL subclass inference. They count
the result once rather than also counting its source record, judgment, or
decision.

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

The checked-in completed-game fixture remains the offline development source.
Query parsing and structural validation do not constitute acceptance of its
totals as season statistics.

## UI composition

The complete `.rq` files are reviewable canned queries. The local web
interface also compiles equivalent queries from fixed select-box components
using the allowlisted [`web/query-builder`](../web/query-builder/README.md)
module. The general compiler covers batting, pitching, baserunning, and game
queries; the original hit-only compiler remains available as a focused
compatibility layer. Its dimensions, metrics, and filters are code-owned
components, while user input is limited to validated selections and values
rather than raw SPARQL.

## Empty Games prototype

[`empty-games-prototype.rq`](empty-games-prototype.rq) is an executable review query, not yet the final product definition. It uses `BatterAct` for offensive participation and recognizes reviewed contribution process patterns, including:

- single, double, triple, home run, or walk;
- sacrifice fly or fielder's choice;
- an explicitly adjudicated stolen-base process.

The query excludes entire games containing a plate-appearance result outside
the mapping's current 19-source-token completeness profile (`walk` and
`intent_walk` share the same `WalkProcess` pattern). That prevents an unknown
result from silently becoming an empty game. Set-based exclusions preserve the
same negative definition without repeating each absence test for every batter
act.

Runner acts and resolutions are now explicitly linked to their enclosing plate
appearance through execution-only structural context. The contribution policy
still remains incomplete, so output must be treated as candidates for review,
not a published statistic. The local Explorer exposes it in a dedicated
authoritative-only review view and labels the definition as a prototype.

The project owner is needed before promotion from reviewed prototype to a final
product definition to approve the contribution policy: productive outs,
reach-on-error, hit-by-pitch, fielder's choice, sacrifice types, steals/caught
stealing, pinch runners, and any minimum offensive-participation threshold.
