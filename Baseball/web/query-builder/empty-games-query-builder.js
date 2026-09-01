const AUTHORITATIVE_GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/";
const XSD = "http://www.w3.org/2001/XMLSchema#";

export const EMPTY_GAME_ANALYSES = Object.freeze({
  players: Object.freeze({
    label: "Players and empty-game ratio",
    description: "Empty games and offensive games played for each batter.",
    limitation: "The ratio is empty games divided by reviewed offensive games in the selected range.",
  }),
  teams: Object.freeze({
    label: "Batting teams",
    description: "Empty player-games and offensive player-games grouped by batting team.",
    limitation: "This is a player-game rate, not the percentage of team games in which nobody contributed.",
  }),
  stretches: Object.freeze({
    label: "Empty-game stretches",
    description: "Consecutive empty offensive appearances by a player within the selected range.",
    limitation: "A stretch is broken by the player's next non-empty offensive game; games outside the selected range are not inspected.",
  }),
  pitcher_matchups: Object.freeze({
    label: "Against pitchers",
    description: "Whole-game empty results grouped by each pitcher the batter faced.",
    limitation: "The empty classification applies to the batter's complete game, not only to plate appearances against the listed pitcher.",
  }),
  games: Object.freeze({
    label: "Individual empty games",
    description: "One row per reviewed empty player-game.",
    limitation: "Use the pitcher-matchup view when pitcher context is needed; this view preserves every reviewed empty player-game.",
  }),
  damage: Object.freeze({
    label: "Most damaging empty games",
    description: "Ranks empty player-games by failed plate appearances with runners on base, out pressure, quickness, and double plays.",
    limitation: "This is a transparent exploratory score: bases are weighted 1/2/3, outs scale from one-third to full pressure, grind above six reduces damage, and double plays receive a 1.25 multiplier capped at 100 per plate appearance.",
  }),
});

function filterClause(variable, value) {
  return value ? `FILTER(?${variable} = <${value}>)` : "";
}

