import { createServer } from "node:http";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { readFile, readdir } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import {
  ANALYTICS_QUERY_FAMILIES,
  compileAnalyticsQuery,
} from "./query-builder/analytics-query-builder.js";
import {
  buildPublicDerivedMetricCatalog,
  compileDerivedMetricQuery,
} from "./query-builder/derived-metric-query-builder.js";
import {
  EMPTY_GAME_ANALYSES,
  aggregateEmptyGameEvidence,
  buildPublicEmptyGameCatalog,
  compileEmptyGameDamageOpportunityQuery,
  compileEmptyGameEvidenceQuery,
} from "./query-builder/empty-games-query-builder.js";

const WEB_ROOT = dirname(fileURLToPath(import.meta.url));
const QUERY_BUILDER_ROOT = resolve(WEB_ROOT, "query-builder");
const OPTIONS_ROOT = resolve(WEB_ROOT, "..", "sparql", "options");
const ADVANCED_QUERY_ROOT = resolve(WEB_ROOT, "..", "sparql", "advanced");
const ADVANCED_QUERY_CATALOG = resolve(ADVANCED_QUERY_ROOT, "advanced-query-catalog.json");
const SERVING_QUERY_SCRIPT = resolve(WEB_ROOT, "..", "scripts", "pipeline", "query-serving-layer.py");
const RAW_SAMPLES_ROOT = resolve(WEB_ROOT, "..", "data", "raw", "samples");
const RAW_FIXTURE = resolve(WEB_ROOT, "..", "data", "raw", "game-566279.json");
const LOCAL_STATE_ROOT = process.env.BASEBALLO_STATE_ROOT
  ?? (process.env.LOCALAPPDATA ? resolve(process.env.LOCALAPPDATA, "BaseballO", "state") : null);
const DEFAULT_QUERY_ENDPOINT = "http://127.0.0.1:3031/baseball-dev/query";
const AUTHORITATIVE_GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/";
const AUTHORITATIVE_GRAPH_GUARD = `FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))`;
const DATA_IRI_PREFIX = "https://baseballontology.org/data/";
const XSD = "http://www.w3.org/2001/XMLSchema#";
const MAX_BODY_BYTES = 64 * 1024;
const MAX_RESULTS = 1000;
const GOOD_AT_BAT_QUERY_ID = "plate-appearance-fingerprint";
const GAME_DATE_INDEX_TTL_MS = 30_000;
const RESULT_CACHE_TTL_MS = 30_000;
const RESULT_CACHE_LIMIT = 100;
const REQUIRE_MATERIALIZED_HEADER = "x-baseballo-require-materialized";
const DATE_SCOPE_PRESETS = new Set(["one_day", "seven_days", "thirty_days", "season_to_date", "custom"]);
const GAME_SETS = new Set(["regular_season", "all_star"]);
const EXPLORER_RUNTIME_SOURCE_PATHS = [
  resolve(WEB_ROOT, "server.mjs"),
  resolve(QUERY_BUILDER_ROOT, "analytics-query-builder.js"),
  resolve(QUERY_BUILDER_ROOT, "derived-metric-query-builder.js"),
  resolve(QUERY_BUILDER_ROOT, "empty-games-query-builder.js"),
];
const explorerSourceHashes = await Promise.all(EXPLORER_RUNTIME_SOURCE_PATHS.map(async (path) =>
  createHash("sha256").update(await readFile(path)).digest("hex")));
const EXPLORER_SOURCE_FINGERPRINT = createHash("sha256")
  .update(explorerSourceHashes.join("\n"), "utf8")
  .digest("hex");
const ADVANCED_PRESENTATION = Object.freeze({
  "plate-appearance-fingerprint": Object.freeze({
    featured: true,
    visibleColumns: [
      "batterLabel", "pitcherLabel", "outcome", "plateAppearanceQuality",
      "plateAppearanceQualityBand", "outcomeRating", "grindRating",
      "situationalRating",
    ],
    playerAverageColumns: [
      "playerLabel", "averagePlateAppearanceQuality", "plateAppearances",
      "excellentPlateAppearances", "goodPlateAppearances", "mixedPlateAppearances",
      "poorPlateAppearances", "badPlateAppearances",
    ],
    columnOrder: [
      "game", "plateAppearance", "batterLabel", "pitcherLabel", "outcome", "wasHit", "hitType",
      "goodAtBat", "pitches", "swings", "contacts", "balls", "strikes",
      "fouls", "foulTips", "runnerRuns", "runnerOuts", "safeResolutions",
    ],
    columnLabels: {
      wasHit: "Hit",
      goodAtBat: "Good at bat",
      plateAppearanceQuality: "PAQ",
      averagePlateAppearanceQuality: "Average PAQ",
      plateAppearanceQualityBand: "Rating",
      plateAppearances: "Plate appearances",
      excellentPlateAppearances: "Excellent",
      goodPlateAppearances: "Good",
      mixedPlateAppearances: "Mixed",
      poorPlateAppearances: "Poor",
      badPlateAppearances: "Bad",
      outcomeRating: "Outcome",
      grindRating: "Grind",
      situationalRating: "Situation",
      productiveOtherRunner: "Advanced another runner",
      goodAtBatEvidenceCount: "Good-at-bat evidence count",
    },
  }),
});
const STATIC_FILES = new Map([
  ["/", "index.html"],
  ["/index.html", "index.html"],
  ["/app.js", "app.js"],
  ["/result-sort.js", "result-sort.js"],
  ["/styles.css", "styles.css"],
]);
const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

function responseHeaders(contentType) {
  return {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; connect-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    "Content-Type": contentType,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
  };
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, responseHeaders("application/json; charset=utf-8"));
  response.end(JSON.stringify(payload));
}

function rejectMaterializedFallback(request, response) {
  if (request.headers[REQUIRE_MATERIALIZED_HEADER] !== "true") return false;
  sendJson(response, 503, {
    error: "The materialized serving layer is required but unavailable.",
    code: "materialized-serving-unavailable",
  });
  return true;
}

