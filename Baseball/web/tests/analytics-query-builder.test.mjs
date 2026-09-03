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
import {
  aggregateEmptyGameEvidence,
  buildPublicEmptyGameCatalog,
  compileEmptyGameDamageOpportunityQuery,
  compileEmptyGameEvidenceQuery,
  scoreEmptyPlateAppearanceDamage,
} from "../query-builder/empty-games-query-builder.js";
import {
  buildQuestionRecipes,
  groupedQuestionRecipes,
  QUESTION_GROUPS,
  QUESTION_RECIPE_COUNTS,
} from "../question-recipes.js";
import { sortBindings } from "../result-sort.js";
import {
  aggregatePaqPlayerAverages,
  applyAdvancedResultFilters,
  buildPublicCatalog,
  compileGameDateIndexQuery,
  createBaseballServer,
} from "../server.mjs";

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
  assert.doesNotMatch(query, /dcterms:(?:type|identifier)/u);
  assert.match(query, /base:FoulBallProcess base:FoulTipProcess/u);
  assert.match(query, /base:FairBallProcess/u);
  assert.match(query, /base:StrikeCallAct/u);
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

test("Empty Games supports player, team, streak, pitcher, game, and damage analyses", () => {
  const catalog = buildPublicEmptyGameCatalog();
  assert.deepEqual(Object.keys(catalog.analyses), ["players", "teams", "stretches", "pitcher_matchups", "games", "damage"]);
  const query = compileEmptyGameEvidenceQuery({
    player: "https://baseballontology.org/data/player/1",
    pitcher: "https://baseballontology.org/data/player/2",
  });
  assert.match(query, /AS \?emptyFlag/u);
  assert.match(query, /FILTER\(\?player = <https:\/\/baseballontology\.org\/data\/player\/1>\)/u);
  assert.match(query, /FILTER\(\?pitcher = <https:\/\/baseballontology\.org\/data\/player\/2>\)/u);
  assert.match(query, /reviewedResultType/u);

  const evidence = { results: { bindings: [
    {
      graph: { value: "https://w3id.org/baseball/graph/game/1" },
      game: { value: "https://baseballontology.org/data/game/1" },
      gameStart: { value: "2026-08-01T19:00:00Z" },
      player: { value: "https://baseballontology.org/data/player/1" },
      playerLabel: { value: "Batter One" },
      team: { value: "https://baseballontology.org/data/team/10" },
      teamLabel: { value: "Team Ten" },
      pitcher: { value: "https://baseballontology.org/data/player/2" },
      pitcherLabel: { value: "Pitcher Two" },
      emptyFlag: { value: "1" },
    },
    {
      graph: { value: "https://w3id.org/baseball/graph/game/2" },
      game: { value: "https://baseballontology.org/data/game/2" },
      gameStart: { value: "2026-08-02T19:00:00Z" },
      player: { value: "https://baseballontology.org/data/player/1" },
      playerLabel: { value: "Batter One" },
      team: { value: "https://baseballontology.org/data/team/10" },
      teamLabel: { value: "Team Ten" },
      pitcher: { value: "https://baseballontology.org/data/player/2" },
      pitcherLabel: { value: "Pitcher Two" },
      emptyFlag: { value: "0" },
    },
  ] } };
  const players = aggregateEmptyGameEvidence(evidence, "players");
  assert.equal(players.results.bindings[0].emptyGames.value, "1");
  assert.equal(players.results.bindings[0].offensiveGamesPlayed.value, "2");
  assert.equal(players.results.bindings[0].emptyGameRatio.value, "0.5000");
  assert.equal(aggregateEmptyGameEvidence(evidence, "stretches").results.bindings[0].emptyGameStreak.value, "1");
  assert.equal(aggregateEmptyGameEvidence(evidence, "pitcher_matchups").results.bindings[0].gamesFaced.value, "2");
});