export function compileEmptyGameDamageOpportunityQuery({ player, team, pitcher } = {}) {
  const entityFilters = [
    filterClause("player", player),
    filterClause("team", team),
    filterClause("damagePitcher", pitcher),
  ].filter(Boolean).join("\n  ");
  return `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# Failure-first evidence for damaging empty games. This avoids joining the
# general Empty Games result set to a second corpus-wide aggregation.
SELECT ?graph ?game ?gameStart ?player ?playerLabel ?team ?teamLabel
       ?damagePlateAppearance ?outsBefore
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?failureType), STR(base:)); separator=", ") AS ?failureTypes)
       (MAX(IF(?failureType IN (base:DoublePlayProcess, base:GroundedIntoDoublePlayProcess), 1, 0)) AS ?doublePlay)
       (COALESCE(MAX(?firstFlag), 0) AS ?onFirst)
       (COALESCE(MAX(?secondFlag), 0) AS ?onSecond)
       (COALESCE(MAX(?thirdFlag), 0) AS ?onThird)
       (COUNT(DISTINCT ?damagePitch) AS ?pitches)
       (COUNT(DISTINCT ?damageSwing) AS ?swings)
       (COUNT(DISTINCT ?damageContact) AS ?contacts)
       (COUNT(DISTINCT ?damageFoul) AS ?fouls)
       ?damagePitcher ?damagePitcherLabel
WHERE {
  # Empty player-game tuple scope is inserted here by the allowlisted server.
  GRAPH ?graph {
    ?damageBatterAct a base:BatterAct ;
                     obo:BFO_0000057 ?player ;
                     obo:BFO_0000132 ?damagePlateAppearance .
    ?damagePlateAppearance a base:PlateAppearance ;
      obo:BFO_0000132/obo:BFO_0000132/obo:BFO_0000132 ?game .
    ?game a base:BaseballGame ;
          obo:BFO_0000199/obo:BFO_0000222 ?gameStartInstant .
    ?gameStartTimestamp a base:BaseballTimestampICE ;
                        cco:ont00001916 ?gameStartInstant ;
                        cco:ont00001767 ?gameStart .
    ?halfInning a base:HalfInning ; obo:BFO_0000117 ?damagePlateAppearance .
    BIND(IF(STRENDS(STR(?halfInning), "/top"), base:AwayTeamRole, base:HomeTeamRole) AS ?teamRoleClass)
    ?teamRole a ?teamRoleClass ; obo:BFO_0000197 ?team ; obo:BFO_0000054 ?game .
    ?failureResult obo:BFO_0000132 ?damagePlateAppearance ; a ?failureType .
    VALUES ?failureType {
      base:BattedBallOutProcess base:ForceOutProcess base:StrikeoutProcess
      base:DoublePlayProcess base:GroundedIntoDoublePlayProcess
    }
    ?damageOutCount a base:PlateAppearanceStartOutCountICE ;
                    cco:ont00001808 ?damagePlateAppearance ;
                    cco:ont00001773 ?outsBefore .
    ?damagePitch a base:PitchAct ;
                 obo:BFO_0000132 ?damagePlateAppearance ;
                 obo:BFO_0000057 ?damagePitcher .
    ?damagePitcher a cco:ont00001262 .
    OPTIONAL { ?player rdfs:label ?playerLabel }
    OPTIONAL { ?team rdfs:label ?teamLabel }
    OPTIONAL { ?damagePitcher rdfs:label ?damagePitcherLabel }
    OPTIONAL { ?damageSwing a base:SwingAct ; obo:BFO_0000132 ?damagePlateAppearance }
    OPTIONAL { ?damageContact a base:BatBallContactProcess ; obo:BFO_0000132 ?damagePlateAppearance }
    OPTIONAL { ?damageFoul a base:FoulBallProcess ; obo:BFO_0000132 ?damagePlateAppearance }
    OPTIONAL {
      ?occupancy a base:BaserunnerAtBaseStasis ;
                 obo:BFO_0000132 ?damagePlateAppearance ;
                 obo:BFO_0000057 ?occupiedBase .
      ?occupiedBase a base:Base .
      ?baseIdentifier a cco:ont00000649 ;
                      cco:ont00001916 ?occupiedBase ;
                      cco:ont00001765 ?baseCode .
      BIND(IF(STR(?baseCode) = "1B", 1, 0) AS ?firstFlag)
      BIND(IF(STR(?baseCode) = "2B", 1, 0) AS ?secondFlag)
      BIND(IF(STR(?baseCode) = "3B", 1, 0) AS ?thirdFlag)
    }
  }
  FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
  ${entityFilters}
}
GROUP BY ?graph ?game ?gameStart ?player ?playerLabel ?team ?teamLabel
         ?damagePlateAppearance ?outsBefore
         ?damagePitcher ?damagePitcherLabel
ORDER BY ?gameStart ?game LCASE(STR(?playerLabel)) ?damagePlateAppearance`;
}

