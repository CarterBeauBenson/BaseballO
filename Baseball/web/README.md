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
- a dedicated authoritative-only Empty Games review view that displays its
  current contribution policy and completeness gate;
- a dedicated Advanced view for all 16 cataloged event-chain analytics, with
  positive-evidence, completeness-gated, or integrity-audit semantics shown
  before execution;
- dimensions and metrics generated from the existing component catalog;
- graph-backed filter options for seasons, games, players, venues, event types,
  teams, umpires, and official scorers;
- tabular results, execution metadata, and CSV export;
- generated-SPARQL inspection and copy; and
- responsive keyboard-accessible local interface.

This is a local research interface, not a public deployment. Fuseki remains
bound to loopback, update endpoints are not exposed through the explorer, and
live MLB acquisition remains disabled.
