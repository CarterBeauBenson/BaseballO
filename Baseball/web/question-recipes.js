const PAQ_QUERY_ID = "plate-appearance-fingerprint";

export const QUESTION_GROUPS = Object.freeze([
  Object.freeze({ id: "plate_appearances", label: "Plate appearances" }),
  Object.freeze({ id: "players_matchups", label: "Players and matchups" }),
  Object.freeze({ id: "games_innings", label: "Games and innings" }),
  Object.freeze({ id: "empty_games", label: "Empty Games" }),
  Object.freeze({ id: "decisions", label: "Decisions and review" }),
  Object.freeze({ id: "data_quality", label: "Data quality" }),
]);

const PRESENTATION = Object.freeze({
  "grinder-index": Object.freeze({
    group: "plate_appearances", grain: "One plate appearance", calculation: "Individual score",
  }),
  "swing-to-result-funnel": Object.freeze({
    group: "players_matchups", grain: "One batter over the selected span", calculation: "Cumulative profile",
  }),
  "whiff-and-take-profiles": Object.freeze({
    group: "players_matchups", grain: "One batter-pitcher pairing", calculation: "Cumulative profile",
  }),
  "batter-pitcher-matchup-profiles": Object.freeze({
    group: "players_matchups", grain: "One batter-pitcher pairing", calculation: "Cumulative profile",
  }),
  "productive-plate-appearances": Object.freeze({
    group: "plate_appearances", grain: "One plate appearance", calculation: "Individual evidence",
  }),
  "contact-conversion": Object.freeze({
    group: "players_matchups", grain: "One batter and outcome", calculation: "Cumulative profile",
  }),
  "half-inning-rally-anatomy": Object.freeze({
    group: "games_innings", grain: "One half-inning", calculation: "Cumulative event totals",
  }),
  "game-action-density": Object.freeze({
    group: "games_innings", grain: "One game", calculation: "Rate",
  }),
  "scorer-classification-profile": Object.freeze({
    group: "decisions", grain: "One scorer and classification", calculation: "Cumulative profile",
  }),
  "umpire-call-profile": Object.freeze({
    group: "decisions", grain: "One umpire and call transition", calculation: "Cumulative profile",
  }),
  "review-outcome-profile": Object.freeze({
    group: "decisions", grain: "One review transition", calculation: "Cumulative profile",
  }),
  "hit-diversity": Object.freeze({
    group: "games_innings", grain: "One player-game", calculation: "Cumulative game evidence",
  }),
  "base-destination-profile": Object.freeze({
    group: "players_matchups", grain: "One runner and destination", calculation: "Cumulative profile",
  }),
  "steal-attempt-efficiency": Object.freeze({
    group: "players_matchups", grain: "One runner over the selected span", calculation: "Rate",
  }),
  "unproductive-contact-games": Object.freeze({
    group: "players_matchups", grain: "One player over the selected span", calculation: "Cumulative game count",
  }),
  "event-chain-integrity": Object.freeze({
    group: "data_quality", grain: "One structural finding", calculation: "Integrity audit",
  }),
});

const ADVANCED_QUESTIONS = Object.freeze({
  [PAQ_QUERY_ID]: Object.freeze([
    Object.freeze({
      id: "paq-plate-appearances",
      label: "Which plate appearances have the highest PAQ-1.0?",
      view: "plate_appearances",
      group: "plate_appearances",
      grain: "One plate appearance",
      calculation: "Individual score",
    }),
    Object.freeze({
      id: "paq-player-averages",
      label: "Which players have the highest average PAQ-1.0?",
      view: "player_averages",
      group: "players_matchups",
      grain: "One player over the selected span",
      calculation: "Average",
    }),
  ]),
  "grinder-index": "Which plate appearances have the highest Grind Score?",
  "swing-to-result-funnel": "Which batters convert swings into positive results?",
  "whiff-and-take-profiles": "How do batters and pitchers compare on whiffs and takes?",
  "batter-pitcher-matchup-profiles": "How have batters and pitchers matched up?",
  "productive-plate-appearances": "Which non-hit plate appearances advanced another runner?",
  "contact-conversion": "What results followed terminal contact?",
  "half-inning-rally-anatomy": "What made up each half-inning rally?",
  "game-action-density": "Which games had the most action per minute?",
  "scorer-classification-profile": "What decisions did each official scorer make?",
  "umpire-call-profile": "How did umpires call pitches before and after review?",
  "review-outcome-profile": "How did replay reviews change on-field decisions?",
  "hit-diversity": "Which players recorded every hit type?",
  "base-destination-profile": "Where did runners safely finish?",
  "steal-attempt-efficiency": "How often did each runner succeed on stolen-base attempts?",
  "unproductive-contact-games": "Which players had contact games without a positive result?",
  "event-chain-integrity": "Which mapped event chains need attention?",
});

