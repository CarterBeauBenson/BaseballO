import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import {
  ANALYTICS_QUERY_FAMILIES,
  compileAnalyticsQuery,
} from "../query-builder/analytics-query-builder.js";
import { buildPublicCatalog, createBaseballServer } from "../server.mjs";

test("public catalog exposes labels without SPARQL implementation details", () => {
  const catalog = buildPublicCatalog();
  assert.deepEqual(Object.keys(catalog), ["batting", "pitching", "baserunning", "games"]);
  assert.equal(catalog.batting.metrics.hits.label, "Hits");
  assert.equal(catalog.batting.dimensions.player.hasOptions, true);
  assert.equal("corePatterns" in catalog.batting, false);
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
    const payload = statusQuery
      ? {
          head: { vars: ["games"] },
          results: { bindings: [{ games: { type: "literal", value: "9" } }] },
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

test("local server reports graph status through its read-only API", async () => {
  const response = await fetch(`${baseUrl}/api/status`);
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.connected, true);
  assert.equal(payload.games, 9);
  assert.equal(payload.layer, "authoritative");
});

test("local server compiles selections instead of accepting raw SPARQL", async () => {
  const response = await fetch(`${baseUrl}/api/query`, {
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
  assert.match(payload.query, /^PREFIX base:/u);
  assert.doesNotMatch(issuedQueries.at(-1), /DROP ALL/u);
});

test("local server rejects invalid query components", async () => {
  const response = await fetch(`${baseUrl}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ family: "batting", metrics: ["DROP ALL"] }),
  });
  assert.equal(response.status, 400);
});

test("local server exposes Empty Games only through its reviewed canned query", async () => {
  const response = await fetch(`${baseUrl}/api/canned/empty-games`);
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.deepEqual(payload.head.vars, ["player", "playerLabel", "emptyGames"]);
  assert.equal(payload.meta.definition, "reviewed-prototype");
  assert.match(payload.query, /19 source tokens|completeness profile/u);
  assert.match(payload.query, /FILTER\(STRSTARTS\(STR\(\?graph\)/u);
});

test("local server exposes the complete advanced catalog without file paths", async () => {
  const response = await fetch(`${baseUrl}/api/advanced/catalog`);
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.queries.length, 16);
  assert.equal(payload.blockedAnalytics.length, 4);
  assert.equal(payload.queries[0].id, "plate-appearance-fingerprint");
  assert.equal("path" in payload.queries[0], false);
});

test("local server runs only cataloged advanced queries", async () => {
  const response = await fetch(`${baseUrl}/api/advanced`, {
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

  const rejected = await fetch(`${baseUrl}/api/advanced`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "../../ontology/BaseballO.ttl" }),
  });
  assert.equal(rejected.status, 400);
});