export function compileEmptyGameEvidenceQuery({ player, team, pitcher, analysis = "players" } = {}) {
  if (!EMPTY_GAME_ANALYSES[analysis]) throw new RangeError(`Unknown Empty Games analysis: ${analysis}`);
  if (analysis === "damage") {
    return compileEmptyGameEvidenceQuery({ player, team, pitcher, analysis: "games" });
  }
  const includePitchers = Boolean(pitcher) || analysis === "pitcher_matchups";
  const pitcherPattern = includePitchers ? `
        ?pitch a base:PitchAct ;
               obo:BFO_0000132 ?plateAppearance ;
               obo:BFO_0000057 ?pitcher .` : "";
  const pitcherLabelPattern = includePitchers
    ? "GRAPH ?graph { ?pitcher rdfs:label ?pitcherLabel }"
    : "";
  const entityFilters = [
    filterClause("player", player),
    filterClause("team", team),
    filterClause("pitcher", pitcher),
  ].filter(Boolean).join("\n  ");
  return `PREFIX base: <https://baseballontology.org/>
PREFIX cco: <https://www.commoncoreontologies.org/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# One evidence row per batter, game, and observed opposing pitcher. The
# whole-game empty flag is calculated independently of the pitcher dimension.
SELECT DISTINCT ?graph ?game ?gameStart ?player ?playerLabel
                ?team ?teamLabel ?pitcher ?pitcherLabel ?emptyFlag
WHERE {
  {
    SELECT DISTINCT ?graph ?game ?gameStart ?player ?team ?pitcher
    WHERE {
      GRAPH ?graph {
        ?game a base:BaseballGame ;
              obo:BFO_0000199/obo:BFO_0000222 ?gameStartInstant .
        ?gameStartTimestamp a base:BaseballTimestampICE ;
                            cco:ont00001916 ?gameStartInstant ;
                            cco:ont00001767 ?gameStart .
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
${pitcherPattern}
      }
      FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
    }
  }

  ${entityFilters}

  # Completeness gate: do not classify a game whose plate-appearance result
  # result vocabulary falls outside the reviewed world-side result classes.
  MINUS {
    SELECT DISTINCT ?graph ?game
    WHERE {
      GRAPH ?graph {
        ?game a base:BaseballGame .
        ?unknownResult a base:BaseballInstitutionalProcess ;
                       obo:BFO_0000132 ?unknownPlateAppearance .
        ?unknownPlateAppearance a base:PlateAppearance .
        FILTER NOT EXISTS {
          ?unknownResult a ?reviewedResultType .
          VALUES ?reviewedResultType {
            base:SingleProcess base:DoubleProcess base:TripleProcess base:HomeRunProcess
            base:WalkProcess base:StrikeoutProcess base:HitByPitchProcess
            base:FieldersChoiceProcess base:ErrorProcess base:SacrificeFlyProcess
            base:SacrificeBuntProcess base:BattedBallOutProcess base:ForceOutProcess
            base:DoublePlayProcess base:GroundedIntoDoublePlayProcess
            base:BalkProcess base:InterferenceProcess
          }
        }
      }
      FILTER(STRSTARTS(STR(?graph), "${AUTHORITATIVE_GRAPH_PREFIX}"))
    }
  }

  OPTIONAL {
    SELECT DISTINCT ?graph ?game ?player (1 AS ?contributionFlag)
    WHERE {
      {
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
      }
      UNION
      {
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
      }
    }
  }
  BIND(IF(BOUND(?contributionFlag), 0, 1) AS ?emptyFlag)

  OPTIONAL { GRAPH ?graph { ?player rdfs:label ?playerLabel } }
  OPTIONAL { GRAPH ?graph { ?team rdfs:label ?teamLabel } }
  ${pitcherLabelPattern}
}
ORDER BY ?gameStart ?game LCASE(STR(?playerLabel)) LCASE(STR(?pitcherLabel))`;
}

function uri(value) {
  return { type: "uri", value };
}

function literal(value) {
  return { type: "literal", value: String(value) };
}

function typed(value, datatype) {
  return { type: "literal", datatype: `${XSD}${datatype}`, value: String(value) };
}

function ratio(emptyGames, offensiveGames) {
  return offensiveGames === 0 ? null : emptyGames / offensiveGames;
}

function ratioTerms(emptyGames, offensiveGames) {
  const value = ratio(emptyGames, offensiveGames);
  return value === null ? {} : {
    emptyGameRatio: typed(value.toFixed(4), "decimal"),
    emptyGamePercentage: typed((value * 100).toFixed(2), "decimal"),
  };
}