async function executeServingQuery(input) {
  if (!LOCAL_STATE_ROOT) throw new Error("No local BaseballO state root is configured.");
  const python = process.env.BASEBALLO_PYTHON ?? "python";
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn(python, [SERVING_QUERY_SCRIPT, "--state-root", LOCAL_STATE_ROOT], {
      cwd: resolve(WEB_ROOT, ".."),
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
      if (stdout.length > 16 * 1024 * 1024) child.kill();
    });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", rejectPromise);
    child.on("close", (code) => {
      try {
        const payload = JSON.parse(stdout);
        if (code !== 0 || payload.status === "unavailable") {
          rejectPromise(new Error(payload.error ?? stderr ?? "Serving query failed."));
          return;
        }
        resolvePromise(payload);
      } catch (error) {
        rejectPromise(error);
      }
    });
    child.stdin.end(JSON.stringify(input));
  });
}

function publicError(error) {
  if (error?.cause?.code === "ECONNREFUSED" || error?.code === "ECONNREFUSED") {
    return { status: 503, message: "The local graph database is not available." };
  }
  if (error instanceof RangeError || error instanceof TypeError) {
    return { status: 400, message: error.message };
  }
  if (error?.name === "AbortError" || error?.name === "TimeoutError") {
    return { status: 504, message: "The graph query timed out." };
  }
  return { status: 500, message: "The local explorer could not complete the request." };
}

function requireFamily(familyId) {
  const definition = ANALYTICS_QUERY_FAMILIES[familyId];
  if (!definition) {
    throw new RangeError(`Unknown query family: ${familyId}`);
  }
  return definition;
}

function requireDimension(familyId, dimensionId) {
  const family = requireFamily(familyId);
  const dimension = family.dimensions[dimensionId];
  if (!dimension) {
    throw new RangeError(`Unknown ${familyId} dimension: ${dimensionId}`);
  }
  return dimension;
}

function advancedLabel(queryId) {
  return queryId
    .split("-")
    .map((word) => word === "pa" ? "PA" : word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function aggregatePaqPlayerAverages(payload) {
  const players = new Map();
  for (const binding of payload.results?.bindings ?? []) {
    const player = binding.batter;
    const score = Number(binding.plateAppearanceQuality?.value);
    if (!player?.value || !Number.isFinite(score)) continue;
    const key = player.value;
    const aggregate = players.get(key) ?? {
      player,
      playerLabel: binding.batterLabel ?? { type: "literal", value: key.split("/").at(-1) },
      plateAppearances: 0,
      scoreTotal: 0,
      bands: { Excellent: 0, Good: 0, Mixed: 0, Poor: 0, Bad: 0 },
    };
    aggregate.plateAppearances += 1;
    aggregate.scoreTotal += score;
    const band = binding.plateAppearanceQualityBand?.value;
    if (Object.hasOwn(aggregate.bands, band)) aggregate.bands[band] += 1;
    players.set(key, aggregate);
  }
  const integer = (value) => ({ type: "literal", datatype: `${XSD}integer`, value: String(value) });
  const bindings = [...players.values()]
    .sort((left, right) => (right.scoreTotal / right.plateAppearances) - (left.scoreTotal / left.plateAppearances)
      || left.playerLabel.value.localeCompare(right.playerLabel.value))
    .slice(0, MAX_RESULTS)
    .map((aggregate) => ({
      player: aggregate.player,
      playerLabel: aggregate.playerLabel,
      plateAppearances: integer(aggregate.plateAppearances),
      averagePlateAppearanceQuality: {
        type: "literal",
        datatype: `${XSD}decimal`,
        value: (aggregate.scoreTotal / aggregate.plateAppearances).toFixed(3),
      },
      excellentPlateAppearances: integer(aggregate.bands.Excellent),
      goodPlateAppearances: integer(aggregate.bands.Good),
      mixedPlateAppearances: integer(aggregate.bands.Mixed),
      poorPlateAppearances: integer(aggregate.bands.Poor),
      badPlateAppearances: integer(aggregate.bands.Bad),
    }));
  return {
    head: { vars: [
      "player", "playerLabel", "plateAppearances", "averagePlateAppearanceQuality",
      "excellentPlateAppearances", "goodPlateAppearances", "mixedPlateAppearances",
      "poorPlateAppearances", "badPlateAppearances",
    ] },
    results: { bindings },
  };
}

async function readAdvancedCatalog() {
  const catalog = JSON.parse(await readFile(ADVANCED_QUERY_CATALOG, "utf8"));
  if (catalog.artifactType !== "baseball-advanced-semantic-query-catalog"
      || !Array.isArray(catalog.queries)
      || catalog.queries.length !== 17) {
    throw new Error("The advanced-query catalog is invalid.");
  }
  return catalog;
}

function publicAdvancedEntry(entry) {
  const presentation = ADVANCED_PRESENTATION[entry.id] ?? {};
  return {
    id: entry.id,
    label: entry.label ?? advancedLabel(entry.id),
    claim: entry.claim,
    semanticMode: entry.semanticMode,
    allowZeroRows: entry.allowZeroRows,
    resultFilters: entry.resultFilters ?? [],
    featured: presentation.featured === true,
  };
}

function resolveAdvancedQueryPath(entry) {
  const candidate = resolve(WEB_ROOT, "..", entry.path);
  const allowedPrefix = `${ADVANCED_QUERY_ROOT}${sep}`;
  if (!candidate.startsWith(allowedPrefix) || extname(candidate) !== ".rq") {
    throw new RangeError("The advanced query is outside the allowlist.");
  }
  return candidate;
}

export function buildPublicCatalog() {
  return Object.fromEntries(
    Object.entries(ANALYTICS_QUERY_FAMILIES).map(([familyId, family]) => [
      familyId,
      {
        label: family.label,
        description: family.description,
        dimensions: Object.fromEntries(
          Object.entries(family.dimensions).map(([dimensionId, dimension]) => [
            dimensionId,
            {
              label: dimension.label,
              input: dimension.input,
              hasOptions: Boolean(dimension.optionsQuery || dimension.values),
            },
          ]),
        ),
        metrics: Object.fromEntries(
          Object.entries(family.metrics).map(([metricId, metric]) => [
            metricId,
            { label: metric.label, description: metric.description },
          ]),
        ),
      },
    ]),
  );
}

async function readJsonBody(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      throw new RangeError("The request is too large.");
    }
    chunks.push(chunk);
  }
  if (chunks.length === 0) {
    throw new TypeError("A JSON request body is required.");
  }
  let value;
  try {
    value = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new TypeError("The request body must be valid JSON.");
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("The request body must be a JSON object.");
  }
  return value;
}

