# BaseballO Explorer

This directory contains the playable, local BaseballO analytics interface. It
lets a user assemble reviewed questions about batting, pitching, baserunning,
games, teams, venues, officials, and Plate Appearance Quality
without writing SPARQL.

The browser never submits arbitrary SPARQL. A loopback-only Node server accepts
allowlisted component IDs and compiles them through
[`query-builder/`](query-builder/README.md). The versioned serving adapter is
consulted first, but its contract currently admits only Plate Appearance
Quality/Good At Bat and that slice's option lists to SQLite. Simple Explore,
the other reviewed Advanced questions, Empty Games, Derived, and their option
lists remain on authoritative SPARQL until their own end-to-end equivalence is
accepted. A missing or stale admitted build also fails open to the matching
authoritative query. The browser never queries the disposable index directly.
The batch materializer may use proven indexed identities while building SQL
grains, but a populated grain is not itself permission to route a UI family to
SQL.

## Explorer interaction contract

Preserve the Explorer's general visual design and the baseball interaction used
for search. The remaining navigation, selectors, filters, result layouts, and
information hierarchy are open to revision. The current interface implements
the first vertical slice of this contract without changing any semantic query
or serving-route admission.

The primary path is **Questions**. Search for players, games, teams,
and venues should remain persistently available as that capability grows, while **Build a Metric** should
be presented as an intentionally advanced workspace. The Questions interface
must expose user questions rather than implementation or report names. A UI
question is a versioned recipe that identifies its underlying query, result
grain, view or reducer, default ordering, and permitted refinements. One SPARQL
artifact may therefore support several distinct questions.

Question wording must name the analytic being used instead of hiding the
judgment behind words such as "best." Examples include:

- Which plate appearances have the highest PAQ-1.0?
- Which players have the highest average PAQ-1.0?
- Which plate appearances have the highest Grind Score?
- Who has the highest average Grind Score?
- Who has the highest Empty Game Rate?
- Which empty games have the highest Damage Score?

The interaction model separates scope from calculation. Supported scopes are
one plate appearance, one game, or a selected span of games. Calculations over
a span may be cumulative, average or rate, or sequence and trend. Players,
teams, pitchers, matchups, venues, game types, travel sequences, rest, weather,
and similar features are contexts or dimensions, not additional top-level
modes. A single plate-appearance view may later link to finer pitch and contact
evidence without adding another top-level mode.

Do not turn the knowledge graph's combinatorial power into a universal filter
panel. All reviewed questions may remain available, but they need not all be
visible at once. Use a small set of featured or grouped questions, question
search or browse, sensible defaults, and only the controls that materially
change the selected question. Put uncommon compatible controls behind a
discoverable **Refine** action. Results should offer contextual pivots such as
player, game, venue, matchup, or travel sequence rather than requiring the user
to construct every path before running a question.

The Questions menu keeps every reviewed question in one place but groups the
native options by plate appearances, players and matchups, games and innings,
Empty Games, decisions and review, and data quality. Selecting a question shows
its answer grain and calculation type immediately. This makes the individual,
single-game, cumulative-span, average/rate, sequence, and audit behaviors clear
without adding another mode or exposing more filters.

Every answer must visibly state its analytic version, population and game set,
time scope, minimum sample when applicable, data coverage, and serving-build
time. Average rankings must show their denominator and must not silently rank a
one-appearance sample against a season sample. Measurement-enabled and
measurement-missing plate appearances require an explicit comparability rule,
and different PAQ versions must not be silently combined. Contextual results
such as venue, weather, rest, or travel should be described as associations
unless a separate defensible causal model exists.

Every calculated question should provide an inline **Show math** disclosure.
It displays the complete formula in human-readable form, including component
weights, lookup tables, conditional branches, caps, thresholds, missing-data
rules, normalization, and rounding. It does not need to display the raw values
for every result. Instead, an individual result should link to **View this plate
appearance**, which shows the evidence for that one plate appearance: game and
participants, game state, result, pitches seen, swing/foul/contact evidence,
grind inputs, and batted-ball measurements when applicable. Routine drill-down
data should be materialized as reusable SQL grains so following a result link
does not require an interactive traversal of the full RDF corpus.

The intended navigation is therefore:

```text
question -> scoped answer -> player/game/plate-appearance evidence
      \-> Show math -> complete human-readable formula
```

## Run locally

For normal use, install the idempotent Windows desktop launcher once:

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/install-explorer-shortcut.ps1
```

The **BaseballO Explorer** desktop shortcut starts or reuses Fuseki, NiFi, and
the loopback Explorer server, waits for their health checks, and opens the
Explorer in the default browser. Repeated clicks reuse a healthy current
Explorer. When server or query-builder code changes, its startup fingerprint
causes the launcher to restart only the stale Node process before opening the
browser.

Start Fuseki first, then launch the explorer from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/start-fuseki.ps1
Set-Location Baseball/web
npm start
```

Open <http://127.0.0.1:4173/>. The interface reports whether Fuseki is connected
and how many authoritative game graphs are loaded.

Run the web checks with:

```powershell
Set-Location Baseball/web
npm test
npm run check
```

## Current capabilities

- batting, pitching, baserunning, and game/assignment question families;
- a shared official-game-date scope resolved from a compact, short-lived
  graph/date index before each substantive query, with latest-day, seven-day,
  30-day, season-to-date, and custom ranges;
- separate Regular season and 2026 All-Star Game sets, with regular-season play
  selected by default and option lists restricted to the active set;
- game-scoped team grouping and filtering for batting, pitching, and
  baserunning; offensive teams are derived from the half-inning while pitching
  uses the opposing fielding team;