function evidenceRows(payload) {
  const games = new Map();
  for (const row of payload.results?.bindings ?? []) {
    const graph = row.graph?.value;
    const game = row.game?.value;
    const player = row.player?.value;
    if (!graph || !game || !player) continue;
    const key = `${graph}\u001f${player}`;
    let record = games.get(key);
    const empty = row.emptyFlag?.value === "1";
    if (!record) {
      record = {
        graph,
        game,
        gameStart: row.gameStart?.value ?? "",
        player,
        playerLabel: row.playerLabel?.value ?? player.split("/").at(-1),
        team: row.team?.value ?? "",
        teamLabel: row.teamLabel?.value ?? row.team?.value?.split("/").at(-1) ?? "Unknown team",
        empty,
        pitchers: new Map(),
        damageOpportunities: new Map(),
      };
      games.set(key, record);
    } else if (record.empty !== empty) {
      throw new Error(`Conflicting Empty Games evidence for ${game} and ${player}`);
    }
    if (row.pitcher?.value) {
      record.pitchers.set(
        row.pitcher.value,
        row.pitcherLabel?.value ?? row.pitcher.value.split("/").at(-1),
      );
    }
    if (row.damagePlateAppearance?.value) {
      record.damageOpportunities.set(row.damagePlateAppearance.value, {
        plateAppearance: row.damagePlateAppearance.value,
        failureTypes: row.failureTypes?.value ?? "",
        doublePlay: row.doublePlay?.value === "1",
        outsBefore: Number(row.outsBefore?.value ?? 0),
        onFirst: row.onFirst?.value === "1",
        onSecond: row.onSecond?.value === "1",
        onThird: row.onThird?.value === "1",
        pitches: Number(row.pitches?.value ?? 0),
        swings: Number(row.swings?.value ?? 0),
        contacts: Number(row.contacts?.value ?? 0),
        fouls: Number(row.fouls?.value ?? 0),
        pitcher: row.damagePitcher?.value ?? "",
        pitcherLabel: row.damagePitcherLabel?.value
          ?? row.damagePitcher?.value?.split("/").at(-1)
          ?? "Unknown pitcher",
      });
    }
  }
  return [...games.values()];
}

function aggregate(records, keyOf, create) {
  const groups = new Map();
  for (const record of records) {
    const key = keyOf(record);
    if (!groups.has(key)) groups.set(key, create(record));
    const group = groups.get(key);
    group.offensiveGames += 1;
    if (record.empty) group.emptyGames += 1;
  }
  return [...groups.values()];
}

function playerResults(records) {
  return aggregate(records, (record) => record.player, (record) => ({
    player: record.player,
    playerLabel: record.playerLabel,
    emptyGames: 0,
    offensiveGames: 0,
  })).sort((left, right) => right.emptyGames - left.emptyGames
    || right.offensiveGames - left.offensiveGames
    || left.playerLabel.localeCompare(right.playerLabel))
    .map((row) => ({
      player: uri(row.player),
      playerLabel: literal(row.playerLabel),
      emptyGames: typed(row.emptyGames, "integer"),
      offensiveGamesPlayed: typed(row.offensiveGames, "integer"),
      ...ratioTerms(row.emptyGames, row.offensiveGames),
    }));
}

function teamResults(records) {
  const groups = aggregate(records, (record) => record.team, (record) => ({
    team: record.team,
    teamLabel: record.teamLabel,
    emptyGames: 0,
    offensiveGames: 0,
    games: new Set(),
  }));
  for (const record of records) groups.find((group) => group.team === record.team)?.games.add(record.game);
  return groups.sort((left, right) => ratio(right.emptyGames, right.offensiveGames) - ratio(left.emptyGames, left.offensiveGames)
    || left.teamLabel.localeCompare(right.teamLabel))
    .map((row) => ({
      team: uri(row.team),
      teamLabel: literal(row.teamLabel),
      emptyPlayerGames: typed(row.emptyGames, "integer"),
      offensivePlayerGames: typed(row.offensiveGames, "integer"),
      teamGames: typed(row.games.size, "integer"),
      ...ratioTerms(row.emptyGames, row.offensiveGames),
    }));
}

function matchupResults(records) {
  const groups = new Map();
  for (const record of records) {
    for (const [pitcher, pitcherLabel] of record.pitchers) {
      const key = `${record.player}\u001f${pitcher}`;
      if (!groups.has(key)) groups.set(key, {
        player: record.player,
        playerLabel: record.playerLabel,
        pitcher,
        pitcherLabel,
        emptyGames: 0,
        gamesFaced: 0,
      });
      const group = groups.get(key);
      group.gamesFaced += 1;
      if (record.empty) group.emptyGames += 1;
    }
  }
  return [...groups.values()].sort((left, right) => right.emptyGames - left.emptyGames
    || right.gamesFaced - left.gamesFaced
    || left.playerLabel.localeCompare(right.playerLabel)
    || left.pitcherLabel.localeCompare(right.pitcherLabel))
    .map((row) => ({
      player: uri(row.player),
      playerLabel: literal(row.playerLabel),
      pitcher: uri(row.pitcher),
      pitcherLabel: literal(row.pitcherLabel),
      emptyGames: typed(row.emptyGames, "integer"),
      gamesFaced: typed(row.gamesFaced, "integer"),
      ...ratioTerms(row.emptyGames, row.gamesFaced),
    }));
}

