import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import {
  ANALYTICS_QUERY_FAMILIES,
  compileAnalyticsQuery,
} from "../query-builder/analytics-query-builder.js";
import {
  buildPublicDerivedMetricCatalog,
  compileDerivedMetricQuery,
} from "../query-builder/derived-metric-query-builder.js";
import { buildPublicCatalog, compileGameDateIndexQuery, createBaseballServer } from "../server.mjs";

test("public catalog exposes labels without SPARQL implementation details", () => {
  const catalog = buildPublicCatalog();
  assert.deepEqual(Object.keys(catalog), ["batting", "pitching", "baserunning", "games"]);
  assert.equal(catalog.batting.metrics.hits.label, "Hits");
  assert.equal(catalog.pitching.metrics.called_strikes.label, "Called strikes");
  assert.equal(catalog.pitching.metrics.fouls.label, "Fouls/foul tips");
  assert.equal(catalog.pitching.metrics.in_play.label, "Balls put in play");
  assert.equal(catalog.batting.dimensions.player.hasOptions, true);
  assert.equal(catalog.batting.dimensions.team.label, "Batting team");
  assert.equal(catalog.pitching.dimensions.team.label, "Pitching team");
  assert.equal(catalog.baserunning.dimensions.team.label, "Baserunning team");
  assert.equal("corePatterns" in catalog.batting, false);
});

test("team dimensions use game-scoped offensive and fielding roles", () => {
  const batting = compileAnalyticsQuery({
    family: "batting",
    dimensions: ["team"],
    metrics: ["hits"],
  });
  assert.match(batting, /STRENDS\(STR\(\?halfInning\), "\/top"\), base:AwayTeamRole, base:HomeTeamRole/u);
  assert.match(batting, /GROUP BY \?team \?teamLabel/u);

  const pitching = compileAnalyticsQuery({
    family: "pitching",
    dimensions: ["team"],
    metrics: ["pitches"],
  });
  assert.match(pitching, /STRENDS\(STR\(\?halfInning\), "\/top"\), base:HomeTeamRole, base:AwayTeamRole/u);
});

test("pitching metrics form an SME-labeled pitch outcome partition", () => {
  const query = compileAnalyticsQuery({
    family: "pitching",
    dimensions: ["pitcher"],
    metrics: ["pitches", "balls", "called_strikes", "swinging_strikes", "fouls", "in_play", "hit_batters"],
  });
  assert.match(query, /dcterms:type \?pitchCallCode/u);
  assert.match(query, /"F", "T", "L"/u);
  assert.match(query, /"X", "D", "E"/u);
  assert.match(query, /AS \?calledStrikes/u);
  assert.match(query, /AS \?swingingStrikes/u);
  assert.match(query, /AS \?fouls/u);
  assert.match(query, /AS \?inPlay/u);
  assert.match(query, /AS \?hitBatters/u);
});

test("compiler restricts UI queries to authoritative game graphs", () => {
  const query = compileAnalyticsQuery({
    family: "batting",
    dimensions: ["player", "venue"],
    metrics: ["hits"],
    filters: { season: 2026 },
  });
  assert.match(query, /FILTER\(STRSTARTS\(STR\(\?graph\), "https:\/\/w3id\.org\/baseball\/graph\/game\/"\)\)/u);
  assert.match(query, /FILTER\(\?season = 2026\)/u);
  assert.doesNotMatch(query, /query-index/u);
});

test("compiler rejects unknown components and noncanonical IRIs", () => {
  assert.throws(
    () => compileAnalyticsQuery({ family: "batting", metrics: ["made_up"] }),
    /Unknown batting metric/u,
  );
  assert.throws(
    () => compileAnalyticsQuery({
      family: "games",
      metrics: ["games"],
      filters: { venue: "https://example.com/injected" },
    }),
    /canonical BaseballO data IRI/u,
  );
});

test("every family has at least one dimension and metric", () => {
  for (const definition of Object.values(ANALYTICS_QUERY_FAMILIES)) {
    assert.ok(Object.keys(definition.dimensions).length > 0);
    assert.ok(Object.keys(definition.metrics).length > 0);
  }
});

let server;
let baseUrl;
const issuedQueries = [];

