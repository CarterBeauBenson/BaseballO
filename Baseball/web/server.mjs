import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import {
  ANALYTICS_QUERY_FAMILIES,
  compileAnalyticsQuery,
} from "./query-builder/analytics-query-builder.js";

const WEB_ROOT = dirname(fileURLToPath(import.meta.url));
const QUERY_BUILDER_ROOT = resolve(WEB_ROOT, "query-builder");
const OPTIONS_ROOT = resolve(WEB_ROOT, "..", "sparql", "options");
const EMPTY_GAMES_QUERY = resolve(WEB_ROOT, "..", "sparql", "empty-games-prototype.rq");
const ADVANCED_QUERY_ROOT = resolve(WEB_ROOT, "..", "sparql", "advanced");
const ADVANCED_QUERY_CATALOG = resolve(ADVANCED_QUERY_ROOT, "advanced-query-catalog.json");
const DEFAULT_QUERY_ENDPOINT = "http://127.0.0.1:3030/baseball-dev/query";
const AUTHORITATIVE_GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/";
const AUTHORITATIVE_GRAPH_GUARD = `FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))`;
const DATA_IRI_PREFIX = "https://baseballontology.org/data/";
const MAX_BODY_BYTES = 64 * 1024;
const MAX_RESULTS = 1000;
const STATIC_FILES = new Map([
  ["/", "index.html"],
  ["/index.html", "index.html"],
  ["/app.js", "app.js"],
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

async function readAdvancedCatalog() {
  const catalog = JSON.parse(await readFile(ADVANCED_QUERY_CATALOG, "utf8"));
  if (catalog.artifactType !== "baseball-advanced-semantic-query-catalog"
      || !Array.isArray(catalog.queries)
      || catalog.queries.length !== 16) {
    throw new Error("The advanced-query catalog is invalid.");
  }
  return catalog;
}

function publicAdvancedEntry(entry) {
  return {
    id: entry.id,
    label: advancedLabel(entry.id),
    claim: entry.claim,
    semanticMode: entry.semanticMode,
    allowZeroRows: entry.allowZeroRows,
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
    : `FILTER(?graph IN (${graphIris.map(iri).join(", ")}))`;
  return query.split(AUTHORITATIVE_GRAPH_GUARD)
    .join(`${AUTHORITATIVE_GRAPH_GUARD}\n  ${scope}`);
}

function applyEmptyEntityFilters(query, filters) {
  const marker = "  # Do not classify a graph whose PA result vocabulary";
  const clauses = [];
  if (filters.player) clauses.push(`FILTER(?player = ${iri(filters.player)})`);
  if (filters.team) clauses.push(`FILTER(?team = ${iri(filters.team)})`);
  if (clauses.length === 0) return query;
  if (!query.includes(marker)) throw new Error("The Empty Games filter boundary is missing.");
  return query.replace(marker, `  ${clauses.join("\n  ")}\n\n${marker}`);
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

export function createBaseballServer({
  fetchImpl = globalThis.fetch,
  queryEndpoint = process.env.BASEBALLO_FUSEKI_QUERY ?? DEFAULT_QUERY_ENDPOINT,
} = {}) {
  const optionCache = new Map();

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
        const games = Number(payload.results?.bindings?.[0]?.games?.value ?? 0);
        sendJson(response, 200, { connected: true, games, durationMs, layer: "authoritative" });
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

      if (request.method === "GET" && requestUrl.pathname === "/api/options") {
        const familyId = requestUrl.searchParams.get("family") ?? "";
        const dimensionId = requestUrl.searchParams.get("dimension") ?? "";
        const cacheKey = `${familyId}:${dimensionId}`;
        const dimension = requireDimension(familyId, dimensionId);
        if (!dimension.optionsQuery && !dimension.values) {
          sendJson(response, 200, { options: [] });
          return;
        }
        if (optionCache.has(cacheKey)) {
          sendJson(response, 200, { options: optionCache.get(cacheKey), cached: true });
          return;
        }
        let options;
        if (dimension.values) {
          options = mapOptions(dimensionId, dimension, { results: { bindings: [] } });
        } else {
          const queryPath = resolveOptionsPath(dimension.optionsQuery);
          const query = await readFile(queryPath, "utf8");
          const { payload } = await executeSparql(query, { fetchImpl, queryEndpoint });
          options = mapOptions(dimensionId, dimension, payload);
        }
        optionCache.set(cacheKey, options);
        sendJson(response, 200, { options });
        return;
      }

      if ((request.method === "GET" || request.method === "POST")
          && requestUrl.pathname === "/api/canned/empty-games") {
        const input = request.method === "POST" ? await readJsonBody(request) : {};
        const filters = normalizeSpecialFilters(input.filters, ["season", "game", "venue", "team", "player"]);
        const graphFilters = Object.fromEntries(
          Object.entries(filters).filter(([id]) => !["team", "player"].includes(id)),
        );
        const graphs = await graphScope(graphFilters, { fetchImpl, queryEndpoint });
        let query = await readFile(EMPTY_GAMES_QUERY, "utf8");
        if (graphs) query = applyGraphScope(query, graphs);
        query = applyEmptyEntityFilters(query, filters);
        const { payload, durationMs } = await executeSparql(query, { fetchImpl, queryEndpoint });
        sendJson(response, 200, {
          ...payload,
          query,
          meta: {
            durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: "authoritative",
            definition: "reviewed-prototype",
            filters,
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
        const filters = normalizeSpecialFilters(input.filters, ["season", "game", "venue", "team"]);
        const graphs = await graphScope(filters, { fetchImpl, queryEndpoint });
        let query = await readFile(resolveAdvancedQueryPath(entry), "utf8");
        if (graphs) query = applyGraphScope(query, graphs);
        const executedQuery = `${query.trimEnd()}\nLIMIT ${MAX_RESULTS}\n`;
        const { payload, durationMs } = await executeSparql(executedQuery, { fetchImpl, queryEndpoint });
        sendJson(response, 200, {
          ...payload,
          query: executedQuery,
          meta: {
            durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: "authoritative",
            definition: entry.semanticMode,
            claim: entry.claim,
            truncatedAt: MAX_RESULTS,
            filters,
          },
        });
        return;
      }

      if (request.method === "POST" && requestUrl.pathname === "/api/query") {
        const input = normalizeQueryRequest(await readJsonBody(request));
        const query = compileAnalyticsQuery(input);
        const { payload, durationMs } = await executeSparql(query, { fetchImpl, queryEndpoint });
        sendJson(response, 200, {
          ...payload,
          query,
          meta: {
            durationMs,
            rowCount: payload.results?.bindings?.length ?? 0,
            layer: "authoritative",
            filters: input.filters ?? {},
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
