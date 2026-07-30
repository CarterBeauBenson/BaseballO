const DATA_IRI_PREFIX = "https://baseballontology.org/data/";

const PREFIXES = `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>`;

const TIME_PATTERNS = Object.freeze([
  `?game obo:BFO_0000199/obo:BFO_0000222 ?gameStartInstant .`,
  `?gameStartTimestamp a base:BaseballTimestampICE ;
                      cco:ont00001916 ?gameStartInstant ;
                      cco:ont00001767 ?gameStart .`,
  `BIND(YEAR(?gameStart) AS ?season)`,
]);

const VENUE_PATTERNS = Object.freeze([
  `?field a base:BaseballFieldSite ;
          obo:BFO_0000171 ?venue .`,
  `?venue a base:BaseballVenue ;
          rdfs:label ?venueLabel .`,
]);

const dimensions = {
  season: (optionsQuery = "../../sparql/options/available-seasons.rq") => ({
    label: "Season",
    select: ["?season"],
    groupBy: ["?season"],
    sortExpression: "?season",
    variable: "?season",
    input: "integer",
    optionsQuery,
  }),
  game: (optionsQuery = "../../sparql/options/available-games.rq") => ({
    label: "Game",
    select: ["?game", "?gameStart"],
    groupBy: ["?game", "?gameStart"],
    sortExpression: "?gameStart",
    variable: "?game",
    input: "iri",
    optionsQuery,
  }),
  venue: () => ({
    label: "Venue",
    select: ["?venue", "?venueLabel"],
    groupBy: ["?venue", "?venueLabel"],
    sortExpression: "LCASE(STR(?venueLabel))",
    variable: "?venue",
    input: "iri",
    optionsQuery: "../../sparql/options/available-venues.rq",
  }),
};