async function executeSparql(query, { fetchImpl, queryEndpoint }) {
  const startedAt = performance.now();
  const response = await fetchImpl(queryEndpoint, {
    method: "POST",
    headers: {
      Accept: "application/sparql-results+json",
      "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    },
    body: new URLSearchParams({ query }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) {
    const details = (await response.text()).replace(/\s+/gu, " ").slice(0, 240);
    throw new Error(`Fuseki returned ${response.status}: ${details}`);
  }
  return {
    payload: await response.json(),
    durationMs: Math.round((performance.now() - startedAt) * 10) / 10,
  };
}

function optionLabel(dimensionId, binding, value) {
  if (dimensionId === "game") {
    const dateValue = binding.gameStart?.value;
    const date = dateValue
      ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(dateValue))
      : "Unknown date";
    const gameId = value.split("/").filter(Boolean).at(-1);
    const venue = binding.venueLabel?.value ?? "Unknown venue";
    return `${date} · ${venue} · Game ${gameId}`;
  }
  const labelKey = `${dimensionId.replace(/_([a-z])/gu, (_, letter) => letter.toUpperCase())}Label`;
  return binding[labelKey]?.value
    ?? binding.playerLabel?.value
    ?? String(value).replaceAll("_", " ");
}

function mapOptions(dimensionId, dimension, payload) {
  if (dimension.values) {
    return dimension.values.map((value) => ({
      value,
      label: value.charAt(0).toUpperCase() + value.slice(1),
    }));
  }
  const valueKey = dimension.variable.replace(/^\?/u, "");
  return (payload.results?.bindings ?? []).flatMap((binding) => {
    const value = binding[valueKey]?.value;
    return value === undefined ? [] : [{ value, label: optionLabel(dimensionId, binding, value) }];
  });
}

function resolveOptionsPath(relativePath) {
  const candidate = resolve(QUERY_BUILDER_ROOT, relativePath);
  const allowedPrefix = `${OPTIONS_ROOT}${sep}`;
  if (candidate !== OPTIONS_ROOT && !candidate.startsWith(allowedPrefix)) {
    throw new RangeError("The requested option source is outside the allowlist.");
  }
  return candidate;
}

function normalizeQueryRequest(value) {
  const limit = value.limit === undefined ? 250 : value.limit;
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_RESULTS) {
    throw new TypeError(`limit must be an integer between 1 and ${MAX_RESULTS}`);
  }
  if (value.offset !== undefined && (!Number.isInteger(value.offset) || value.offset < 0 || value.offset > 100_000)) {
    throw new TypeError("offset must be an integer between 0 and 100000");
  }
  return { ...value, limit };
}

function isoDate(value, fieldName) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/u.test(value)) {
    throw new TypeError(`${fieldName} must use YYYY-MM-DD`);
  }
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value) {
    throw new TypeError(`${fieldName} must be a real calendar date`);
  }
  return value;
}

function normalizeDateScope(value) {
  if (value === undefined) return { preset: "seven_days" };
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("dateScope must be an object");
  }
  const preset = value.preset ?? "seven_days";
  if (!DATE_SCOPE_PRESETS.has(preset)) throw new RangeError(`Unsupported date preset: ${preset}`);
  if (preset !== "custom") return { preset };
  const startDate = isoDate(value.startDate, "startDate");
  const endDate = isoDate(value.endDate, "endDate");
  if (startDate > endDate) throw new RangeError("startDate must not be after endDate");
  return { preset, startDate, endDate };
}

function normalizeGameSet(value) {
  const gameSet = value ?? "regular_season";
  if (!GAME_SETS.has(gameSet)) throw new RangeError(`Unsupported game set: ${gameSet}`);
  return gameSet;
}