test("empty-game damage covers every base combination and out count", () => {
  const baseCombinations = [
    [true, false, false],
    [false, true, false],
    [false, false, true],
    [true, true, false],
    [true, false, true],
    [false, true, true],
    [true, true, true],
  ];
  const scores = [];
  for (const outsBefore of [0, 1, 2]) {
    for (const [onFirst, onSecond, onThird] of baseCombinations) {
      const basePressure = Number(onFirst) + (2 * Number(onSecond)) + (3 * Number(onThird));
      const score = scoreEmptyPlateAppearanceDamage({
        outsBefore,
        onFirst,
        onSecond,
        onThird,
        pitches: 3,
        swings: 1,
        contacts: 1,
        fouls: 0,
      });
      assert.equal(score, 100 * (basePressure / 6) * ((outsBefore + 1) / 3));
      scores.push(score);
    }
  }
  assert.equal(scores.length, 21);
  assert.equal(scores.at(-1), 100);
  for (const outsBefore of [0, 1]) {
    for (const [onFirst, onSecond, onThird] of baseCombinations) {
      const ordinary = scoreEmptyPlateAppearanceDamage({
        outsBefore, onFirst, onSecond, onThird, pitches: 3, swings: 1, contacts: 1, fouls: 0,
      });
      const doublePlay = scoreEmptyPlateAppearanceDamage({
        outsBefore, onFirst, onSecond, onThird, pitches: 3, swings: 1, contacts: 1, fouls: 0, doublePlay: true,
      });
      assert.equal(doublePlay, Math.min(100, ordinary * 1.25));
    }
  }
  assert.throws(() => scoreEmptyPlateAppearanceDamage({ outsBefore: 3 }), /0, 1, or 2/u);

  const query = compileEmptyGameDamageOpportunityQuery();
  assert.match(query, /BaserunnerAtBaseStasis/u);
  assert.match(query, /GroundedIntoDoublePlayProcess/u);
  assert.match(query, /COALESCE\(MAX\(\?thirdFlag\), 0\) AS \?onThird/u);
  assert.match(query, /MAX\(IF\(\?failureType IN .* AS \?doublePlay/u);
  assert.doesNotMatch(query, /GROUP BY[^]*\?failureType/u);
});

test("Advanced result filters wrap only declared result variables", () => {
  const source = "PREFIX base: <https://baseballontology.org/>\nSELECT ?batter (COUNT(*) AS ?events) WHERE { ?s ?p ?batter } GROUP BY ?batter";
  const query = applyAdvancedResultFilters(source, { player: "https://baseballontology.org/data/player/1" }, [
    { id: "player", variable: "batter" },
  ]);
  assert.match(query, /SELECT \* WHERE/u);
  assert.match(query, /VALUES \?batter \{ <https:\/\/baseballontology\.org\/data\/player\/1> \}/u);
});

let server;
let baseUrl;
let mockFetchImpl;
const issuedQueries = [];

before(async () => {
  mockFetchImpl = async (_url, options) => {
    const query = new URLSearchParams(options.body).get("query");
    issuedQueries.push(query);
    const statusQuery = query.includes("COUNT(DISTINCT ?game) AS ?games")
      && !query.includes("GROUP BY");
    const emptyGamesQuery = query.includes("AS ?emptyGames");
    const emptyGamesEvidenceQuery = query.includes("AS ?emptyFlag")
      && query.includes("reviewed world-side result classes");
    const damageOpportunityQuery = query.includes("BaserunnerAtBaseStasis")
      && query.includes("AS ?onThird");
    const derivedMetricQuery = query.includes("AS ?derivedValue");
    const graphScopeQuery = query.includes("SELECT DISTINCT ?graph WHERE");
    const dateIndexQuery = query.includes("SELECT DISTINCT ?graph ?game WHERE");
    const payload = statusQuery
      ? {
          head: { vars: ["games"] },
          results: { bindings: [{
            games: { type: "literal", value: "9" },
          }] },
        }
      : dateIndexQuery
        ? {
            head: { vars: ["graph", "game"] },
            results: { bindings: [
              {
                graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" },
                game: { type: "uri", value: "https://baseballontology.org/data/game/823105" },
              },
              {
                graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823443" },
                game: { type: "uri", value: "https://baseballontology.org/data/game/823443" },
              },
            ] },
          }
      : graphScopeQuery
        ? {
            head: { vars: ["graph"] },
            results: { bindings: [{ graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" } }] },
          }
      : emptyGamesEvidenceQuery
        ? {
            head: { vars: ["graph", "game", "gameStart", "player", "playerLabel", "team", "teamLabel", "pitcher", "pitcherLabel", "emptyFlag"] },
            results: { bindings: [{
              graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" },
              game: { type: "uri", value: "https://baseballontology.org/data/game/823105" },
              gameStart: { type: "literal", value: "2026-08-06T19:00:00Z", datatype: "http://www.w3.org/2001/XMLSchema#dateTime" },
              player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
              playerLabel: { type: "literal", value: "Example Player" },
              team: { type: "uri", value: "https://baseballontology.org/data/team/2" },
              teamLabel: { type: "literal", value: "Example Team" },
              pitcher: { type: "uri", value: "https://baseballontology.org/data/player/3" },
              pitcherLabel: { type: "literal", value: "Example Pitcher" },
              emptyFlag: { type: "literal", value: "1", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
            }] },
          }
      : damageOpportunityQuery
        ? {
            head: { vars: ["graph", "game", "gameStart", "player", "playerLabel", "team", "teamLabel", "damagePlateAppearance", "failureTypes", "doublePlay", "outsBefore", "onFirst", "onSecond", "onThird", "pitches", "swings", "contacts", "fouls", "damagePitcher", "damagePitcherLabel"] },
            results: { bindings: [{
              graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/823105" },
              game: { type: "uri", value: "https://baseballontology.org/data/game/823105" },
              gameStart: { type: "literal", value: "2026-08-06T19:00:00Z", datatype: "http://www.w3.org/2001/XMLSchema#dateTime" },
              player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
              playerLabel: { type: "literal", value: "Example Player" },
              team: { type: "uri", value: "https://baseballontology.org/data/team/2" },
              teamLabel: { type: "literal", value: "Example Team" },
              damagePlateAppearance: { type: "uri", value: "https://baseballontology.org/data/game/823105/plate-appearance/7" },
              failureTypes: { type: "literal", value: "BattedBallOutProcess, GroundedIntoDoublePlayProcess" },
              doublePlay: { type: "literal", value: "1", datatype: "http://www.w3.org/2001/XMLSchema#integer" },
              outsBefore: { type: "literal", value: "1" },
              onFirst: { type: "literal", value: "1" },
              onSecond: { type: "literal", value: "1" },
              onThird: { type: "literal", value: "0" },
              pitches: { type: "literal", value: "3" },
              swings: { type: "literal", value: "1" },
              contacts: { type: "literal", value: "1" },
              fouls: { type: "literal", value: "0" },
              damagePitcher: { type: "uri", value: "https://baseballontology.org/data/player/3" },
              damagePitcherLabel: { type: "literal", value: "Example Pitcher" },
            }] },
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
  server = createBaseballServer({
    fetchImpl: mockFetchImpl,
    queryEndpoint: "http://fuseki.test/query",
    servingExecutor: async () => { throw new Error("No test serving build"); },
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  baseUrl = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

test("result columns sort high-to-low first and keep missing values last", () => {
  const rows = [
    { value: { type: "literal", value: "2", datatype: "http://www.w3.org/2001/XMLSchema#integer" } },
    {},
    { value: { type: "literal", value: "10", datatype: "http://www.w3.org/2001/XMLSchema#integer" } },
    { value: { type: "literal", value: "4", datatype: "http://www.w3.org/2001/XMLSchema#integer" } },
  ];
  assert.deepEqual(
    sortBindings(rows, "value", "desc").map((row) => row.value?.value),
    ["10", "4", "2", undefined],
  );
  assert.deepEqual(
    sortBindings(rows, "value", "asc").map((row) => row.value?.value),
    ["2", "4", "10", undefined],
  );
  assert.throws(() => sortBindings(rows, "value", "sideways"), /Unsupported sort direction/u);
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
  assert.equal(payload.service, "baseballo-explorer");
  assert.equal(payload.processId, process.pid);
  assert.match(payload.explorerSourceFingerprint, /^[0-9a-f]{64}$/u);
  assert.equal(payload.connected, true);
  assert.equal(payload.games, 9);
  assert.deepEqual(payload.serving, { available: false });
  assert.equal(payload.layer, "authoritative");
});

test("Explorer separates simple exploration, reviewed questions, and metric building", async () => {
  const pageResponse = await request("/");
  assert.equal(pageResponse.status, 200);
  const page = await pageResponse.text();
  assert.match(page, /Authoritative MLB RDF/u);
  assert.match(page, /Plate Appearance Quality/u);
  assert.match(page, /Explorer mode/u);
  assert.doesNotMatch(page, /More complicated questions/u);
  assert.match(page, /id="question-type"><\/select>/u);
  assert.match(page, /id="scope-disclosure"/u);
  assert.match(page, /id="paq-math"/u);
  assert.match(page, /View this plate appearance/u);
  assert.match(page, /Individual plate appearances/u);
  assert.match(page, /Player averages/u);
  assert.match(page, /\.000–1\.000/u);
  assert.match(page, /id="paq-field-guide"/u);

  const appResponse = await request("/app.js");
  assert.equal(appResponse.status, 200);
  const app = await appResponse.text();
  assert.match(app, /good_at_bat/u);
  assert.match(app, /buildQuestionRecipes/u);
  assert.match(app, /openPlateAppearanceEvidence/u);
  assert.match(app, /averagePlateAppearanceQuality/u);
  assert.match(app, /resultVariables/u);
  assert.match(app, /lastResponse\.head\?\.vars/u);
});

test("every reviewed analysis is exposed as a plain-language question", async () => {
  const catalogResponse = await request("/api/advanced/catalog");
  const { queries } = await catalogResponse.json();
  const recipes = buildQuestionRecipes(queries, buildPublicEmptyGameCatalog());
  assert.equal(queries.length, QUESTION_RECIPE_COUNTS.advancedQueries);
  assert.equal(recipes.length, QUESTION_RECIPE_COUNTS.questions);
  assert.equal(new Set(recipes.map((recipe) => recipe.id)).size, recipes.length);
  assert.ok(recipes.every((recipe) => recipe.label.endsWith("?")));
  assert.deepEqual(
    recipes.filter((recipe) => recipe.queryId === "plate-appearance-fingerprint").map((recipe) => recipe.view),
    ["plate_appearances", "player_averages"],
  );
  assert.equal(recipes.filter((recipe) => recipe.kind === "empty_games").length, 6);
  assert.ok(recipes.every((recipe) => recipe.group && recipe.grain && recipe.calculation));
  const groups = groupedQuestionRecipes(recipes);
  assert.deepEqual(groups.map((group) => group.id), QUESTION_GROUPS.map((group) => group.id));
  assert.deepEqual(groups.flatMap((group) => group.recipes).map((recipe) => recipe.id).sort(),
    recipes.map((recipe) => recipe.id).sort());
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
  assert.equal(payload.scope.gameSet, "regular_season");
});

test("All-Star play is queryable only through its separate game set", async () => {
  const scopeResponse = await request("/api/date-scope?preset=season_to_date&gameSet=all_star");
  assert.equal(scopeResponse.status, 200);
  const scopePayload = await scopeResponse.json();
  assert.equal(scopePayload.scope.startDate, "2026-01-01");
  assert.equal(scopePayload.scope.endDate, "2026-07-14");
  assert.equal(scopePayload.scope.gameCount, 1);
  assert.equal(scopePayload.scope.gameSet, "all_star");

  const response = await request("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      family: "games",
      dimensions: ["venue"],
      metrics: ["games"],
      gameSet: "all_star",
      dateScope: { preset: "season_to_date" },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.meta.dateScope.gameSet, "all_star");
  assert.match(payload.query, /VALUES \?graph \{ <https:\/\/w3id\.org\/baseball\/graph\/game\/823443> \}/u);
  assert.doesNotMatch(payload.query, /graph\/game\/823105/u);

  const optionsResponse = await request("/api/options?family=games&dimension=game&gameSet=all_star");
  assert.equal(optionsResponse.status, 200);
  assert.match(issuedQueries.at(-1), /graph\/game\/823443/u);
  assert.doesNotMatch(issuedQueries.at(-1), /graph\/game\/823105/u);
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
  assert.match(payload.query, /VALUES \?graph \{ <https:\/\/w3id\.org\/baseball\/graph\/game\/823105> \}/u);
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

test("local server exposes reviewed Empty Games ratios and pitcher context", async () => {
  const response = await request("/api/canned/empty-games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      analysis: "players",
      filters: {
        player: "https://baseballontology.org/data/player/1",
        team: "https://baseballontology.org/data/team/2",
      },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.deepEqual(payload.head.vars, [
    "player", "playerLabel", "emptyGames", "offensiveGamesPlayed", "emptyGameRatio", "emptyGamePercentage",
  ]);
  assert.equal(payload.meta.definition, "reviewed-empty-game-analysis");
  assert.equal(payload.results.bindings[0].emptyGameRatio.value, "1.0000");
  assert.match(payload.query, /reviewed world-side result classes/u);
  assert.match(payload.query, /FILTER\(STRSTARTS\(STR\(\?graph\)/u);
  assert.match(payload.query, /FILTER\(\?player = <https:\/\/baseballontology\.org\/data\/player\/1>\)/u);
  assert.match(payload.query, /FILTER\(\?team = <https:\/\/baseballontology\.org\/data\/team\/2>\)/u);

  const matchupResponse = await request("/api/canned/empty-games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      analysis: "pitcher_matchups",
      filters: { pitcher: "https://baseballontology.org/data/player/3" },
    }),
  });
  assert.equal(matchupResponse.status, 200);
  const matchup = await matchupResponse.json();
  assert.equal(matchup.results.bindings[0].pitcherLabel.value, "Example Pitcher");
  assert.match(matchup.query, /FILTER\(\?pitcher = <https:\/\/baseballontology\.org\/data\/player\/3>\)/u);

  const damageResponse = await request("/api/canned/empty-games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis: "damage" }),
  });
  assert.equal(damageResponse.status, 200);
  const damage = await damageResponse.json();
  assert.equal(damage.results.bindings[0].worstBaseState.value, "1B + 2B");
  assert.equal(damage.results.bindings[0].doublePlayFailures.value, "1");
  assert.match(damage.query, /# Damage opportunity evidence/u);
  assert.match(damage.query, /VALUES \(\?graph \?player\) \{/u);
  assert.match(damage.query, /graph\/game\/823105> <https:\/\/baseballontology\.org\/data\/player\/1>/u);
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
  assert.match(payload.query, /VALUES \?graph \{ <https:\/\/w3id\.org\/baseball\/graph\/game\/823105> \}/u);
});

test("advanced queries expose and apply only their declared player and role filters", async () => {
  const catalogResponse = await request("/api/advanced/catalog");
  const catalog = await catalogResponse.json();
  const matchup = catalog.queries.find((entry) => entry.id === "batter-pitcher-matchup-profiles");
  assert.deepEqual(matchup.resultFilters.map((filter) => filter.id), ["player", "pitcher"]);

  const response = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: "batter-pitcher-matchup-profiles",
      filters: { player: "https://baseballontology.org/data/player/1" },
    }),
  });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.match(payload.query, /VALUES \?batter \{ <https:\/\/baseballontology\.org\/data\/player\/1> \}/u);
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
  assert.equal(payload.queries[0].label, "Plate Appearance Quality");
  assert.equal(payload.queries[0].resultFilters.length, 2);
  assert.equal(payload.queries[0].featured, true);
  assert.equal("path" in payload.queries[0], false);
  const goodAtBat = payload.queries.find((entry) => entry.id === "plate-appearance-fingerprint");
  assert.equal(goodAtBat.semanticMode, "decision-support");
  assert.match(goodAtBat.claim, /PAQ-1\.0/u);
  assert.equal(payload.queries.some((entry) => entry.id === "good-at-bat-indicator"), false);
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

  const decisionResponse = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "plate-appearance-fingerprint" }),
  });
  assert.equal(decisionResponse.status, 200);
  const decisionPayload = await decisionResponse.json();
  assert.equal(decisionPayload.meta.definition, "decision-support");
  assert.equal(decisionPayload.meta.route, "Unified PAQ evidence · authoritative fallback");
  assert.deepEqual(decisionPayload.meta.visibleColumns.slice(3, 8), [
    "plateAppearanceQuality", "plateAppearanceQualityBand", "outcomeRating",
    "grindRating", "situationalRating",
  ]);
  assert.equal(decisionPayload.meta.columnOrder.indexOf("goodAtBat") < decisionPayload.meta.columnOrder.indexOf("pitches"), true);
  assert.match(decisionPayload.query, /\?wasHit/u);
  assert.match(decisionPayload.query, /\?pitches/u);
  assert.match(decisionPayload.query, /\?goodAtBat/u);

  const rejected = await request("/api/advanced", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: "../../ontology/BaseballO.ttl" }),
  });
  assert.equal(rejected.status, 400);
});

test("Plate Appearance Quality player averages preserve names and calculate sortable scores", () => {
  const payload = aggregatePaqPlayerAverages({ results: { bindings: [
    {
      batter: { type: "uri", value: "https://baseballontology.org/data/player/1" },
      batterLabel: { type: "literal", value: "Eugenio Suárez" },
      plateAppearanceQuality: { type: "literal", value: "0.900" },
      plateAppearanceQualityBand: { type: "literal", value: "Excellent" },
    },
    {
      batter: { type: "uri", value: "https://baseballontology.org/data/player/1" },
      batterLabel: { type: "literal", value: "Eugenio Suárez" },
      plateAppearanceQuality: { type: "literal", value: "0.600" },
      plateAppearanceQualityBand: { type: "literal", value: "Mixed" },
    },
    {
      batter: { type: "uri", value: "https://baseballontology.org/data/player/2" },
      batterLabel: { type: "literal", value: "Aaron Judge" },
      plateAppearanceQuality: { type: "literal", value: "0.700" },
      plateAppearanceQualityBand: { type: "literal", value: "Good" },
    },
  ] } });
  assert.equal(payload.results.bindings[0].playerLabel.value, "Eugenio Suárez");
  assert.equal(payload.results.bindings[0].averagePlateAppearanceQuality.value, "0.750");
  assert.equal(payload.results.bindings[0].plateAppearances.value, "2");
  assert.equal(payload.results.bindings[0].excellentPlateAppearances.value, "1");
  assert.equal(payload.results.bindings[0].mixedPlateAppearances.value, "1");
});

test("Plate Appearance Quality uses a validated materialized executor without touching Fuseki", async () => {
  const before = issuedQueries.length;
  const servingInputs = [];
  const materializedServer = createBaseballServer({
    fetchImpl: mockFetchImpl,
    queryEndpoint: "http://fuseki.test/query",
    servingExecutor: async (input) => {
      servingInputs.push(input);
      const playerAverages = input.view === "player_averages";
      return {
        head: { vars: playerAverages
          ? ["player", "playerLabel", "plateAppearances", "averagePlateAppearanceQuality"]
          : ["game", "plateAppearance", "batterLabel", "plateAppearanceQuality", "plateAppearanceQualityBand"] },
        results: { bindings: [playerAverages ? {
          player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
          playerLabel: { type: "literal", value: "Eugenio Suárez" },
          plateAppearances: { type: "literal", datatype: "http://www.w3.org/2001/XMLSchema#integer", value: "8" },
          averagePlateAppearanceQuality: { type: "literal", datatype: "http://www.w3.org/2001/XMLSchema#decimal", value: "0.812" },
        } : {
          game: { type: "uri", value: "https://baseballontology.org/data/game/823105" },
          plateAppearance: { type: "uri", value: "https://baseballontology.org/data/plate-appearance/823105/1" },
          batterLabel: { type: "literal", value: "Eugenio Suárez" },
          plateAppearanceQuality: { type: "literal", datatype: "http://www.w3.org/2001/XMLSchema#decimal", value: "0.812" },
          plateAppearanceQualityBand: { type: "literal", value: "Good" },
        }] },
        query: "-- reviewed materialized SQL",
        serving: {
          durationMs: 0.4,
          buildId: "build-1",
          corpusFingerprint: "f".repeat(64),
          dateScope: { ...input.dateScope, gameSet: input.gameSet, gameCount: 1 },
          coverage: { advancedQueries: 17, advancedBindings: 1234 },
        },
      };
    },
  });
  await new Promise((resolve) => materializedServer.listen(0, "127.0.0.1", resolve));
  try {
    const address = materializedServer.address();
    const response = await fetch(`http://127.0.0.1:${address.port}/api/advanced`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ id: "plate-appearance-fingerprint", dateScope: { preset: "seven_days" } }),
    });
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.meta.layer, "materialized");
    assert.equal(payload.meta.route, "Materialized SQL · Plate Appearance Quality");
    assert.equal(payload.meta.servingBuildId, "build-1");
    assert.equal(payload.results.bindings.length, 1);
    assert.equal(payload.results.bindings[0].batterLabel.value, "Eugenio Suárez");
    assert.equal(servingInputs[0].view, "plate_appearances");
    assert.equal(issuedQueries.length, before);

    const reviewedResponse = await fetch(`http://127.0.0.1:${address.port}/api/advanced`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ id: "swing-to-result-funnel", dateScope: { preset: "thirty_days" } }),
    });
    assert.equal(reviewedResponse.status, 200);
    const reviewed = await reviewedResponse.json();
    assert.equal(reviewed.meta.layer, "materialized");
    assert.equal(reviewed.meta.route, "Materialized SQL · Swing-to-result conversion");
    assert.deepEqual(reviewed.meta.servingCoverage, { advancedQueries: 17, advancedBindings: 1234 });
    assert.equal(servingInputs[1].id, "swing-to-result-funnel");
    assert.equal("view" in servingInputs[1], false);
    assert.equal(issuedQueries.length, before);

    const averagesResponse = await fetch(`http://127.0.0.1:${address.port}/api/advanced`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ id: "plate-appearance-fingerprint", view: "player_averages" }),
    });
    assert.equal(averagesResponse.status, 200);
    const averages = await averagesResponse.json();
    assert.equal(averages.meta.view, "player_averages");
    assert.deepEqual(averages.meta.visibleColumns.slice(0, 3), [
      "playerLabel", "averagePlateAppearanceQuality", "plateAppearances",
    ]);
    assert.equal(averages.results.bindings[0].playerLabel.value, "Eugenio Suárez");
    assert.equal(servingInputs[2].view, "player_averages");
    assert.equal(issuedQueries.length, before);

    const forcedResponse = await fetch(`http://127.0.0.1:${address.port}/api/advanced`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-BaseballO-Force-Authoritative": "true",
        Connection: "close",
      },
      body: JSON.stringify({ id: "plate-appearance-fingerprint", dateScope: { preset: "one_day" } }),
    });
    assert.equal(forcedResponse.status, 200);
    const forced = await forcedResponse.json();
    assert.equal(forced.meta.layer, "unified");
    assert.equal(servingInputs.length, 3);
    assert.ok(issuedQueries.length > before);
  } finally {
    await new Promise((resolve, reject) => materializedServer.close((error) => error ? reject(error) : resolve()));
  }
});