const FAMILY_DEFINITIONS = {
  batting: {
    label: "Batting outcomes",
    corePatterns: [
      `?game a base:BaseballGame .`,
      ...TIME_PATTERNS,
      `?resultRecord a base:BaseballEventRecord ;
                    cco:ont00001808 ?result ;
                    dcterms:identifier ?eventType .`,
      `?result a base:BaseballInstitutionalProcess ;
              obo:BFO_0000132 ?plateAppearance ;
              cco:ont00001918 ?field .`,
      `?batterAct a base:BatterAct ;
                 obo:BFO_0000132 ?plateAppearance ;
                 cco:ont00001833 ?player .`,
      `?player rdfs:label ?playerLabel .`,
      ...VENUE_PATTERNS,
    ],
    dimensions: {
      season: dimensions.season(),
      player: {
        label: "Batter",
        select: ["?player", "?playerLabel"],
        groupBy: ["?player", "?playerLabel"],
        sortExpression: "LCASE(STR(?playerLabel))",
        variable: "?player",
        input: "iri",
        optionsQuery: "../../sparql/options/available-players.rq",
      },
      venue: dimensions.venue(),
      event_type: {
        label: "Plate-appearance result",
        select: ["?eventType"],
        groupBy: ["?eventType"],
        sortExpression: "?eventType",
        variable: "?eventType",
        input: "source-token",
        optionsQuery: "../../sparql/options/available-batting-outcomes.rq",
      },
      game: dimensions.game(),
    },
    metrics: {
      plate_appearances: {
        label: "Plate appearances",
        select: "(COUNT(DISTINCT ?result) AS ?plateAppearances)",
        sortExpression: "?plateAppearances",
      },
      hits: {
        label: "Hits",
        select: `(SUM(IF(?eventType IN ("single", "double", "triple", "home_run"), 1, 0)) AS ?hits)`,
        sortExpression: "?hits",
      },
      singles: {
        label: "Singles",
        select: `(SUM(IF(?eventType = "single", 1, 0)) AS ?singles)`,
        sortExpression: "?singles",
      },
      doubles: {
        label: "Doubles",
        select: `(SUM(IF(?eventType = "double", 1, 0)) AS ?doubles)`,
        sortExpression: "?doubles",
      },
      triples: {
        label: "Triples",
        select: `(SUM(IF(?eventType = "triple", 1, 0)) AS ?triples)`,
        sortExpression: "?triples",
      },
      home_runs: {
        label: "Home runs",
        select: `(SUM(IF(?eventType = "home_run", 1, 0)) AS ?homeRuns)`,
        sortExpression: "?homeRuns",
      },
      walks: {
        label: "Walks",
        select: `(SUM(IF(?eventType = "walk", 1, 0)) AS ?walks)`,
        sortExpression: "?walks",
      },
      strikeouts: {
        label: "Strikeouts",
        select: `(SUM(IF(?eventType = "strikeout", 1, 0)) AS ?strikeouts)`,
        sortExpression: "?strikeouts",
      },
      total_bases: {
        label: "Total bases",
        select: `(SUM(IF(?eventType = "single", 1,
                    IF(?eventType = "double", 2,
                    IF(?eventType = "triple", 3,
                    IF(?eventType = "home_run", 4, 0))))) AS ?totalBases)`,
        sortExpression: "?totalBases",
      },
      games: {
        label: "Games",
        select: "(COUNT(DISTINCT ?game) AS ?games)",
        sortExpression: "?games",
      },
    },
  },
  pitching: {
    label: "Pitching and pitch calls",
    corePatterns: [
      `?game a base:BaseballGame .`,
      ...TIME_PATTERNS,
      `?pitch a base:PitchAct ;
             obo:BFO_0000132 ?plateAppearance ;
             cco:ont00001833 ?pitcher ;
             cco:ont00001918 ?field .`,
      `?pitcher rdfs:label ?pitcherLabel .`,
      ...VENUE_PATTERNS,
      `OPTIONAL {
        ?ball a base:BallProcess ;
              obo:BFO_0000062 ?pitch .
      }`,
      `OPTIONAL {
        ?strike a base:StrikeProcess ;
                obo:BFO_0000062 ?pitch .
      }`,
    ],
    dimensions: {
      season: dimensions.season(),
      pitcher: {
        label: "Pitcher",
        select: ["?pitcher", "?pitcherLabel"],
        groupBy: ["?pitcher", "?pitcherLabel"],
        sortExpression: "LCASE(STR(?pitcherLabel))",
        variable: "?pitcher",
        input: "iri",
        optionsQuery: "../../sparql/options/available-pitchers.rq",
      },
      venue: dimensions.venue(),
      game: dimensions.game(),
    },
    metrics: {
      pitches: {
        label: "Pitches",
        select: "(COUNT(DISTINCT ?pitch) AS ?pitches)",
        sortExpression: "?pitches",
      },
      balls: {
        label: "Ball processes",
        select: "(COUNT(DISTINCT ?ball) AS ?balls)",
        sortExpression: "?balls",
      },
      strikes: {
        label: "Strike processes",
        select: "(COUNT(DISTINCT ?strike) AS ?strikes)",
        sortExpression: "?strikes",
      },
      plate_appearances: {
        label: "Plate appearances faced",
        select: "(COUNT(DISTINCT ?plateAppearance) AS ?plateAppearances)",
        sortExpression: "?plateAppearances",
      },
      games: {
        label: "Games",
        select: "(COUNT(DISTINCT ?game) AS ?games)",
        sortExpression: "?games",
      },
    },
  },
  baserunning: {
    label: "Baserunning and scoring",
    corePatterns: [
      `?game a base:BaseballGame .`,
      ...TIME_PATTERNS,
      `?runnerRecord a base:BaseballEventRecord ;
                    cco:ont00001808 ?resolution ;
                    dcterms:identifier ?eventType .`,
      `?resolution a base:RunnerResolutionProcess ;
                  obo:BFO_0000132 ?game ;
                  obo:BFO_0000057 ?player ;
                  cco:ont00001918 ?field .`,
      `?player rdfs:label ?playerLabel .`,
      ...VENUE_PATTERNS,
      `OPTIONAL {
        ?resolution a base:RunProcess .
        BIND(?resolution AS ?run)
      }`,
      `OPTIONAL {
        ?resolution a base:OutProcess .
        BIND(?resolution AS ?out)
      }`,
      `OPTIONAL {
        ?resolution a base:SafeProcess .
        BIND(?resolution AS ?safe)
      }`,
    ],
    dimensions: {
      season: dimensions.season(),
      player: {
        label: "Runner",
        select: ["?player", "?playerLabel"],
        groupBy: ["?player", "?playerLabel"],
        sortExpression: "LCASE(STR(?playerLabel))",
        variable: "?player",
        input: "iri",
        optionsQuery: "../../sparql/options/available-baserunners.rq",
      },
      venue: dimensions.venue(),
      event_type: {
        label: "Runner event",
        select: ["?eventType"],
        groupBy: ["?eventType"],
        sortExpression: "?eventType",
        variable: "?eventType",
        input: "source-token",
        optionsQuery: "../../sparql/options/available-baserunning-events.rq",
      },
      game: dimensions.game(),
    },
    metrics: {
      runner_events: {
        label: "Runner events",
        select: "(COUNT(DISTINCT ?resolution) AS ?runnerEvents)",
        sortExpression: "?runnerEvents",
      },
      runs: {
        label: "Runs",
        select: "(COUNT(DISTINCT ?run) AS ?runs)",
        sortExpression: "?runs",
      },
      outs: {
        label: "Outs",
        select: "(COUNT(DISTINCT ?out) AS ?outs)",
        sortExpression: "?outs",
      },
      safe_resolutions: {
        label: "Safe resolutions",
        select: "(COUNT(DISTINCT ?safe) AS ?safeResolutions)",
        sortExpression: "?safeResolutions",
      },
      stolen_bases: {
        label: "Stolen bases",
        select: `(SUM(IF(STRSTARTS(LCASE(STR(?eventType)), "stolen_base"), 1, 0)) AS ?stolenBases)`,
        sortExpression: "?stolenBases",
      },
      games: {
        label: "Games",
        select: "(COUNT(DISTINCT ?game) AS ?games)",
        sortExpression: "?games",
      },
    },
  },
  games: {
    label: "Games, teams, and officials",
    corePatterns: [
      `?game a base:BaseballGame ;
             cco:ont00001918 ?field .`,
      ...TIME_PATTERNS,
      ...VENUE_PATTERNS,
    ],
    patternComponents: {
      team: [
        `?teamRole a ?teamRoleClass ;
                  obo:BFO_0000197 ?team ;
                  obo:BFO_0000054 ?game .`,
        `?team rdfs:label ?teamLabel .`,
        `VALUES (?teamRoleClass ?side) {
          (base:HomeTeamRole "home")
          (base:AwayTeamRole "away")
        }`,
      ],
      umpire: [
        `?umpireRole a base:UmpireRole ;
                     obo:BFO_0000197 ?umpire ;
                     obo:BFO_0000054 ?game .`,
        `?umpire rdfs:label ?umpireLabel .`,
      ],
      scorer: [
        `?scorerRole a base:OfficialScorerRole ;
                    obo:BFO_0000197 ?officialScorer ;
                    obo:BFO_0000054 ?game .`,
        `?officialScorer rdfs:label ?officialScorerLabel .`,
      ],
    },
    dimensions: {
      season: dimensions.season(),
      venue: dimensions.venue(),
      team: {
        label: "Team",
        select: ["?team", "?teamLabel"],
        groupBy: ["?team", "?teamLabel"],
        sortExpression: "LCASE(STR(?teamLabel))",
        variable: "?team",
        input: "iri",
        requires: ["team"],
        optionsQuery: "../../sparql/options/available-teams.rq",
      },
      side: {
        label: "Home or away",
        select: ["?side"],
        groupBy: ["?side"],
        sortExpression: "?side",
        variable: "?side",
        input: "enum",
        values: ["home", "away"],
        requires: ["team"],
      },
      umpire: {
        label: "Umpire",
        select: ["?umpire", "?umpireLabel"],
        groupBy: ["?umpire", "?umpireLabel"],
        sortExpression: "LCASE(STR(?umpireLabel))",
        variable: "?umpire",
        input: "iri",
        requires: ["umpire"],
        optionsQuery: "../../sparql/options/available-umpires.rq",
      },
      official_scorer: {
        label: "Official scorer",
        select: ["?officialScorer", "?officialScorerLabel"],
        groupBy: ["?officialScorer", "?officialScorerLabel"],
        sortExpression: "LCASE(STR(?officialScorerLabel))",
        variable: "?officialScorer",
        input: "iri",
        requires: ["scorer"],
        optionsQuery: "../../sparql/options/available-official-scorers.rq",
      },
      game: dimensions.game(),
    },
    metrics: {
      games: {
        label: "Games",
        select: "(COUNT(DISTINCT ?game) AS ?games)",
        sortExpression: "?games",
      },
    },
  },
};