function shiftIsoDate(value, days) {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function compileGameDateIndexQuery() {
  return `PREFIX base: <https://baseballontology.org/>

SELECT DISTINCT ?graph ?game WHERE {
  GRAPH ?graph {
    ?game a base:BaseballGame .
  }
  ${AUTHORITATIVE_GRAPH_GUARD}
}
ORDER BY ?graph`;
}

export async function readOfficialGameMetadata() {
  const metadata = new Map();
  const directories = await readdir(RAW_SAMPLES_ROOT, { withFileTypes: true });
  await Promise.all(directories.filter((entry) => entry.isDirectory()).map(async (entry) => {
    const schedule = JSON.parse(await readFile(resolve(RAW_SAMPLES_ROOT, entry.name, "schedule.json"), "utf8"));
    for (const dateBlock of schedule.dates ?? []) {
      for (const game of dateBlock.games ?? []) {
        if (Number.isInteger(game.gamePk) && /^\d{4}-\d{2}-\d{2}$/u.test(game.officialDate ?? "")) {
          metadata.set(String(game.gamePk), {
            date: game.officialDate,
            gameSet: game.gameType === "R" ? "regular_season" : game.gameType === "A" ? "all_star" : "other",
            gameType: game.gameType ?? "",
            description: game.description ?? game.seriesDescription ?? "",
          });
        }
      }
    }
  }));
  const fixture = JSON.parse(await readFile(RAW_FIXTURE, "utf8"));
  const fixtureId = fixture.gamePk ?? fixture.gameData?.game?.pk;
  const fixtureDate = fixture.gameData?.datetime?.officialDate;
  if (Number.isInteger(fixtureId) && /^\d{4}-\d{2}-\d{2}$/u.test(fixtureDate ?? "")) {
    metadata.set(String(fixtureId), { date: fixtureDate, gameSet: "fixture", gameType: "fixture", description: "Development fixture" });
  }
  if (LOCAL_STATE_ROOT) {
    const acquisitionRoot = resolve(LOCAL_STATE_ROOT, "pipeline", "manifests", "acquisition", "games");
    async function visit(directory) {
      let entries;
      try {
        entries = await readdir(directory, { withFileTypes: true });
      } catch {
        return;
      }
      await Promise.all(entries.map(async (entry) => {
        const path = resolve(directory, entry.name);
        if (entry.isDirectory()) {
          await visit(path);
          return;
        }
        if (!entry.isFile() || extname(entry.name) !== ".json") return;
        try {
          const manifest = JSON.parse((await readFile(path, "utf8")).replace(/^\uFEFF/u, ""));
          const gameId = String(manifest.gamePk ?? "");
          if (/^\d+$/u.test(gameId) && /^\d{4}-\d{2}-\d{2}$/u.test(manifest.scheduleDate ?? "")) {
            const existing = metadata.get(gameId);
            metadata.set(gameId, {
              date: manifest.scheduleDate,
              gameSet: manifest.gameType === "A"
                ? "all_star"
                : manifest.gameType === "R" ? "regular_season" : existing?.gameSet ?? "regular_season",
              gameType: manifest.gameType ?? existing?.gameType ?? "R",
              description: "Compact acquisition provenance",
            });
          }
        } catch {
          // Ignore incomplete historical compact manifests.
        }
      }));
    }
    await visit(acquisitionRoot);
    if (Number.isInteger(fixtureId) && /^\d{4}-\d{2}-\d{2}$/u.test(fixtureDate ?? "")) {
      metadata.set(String(fixtureId), { date: fixtureDate, gameSet: "fixture", gameType: "fixture", description: "Development fixture" });
    }
  }
  return metadata;
}

export function mapGameDateIndex(payload, gameMetadata) {
  const byGraph = new Map();
  for (const binding of payload.results?.bindings ?? []) {
    const graph = binding.graph?.value;
    const game = binding.game?.value;
    const gameId = typeof game === "string" ? game.split("/").at(-1) : "";
    const metadata = gameMetadata.get(gameId);
    if (typeof graph === "string" && graph.startsWith(AUTHORITATIVE_GRAPH_PREFIX)
        && /^\d{4}-\d{2}-\d{2}$/u.test(metadata?.date ?? "")) {
      byGraph.set(graph, metadata);
    }
  }
  return [...byGraph].map(([graph, value]) => ({ graph, ...value }))
    .sort((left, right) => left.date.localeCompare(right.date) || left.graph.localeCompare(right.graph));
}

function sha256Text(value) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

export async function corpusFingerprintLines(entries) {
  return Promise.all(entries.map(async (entry) => {
    const gameId = entry.graph.slice(AUTHORITATIVE_GRAPH_PREFIX.length);
    let graphArtifact = "manifest-unavailable";
    if (LOCAL_STATE_ROOT && /^\d+$/u.test(gameId)) {
      try {
        const path = resolve(LOCAL_STATE_ROOT, "pipeline", "manifests", `game-${gameId}-rml.json`);
        const manifest = JSON.parse((await readFile(path, "utf8")).replace(/^\uFEFF/u, ""));
        if (manifest.graphIri === entry.graph && /^[0-9a-f]{64}$/u.test(manifest.outputSha256 ?? "")) {
          graphArtifact = manifest.outputSha256;
        }
      } catch {
        // The Explorer can run against a remote/mock Fuseki without local NiFi manifests.
      }
    }
    return `${entry.graph}|${entry.date}|${entry.gameSet}|${graphArtifact}`;
  }));
}

export async function corpusFingerprint(entries) {
  const lines = await corpusFingerprintLines(entries);
  return sha256Text(lines.sort().join("\n"));
}

function resolveDateScope(value, index, gameSetValue) {
  const request = normalizeDateScope(value);
  const gameSet = normalizeGameSet(gameSetValue);
  const selectedIndex = index.filter((entry) => entry.gameSet === gameSet);
  const availableStartDate = selectedIndex[0]?.date ?? null;
  const availableEndDate = selectedIndex.at(-1)?.date ?? null;
  let startDate = request.startDate ?? availableEndDate;
  let endDate = request.endDate ?? availableEndDate;
  if (availableEndDate) {
    if (request.preset === "seven_days") startDate = shiftIsoDate(availableEndDate, -6);
    if (request.preset === "thirty_days") startDate = shiftIsoDate(availableEndDate, -29);
    if (request.preset === "season_to_date") startDate = `${availableEndDate.slice(0, 4)}-01-01`;
  }
  const graphs = startDate && endDate
    ? selectedIndex.filter((entry) => entry.date >= startDate && entry.date <= endDate).map((entry) => entry.graph)
    : [];
  return {
    graphs,
    meta: {
      preset: request.preset,
      startDate,
      endDate,
      gameCount: graphs.length,
      availableStartDate,
      availableEndDate,
      dateBasis: "official-source",
      gameSet,
    },
  };
}

function normalizeSpecialFilters(value, allowed) {
  if (value === undefined) return {};
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("filters must be an object");
  }
  const filters = {};
  for (const [id, rawValue] of Object.entries(value)) {
    if (!allowed.includes(id)) throw new RangeError(`Unsupported filter: ${id}`);
    if (id === "season") {
      if (!Number.isInteger(rawValue) || rawValue < 1800 || rawValue > 3000) {
        throw new TypeError("season must be an integer between 1800 and 3000");
      }
      filters[id] = rawValue;
      continue;
    }
    if (typeof rawValue !== "string"
        || !rawValue.startsWith(DATA_IRI_PREFIX)
        || /[<>\s]/u.test(rawValue)) {
      throw new TypeError(`${id} must be a canonical BaseballO data IRI`);
    }
    filters[id] = rawValue;
  }
  return filters;
}

function iri(value) {
  return `<${value}>`;
}

export function compileGraphScopeQuery(filters) {
  const patterns = ["?game a base:BaseballGame ."];
  const filterExpressions = [];
  if (filters.season !== undefined) {
    patterns.push(
      "?game obo:BFO_0000199/obo:BFO_0000222 ?gameStartInstant .",
      "?gameStartTimestamp a base:BaseballTimestampICE ; cco:ont00001916 ?gameStartInstant ; cco:ont00001767 ?gameStart .",
      "BIND(YEAR(?gameStart) AS ?season)",
    );
    filterExpressions.push(`FILTER(?season = ${filters.season})`);
  }
  if (filters.game) filterExpressions.push(`FILTER(?game = ${iri(filters.game)})`);
  if (filters.venue) {
    patterns.push(
      "?game cco:ont00001918 ?field .",
      "?field a base:BaseballFieldSite ; obo:BFO_0000171 ?venue .",
    );
    filterExpressions.push(`FILTER(?venue = ${iri(filters.venue)})`);
  }
  if (filters.team) {
    patterns.push(
      "?teamRole a ?teamRoleClass ; obo:BFO_0000197 ?team ; obo:BFO_0000054 ?game .",
      "VALUES ?teamRoleClass { base:HomeTeamRole base:AwayTeamRole }",
    );
    filterExpressions.push(`FILTER(?team = ${iri(filters.team)})`);
  }
  return `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph {
    ${patterns.join("\n    ")}
  }
  ${AUTHORITATIVE_GRAPH_GUARD}
  ${filterExpressions.join("\n  ")}
}`;
}