function streakResults(records) {
  const byPlayer = new Map();
  for (const record of records) {
    if (!byPlayer.has(record.player)) byPlayer.set(record.player, []);
    byPlayer.get(record.player).push(record);
  }
  const streaks = [];
  for (const appearances of byPlayer.values()) {
    appearances.sort((left, right) => left.gameStart.localeCompare(right.gameStart)
      || left.game.localeCompare(right.game));
    let current = [];
    for (const appearance of appearances) {
      if (appearance.empty) {
        current.push(appearance);
      } else if (current.length) {
        streaks.push({ appearances: current, reachesScopeEnd: false });
        current = [];
      }
    }
    if (current.length) streaks.push({ appearances: current, reachesScopeEnd: true });
  }
  return streaks.sort((left, right) => right.appearances.length - left.appearances.length
    || right.appearances.at(-1).gameStart.localeCompare(left.appearances.at(-1).gameStart)
    || left.appearances[0].playerLabel.localeCompare(right.appearances[0].playerLabel))
    .map(({ appearances, reachesScopeEnd }) => ({
      player: uri(appearances[0].player),
      playerLabel: literal(appearances[0].playerLabel),
      emptyGameStreak: typed(appearances.length, "integer"),
      startGame: uri(appearances[0].game),
      endGame: uri(appearances.at(-1).game),
      startDate: typed(appearances[0].gameStart, "dateTime"),
      endDate: typed(appearances.at(-1).gameStart, "dateTime"),
      reachesScopeEnd: typed(reachesScopeEnd, "boolean"),
    }));
}

function gameResults(records) {
  return records.filter((record) => record.empty)
    .sort((left, right) => right.gameStart.localeCompare(left.gameStart)
      || left.playerLabel.localeCompare(right.playerLabel))
    .map((record) => ({
      gameStart: typed(record.gameStart, "dateTime"),
      game: uri(record.game),
      player: uri(record.player),
      playerLabel: literal(record.playerLabel),
      team: uri(record.team),
      teamLabel: literal(record.teamLabel),
    }));
}

export function scoreEmptyPlateAppearanceDamage({
  outsBefore,
  onFirst,
  onSecond,
  onThird,
  pitches,
  swings,
  contacts,
  fouls,
  doublePlay = false,
}) {
  if (!Number.isInteger(outsBefore) || outsBefore < 0 || outsBefore > 2) {
    throw new RangeError("outsBefore must be 0, 1, or 2");
  }
  const basePressure = Number(Boolean(onFirst))
    + (2 * Number(Boolean(onSecond)))
    + (3 * Number(Boolean(onThird)));
  if (basePressure === 0) return 0;
  const grindScore = Number(pitches) + Number(swings)
    + (2 * Number(contacts)) + (2 * Number(fouls));
  const outPressure = (outsBefore + 1) / 3;
  const quickFailurePressure = Math.min(1, 6 / Math.max(grindScore, 1));
  const doublePlayPressure = doublePlay ? 1.25 : 1;
  return Math.min(
    100,
    100 * (basePressure / 6) * outPressure * quickFailurePressure * doublePlayPressure,
  );
}

function baseState(opportunity) {
  return [
    opportunity.onFirst ? "1B" : "",
    opportunity.onSecond ? "2B" : "",
    opportunity.onThird ? "3B" : "",
  ].filter(Boolean).join(" + ") || "Empty";
}