const EMPTY_GAME_QUESTIONS = Object.freeze({
  players: "Who has the highest Empty Game Rate?",
  teams: "Which batting teams have the highest Empty Game Rate?",
  stretches: "Who has the longest Empty Game streaks?",
  pitcher_matchups: "Against which pitchers do players have the most Empty Games?",
  games: "Which player-games qualify as Empty Games?",
  damage: "Which Empty Games have the highest Damage Score?",
});

function advancedRecipes(advancedCatalog) {
  return advancedCatalog.flatMap((entry) => {
    const presentation = ADVANCED_QUESTIONS[entry.id];
    if (!presentation) throw new Error(`No UI question is defined for ${entry.id}.`);
    if (Array.isArray(presentation)) {
      return presentation.map((recipe) => ({
        ...recipe,
        kind: "advanced",
        queryId: entry.id,
      }));
    }
    const metadata = PRESENTATION[entry.id];
    if (!metadata) throw new Error(`No interaction metadata is defined for ${entry.id}.`);
    return [{
      id: `advanced-${entry.id}`,
      kind: "advanced",
      queryId: entry.id,
      label: presentation,
      ...metadata,
    }];
  });
}

function emptyGameRecipes(emptyGameCatalog) {
  return Object.keys(emptyGameCatalog.analyses ?? {}).map((analysis) => {
    const label = EMPTY_GAME_QUESTIONS[analysis];
    if (!label) throw new Error(`No UI question is defined for Empty Games analysis ${analysis}.`);
    return {
      id: `empty-games-${analysis.replaceAll("_", "-")}`,
      kind: "empty_games",
      analysis,
      label,
      group: "empty_games",
      grain: analysis === "damage" || analysis === "games"
        ? "One player-game"
        : analysis === "stretches"
          ? "One player sequence"
          : analysis === "pitcher_matchups"
            ? "One batter-pitcher pairing"
            : analysis === "teams"
              ? "One batting team over the selected span"
              : "One player over the selected span",
      calculation: analysis === "players" || analysis === "teams"
        ? "Rate"
        : analysis === "stretches"
          ? "Sequence and trend"
          : analysis === "damage"
            ? "Individual damage score"
            : analysis === "games"
              ? "Individual classification"
              : "Cumulative matchup count",
    };
  });
}

export function buildQuestionRecipes(advancedCatalog, emptyGameCatalog) {
  const advanced = advancedRecipes(advancedCatalog);
  const featuredIds = new Set(["paq-plate-appearances", "paq-player-averages", "advanced-grinder-index"]);
  const featured = advanced.filter((recipe) => featuredIds.has(recipe.id));
  const remaining = advanced.filter((recipe) => !featuredIds.has(recipe.id));
  return [...featured, ...emptyGameRecipes(emptyGameCatalog), ...remaining];
}

export function questionRecipeById(recipes, id) {
  return recipes.find((recipe) => recipe.id === id) ?? null;
}

export function groupedQuestionRecipes(recipes) {
  const knownGroups = new Set(QUESTION_GROUPS.map((group) => group.id));
  const unknown = recipes.filter((recipe) => !knownGroups.has(recipe.group));
  if (unknown.length) {
    throw new Error(`Questions have unknown interaction groups: ${unknown.map((recipe) => recipe.id).join(", ")}`);
  }
  return QUESTION_GROUPS.map((group) => ({
    ...group,
    recipes: recipes.filter((recipe) => recipe.group === group.id),
  })).filter((group) => group.recipes.length);
}

export const QUESTION_RECIPE_COUNTS = Object.freeze({ advancedQueries: 17, questions: 24 });
