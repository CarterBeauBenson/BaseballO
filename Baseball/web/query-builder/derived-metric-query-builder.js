const AUTHORITATIVE_GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/";

export const DERIVED_BASE_MEASURES = Object.freeze({
  empty_games: Object.freeze({
    label: "Empty Games",
    variable: "?emptyGames",
    unit: "player-games",
    grain: "player-game",
    dimensions: Object.freeze(["player"]),
    evidenceUniverse: "reviewed-offensive-games",
    zeroDenominator: "unbound",
    subsetOf: Object.freeze(["offensive_games_played"]),
  }),
  offensive_games_played: Object.freeze({
    label: "Offensive Games Played",
    variable: "?offensiveGamesPlayed",
    unit: "player-games",
    grain: "player-game",
    dimensions: Object.freeze(["player"]),
    evidenceUniverse: "reviewed-offensive-games",
    zeroDenominator: "unbound",
    subsetOf: Object.freeze([]),
  }),
});

function requireMeasure(id, role) {
  if (typeof id !== "string" || !DERIVED_BASE_MEASURES[id]) {
    throw new RangeError(`Unknown ${role} measure: ${id}`);
  }
  return DERIVED_BASE_MEASURES[id];
}

function sameValues(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export function buildPublicDerivedMetricCatalog() {
  return {
    measures: Object.fromEntries(Object.entries(DERIVED_BASE_MEASURES).map(([id, measure]) => [
      id,
      {
        label: measure.label,
        unit: measure.unit,
        grain: measure.grain,
        dimensions: measure.dimensions,
        evidenceUniverse: measure.evidenceUniverse,
        zeroDenominator: measure.zeroDenominator,
        subsetOf: measure.subsetOf,
      },
    ])),
    operations: ["divide"],
  };
}

export function compileDerivedMetricQuery({ numerator, denominator } = {}) {
  const numeratorMeasure = requireMeasure(numerator, "numerator");
  const denominatorMeasure = requireMeasure(denominator, "denominator");
  if (numerator === denominator) throw new RangeError("Choose two different base measures");
  if (numeratorMeasure.unit !== denominatorMeasure.unit
      || numeratorMeasure.grain !== denominatorMeasure.grain
      || numeratorMeasure.evidenceUniverse !== denominatorMeasure.evidenceUniverse
      || !sameValues(numeratorMeasure.dimensions, denominatorMeasure.dimensions)) {
    throw new RangeError("The selected measures do not share a compatible semantic contract");
  }

  const isPercentage = numeratorMeasure.subsetOf.includes(denominator);
  const scale = isPercentage ? 100 : 1;
  const expression = `${scale} * xsd:decimal(${numeratorMeasure.variable}) / xsd:decimal(${denominatorMeasure.variable})`;
  const query = `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?player
       ?playerLabel
       ?emptyGames
       ?offensiveGamesPlayed
       (IF(${denominatorMeasure.variable} = 0, 1 / 0, ${expression}) AS ?derivedValue)
WHERE {
  {
    SELECT ?player
           (SAMPLE(?label) AS ?playerLabel)
           (SUM(?emptyFlag) AS ?emptyGames)
           (COUNT(*) AS ?offensiveGamesPlayed)
    WHERE {
      {
        SELECT DISTINCT ?graph ?game ?player ?team ?label
        WHERE {
          GRAPH ?graph {
            ?game a base:BaseballGame .
            ?batterAct a base:BatterAct ;
                       obo:BFO_0000057 ?player ;
                       obo:BFO_0000132 ?plateAppearance .
            ?plateAppearance a base:PlateAppearance ;
              obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 ?game .
            ?halfInning a base:HalfInning ;
                         obo:BFO_0000117 ?plateAppearance .
            BIND(IF(STRENDS(STR(?halfInning), "/top"), base:AwayTeamRole, base:HomeTeamRole) AS ?teamRoleClass)
            ?teamRole a ?teamRoleClass ;
                      obo:BFO_0000197 ?team ;
                      obo:BFO_0000054 ?game .
            OPTIONAL { ?player rdfs:label ?label }
          }
          FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
        }
      }

      # Derived-metric entity filters are inserted here by the allowlisted server.

      MINUS {
        SELECT DISTINCT ?graph ?game
        WHERE {
          GRAPH ?graph {
            ?unknownRecord a base:BaseballEventRecord ;
                           cco:ont00001808 ?unknownResult ;
                           dcterms:identifier ?unknownEventType .
            ?unknownResult a base:BaseballInstitutionalProcess ;
                           obo:BFO_0000132 ?unknownPlateAppearance .
            ?unknownPlateAppearance a base:PlateAppearance .
            FILTER(
              LCASE(STR(?unknownEventType)) NOT IN (
                "home_run", "field_out", "double", "walk", "intent_walk", "force_out",
                "strikeout", "single", "grounded_into_double_play", "sac_fly",
                "double_play", "fielders_choice", "triple", "sac_bunt",
                "fielders_choice_out", "field_error", "hit_by_pitch", "balk",
                "catcher_interf"
              )
            )
          }
          FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
        }
      }

      BIND(EXISTS {
        GRAPH ?graph {
          ?qualifyingBatterAct a base:BatterAct ;
                               obo:BFO_0000057 ?player ;
                               obo:BFO_0000132 ?qualifyingPlateAppearance .
          ?qualifyingPlateAppearance a base:PlateAppearance ;
            obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 ?game .
          ?qualifyingResult obo:BFO_0000132 ?qualifyingPlateAppearance ;
                            a ?qualifyingType .
          VALUES ?qualifyingType {
            base:SingleProcess base:DoubleProcess base:TripleProcess
            base:HomeRunProcess base:WalkProcess base:SacrificeFlyProcess
            base:FieldersChoiceProcess
          }
        }
        FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
      } || EXISTS {
        GRAPH ?graph {
          ?stolenBase a base:StolenBaseProcess ;
                      obo:BFO_0000057 ?player ;
                      obo:BFO_0000132 ?stolenBasePlateAppearance ;
                      obo:BFO_0000117 ?stolenBaseJudgment .
          ?stolenBasePlateAppearance a base:PlateAppearance ;
            obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 ?game .
          ?stolenBaseJudgment a base:StolenBaseJudgmentAct .
        }
        FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
      } AS ?hasContribution)
      BIND(IF(?hasContribution, 0, 1) AS ?emptyFlag)
    }
    GROUP BY ?player
  }
}
ORDER BY DESC(?derivedValue) LCASE(STR(?playerLabel))`;

  return {
    query,
    contract: {
      numerator,
      denominator,
      operation: "divide",
      resultKind: isPercentage ? "percentage" : "ratio",
      label: isPercentage
        ? `${numeratorMeasure.label} percentage`
        : `${numeratorMeasure.label} per ${denominatorMeasure.label}`,
      unit: isPercentage ? "percent" : `${numeratorMeasure.unit} per ${denominatorMeasure.unit}`,
      grain: numeratorMeasure.grain,
      dimensions: numeratorMeasure.dimensions,
      evidenceUniverse: numeratorMeasure.evidenceUniverse,
      zeroDenominator: denominatorMeasure.zeroDenominator,
    },
  };
}
