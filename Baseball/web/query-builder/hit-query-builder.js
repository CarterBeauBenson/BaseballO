const DATA_IRI_PREFIX = "https://baseballontology.org/data/";
const HIT_TYPES = Object.freeze(["single", "double", "triple", "home_run"]);

const PREFIXES = `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>`;

const CORE_PATTERNS = Object.freeze([
  `?game a base:BaseballGame ;
        obo:BFO_0000199/obo:BFO_0000222 ?gameStartInstant .`,
  `?gameStartTimestamp a base:BaseballTimestampICE ;
                      cco:ont00001916 ?gameStartInstant ;
                      cco:ont00001767 ?gameStart .`,
  `?hitRecord a base:BaseballEventRecord ;
             cco:ont00001808 ?hit ;
             dcterms:identifier ?eventType .`,
  `?hit obo:BFO_0000132 ?plateAppearance .`,
  `?plateAppearance a base:PlateAppearance .`,
  `BIND(YEAR(?gameStart) AS ?season)`,
]);

const PATTERN_COMPONENTS = Object.freeze({
  venue: Object.freeze([
    `?hit cco:ont00001918 ?field .`,
    `?field a base:BaseballFieldSite ;
          obo:BFO_0000171 ?venue .`,
    `?venue a base:BaseballVenue ;
           rdfs:label ?venueLabel .`,
  ]),
  player: Object.freeze([
    `?batterAct a base:BatterAct ;
               obo:BFO_0000132 ?plateAppearance ;
               cco:ont00001833 ?player .`,
    `?player rdfs:label ?playerLabel .`,
  ]),
});

export const HIT_QUERY_COMPONENTS = Object.freeze({
  dimensions: Object.freeze({
    season: Object.freeze({
      label: "Season",
      select: Object.freeze(["?season"]),
      groupBy: Object.freeze(["?season"]),
      requires: Object.freeze([]),
      sortExpression: "?season",
      optionsQuery: "../../sparql/options/available-seasons.rq",
    }),
    venue: Object.freeze({
      label: "Venue",
      select: Object.freeze(["?venue", "?venueLabel"]),
      groupBy: Object.freeze(["?venue", "?venueLabel"]),
      requires: Object.freeze(["venue"]),
      sortExpression: "LCASE(STR(?venueLabel))",
      optionsQuery: "../../sparql/options/available-venues.rq",
    }),
    player: Object.freeze({
      label: "Player",
      select: Object.freeze(["?player", "?playerLabel"]),
      groupBy: Object.freeze(["?player", "?playerLabel"]),
      requires: Object.freeze(["player"]),
      sortExpression: "LCASE(STR(?playerLabel))",
      optionsQuery: "../../sparql/options/available-players.rq",
    }),
    hit_type: Object.freeze({
      label: "Hit type",
      select: Object.freeze(["?eventType"]),
      groupBy: Object.freeze(["?eventType"]),
      requires: Object.freeze([]),
      sortExpression: "?eventType",
      optionsQuery: "../../sparql/options/available-hit-types.rq",
    }),
    game: Object.freeze({
      label: "Game",
      select: Object.freeze(["?game", "?gameStart"]),
      groupBy: Object.freeze(["?game", "?gameStart"]),
      requires: Object.freeze([]),
      sortExpression: "?gameStart",
      optionsQuery: "../../sparql/options/available-games.rq",
    }),
  }),
  metrics: Object.freeze({
    hits: Object.freeze({
      label: "Hits",
      select: "(COUNT(DISTINCT ?hit) AS ?hits)",
      sortExpression: "?hits",
    }),
    games_with_hits: Object.freeze({
      label: "Games with hits",
      select: "(COUNT(DISTINCT ?game) AS ?gamesWithHits)",
      sortExpression: "?gamesWithHits",
    }),
  }),
  filters: Object.freeze({
    season: Object.freeze({ label: "Season", input: "integer" }),
    venue: Object.freeze({ label: "Venue", input: "iri", pattern: "venue" }),
    player: Object.freeze({ label: "Player", input: "iri", pattern: "player" }),
    hit_type: Object.freeze({
      label: "Hit type",
      input: "multi-select",
      values: HIT_TYPES,
    }),
    game: Object.freeze({ label: "Game", input: "iri" }),
  }),
});

function requireComponent(collection, id, kind) {
  const component = collection[id];
  if (!component) {
    throw new RangeError(`Unknown ${kind} component: ${id}`);
  }
  return component;
}

function unique(values) {
  return [...new Set(values)];
}

function validateDataIri(value, filterName) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new TypeError(`${filterName} must be an absolute IRI`);
  }
  if (!url.href.startsWith(DATA_IRI_PREFIX) || /[<>\s]/u.test(value)) {
    throw new TypeError(`${filterName} must be a canonical BaseballO data IRI`);
  }
  return url.href;
}

function renderHitTypeValues(requestedTypes) {
  const values = requestedTypes === undefined ? HIT_TYPES : requestedTypes;
  if (!Array.isArray(values) || values.length === 0) {
    throw new TypeError("hit_type must contain at least one selected value");
  }
  const selected = unique(values);
  for (const value of selected) {
    if (!HIT_TYPES.includes(value)) {
      throw new RangeError(`Unsupported hit_type value: ${value}`);
    }
  }
  return `VALUES ?eventType { ${selected.map((value) => `"${value}"`).join(" ")} }`;
}