test("routine routes delegate to the materialized adapter while admission remains adapter-owned", async () => {
  const before = issuedQueries.length;
  const common = {
    durationMs: 0.2,
    buildId: "build-5",
    corpusFingerprint: "e".repeat(64),
    dateScope: { preset: "seven_days", gameSet: "regular_season", gameCount: 1 },
    coverage: { advancedQueries: 17, battingResults: 79, pitches: 282, emptyPlayerGames: 22 },
  };
  const materializedServer = createBaseballServer({
    fetchImpl: mockFetchImpl,
    queryEndpoint: "http://fuseki.test/query",
    servingExecutor: async (input) => {
      if (input.route === "options") return {
        head: { vars: ["player", "playerLabel"] },
        results: { bindings: [{
          player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
          playerLabel: { type: "literal", value: "Player One" },
        }] }, query: "-- options SQL", serving: { ...common, view: "options" },
      };
      if (input.route === "explore") return {
        head: { vars: ["season", "hits"] },
        results: { bindings: [{
          season: { type: "literal", value: "2026" },
          hits: { type: "literal", value: "10" },
        }] }, query: "-- explore SQL", serving: { ...common, view: "explore" },
      };
      if (input.route === "empty-games") return {
        head: { vars: ["graph", "game", "gameStart", "player", "playerLabel", "team", "teamLabel", "emptyFlag"] },
        results: { bindings: [{
          graph: { type: "uri", value: "https://w3id.org/baseball/graph/game/1" },
          game: { type: "uri", value: "https://baseballontology.org/data/game/1" },
          gameStart: { type: "literal", value: "2026-08-01T19:00:00Z" },
          player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
          playerLabel: { type: "literal", value: "Player One" },
          team: { type: "uri", value: "https://baseballontology.org/data/team/1" },
          teamLabel: { type: "literal", value: "Team One" },
          emptyFlag: { type: "literal", value: "1" },
        }] }, query: "-- empty SQL", serving: { ...common, view: "empty_games" },
      };
      if (input.route === "derived") return {
        head: { vars: ["player", "playerLabel", "emptyGames", "offensiveGamesPlayed", "derivedValue"] },
        results: { bindings: [{
          player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
          playerLabel: { type: "literal", value: "Player One" },
          emptyGames: { type: "literal", value: "1" },
          offensiveGamesPlayed: { type: "literal", value: "2" },
          derivedValue: { type: "literal", value: "50.0" },
        }] }, query: "-- derived SQL", serving: { ...common, view: "derived" },
      };
      throw new Error("Unexpected serving request");
    },
  });
  await new Promise((resolve) => materializedServer.listen(0, "127.0.0.1", resolve));
  try {
    const address = materializedServer.address();
    const url = `http://127.0.0.1:${address.port}`;
    const explore = await fetch(`${url}/api/query`, {
      method: "POST", headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ family: "batting", dimensions: ["season"], metrics: ["hits"] }),
    }).then((response) => response.json());
    assert.equal(explore.meta.layer, "materialized");
    assert.equal(explore.results.bindings[0].hits.value, "10");
    const options = await fetch(`${url}/api/options?family=batting&dimension=player`, {
      headers: { Connection: "close" },
    }).then((response) => response.json());
    assert.equal(options.layer, "materialized");
    assert.equal(options.options[0].label, "Player One");
    const empty = await fetch(`${url}/api/canned/empty-games`, {
      method: "POST", headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ analysis: "players" }),
    }).then((response) => response.json());
    assert.equal(empty.meta.layer, "materialized");
    assert.equal(empty.results.bindings[0].emptyGames.value, "1");
    const derived = await fetch(`${url}/api/derived`, {
      method: "POST", headers: { "Content-Type": "application/json", Connection: "close" },
      body: JSON.stringify({ numerator: "empty_games", denominator: "offensive_games_played" }),
    }).then((response) => response.json());
    assert.equal(derived.meta.layer, "materialized");
    assert.equal(derived.results.bindings[0].derivedValue.value, "50.0");
    assert.equal(issuedQueries.length, before);
  } finally {
    await new Promise((resolve, reject) => materializedServer.close((error) => error ? reject(error) : resolve()));
  }
});