before(async () => {
  const fetchImpl = async (_url, options) => {
    const query = new URLSearchParams(options.body).get("query");
    issuedQueries.push(query);
    const statusQuery = query.includes("COUNT(DISTINCT ?game) AS ?games")
      && !query.includes("GROUP BY");
    const emptyGamesQuery = query.includes("AS ?emptyGames");
    const derivedMetricQuery = query.includes("AS ?derivedValue");
    const graphScopeQuery = query.includes("SELECT DISTINCT ?graph WHERE");
    const dateIndexQuery = query.includes("SELECT DISTINCT ?graph ?game WHERE");
    const payload = statusQuery
      ? {
          head: { vars: ["games"] },
          results: { bindings: [{ games: { type: "literal", value: "9" } }] },
        }
      : dateIndexQuery
        ? {
            head: { vars: ["graph", "game"] },
            results: { bindings: [{
              graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" },
              game: { type: "uri", value: "https://baseballontology.org/data/game/823105" },
            }] },
          }
      : graphScopeQuery
        ? {
            head: { vars: ["graph"] },
            results: { bindings: [{ graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" } }] },
          }
      : derivedMetricQuery
        ? {
            head: { vars: ["player", "playerLabel", "emptyGames", "offensiveGamesPlayed", "derivedValue"] },
            results: { bindings: [{
              player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
              playerLabel: { type: "literal", value: "Example Player" },
              emptyGames: { type: "literal", value: "2", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
              offensiveGamesPlayed: { type: "literal", value: "8", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
              derivedValue: { type: "literal", value: "25", datatype: "http://www.w3.org/2001/XMLSchema#decimal" },
            }] },
          }
      : emptyGamesQuery
        ? {
            head: { vars: ["player", "playerLabel", "emptyGames"] },
            results: {
              bindings: [{
                player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
                playerLabel: { type: "literal", value: "Example Player" },
                emptyGames: { type: "literal", value: "2", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
              }],
            },
          }
      : {
          head: { vars: ["season", "hits"] },
          results: {
            bindings: [{
              season: { type: "literal", value: "2026" },
              hits: { type: "literal", value: "184", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
            }],
          },
        };
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/sparql-results+json" },
    });
  };
  server = createBaseballServer({ fetchImpl, queryEndpoint: "http://fuseki.test/query" });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  baseUrl = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

function request(path, options = {}) {
  return fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { ...options.headers, Connection: "close" },
  });
}

test("local server reports graph status through its read-only API", async () => {
  const response = await request("/api/status");
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.connected, true);
  assert.equal(payload.games, 9);
  assert.equal(payload.layer, "authoritative");
});

test("derived measures expose semantic contracts and compile only compatible base measures", () => {
  const catalog = buildPublicDerivedMetricCatalog();
  assert.deepEqual(Object.keys(catalog.measures), ["empty_games", "offensive_games_played"]);
  assert.equal(catalog.measures.empty_games.grain, "player-game");
  assert.deepEqual(catalog.measures.empty_games.subsetOf, ["offensive_games_played"]);

  const percentage = compileDerivedMetricQuery({
    numerator: "empty_games",
    denominator: "offensive_games_played",
  });
  assert.equal(percentage.contract.resultKind, "percentage");
  assert.match(percentage.query, /100 \* xsd:decimal\(\?emptyGames\)/u);
  assert.match(percentage.query, /AS \?derivedValue/u);

  const ratio = compileDerivedMetricQuery({
    numerator: "offensive_games_played",
    denominator: "empty_games",
  });
  assert.equal(ratio.contract.resultKind, "ratio");
  assert.throws(
    () => compileDerivedMetricQuery({ numerator: "empty_games", denominator: "empty_games" }),
    /two different base measures/u,
  );
  assert.throws(
    () => compileDerivedMetricQuery({ numerator: "raw_formula", denominator: "empty_games" }),
    /Unknown numerator measure/u,
  );
});

test("date presets resolve against the latest loaded official game date", async () => {
  const response = await request("/api/date-scope?preset=seven_days");
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.scope.startDate, "2026-07-31");
  assert.equal(payload.scope.endDate, "2026-08-06");
  assert.equal(payload.scope.gameCount, 1);
});

test("local server compiles selections instead of accepting raw SPARQL", async () => {
  const response = await request("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      family: "batting",
      dimensions: ["season"],
      metrics: ["hits"],
      sparql: "DROP ALL",
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.meta.rowCount, 1);
  assert.equal(payload.meta.dateScope.preset, "seven_days");
  assert.equal(payload.meta.dateScope.gameCount, 1);
  assert.match(payload.query, /FILTER\(\?graph IN \(<https:\/\/w3id\.org\/baseball\/graph\/game\/823105>\)\)/u);
  assert.match(payload.query, /^PREFIX base:/u);
  assert.doesNotMatch(issuedQueries.at(-1), /DROP ALL/u);
});

test("local server rejects invalid query components", async () => {
  const response = await request("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ family: "batting", metrics: ["DROP ALL"] }),
  });
  assert.equal(response.status, 400);
});

test("local server exposes Empty Games only through its reviewed canned query", async () => {
  const response = await request("/api/canned/empty-games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filters: {
        player: "https://baseballontology.org/data/player/1",
        team: "https://baseballontology.org/data/team/2",
      },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.deepEqual(payload.head.vars, ["player", "playerLabel", "emptyGames"]);
  assert.equal(payload.meta.definition, "reviewed-prototype");
  assert.match(payload.query, /19 source tokens|completeness profile/u);
  assert.match(payload.query, /FILTER\(STRSTARTS\(STR\(\?graph\)/u);
  assert.match(payload.query, /FILTER\(\?player = <https:\/\/baseballontology\.org\/data\/player\/1>\)/u);
  assert.match(payload.query, /FILTER\(\?team = <https:\/\/baseballontology\.org\/data\/team\/2>\)/u);
});

test("local server exposes derived measures and compiles the reviewed percentage", async () => {
  const catalogResponse = await request("/api/derived/catalog");
  assert.equal(catalogResponse.status, 200);
  const catalog = await catalogResponse.json();
  assert.deepEqual(catalog.operations, ["divide"]);
  assert.equal(catalog.measures.offensive_games_played.unit, "player-games");

  const response = await request("/api/derived", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      numerator: "empty_games",
      denominator: "offensive_games_played",
      formula: "DROP ALL",
      filters: { player: "https://baseballontology.org/data/player/1" },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.meta.derivedMetric.resultKind, "percentage");
  assert.equal(payload.meta.derivedMetric.grain, "player-game");
  assert.equal(payload.meta.columnLabels.derivedValue, "Empty Games percentage");
  assert.match(payload.query, /FILTER\(\?player = <https:\/\/baseballontology\.org\/data\/player\/1>\)/u);
  assert.doesNotMatch(payload.query, /DROP ALL/u);
  assert.match(payload.query, /LIMIT 1000/u);
});

test("local server rejects same-measure and unknown derived calculations", async () => {
  const same = await request("/api/derived", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numerator: "empty_games", denominator: "empty_games" }),
  });
  assert.equal(same.status, 400);

  const unknown = await request("/api/derived", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numerator: "sparql", denominator: "empty_games" }),
  });
  assert.equal(unknown.status, 400);
});