function applyGraphScope(query, graphIris) {
  if (!query.includes(AUTHORITATIVE_GRAPH_GUARD)) {
    throw new Error("The reviewed query has no authoritative graph guard.");
  }
  const scope = graphIris.length === 0
    ? "FILTER(false)"
    : `VALUES ?graph { ${graphIris.map(iri).join(" ")} }`;
  return query.split(AUTHORITATIVE_GRAPH_GUARD)
    .join(`${AUTHORITATIVE_GRAPH_GUARD}\n  ${scope}`);
}

function applyEmptyPlayerGameScope(query, pairs) {
  const marker = "  # Empty player-game tuple scope is inserted here by the allowlisted server.";
  if (!query.includes(marker)) {
    throw new Error("The damage opportunity query has no empty player-game scope marker.");
  }
  for (const [graph, player] of pairs) {
    if (!graph.startsWith(AUTHORITATIVE_GRAPH_PREFIX)
        || !player.startsWith(`${DATA_IRI_PREFIX}player/`)) {
      throw new Error("Empty player-game evidence contains a noncanonical IRI.");
    }
  }
  const scope = pairs.length === 0
    ? "  FILTER(false)"
    : `  VALUES (?graph ?player) {\n${pairs.map(([graph, player]) => `    (${iri(graph)} ${iri(player)})`).join("\n")}\n  }`;
  return query.replace(marker, scope);
}

function applyDerivedEntityFilters(query, filters) {
  const marker = "      # Derived-metric entity filters are inserted here by the allowlisted server.";
  const clauses = [];
  if (filters.player) clauses.push(`FILTER(?player = ${iri(filters.player)})`);
  if (filters.team) clauses.push(`FILTER(?team = ${iri(filters.team)})`);
  if (clauses.length === 0) return query;
  if (!query.includes(marker)) throw new Error("The derived-metric filter boundary is missing.");
  return query.replace(marker, `${clauses.map((clause) => `      ${clause}`).join("\n")}\n\n${marker}`);
}

export function applyAdvancedResultFilters(query, filters, declarations = []) {
  const active = declarations.filter((declaration) => filters[declaration.id]);
  if (active.length === 0) return query;
  const selectIndex = query.search(/^SELECT\b/mu);
  if (selectIndex < 0) throw new Error("The reviewed Advanced query has no SELECT boundary.");
  const clauses = active.map((declaration) => {
    if (!/^[A-Za-z][A-Za-z0-9_]*$/u.test(declaration.variable ?? "")) {
      throw new Error(`Invalid Advanced result variable for ${declaration.id}.`);
    }
    return `VALUES ?${declaration.variable} { ${iri(filters[declaration.id])} }`;
  });
  const prefixes = query.slice(0, selectIndex).trimEnd();
  const body = query.slice(selectIndex).trim().split("\n").map((line) => `    ${line}`).join("\n");
  return `${prefixes}\n\nSELECT * WHERE {\n  {\n${body}\n  }\n  ${clauses.join("\n  ")}\n}`;
}

async function graphScope(filters, execution) {
  if (Object.keys(filters).length === 0) return null;
  const { payload } = await executeSparql(compileGraphScopeQuery(filters), execution);
  return (payload.results?.bindings ?? []).flatMap((binding) => {
    const value = binding.graph?.value;
    return typeof value === "string" && value.startsWith(AUTHORITATIVE_GRAPH_PREFIX)
      ? [value]
      : [];
  });
}

function intersectGraphScopes(left, right) {
  if (left === null) return right;
  const allowed = new Set(right);
  return left.filter((graph) => allowed.has(graph));
}