test("equivalence requests use the isolated candidate SQL executor", async () => {
  let normalCalls = 0;
  let candidateCalls = 0;
  const candidateServer = createBaseballServer({
    fetchImpl: async () => { throw new Error("Candidate SQL must not touch Fuseki"); },
    queryEndpoint: "http://fuseki.test/query",
    servingExecutor: async () => {
      normalCalls += 1;
      throw new Error("Normal serving executor must not receive candidate proof requests");
    },
    candidateServingExecutor: async (input) => {
      candidateCalls += 1;
      return {
        head: { vars: ["player", "hits"] },
        results: { bindings: [{
          player: { type: "uri", value: "https://baseballontology.org/data/player/1" },
          hits: { type: "literal", value: "3" },
        }] },
        query: "-- candidate SQL",
        serving: {
          durationMs: 0.1,
          buildId: "candidate-build",
          corpusFingerprint: "c".repeat(64),
          dateScope: { preset: "one_day", gameSet: "regular_season", gameCount: 1 },
          coverage: {},
        },
      };
    },
    equivalenceToken: "test-equivalence-token",
  });
  await new Promise((resolve) => candidateServer.listen(0, "127.0.0.1", resolve));
  try {
    const address = candidateServer.address();
    const unauthorized = await fetch(`http://127.0.0.1:${address.port}/api/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-BaseballO-Use-Candidate-Sql": "true",
        "X-BaseballO-Require-Materialized": "true",
        Connection: "close",
      },
      body: JSON.stringify({ family: "batting", dimensions: ["player"], metrics: ["hits"] }),
    });
    assert.equal(unauthorized.status, 503);
    assert.equal(candidateCalls, 0);
    assert.equal(normalCalls, 0);

    const response = await fetch(`http://127.0.0.1:${address.port}/api/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-BaseballO-Use-Candidate-Sql": "true",
        "X-BaseballO-Require-Materialized": "true",
        "X-BaseballO-Equivalence-Token": "test-equivalence-token",
        Connection: "close",
      },
      body: JSON.stringify({ family: "batting", dimensions: ["player"], metrics: ["hits"] }),
    });
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(payload.meta.layer, "materialized");
    assert.equal(payload.meta.servingBuildId, "candidate-build");
    assert.equal(candidateCalls, 1);
    assert.equal(normalCalls, 0);
  } finally {
    await new Promise((resolve, reject) => candidateServer.close((error) => error ? reject(error) : resolve()));
  }
});