- reconciled pitching totals split into balls, called strikes,
  swinging/missed strikes, fouls/foul tips, balls put in play, and hit batters;
- three primary modes: **Explore** for simple subject-first tables,
  **Questions** for one flat selector containing all six Empty Games analyses
  and every reviewed advanced query as 24 plain-language question recipes, and
  **Build a Metric** for compatible numerator/denominator calculations;
- Questions is the initial mode and no substantive query runs merely because
  the page opened. Scope and optional refinements use progressive disclosure,
  and only the two currently selectable game sets (Regular season and All-Star)
  are shown;
- a first-class **Plate Appearance Quality** view that serves the reviewed
  plate-appearance question.
  PAQ-1.0 is displayed to three decimals from `.000` through `1.000`; its
  default table shows the overall rating, band, outcome, grind, and situational
  component. The longer evidence remains in the result and CSV without
  overloading the default view.
  A `Show` selector switches the same materialized grain between individual
  plate appearances and player averages. Player averages include PA count and
  quality-band counts and are sortable by player or average PAQ.
  The Questions selector also presents those as two distinct questions even
  though they share one underlying query. **Show math** exposes the complete
  PAQ-1.0 outcome table, component weights, grind and situation rules, damage
  cap, rounding, and the current no-Statcast boundary. Individual PAQ rows link
  to a plate-appearance evidence dialog using the complete row already returned
  by the admitted SQL grain; pre-plate-appearance score and base/out state remain
  explicit follow-up grain work rather than being implied;
  Route metadata distinguishes the materialized SQL build (including its build
  and corpus fingerprints) from explicit authoritative fallback;
- a dedicated reviewed Empty Games view, currently served by authoritative
  SPARQL, that displays its
  current contribution policy and completeness gate, with season, game,
  batting-team, venue, batter, and pitcher filters. One shared reviewed
  classification query supports player counts and ratios, batting-team rates,
  consecutive offensive-game stretches, whole-game results grouped by pitchers
  faced, and individual empty player-games. A damage ranking
  crosses all seven nonempty base configurations with zero, one, or two outs;
  weights first/second/third base as 1/2/3; applies the existing
  `pitch + swing + 2*contact + 2*foul` grind score; and gives double plays a
  1.25 multiplier capped at 100 for one plate appearance. It is an exploratory
  query result, not a stored statistic. Its six analyses now appear directly as
  questions rather than behind a second analysis selector, and Damage Score has
  a complete human-readable **Show math** disclosure. Execution is deliberately staged: the
  reviewed Empty Games query first returns only empty graph/player pairs, a
  second positive-evidence query reduces their failed plate appearances to one
  row per bad at-bat, and the server then scores and aggregates those rows by
  player-game;
- a Build a Metric view whose allowlisted measure contracts combine Empty Games and
  Offensive Games Played at player-game grain, labeling the subset calculation
  as a percentage and the reverse calculation as a ratio, with the selected
  numerator, denominator, scale, and zero-denominator rule shown inline;
- a reviewed Questions path for all 17 cataloged event-chain analytics,
  including the same unified at-bat evidence query for catalog completeness,
  plus
  on-field versus operative replay calls, challenge versus umpire initiation,
  and supported replay-review transitions with unsupported decision families
  shown as unclassified, with
  positive-evidence, completeness-gated, integrity-audit, or decision-support semantics shown
  before execution and shared season, game, team-in-game, and venue filters.
  Catalog-declared result filters additionally narrow only queries whose output
  unambiguously identifies a batter, pitcher, runner, umpire, or official
  scorer;
- dimensions and metrics generated from the existing component catalog;
- graph-backed filter options for seasons, games, players, venues, event types,
  teams, umpires, and official scorers;
- click-sortable tabular results, selected-route and cache metadata, and CSV export that
  preserves the selected table order;
- generated-query inspection and copy; and
- responsive keyboard-accessible local interface.

Advanced filters restrict the authoritative game graphs supplied to the
reviewed query. Accordingly, its Team filter means that the selected team
participated in the game; it does not silently reinterpret a query-specific
player as belonging to that team. Result filters are applied outside each
reviewed Advanced aggregation, so they narrow rows without changing its claim.
The fixed Advanced groupings remain fixed because regrouping several queries
would change the reviewed claim. Empty Games uses the narrower offensive-team
relationship for the selected batter and game and exposes its own safe grouping
choices.

Authoritative option lists and safe repeated SPARQL results are cached for 30
seconds under a corpus fingerprint built from the current NiFi RDF manifests.
A changed fingerprint clears both caches. Admitted materialized requests
instead read the immutable SQL build. Candidate Empty Games, Derived,
Advanced, and Explore grains may be present for backfill and equivalence work,
but their UI routes remain authoritative until admitted in
[`../serving/contract.json`](../serving/contract.json).

The current SQL-backed visible slice is Plate Appearance Quality/Good At Bat,
including individual plate appearances, player averages, and its admitted
filter options. The status line reports the selected layer and, for a
materialized response, its build and coverage. Live SPARQL remains available
for all pending families, novel research, and fail-open fallback. The SQL
database is derived, immutable after promotion, and rebuildable from
authoritative RDF. The operational acceptance script sends
`X-BaseballO-Require-Materialized: true`; diagnostic requests for a route that
is not admitted fail closed with HTTP 503 instead of silently executing a long
RDF fallback query.

This is a local research interface, not a public deployment. Fuseki remains
bound to loopback, update endpoints are not exposed through the explorer, and
the user-authorized MLB acquisition remains isolated in NiFi at 05:00 Eastern.
