# UI query builders

[`analytics-query-builder.js`](analytics-query-builder.js) is the primary
allowlisted component catalog and compiler for the future UI. It supports four
query families:

- batting outcomes: plate appearances, every hit type, walks, strikeouts,
  total bases, and games;
- pitching: pitches, mapped ball and strike processes, plate appearances faced,
  and games;
- baserunning: runner events, runs, outs, safe resolutions, stolen bases, and
  games;
- games: teams, home/away sides, venues, umpires, and official scorers.

[`hit-query-builder.js`](hit-query-builder.js) remains as the narrower first
prototype for callers that want only the four hit outcomes. New UI work should
prefer the analytics builder. Select boxes should use catalog labels and IDs;
they should never accept arbitrary SPARQL fragments from a user.

The initial hit-query family provides these components:

- dimensions: season, venue, player, hit type, and game;
- metrics: distinct hits and games containing hits;
- filters: season, venue, player, hit type, and game;
- presentation controls: allowlisted sort fields, result limit, and offset.

Each dimension also advertises an `optionsQuery`. Those small queries populate
the corresponding select box from values that are actually present in the
loaded graphs. They live under [`sparql/options`](../../sparql/options/) and
return both canonical values and display labels where applicable.

A UI selection such as “group by season and venue, show hits, only Petco Park”
can be compiled as follows:

```javascript
import {
  HIT_QUERY_COMPONENTS,
  compileHitQuery,
} from "./hit-query-builder.js";

const query = compileHitQuery({
  dimensions: ["season", "venue"],
  metrics: ["hits", "games_with_hits"],
  filters: {
    venue: "https://baseballontology.org/data/venue/2680",
    hit_type: ["single", "double", "triple", "home_run"],
  },
  sort: [
    { id: "season", direction: "asc" },
    { id: "hits", direction: "desc" },
  ],
  limit: 100,
});
```

The broader compiler uses the same shape:

```javascript
import {
  ANALYTICS_QUERY_FAMILIES,
  compileAnalyticsQuery,
} from "./analytics-query-builder.js";

const query = compileAnalyticsQuery({
  family: "batting",
  dimensions: ["season", "venue", "player"],
  metrics: ["hits", "home_runs", "total_bases"],
  filters: {
    season: 2019,
    venue: "https://baseballontology.org/data/venue/2680",
  },
  limit: 250,
});
```

The compiler accepts only known component IDs, a bounded integer season,
allowlisted hit types, and canonical BaseballO data IRIs. This preserves the
future public-query boundary: the browser composes reviewed reads, while a
server-side query API should still enforce its own allowlist and limits before
submitting anything to Fuseki.