export function createBaseballServer({
  fetchImpl = globalThis.fetch,
  queryEndpoint = process.env.BASEBALLO_FUSEKI_QUERY ?? DEFAULT_QUERY_ENDPOINT,
  servingExecutor = executeServingQuery,
} = {}) {
  const optionCache = new Map();
  const resultCache = new Map();
  let gameDateIndexCache;

  async function gameDateSnapshot() {
    if (gameDateIndexCache?.expiresAt > Date.now()) return gameDateIndexCache;
    const { payload } = await executeSparql(compileGameDateIndexQuery(), { fetchImpl, queryEndpoint });
    const gameMetadata = await readOfficialGameMetadata();
    const entries = mapGameDateIndex(payload, gameMetadata);
    const fingerprint = await corpusFingerprint(entries);
    if (gameDateIndexCache?.fingerprint && gameDateIndexCache.fingerprint !== fingerprint) {
      optionCache.clear();
      resultCache.clear();
    }
    gameDateIndexCache = { entries, fingerprint, expiresAt: Date.now() + GAME_DATE_INDEX_TTL_MS };
    return gameDateIndexCache;
  }

  async function executeCachedSparql(query, fingerprint) {
    const key = sha256Text(`${fingerprint}\n${query}`);
    const cached = resultCache.get(key);
    if (cached?.expiresAt > Date.now()) {
      return { payload: cached.payload, durationMs: 0, cached: true };
    }
    const executed = await executeSparql(query, { fetchImpl, queryEndpoint });
    if (resultCache.size >= RESULT_CACHE_LIMIT) resultCache.delete(resultCache.keys().next().value);
    resultCache.set(key, { payload: executed.payload, expiresAt: Date.now() + RESULT_CACHE_TTL_MS });
    return { ...executed, cached: false };
  }

  async function scopedGraphs(dateScope, filters = {}, gameSet) {
    const snapshot = await gameDateSnapshot();
    const resolved = resolveDateScope(dateScope, snapshot.entries, gameSet);
    let filtered = null;
    if (Object.keys(filters).length > 0) {
      const { payload } = await executeCachedSparql(compileGraphScopeQuery(filters), snapshot.fingerprint);
      filtered = (payload.results?.bindings ?? []).flatMap((binding) => {
        const value = binding.graph?.value;
        return typeof value === "string" && value.startsWith(AUTHORITATIVE_GRAPH_PREFIX) ? [value] : [];
      });
    }
    return {
      graphs: intersectGraphScopes(filtered, resolved.graphs),
      dateScope: resolved.meta,
      corpusFingerprint: snapshot.fingerprint,
    };
  }

  return createServer(async (request, response) => {
    const requestUrl = new URL(request.url ?? "/", "http://127.0.0.1");
    try {
      if (request.method === "GET" && requestUrl.pathname === "/api/catalog") {
        sendJson(response, 200, { families: buildPublicCatalog() });
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/status") {
        const query = `PREFIX base: <https://baseballontology.org/>\nSELECT (COUNT(DISTINCT ?game) AS ?games) WHERE {\n  GRAPH ?graph { ?game a base:BaseballGame . }\n  FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))\n}`;
        const { payload, durationMs } = await executeSparql(query, { fetchImpl, queryEndpoint });
        const binding = payload.results?.bindings?.[0] ?? {};
        const games = Number(binding.games?.value ?? 0);
        let serving = { available: false };
        try {
          const probe = await servingExecutor({
            id: GOOD_AT_BAT_QUERY_ID,
            view: "player_averages",
            filters: {},
            dateScope: { preset: "one_day" },
            gameSet: "regular_season",
          });
          serving = {
            available: true,
            route: "Materialized SQL · reviewed Questions",
            buildId: probe.serving.buildId,
            corpusFingerprint: probe.serving.corpusFingerprint,
            probeView: probe.serving.view,
            probeRows: probe.results?.bindings?.length ?? 0,
            dateScope: probe.serving.dateScope,
            advancedQueries: probe.serving.coverage?.advancedQueries ?? 0,
            advancedBindings: probe.serving.coverage?.advancedBindings ?? 0,
            coverage: probe.serving.coverage ?? {},
          };
        } catch {
          // The visible status must report fallback honestly without making
          // graph connectivity depend on the disposable serving layer.
        }
        sendJson(response, 200, {
          service: "baseballo-explorer",
          processId: process.pid,
          explorerSourceFingerprint: EXPLORER_SOURCE_FINGERPRINT,
          connected: true,
          games,
          serving,
          durationMs,
          layer: "authoritative",
        });
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/date-scope") {
        const preset = requestUrl.searchParams.get("preset") ?? "seven_days";
        const input = { preset };
        if (requestUrl.searchParams.has("startDate")) input.startDate = requestUrl.searchParams.get("startDate");
        if (requestUrl.searchParams.has("endDate")) input.endDate = requestUrl.searchParams.get("endDate");
        const { meta } = resolveDateScope(input, (await gameDateSnapshot()).entries, requestUrl.searchParams.get("gameSet") ?? undefined);
        sendJson(response, 200, { scope: meta });
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/advanced/catalog") {
        const advancedCatalog = await readAdvancedCatalog();
        sendJson(response, 200, {
          queries: advancedCatalog.queries.map(publicAdvancedEntry),
          blockedAnalytics: advancedCatalog.blockedAnalytics,
        });
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/derived/catalog") {
        sendJson(response, 200, buildPublicDerivedMetricCatalog());
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/empty-games/catalog") {
        sendJson(response, 200, buildPublicEmptyGameCatalog());
        return;
      }

      if (request.method === "GET" && requestUrl.pathname === "/api/options") {
        const familyId = requestUrl.searchParams.get("family") ?? "";
        const dimensionId = requestUrl.searchParams.get("dimension") ?? "";
        const gameSet = normalizeGameSet(requestUrl.searchParams.get("gameSet") ?? undefined);
        const dimension = requireDimension(familyId, dimensionId);
        if (!dimension.optionsQuery && !dimension.values) {
          sendJson(response, 200, { options: [] });
          return;
        }
        try {
          const materialized = await servingExecutor({
            route: "options", family: familyId, dimension: dimensionId, gameSet,
          });
          const options = mapOptions(dimensionId, dimension, materialized);
          sendJson(response, 200, {
            options, cached: false, layer: "materialized",
            servingBuildId: materialized.serving.buildId,
            corpusFingerprint: materialized.serving.corpusFingerprint,
            servingCoverage: materialized.serving.coverage,
          });
          return;
        } catch {
          if (rejectMaterializedFallback(request, response)) return;
          // Fail open to the authoritative option query.
        }
        const snapshot = await gameDateSnapshot();
        const cacheKey = `${snapshot.fingerprint}:${gameSet}:${familyId}:${dimensionId}`;
        if (optionCache.has(cacheKey)) {
          sendJson(response, 200, { options: optionCache.get(cacheKey), cached: true });
          return;
        }
        let options;
        if (dimension.values) {
          options = mapOptions(dimensionId, dimension, { results: { bindings: [] } });
        } else {
          const queryPath = resolveOptionsPath(dimension.optionsQuery);
          const sourceQuery = await readFile(queryPath, "utf8");
          const graphs = snapshot.entries
            .filter((entry) => entry.gameSet === gameSet)
            .map((entry) => entry.graph);
          const query = applyGraphScope(sourceQuery, graphs);
          const { payload } = await executeCachedSparql(query, snapshot.fingerprint);
          options = mapOptions(dimensionId, dimension, payload);
        }
        optionCache.set(cacheKey, options);
        sendJson(response, 200, { options });
        return;
      }

      if ((request.method === "GET" || request.method === "POST")
          && requestUrl.pathname === "/api/canned/empty-games") {
        const input = request.method === "POST" ? await readJsonBody(request) : {};
        const analysis = input.analysis ?? "players";
        if (typeof analysis !== "string" || !EMPTY_GAME_ANALYSES[analysis]) {
          throw new RangeError(`Unknown Empty Games analysis: ${analysis}`);
        }
        const filters = normalizeSpecialFilters(
          input.filters,
          ["season", "game", "venue", "team", "player", "pitcher"],
        );
        const graphFilters = Object.fromEntries(
          Object.entries(filters).filter(([id]) => !["team", "player", "pitcher"].includes(id)),
        );
        try {
          const materialized = await servingExecutor({
            route: "empty-games", analysis, filters,
            dateScope: normalizeDateScope(input.dateScope),
            gameSet: normalizeGameSet(input.gameSet),
          });
          const result = aggregateEmptyGameEvidence(materialized, analysis, MAX_RESULTS);
          sendJson(response, 200, {
            head: result.head,
            results: result.results,
            query: materialized.query,
            meta: {
              durationMs: materialized.serving.durationMs,
              rowCount: result.results.bindings.length,
              layer: "materialized",
              route: `Materialized SQL · ${EMPTY_GAME_ANALYSES[analysis].label}`,
              cached: false,
              corpusFingerprint: materialized.serving.corpusFingerprint,
              servingBuildId: materialized.serving.buildId,
              servingCoverage: materialized.serving.coverage,
              definition: "reviewed-empty-game-analysis",
              analysis,
              analysisLabel: EMPTY_GAME_ANALYSES[analysis].label,
              description: EMPTY_GAME_ANALYSES[analysis].description,
              limitation: EMPTY_GAME_ANALYSES[analysis].limitation,
              evidenceRowCount: result.evidenceRowCount,
              playerGameCount: result.playerGameCount,
              totalRowCount: result.totalRowCount,
              truncatedAt: result.totalRowCount > MAX_RESULTS ? MAX_RESULTS : null,
              filters,
              dateScope: materialized.serving.dateScope,
            },
          });
          return;
        } catch {
          if (rejectMaterializedFallback(request, response)) return;
          // Fail open to the reviewed authoritative evidence query.
        }
        const { graphs, dateScope, corpusFingerprint } = await scopedGraphs(input.dateScope, graphFilters, input.gameSet);
        let query = applyGraphScope(
          compileEmptyGameEvidenceQuery({ ...filters, analysis }),
          graphs,
        );
        let payload;
        let durationMs;
        let cached;
        if (analysis === "damage") {
          const classification = await executeCachedSparql(query, corpusFingerprint);
          const emptyPlayerGames = [...new Map(
            (classification.payload.results?.bindings ?? [])
              .filter((row) => row.emptyFlag?.value === "1" && row.graph?.value && row.player?.value)
              .map((row) => [
                `${row.graph.value}\u001f${row.player.value}`,
                [row.graph.value, row.player.value],
              ]),
          ).values()];
          let opportunityQuery = applyGraphScope(
            compileEmptyGameDamageOpportunityQuery(filters),
            graphs,
          );
          opportunityQuery = applyEmptyPlayerGameScope(opportunityQuery, emptyPlayerGames);
          const opportunities = await executeCachedSparql(opportunityQuery, corpusFingerprint);
          const bindings = (opportunities.payload.results?.bindings ?? [])
            .map((row) => ({
              ...row,
              emptyFlag: { type: "literal", datatype: `${XSD}integer`, value: "1" },
            }));
          payload = { head: opportunities.payload.head, results: { bindings } };
          durationMs = classification.durationMs + opportunities.durationMs;
          cached = classification.cached && opportunities.cached;
          query = `${query}\n\n# Damage opportunity evidence\n${opportunityQuery}`;
        } else {
          ({ payload, durationMs, cached } = await executeCachedSparql(query, corpusFingerprint));
        }
        const result = aggregateEmptyGameEvidence(payload, analysis, MAX_RESULTS);
        sendJson(response, 200, {
          head: result.head,
          results: result.results,
          query,
          meta: {
            durationMs,
            rowCount: result.results.bindings.length,
            layer: "authoritative",
            route: "Authoritative",
            cached,
            corpusFingerprint,
            definition: "reviewed-empty-game-analysis",
            analysis,
            analysisLabel: EMPTY_GAME_ANALYSES[analysis].label,
            description: EMPTY_GAME_ANALYSES[analysis].description,
            limitation: EMPTY_GAME_ANALYSES[analysis].limitation,
            evidenceRowCount: result.evidenceRowCount,
            playerGameCount: result.playerGameCount,
            totalRowCount: result.totalRowCount,
            truncatedAt: result.totalRowCount > MAX_RESULTS ? MAX_RESULTS : null,
            filters,
            dateScope,
          },
        });
        return;
      }

      if (request.method === "POST" && requestUrl.pathname === "/api/derived") {
        const input = await readJsonBody(request);
        const compiled = compileDerivedMetricQuery(input);
        const filters = normalizeSpecialFilters(input.filters, ["season", "game", "venue", "team", "player"]);
        try {
          const materialized = await servingExecutor({
            route: "derived", numerator: input.numerator, denominator: input.denominator, filters,
            dateScope: normalizeDateScope(input.dateScope), gameSet: normalizeGameSet(input.gameSet),
          });
          sendJson(response, 200, {
            head: materialized.head,
            results: materialized.results,
            query: materialized.query,
            meta: {
              durationMs: materialized.serving.durationMs,
              rowCount: materialized.results?.bindings?.length ?? 0,
              layer: "materialized",
              route: "Materialized SQL · Derived metric",
              cached: false,
              corpusFingerprint: materialized.serving.corpusFingerprint,
              servingBuildId: materialized.serving.buildId,
              servingCoverage: materialized.serving.coverage,
              definition: "reviewed-derived-metric",
              filters,
              dateScope: materialized.serving.dateScope,
              derivedMetric: compiled.contract,
              columnLabels: { derivedValue: compiled.contract.label },
            },
          });
          return;
        } catch {
          if (rejectMaterializedFallback(request, response)) return;
          // Fail open to the reviewed authoritative metric query.
        }
        const graphFilters = Object.fromEntries(
          Object.entries(filters).filter(([id]) => !["team", "player"].includes(id)),
        );
        const { graphs, dateScope, corpusFingerprint } = await scopedGraphs(input.dateScope, graphFilters, input.gameSet);
        let query = applyGraphScope(compiled.query, graphs);
        query = applyDerivedEntityFilters(query, filters);
        const executedQuery = `${query.trimEnd()}\nLIMIT ${MAX_RESULTS}\n`;
        const { payload, durationMs, cached } = await executeCachedSparql(executedQuery, corpusFingerprint);
        sendJson(response, 200, {
          ...payload,
          query: executedQuery,
          meta: {
            durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: "authoritative",
            route: "Authoritative",
            cached,
            corpusFingerprint,
            definition: "reviewed-derived-metric",
            filters,
            dateScope,
            derivedMetric: compiled.contract,
            columnLabels: { derivedValue: compiled.contract.label },
          },
        });
        return;
      }


      if (request.method === "POST" && requestUrl.pathname === "/api/advanced") {
        const input = await readJsonBody(request);
        if (typeof input.id !== "string") {
          throw new TypeError("An advanced query ID is required.");
        }
        const advancedCatalog = await readAdvancedCatalog();
        const entry = advancedCatalog.queries.find((candidate) => candidate.id === input.id);
        if (!entry) {
          throw new RangeError(`Unknown advanced query: ${input.id}`);
        }
        const resultFilterDeclarations = entry.resultFilters ?? [];
        const resultFilterIds = resultFilterDeclarations.map((declaration) => declaration.id);
        const filters = normalizeSpecialFilters(
          input.filters,
          ["season", "game", "venue", "team", ...resultFilterIds],
        );
        const presentation = ADVANCED_PRESENTATION[entry.id] ?? {};
        const view = entry.id === GOOD_AT_BAT_QUERY_ID
          ? input.view ?? "plate_appearances"
          : undefined;
        if (entry.id === GOOD_AT_BAT_QUERY_ID) {
          if (!["plate_appearances", "player_averages"].includes(view)) {
            throw new RangeError(`Unknown Plate Appearance Quality view: ${view}`);
          }
        } else if (input.view !== undefined) {
          throw new RangeError("Views are only supported for Plate Appearance Quality.");
        }
        const visibleColumns = view === "player_averages"
          ? presentation.playerAverageColumns
          : presentation.visibleColumns;
        try {
          const materialized = await servingExecutor({
            id: entry.id,
            ...(view === undefined ? {} : { view }),
            filters,
            dateScope: normalizeDateScope(input.dateScope),
            gameSet: normalizeGameSet(input.gameSet),
          });
          sendJson(response, 200, {
            head: materialized.head,
            results: materialized.results,
            query: materialized.query,
            meta: {
              durationMs: materialized.serving.durationMs,
              rowCount: materialized.results?.bindings?.length ?? 0,
              layer: "materialized",
              route: `Materialized SQL · ${entry.label}`,
              cached: false,
              corpusFingerprint: materialized.serving.corpusFingerprint,
              servingBuildId: materialized.serving.buildId,
              servingCoverage: materialized.serving.coverage,
              definition: entry.semanticMode,
              claim: entry.claim,
              view,
              truncatedAt: MAX_RESULTS,
              filters,
              dateScope: materialized.serving.dateScope,
              columnOrder: presentation.columnOrder,
              visibleColumns,
              columnLabels: presentation.columnLabels,
            },
          });
          return;
        } catch {
          if (rejectMaterializedFallback(request, response)) return;
          // A missing, stale, or invalid serving build fails open to the
          // persistent authoritative RDF research path.
        }
        const graphFilters = Object.fromEntries(
          Object.entries(filters).filter(([id]) => !resultFilterIds.includes(id)),
        );
        const { graphs, dateScope, corpusFingerprint } = await scopedGraphs(input.dateScope, graphFilters, input.gameSet);
        let query = await readFile(resolveAdvancedQueryPath(entry), "utf8");
        query = applyGraphScope(query, graphs);
        query = applyAdvancedResultFilters(query, filters, resultFilterDeclarations);
        const executedQuery = entry.id === GOOD_AT_BAT_QUERY_ID && view === "player_averages"
          ? query
          : `${query.trimEnd()}\nLIMIT ${MAX_RESULTS}\n`;
        const execution = await executeCachedSparql(executedQuery, corpusFingerprint);
        const payload = entry.id === GOOD_AT_BAT_QUERY_ID && view === "player_averages"
          ? aggregatePaqPlayerAverages(execution.payload)
          : execution.payload;
        sendJson(response, 200, {
          ...payload,
          query: executedQuery,
          meta: {
            durationMs: execution.durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: entry.semanticMode === "decision-support" ? "unified" : "authoritative",
            route: entry.semanticMode === "decision-support"
              ? "Unified PAQ evidence · authoritative fallback"
              : "Authoritative",
            cached: execution.cached,
            corpusFingerprint,
            definition: entry.semanticMode,
            claim: entry.claim,
            view,
            truncatedAt: MAX_RESULTS,
            filters,
            dateScope,
            columnOrder: presentation.columnOrder,
            visibleColumns,
            columnLabels: presentation.columnLabels,
          },
        });
        return;
      }

      if (request.method === "POST" && requestUrl.pathname === "/api/query") {
        const input = normalizeQueryRequest(await readJsonBody(request));
        try {
          const materialized = await servingExecutor({
            route: "explore", ...input,
            dateScope: normalizeDateScope(input.dateScope),
            gameSet: normalizeGameSet(input.gameSet),
          });
          sendJson(response, 200, {
            head: materialized.head,
            results: materialized.results,
            query: materialized.query,
            meta: {
              durationMs: materialized.serving.durationMs,
              rowCount: materialized.results?.bindings?.length ?? 0,
              layer: "materialized",
              route: `Materialized SQL · ${requireFamily(input.family).label}`,
              cached: false,
              corpusFingerprint: materialized.serving.corpusFingerprint,
              servingBuildId: materialized.serving.buildId,
              servingCoverage: materialized.serving.coverage,
              filters: input.filters ?? {},
              dateScope: materialized.serving.dateScope,
            },
          });
          return;
        } catch {
          if (rejectMaterializedFallback(request, response)) return;
          // Fail open to the compiled authoritative query.
        }
        const { graphs, dateScope, corpusFingerprint } = await scopedGraphs(input.dateScope, {}, input.gameSet);
        const query = applyGraphScope(compileAnalyticsQuery(input), graphs);
        const { payload, durationMs, cached } = await executeCachedSparql(query, corpusFingerprint);
        sendJson(response, 200, {
          ...payload,
          query,
          meta: {
            durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: "authoritative",
            route: "Compiled Authoritative",
            cached,
            corpusFingerprint,
            filters: input.filters ?? {},
            dateScope,
          },
        });
        return;
      }

      if (request.method === "GET" && STATIC_FILES.has(requestUrl.pathname)) {
        const fileName = STATIC_FILES.get(requestUrl.pathname);
        const body = await readFile(resolve(WEB_ROOT, fileName));
        response.writeHead(200, responseHeaders(CONTENT_TYPES[extname(fileName)] ?? "application/octet-stream"));
        response.end(body);
        return;
      }

      sendJson(response, 404, { error: "Not found." });
    } catch (error) {
      const { status, message } = publicError(error);
      sendJson(response, status, { error: message });
    }
  });
}

const launchedDirectly = process.argv[1]
  && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));

if (launchedDirectly) {
  const port = Number.parseInt(process.env.PORT ?? "4173", 10);
  const server = createBaseballServer();
  server.listen(port, "127.0.0.1", () => {
    console.log(`BaseballO Explorer: http://127.0.0.1:${port}/`);
    console.log(`Graph endpoint: ${process.env.BASEBALLO_FUSEKI_QUERY ?? DEFAULT_QUERY_ENDPOINT}`);
  });
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}