test("game-date index is authoritative and compact", () => {
  const query = compileGameDateIndexQuery();
  assert.match(query, /SELECT DISTINCT \?graph \?game/u);
  assert.doesNotMatch(query, /BaseballTimestampICE/u);
  assert.match(query, /graph\/game\//u);
});

test("advanced filters compile to an allowlisted authoritative graph scope", async () => {
  const response = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: "game-action-density",
      filters: {
        season: 2026,
        team: "https://baseballontology.org/data/team/2",
      },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.match(issuedQueries.at(-2), /FILTER\(\?season = 2026\)/u);
  assert.match(issuedQueries.at(-2), /base:HomeTeamRole base:AwayTeamRole/u);
  assert.match(payload.query, /FILTER\(\?graph IN \(<https:\/\/w3id\.org\/baseball\/graph\/game\/823105>\)\)/u);
});

test("special analytics reject arbitrary filter keys", async () => {
  const response = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "hit-diversity", filters: { sparql: "DROP ALL" } }),
  });
  assert.equal(response.status, 400);
});

test("local server rejects malformed custom date scopes", async () => {
  const response = await request("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      family: "games",
      metrics: ["games"],
      dateScope: { preset: "custom", startDate: "2026-08-07", endDate: "2026-08-01" },
    }),
  });
  assert.equal(response.status, 400);
});

test("local server exposes the complete advanced catalog without file paths", async () => {
  const response = await request("/api/advanced/catalog");
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.queries.length, 17);
  assert.equal(payload.blockedAnalytics.length, 4);
  assert.equal(payload.queries[0].id, "plate-appearance-fingerprint");
  assert.equal("path" in payload.queries[0], false);
});

test("local server runs only cataloged advanced queries", async () => {
  const response = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "event-chain-integrity", sparql: "DROP ALL" }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.meta.definition, "integrity-audit");
  assert.match(payload.query, /BatBallContactProcess/u);
  assert.match(payload.query, /LIMIT 1000/u);
  assert.doesNotMatch(issuedQueries.at(-1), /DROP ALL/u);

  const rejected = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "../../ontology/BaseballO.ttl" }),
  });
  assert.equal(rejected.status, 400);
});