test("acceptance requests fail closed without touching Fuseki when SQL is unavailable", async () => {
  let fusekiRequests = 0;
  const failClosedServer = createBaseballServer({
    fetchImpl: async () => {
      fusekiRequests += 1;
      throw new Error("Acceptance must not reach Fuseki");
    },
    queryEndpoint: "http://fuseki.test/query",
    servingExecutor: async () => { throw new Error("No compatible serving build"); },
  });
  await new Promise((resolve) => failClosedServer.listen(0, "127.0.0.1", resolve));
  try {
    const address = failClosedServer.address();
    const url = `http://127.0.0.1:${address.port}`;
    const requests = [
      ["/api/options?family=batting&dimension=player", undefined],
      ["/api/canned/empty-games", { analysis: "players" }],
      ["/api/derived", { numerator: "empty_games", denominator: "offensive_games_played" }],
      ["/api/advanced", { id: "swing-to-result-funnel" }],
      ["/api/query", { family: "batting", dimensions: ["player"], metrics: ["hits"] }],
    ];
    for (const [path, body] of requests) {
      const response = await fetch(`${url}${path}`, {
        method: body ? "POST" : "GET",
        headers: {
          ...(body ? { "Content-Type": "application/json" } : {}),
          "X-BaseballO-Require-Materialized": "true",
          Connection: "close",
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      assert.equal(response.status, 503);
      const payload = await response.json();
      assert.equal(payload.code, "materialized-serving-unavailable");
    }
    assert.equal(fusekiRequests, 0);
  } finally {
    await new Promise((resolve, reject) => failClosedServer.close((error) => error ? reject(error) : resolve()));
  }
});