export const ANALYTICS_QUERY_FAMILIES = Object.freeze(FAMILY_DEFINITIONS);

function unique(values) {
  return [...new Set(values)];
}

function requireEntry(collection, id, kind) {
  const value = collection[id];
  if (!value) {
    throw new RangeError(`Unknown ${kind}: ${id}`);
  }
  return value;
}

function validateDataIri(value, name) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new TypeError(`${name} must be an absolute IRI`);
  }
  if (!url.href.startsWith(DATA_IRI_PREFIX) || /[<>\s]/u.test(value)) {
    throw new TypeError(`${name} must be a canonical BaseballO data IRI`);
  }
  return url.href;
}

function renderFilter(dimension, value, id) {
  if (dimension.input === "integer") {
    if (!Number.isInteger(value) || value < 1800 || value > 3000) {
      throw new TypeError(`${id} must be an integer between 1800 and 3000`);
    }
    return `FILTER(${dimension.variable} = ${value})`;
  }
  if (dimension.input === "iri") {
    return `VALUES ${dimension.variable} { <${validateDataIri(value, id)}> }`;
  }
  const values = Array.isArray(value) ? unique(value) : [value];
  if (values.length === 0) {
    throw new TypeError(`${id} must contain at least one value`);
  }
  if (dimension.input === "enum") {
    for (const item of values) {
      if (!dimension.values.includes(item)) {
        throw new RangeError(`Unsupported ${id} value: ${item}`);
      }
    }
  } else if (dimension.input === "source-token") {
    for (const item of values) {
      if (typeof item !== "string" || !/^[a-z0-9_]+$/u.test(item)) {
        throw new TypeError(`${id} values must be lowercase source tokens`);
      }
    }
  } else {
    throw new RangeError(`Unsupported filter input type: ${dimension.input}`);
  }
  return `VALUES ${dimension.variable} { ${values.map((item) => `"${item}"`).join(" ")} }`;
}