function damageResults(records) {
  return records.filter((record) => record.empty && record.damageOpportunities.size > 0)
    .map((record) => {
      const opportunities = [...record.damageOpportunities.values()].map((opportunity) => {
        const grindScore = opportunity.pitches + opportunity.swings
          + (2 * opportunity.contacts) + (2 * opportunity.fouls);
        return {
          ...opportunity,
          grindScore,
          baseState: baseState(opportunity),
          damage: scoreEmptyPlateAppearanceDamage(opportunity),
        };
      });
      opportunities.sort((left, right) => right.damage - left.damage
        || left.plateAppearance.localeCompare(right.plateAppearance));
      const worst = opportunities[0];
      return {
        ...record,
        totalDamage: opportunities.reduce((sum, opportunity) => sum + opportunity.damage, 0),
        damagingPlateAppearances: opportunities.filter((opportunity) => opportunity.damage > 0).length,
        doublePlayFailures: opportunities.filter((opportunity) => opportunity.doublePlay).length,
        worst,
      };
    })
    .sort((left, right) => right.totalDamage - left.totalDamage
      || right.worst.damage - left.worst.damage
      || right.gameStart.localeCompare(left.gameStart)
      || left.playerLabel.localeCompare(right.playerLabel))
    .map((record) => ({
      gameStart: typed(record.gameStart, "dateTime"),
      game: uri(record.game),
      player: uri(record.player),
      playerLabel: literal(record.playerLabel),
      team: uri(record.team),
      teamLabel: literal(record.teamLabel),
      totalDamageScore: typed(record.totalDamage.toFixed(2), "decimal"),
      worstPlateAppearanceScore: typed(record.worst.damage.toFixed(2), "decimal"),
      damagingPlateAppearances: typed(record.damagingPlateAppearances, "integer"),
      doublePlayFailures: typed(record.doublePlayFailures, "integer"),
      worstPlateAppearance: uri(record.worst.plateAppearance),
      worstBaseState: literal(record.worst.baseState),
      worstOutsBefore: typed(record.worst.outsBefore, "integer"),
      worstGrindScore: typed(record.worst.grindScore, "integer"),
      worstPitcher: uri(record.worst.pitcher),
      worstPitcherLabel: literal(record.worst.pitcherLabel),
      worstResult: literal(record.worst.failureTypes),
    }));
}

const VARIABLES = Object.freeze({
  players: ["player", "playerLabel", "emptyGames", "offensiveGamesPlayed", "emptyGameRatio", "emptyGamePercentage"],
  teams: ["team", "teamLabel", "emptyPlayerGames", "offensivePlayerGames", "teamGames", "emptyGameRatio", "emptyGamePercentage"],
  stretches: ["player", "playerLabel", "emptyGameStreak", "startGame", "endGame", "startDate", "endDate", "reachesScopeEnd"],
  pitcher_matchups: ["player", "playerLabel", "pitcher", "pitcherLabel", "emptyGames", "gamesFaced", "emptyGameRatio", "emptyGamePercentage"],
  games: ["gameStart", "game", "player", "playerLabel", "team", "teamLabel"],
  damage: ["gameStart", "game", "player", "playerLabel", "team", "teamLabel", "totalDamageScore", "worstPlateAppearanceScore", "damagingPlateAppearances", "doublePlayFailures", "worstPlateAppearance", "worstBaseState", "worstOutsBefore", "worstGrindScore", "worstPitcher", "worstPitcherLabel", "worstResult"],
});

export function aggregateEmptyGameEvidence(payload, analysis = "players", limit = 1000) {
  if (!EMPTY_GAME_ANALYSES[analysis]) throw new RangeError(`Unknown Empty Games analysis: ${analysis}`);
  const records = evidenceRows(payload);
  const allRows = {
    players: playerResults,
    teams: teamResults,
    stretches: streakResults,
    pitcher_matchups: matchupResults,
    games: gameResults,
    damage: damageResults,
  }[analysis](records);
  return {
    head: { vars: VARIABLES[analysis] },
    results: { bindings: allRows.slice(0, limit) },
    totalRowCount: allRows.length,
    evidenceRowCount: payload.results?.bindings?.length ?? 0,
    playerGameCount: records.length,
  };
}

export function buildPublicEmptyGameCatalog() {
  return { analyses: EMPTY_GAME_ANALYSES, defaultAnalysis: "players" };
}
