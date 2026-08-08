# BaseballO Explorer

This directory contains the playable, local BaseballO analytics interface. It
lets a user assemble reviewed questions about batting, pitching, baserunning,
games, teams, venues, and officials without writing SPARQL.

The browser never submits arbitrary SPARQL. A loopback-only Node server accepts
allowlisted component IDs, compiles them through
[`query-builder/`](query-builder/README.md), and sends read-only queries to the
local Fuseki query endpoint. Queries and option lists are explicitly restricted
to authoritative game graphs; the disposable query index is not used yet.
The separately tested operational runner currently manages 18 measured query
pairs (15 indexed and three authoritative), but it is intentionally not wired
into the Explorer until that UI interaction and fallback behavior are reviewed.

## Run locally

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
- game-scoped team grouping and filtering for batting, pitching, and
  baserunning; offensive teams are derived from the half-inning while pitching
  uses the opposing fielding team;
- reconciled pitching totals split into balls, called strikes,
  swinging/missed strikes, fouls/foul tips, balls put in play, and hit batters;
- a dedicated authoritative-only Empty Games review view that displays its
  current contribution policy and completeness gate, with season, game,
  batting-team, venue, and batter filters;
- a dedicated Advanced view for all 17 cataloged event-chain analytics, including
  on-field versus operative replay calls, challenge versus umpire initiation,
  and supported replay-review transitions with unsupported decision families
  shown as unclassified, with
  positive-evidence, completeness-gated, or integrity-audit semantics shown
  before execution and shared season, game, team-in-game, and venue filters;
- dimensions and metrics generated from the existing component catalog;
- graph-backed filter options for seasons, games, players, venues, event types,
  teams, umpires, and official scorers;
- tabular results, execution metadata, and CSV export;
- generated-SPARQL inspection and copy; and
- responsive keyboard-accessible local interface.

Advanced filters restrict the authoritative game graphs supplied to the
reviewed query. Accordingly, its Team filter means that the selected team
participated in the game; it does not silently reinterpret a query-specific
player as belonging to that team. Empty Games uses the narrower offensive-team
relationship for the selected batter and game.

This is a local research interface, not a public deployment. Fuseki remains
bound to loopback, update endpoints are not exposed through the explorer, and
live MLB acquisition remains disabled.