function renderBoundedClause(name, value, maximum) {
  if (value === undefined) {
    return "";
  }
  if (!Number.isInteger(value) || value < 0 || value > maximum) {
    throw new TypeError(`${name} must be an integer between 0 and ${maximum}`);
  }
  return `${name.toUpperCase()} ${value}`;
}

export function compileAnalyticsQuery({
  family,
  dimensions = ["season"],
  metrics,
  filters = {},
  sort,
  limit = 500,
  offset,
} = {}) {
  const definition = requireEntry(ANALYTICS_QUERY_FAMILIES, family, "query family");
  const selectedDimensionIds = unique(dimensions);
  const selectedMetricIds = unique(metrics ?? [Object.keys(definition.metrics)[0]]);
  if (selectedMetricIds.length === 0) {
    throw new TypeError("At least one metric must be selected");
  }

  const selectedDimensions = selectedDimensionIds.map((id) =>
    requireEntry(definition.dimensions, id, `${family} dimension`));
  const selectedMetrics = selectedMetricIds.map((id) =>
    requireEntry(definition.metrics, id, `${family} metric`));

  const filterPatterns = [];
  const filterDimensions = [];
  for (const [id, value] of Object.entries(filters)) {
    const dimension = requireEntry(definition.dimensions, id, `${family} filter`);
    filterDimensions.push(dimension);
    filterPatterns.push(renderFilter(dimension, value, id));
  }

  const requiredPatternIds = unique([
    ...selectedDimensions.flatMap((component) => component.requires ?? []),
    ...filterDimensions.flatMap((component) => component.requires ?? []),
  ]);
  const componentPatterns = requiredPatternIds.flatMap((id) =>
    requireEntry(definition.patternComponents ?? {}, id, `${family} pattern component`));

  const selectItems = [
    ...selectedDimensions.flatMap((component) => component.select),
    ...selectedMetrics.map((component) => component.select),
  ];
  const groupByItems = selectedDimensions.flatMap((component) => component.groupBy);

  const sortItems = sort === undefined
    ? selectedMetricIds.map((id) => `DESC(${definition.metrics[id].sortExpression})`)
    : sort.map(({ id, direction = "asc" }) => {
      const component = definition.dimensions[id] ?? definition.metrics[id];
      if (!component || (!selectedDimensionIds.includes(id) && !selectedMetricIds.includes(id))) {
        throw new RangeError(`Sort component is not selected: ${id}`);
      }
      if (direction !== "asc" && direction !== "desc") {
        throw new RangeError(`Unsupported sort direction: ${direction}`);
      }
      return direction === "desc"
        ? `DESC(${component.sortExpression})`
        : component.sortExpression;
    });

  const patterns = [
    ...definition.corePatterns,
    ...componentPatterns,
    ...filterPatterns,
  ].map((pattern) => pattern.split("\n").map((line) => `    ${line}`).join("\n"));

  return [
    PREFIXES,
    `SELECT ${selectItems.join("\n       ")}`,
    "WHERE {",
    "  GRAPH ?graph {",
    patterns.join("\n\n"),
    "  }",
    "}",
    groupByItems.length ? `GROUP BY ${groupByItems.join(" ")}` : "",
    sortItems.length ? `ORDER BY ${sortItems.join(" ")}` : "",
    renderBoundedClause("limit", limit, 10000),
    renderBoundedClause("offset", offset, 10000000),
  ].filter(Boolean).join("\n");
}