function renderFilters(filters) {
  const patterns = [];
  const requiredPatternComponents = [];

  for (const id of Object.keys(filters)) {
    requireComponent(HIT_QUERY_COMPONENTS.filters, id, "filter");
  }

  if (filters.season !== undefined) {
    if (!Number.isInteger(filters.season) || filters.season < 1800 || filters.season > 3000) {
      throw new TypeError("season must be an integer between 1800 and 3000");
    }
    patterns.push(`FILTER(?season = ${filters.season})`);
  }
  if (filters.venue !== undefined) {
    const venue = validateDataIri(filters.venue, "venue");
    requiredPatternComponents.push("venue");
    patterns.push(`VALUES ?venue { <${venue}> }`);
  }
  if (filters.player !== undefined) {
    const player = validateDataIri(filters.player, "player");
    requiredPatternComponents.push("player");
    patterns.push(`VALUES ?player { <${player}> }`);
  }
  if (filters.game !== undefined) {
    const game = validateDataIri(filters.game, "game");
    patterns.push(`VALUES ?game { <${game}> }`);
  }

  return {
    patterns,
    requiredPatternComponents,
    hitTypeValues: renderHitTypeValues(filters.hit_type),
  };
}

function renderLimit(name, value, maximum) {
  if (value === undefined) {
    return "";
  }
  if (!Number.isInteger(value) || value < 0 || value > maximum) {
    throw new TypeError(`${name} must be an integer between 0 and ${maximum}`);
  }
  return `${name.toUpperCase()} ${value}`;
}

function renderSort(sort, dimensions, metrics) {
  if (sort === undefined) {
    const defaults = [];
    if (dimensions.includes("season")) {
      defaults.push("?season");
    }
    if (metrics.includes("hits")) {
      defaults.push("DESC(?hits)");
    }
    return defaults;
  }
  if (!Array.isArray(sort)) {
    throw new TypeError("sort must be an array");
  }
  return sort.map(({ id, direction = "asc" }) => {
    const component = HIT_QUERY_COMPONENTS.dimensions[id]
      ?? HIT_QUERY_COMPONENTS.metrics[id];
    if (!component || (!dimensions.includes(id) && !metrics.includes(id))) {
      throw new RangeError(`Sort component is not selected: ${id}`);
    }
    if (direction !== "asc" && direction !== "desc") {
      throw new RangeError(`Unsupported sort direction: ${direction}`);
    }
    const expression = component.sortExpression;
    return direction === "desc" ? `DESC(${expression})` : expression;
  });
}

/**
 * Compile an allowlisted hit-statistics selection into one SPARQL 1.1 query.
 * User-provided text is accepted only as validated integers, known enum values,
 * or canonical BaseballO data IRIs.
 */
export function compileHitQuery({
  dimensions = ["season"],
  metrics = ["hits"],
  filters = {},
  sort,
  limit = 500,
  offset,
} = {}) {
  const selectedDimensions = unique(dimensions);
  const selectedMetrics = unique(metrics);
  if (selectedMetrics.length === 0) {
    throw new TypeError("At least one metric must be selected");
  }

  const dimensionComponents = selectedDimensions.map((id) =>
    requireComponent(HIT_QUERY_COMPONENTS.dimensions, id, "dimension"));
  const metricComponents = selectedMetrics.map((id) =>
    requireComponent(HIT_QUERY_COMPONENTS.metrics, id, "metric"));
  const renderedFilters = renderFilters(filters);

  const patternComponentIds = unique([
    ...dimensionComponents.flatMap((component) => component.requires),
    ...renderedFilters.requiredPatternComponents,
  ]);
  const optionalPatterns = patternComponentIds.flatMap((id) => PATTERN_COMPONENTS[id]);

  const selectItems = [
    ...dimensionComponents.flatMap((component) => component.select),
    ...metricComponents.map((component) => component.select),
  ];
  const groupByItems = dimensionComponents.flatMap((component) => component.groupBy);
  const orderItems = renderSort(sort, selectedDimensions, selectedMetrics);
  const limitClause = renderLimit("limit", limit, 10000);
  const offsetClause = renderLimit("offset", offset, 10000000);

  const graphPatterns = [
    ...CORE_PATTERNS,
    ...optionalPatterns,
    renderedFilters.hitTypeValues,
    ...renderedFilters.patterns,
  ].map((pattern) => pattern.split("\n").map((line) => `    ${line}`).join("\n"));

  return [
    PREFIXES,
    "",
    `SELECT ${selectItems.join("\n       ")}`,
    "WHERE {",
    "  GRAPH ?graph {",
    graphPatterns.join("\n\n"),
    "  }",
    "}",
    groupByItems.length ? `GROUP BY ${groupByItems.join(" ")}` : "",
    orderItems.length ? `ORDER BY ${orderItems.join(" ")}` : "",
    limitClause,
    offsetClause,
  ].filter((line) => line !== "").join("\n");
}
