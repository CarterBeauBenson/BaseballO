import { sortBindings } from "./result-sort.js";
import {
  buildQuestionRecipes,
  groupedQuestionRecipes,
  questionRecipeById,
} from "./question-recipes.js";

const GOOD_AT_BAT_QUERY_ID = "plate-appearance-fingerprint";

const DEFAULT_SELECTIONS = Object.freeze({
  batting: {
    dimensions: ["player"],
    metrics: ["hits", "home_runs"],
  },
  pitching: {
    dimensions: ["pitcher"],
    metrics: ["pitches", "balls", "called_strikes", "swinging_strikes", "fouls", "in_play", "hit_batters"],
  },
  baserunning: {
    dimensions: ["player"],
    metrics: ["runner_events", "runs", "stolen_bases"],
  },
  games: {
    dimensions: ["venue"],
    metrics: ["games"],
  },
});

const SPECIAL_FILTERS = Object.freeze({
  advanced: [
    { id: "season", label: "Season", input: "integer", optionFamily: "games" },
    { id: "game", label: "Game", input: "iri", optionFamily: "games" },
    { id: "team", label: "Team in game", input: "iri", optionFamily: "games" },
    { id: "venue", label: "Venue", input: "iri", optionFamily: "games" },
  ],
  empty_games: [
    { id: "season", label: "Season", input: "integer", optionFamily: "games" },
    { id: "game", label: "Game", input: "iri", optionFamily: "games" },
    { id: "team", label: "Batting team", input: "iri", optionFamily: "games" },
    { id: "venue", label: "Venue", input: "iri", optionFamily: "games" },
    { id: "player", label: "Batter", input: "iri", optionFamily: "batting" },
    { id: "pitcher", label: "Pitcher faced", input: "iri", optionFamily: "pitching" },
  ],
  derived_metrics: [
    { id: "season", label: "Season", input: "integer", optionFamily: "games" },
    { id: "game", label: "Game", input: "iri", optionFamily: "games" },
    { id: "team", label: "Batting team", input: "iri", optionFamily: "games" },
    { id: "venue", label: "Venue", input: "iri", optionFamily: "games" },
    { id: "player", label: "Batter", input: "iri", optionFamily: "batting" },
  ],
});

const elements = {
  connectionPill: document.querySelector("#connection-pill"),
  connectionText: document.querySelector("#connection-text"),
  gameCount: document.querySelector("#game-count"),
  servingStatus: document.querySelector("#serving-status"),
  builderTitle: document.querySelector("#builder-title"),
  familyTabs: document.querySelector("#family-tabs"),
  exploreSubjectField: document.querySelector("#explore-subject-field"),
  exploreSubject: document.querySelector("#explore-subject"),
  questionTypeField: document.querySelector("#question-type-field"),
  questionType: document.querySelector("#question-type"),
  questionContext: document.querySelector("#question-context"),
  scopeSummary: document.querySelector("#scope-summary"),
  gameSet: document.querySelector("#game-set"),
  datePreset: document.querySelector("#date-preset"),
  customDateFields: document.querySelector("#custom-date-fields"),
  dateStart: document.querySelector("#date-start"),
  dateEnd: document.querySelector("#date-end"),
  dateScopeStatus: document.querySelector("#date-scope-status"),
  form: document.querySelector("#query-form"),
  emptyGamesBuilder: document.querySelector("#empty-games-builder"),
  emptyGamesAnalysis: document.querySelector("#empty-games-analysis"),
  emptyGamesAnalysisDescription: document.querySelector("#empty-games-analysis-description"),
  emptyGamesQuestionDescription: document.querySelector("#empty-games-question-description"),
  emptyGamesMath: document.querySelector("#empty-games-math"),
  emptyGamesFilterControls: document.querySelector("#empty-games-filter-controls"),
  runEmptyGamesButton: document.querySelector("#run-empty-games-button"),
  resetEmptyGamesButton: document.querySelector("#reset-empty-games-button"),
  derivedBuilder: document.querySelector("#derived-builder"),
  derivedFilterControls: document.querySelector("#derived-filter-controls"),
  derivedNumerator: document.querySelector("#derived-numerator"),
  derivedDenominator: document.querySelector("#derived-denominator"),
  derivedContractText: document.querySelector("#derived-contract-text"),
  derivedMath: document.querySelector("#derived-math"),
  runDerivedButton: document.querySelector("#run-derived-button"),
  resetDerivedButton: document.querySelector("#reset-derived-button"),
  advancedBuilder: document.querySelector("#advanced-builder"),
  advancedFilterControls: document.querySelector("#advanced-filter-controls"),
  advancedSelect: document.querySelector("#advanced-query-select"),
  advancedQueryField: document.querySelector("#advanced-query-field"),
  paqViewField: document.querySelector("#paq-view-field"),
  paqView: document.querySelector("#paq-view"),
  paqMinimumPaField: document.querySelector("#paq-minimum-pa-field"),
  paqMinimumPa: document.querySelector("#paq-minimum-pa"),
  advancedMode: document.querySelector("#advanced-mode"),
  advancedBuilderTitle: document.querySelector("#advanced-builder-title"),
  advancedClaim: document.querySelector("#advanced-claim"),
  advancedEvidenceNote: document.querySelector("#advanced-evidence-note span"),
  paqFieldGuide: document.querySelector("#paq-field-guide"),
  paqMath: document.querySelector("#paq-math"),
  runAdvancedButton: document.querySelector("#run-advanced-button"),
  runAdvancedLabel: document.querySelector("#run-advanced-label"),
  resetAdvancedButton: document.querySelector("#reset-advanced-button"),
  dimensionChoices: document.querySelector("#dimension-choices"),
  metricChoices: document.querySelector("#metric-choices"),
  metricHelp: document.querySelector("#metric-help"),
  filterControls: document.querySelector("#filter-controls"),
  runButton: document.querySelector("#run-button"),
  resetButton: document.querySelector("#reset-button"),
  exportButton: document.querySelector("#export-button"),
  resultsTitle: document.querySelector("#results-title"),
  resultMeta: document.querySelector("#result-meta"),
  emptyState: document.querySelector("#empty-state"),
  loadingState: document.querySelector("#loading-state"),
  errorState: document.querySelector("#error-state"),
  errorMessage: document.querySelector("#error-message"),
  tableWrap: document.querySelector("#table-wrap"),
  resultsTable: document.querySelector("#results-table"),
  queryInspector: document.querySelector("#query-inspector"),
  queryCode: document.querySelector("#query-code"),
  copyQueryButton: document.querySelector("#copy-query-button"),
  suggestionList: document.querySelector("#suggestion-list"),
  plateAppearanceDialog: document.querySelector("#plate-appearance-dialog"),
  plateAppearanceDialogClose: document.querySelector("#plate-appearance-dialog-close"),
  plateAppearanceEvidence: document.querySelector("#plate-appearance-evidence"),
  toast: document.querySelector("#toast"),
};

let catalog = {};
let advancedCatalog = [];
let emptyGameCatalog = { analyses: {}, defaultAnalysis: "players" };
let derivedCatalog = { measures: {} };
let questionRecipes = [];
let currentFamily = "advanced";
let selectedQuestionRecipeId = "paq-plate-appearances";
let selectedQuestionId = GOOD_AT_BAT_QUERY_ID;
let selectedAdvancedView = "plate_appearances";
let selectedEmptyGameAnalysis = "players";
let lastResponse = null;
let currentSort = null;
let toastTimer;
const optionCache = new Map();

function dateScopeRequest() {
  const preset = elements.datePreset.value;
  if (preset !== "custom") return { preset };
  if (!elements.dateStart.value || !elements.dateEnd.value) {
    throw new Error("Choose both dates for a custom range.");
  }
  if (elements.dateStart.value > elements.dateEnd.value) {
    throw new Error("The custom start date must not be after the end date.");
  }
  return { preset, startDate: elements.dateStart.value, endDate: elements.dateEnd.value };
}

function gameSetRequest() {
  return elements.gameSet.value;
}

function dateLabel(value) {
  if (!value) return "No dated games";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

async function refreshDateScope() {
  const request = dateScopeRequest();
  const search = new URLSearchParams({ ...request, gameSet: gameSetRequest() });
  elements.dateScopeStatus.textContent = "Resolving loaded game dates…";
  const { scope } = await fetchJson(`/api/date-scope?${search}`);
  if (scope.availableStartDate) {
    elements.dateStart.min = scope.availableStartDate;
    elements.dateEnd.min = scope.availableStartDate;
  }
  if (scope.availableEndDate) {
    elements.dateStart.max = scope.availableEndDate;
    elements.dateEnd.max = scope.availableEndDate;
  }
  elements.dateScopeStatus.textContent = scope.startDate
    ? `${dateLabel(scope.startDate)} – ${dateLabel(scope.endDate)} · ${scope.gameCount} loaded game${scope.gameCount === 1 ? "" : "s"}`
    : "No dated authoritative games are loaded.";
  const gameSetLabel = elements.gameSet.selectedOptions[0]?.textContent ?? "Selected games";
  const rangeLabel = elements.datePreset.selectedOptions[0]?.textContent ?? "Selected dates";
  elements.scopeSummary.textContent = scope.startDate
    ? `${gameSetLabel} · ${dateLabel(scope.startDate)} – ${dateLabel(scope.endDate)}`
    : `${gameSetLabel} · ${rangeLabel}`;
  return scope;
}

function createElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function showToast(message) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  toastTimer = setTimeout(() => {
    elements.toast.hidden = true;
  }, 2400);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error ?? `Request failed with status ${response.status}`);
  }
  return payload;
}

function setConnection({ connected, games, serving = {} }) {
  elements.connectionPill.classList.toggle("connected", connected);
  elements.connectionPill.classList.toggle("disconnected", !connected);
  elements.connectionText.textContent = connected ? "Local graph connected" : "Graph unavailable";
  elements.gameCount.textContent = connected
    ? `${games} MLB games`
    : "Start Fuseki to explore loaded games";
  elements.servingStatus.textContent = serving.available
    ? `SQL PAQ ready · ${Number(serving.advancedBindings ?? 0).toLocaleString()} reviewed rows · build ${serving.buildId}`
    : "SQL serving unavailable · using authoritative RDF fallback";
}

function activeQuestionRecipe() {
  return questionRecipeById(questionRecipes, selectedQuestionRecipeId);
}

function selectQuestion(recipeId) {
  const recipe = questionRecipeById(questionRecipes, recipeId);
  if (!recipe) return;
  selectedQuestionRecipeId = recipe.id;
  if (recipe.kind === "empty_games") {
    selectedEmptyGameAnalysis = recipe.analysis;
    configureFamily("empty_games");
    return;
  }
  selectedQuestionId = recipe.queryId;
  selectedAdvancedView = recipe.view ?? "plate_appearances";
  configureFamily("advanced");
}

function renderFamilyTabs() {
  const exploreFamilies = [
    ...Object.entries(catalog),
    ...(advancedCatalog.some((entry) => entry.featured)
      ? [["good_at_bat", { label: "Plate Appearance Quality" }]]
      : []),
  ];
  const mode = currentFamily === "derived_metrics"
    ? "derived"
    : ["empty_games", "advanced"].includes(currentFamily) ? "questions" : "explore";
  const modes = [
    ["explore", "Explore"],
    ["questions", "Questions"],
    ["derived", "Build a Metric"],
  ];
  const buttons = modes.map(([modeId, label]) => {
    const button = createElement("button", "", label);
    button.type = "button";
    button.dataset.mode = modeId;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(modeId === mode));
    button.addEventListener("click", () => {
      if (modeId === "questions") selectQuestion(selectedQuestionRecipeId);
      else configureFamily(modeId === "explore" ? "batting" : "derived_metrics");
    });
    return button;
  });
  elements.familyTabs.replaceChildren(...buttons);

  const exploreOptions = exploreFamilies.map(([familyId, family]) => {
    const option = createElement("option", "", family.label);
    option.value = familyId;
    return option;
  });
  elements.exploreSubject.replaceChildren(...exploreOptions);
  if (mode === "explore") elements.exploreSubject.value = currentFamily;
  elements.exploreSubjectField.hidden = mode !== "explore";
  elements.questionTypeField.hidden = mode !== "questions";
  const questionGroups = groupedQuestionRecipes(questionRecipes).map((group) => {
    const optgroup = document.createElement("optgroup");
    optgroup.label = group.label;
    optgroup.append(...group.recipes.map((recipe) => {
      const option = createElement("option", "", recipe.label);
      option.value = recipe.id;
      return option;
    }));
    return optgroup;
  });
  elements.questionType.replaceChildren(...questionGroups);
  if (mode === "questions") elements.questionType.value = selectedQuestionRecipeId;
  const recipe = activeQuestionRecipe();
  elements.questionContext.hidden = mode !== "questions" || !recipe;
  if (recipe) {
    elements.questionContext.textContent = `Answer: ${recipe.grain} · Calculation: ${recipe.calculation}`;
  }
}

function advancedModeLabel(mode) {
  return {
    "positive-evidence": "Positive evidence / Authoritative only",
    "completeness-gated": "Completeness-gated / Authoritative only",
    "integrity-audit": "Integrity audit / Authoritative only",
    "decision-support": "Decision support / unified evidence",
  }[mode] ?? "Authoritative semantic query";
}

function renderAdvancedDefinition() {
  const selected = advancedCatalog.find((entry) => entry.id === elements.advancedSelect.value)
    ?? advancedCatalog[0];
  if (!selected) return;
  elements.advancedSelect.value = selected.id;
  elements.advancedBuilderTitle.textContent = currentFamily === "advanced"
    ? activeQuestionRecipe()?.label ?? "Ask a reviewed question"
    : "Plate Appearance Quality";
  elements.advancedMode.textContent = advancedModeLabel(selected.semanticMode);
  elements.advancedClaim.textContent = selected.claim;
  elements.advancedEvidenceNote.textContent = selected.semanticMode === "positive-evidence"
    ? "This query counts explicit mapped evidence and does not turn missing events into facts."
    : selected.semanticMode === "completeness-gated"
      ? "This query uses absence or a mapped denominator only within its documented source-coverage boundary."
      : selected.semanticMode === "decision-support"
        ? "PAQ is derived from the available evidence, versioned, and shown with its component ratings; it is not asserted as an authoritative fact."
        : "Every returned row is a structural finding. Zero rows is the ideal result, not missing data.";
}

function renderAdvancedBuilder(featuredOnly = false) {
  const entries = featuredOnly
    ? advancedCatalog.filter((entry) => entry.featured && entry.id === GOOD_AT_BAT_QUERY_ID)
    : advancedCatalog;
  const options = entries.map((entry) => {
    const option = createElement("option", "", entry.label);
    option.value = entry.id;
    return option;
  });
  elements.advancedSelect.replaceChildren(...options);
  if (!featuredOnly && entries.some((entry) => entry.id === selectedQuestionId)) {
    elements.advancedSelect.value = selectedQuestionId;
  }
  if (!elements.advancedSelect.value && entries[0]) elements.advancedSelect.value = entries[0].id;
  if (featuredOnly) {
    elements.paqView.value = selectedAdvancedView;
  } else {
    selectedQuestionId = elements.advancedSelect.value;
  }
  // Questions are selected once in the top-level Questions menu.
  elements.advancedQueryField.hidden = true;
  elements.paqViewField.hidden = !featuredOnly;
  const isPaq = elements.advancedSelect.value === GOOD_AT_BAT_QUERY_ID;
  const paqView = featuredOnly ? elements.paqView.value : selectedAdvancedView;
  elements.paqMinimumPaField.hidden = !isPaq || paqView !== "player_averages";
  elements.paqFieldGuide.hidden = !isPaq;
  elements.paqMath.hidden = !isPaq;
  elements.runAdvancedLabel.textContent = featuredOnly ? "Explore plate appearances" : "Run reviewed question";
  renderAdvancedDefinition();
}

function renderEmptyGameDefinition() {
  const selected = emptyGameCatalog.analyses[elements.emptyGamesAnalysis.value]
    ?? emptyGameCatalog.analyses[emptyGameCatalog.defaultAnalysis];
  if (!selected) return;
  elements.emptyGamesAnalysisDescription.textContent = `${selected.description} ${selected.limitation}`;
  elements.emptyGamesQuestionDescription.textContent = `${selected.description} ${selected.limitation}`;
  elements.emptyGamesMath.hidden = elements.emptyGamesAnalysis.value !== "damage";
  elements.emptyGamesBuilder.querySelector("#empty-games-builder-title").textContent =
    activeQuestionRecipe()?.label ?? selected.label;
}

function renderEmptyGameBuilder() {
  const options = Object.entries(emptyGameCatalog.analyses).map(([id, analysis]) => {
    const option = createElement("option", "", analysis.label);
    option.value = id;
    return option;
  });
  elements.emptyGamesAnalysis.replaceChildren(...options);
  elements.emptyGamesAnalysis.value = selectedEmptyGameAnalysis;
  renderEmptyGameDefinition();
}

function renderDerivedContract() {
  const numeratorId = elements.derivedNumerator.value;
  const denominatorId = elements.derivedDenominator.value;
  const numerator = derivedCatalog.measures[numeratorId];
  const denominator = derivedCatalog.measures[denominatorId];
  if (!numerator || !denominator) return;
  if (numeratorId === denominatorId) {
    elements.derivedContractText.textContent = "Choose two different base measures.";
    elements.runDerivedButton.disabled = true;
    return;
  }
  const kind = numerator.subsetOf.includes(denominatorId) ? "Percentage" : "Ratio";
  elements.derivedContractText.textContent = `${kind} · ${numerator.grain} grain · ${numerator.evidenceUniverse.replaceAll("-", " ")} · zero denominator returns no value.`;
  const scale = kind === "Percentage" ? "100 × " : "";
  const suffix = kind === "Percentage" ? "%" : "";
  const math = createElement("p");
  math.append(
    createElement("strong", "", `${numerator.label} ${kind.toLowerCase()} = `),
    document.createTextNode(`${scale}${numerator.label} ÷ ${denominator.label}${suffix}. `),
    document.createTextNode("Rows with a zero denominator have no calculated value."),
  );
  elements.derivedMath.replaceChildren(math);
  elements.runDerivedButton.disabled = false;
}

function renderDerivedBuilder() {
  const options = Object.entries(derivedCatalog.measures).map(([id, measure]) => {
    const option = createElement("option", "", measure.label);
    option.value = id;
    return option;
  });
  elements.derivedNumerator.replaceChildren(...options.map((option) => option.cloneNode(true)));
  elements.derivedDenominator.replaceChildren(...options.map((option) => option.cloneNode(true)));
  elements.derivedNumerator.value = "empty_games";
  elements.derivedDenominator.value = "offensive_games_played";
  renderDerivedContract();
}

function createChoice(kind, id, label, selected, description) {
  const wrapper = createElement("div", "choice");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = kind;
  input.value = id;
  input.id = `${kind}-${id}`;
  input.checked = selected;
  const labelElement = createElement("label", "", label);
  labelElement.htmlFor = input.id;
  if (description) labelElement.title = description;
  wrapper.append(input, labelElement);
  return wrapper;
}

function renderMetricHelp() {
  const family = catalog[currentFamily];
  if (!family || !elements.metricHelp) return;
  const selected = selectedValues("metric")
    .map((id) => family.metrics[id])
    .filter((metric) => metric?.description);
  elements.metricHelp.hidden = selected.length === 0;
  elements.metricHelp.replaceChildren(...selected.map((metric) => {
    const row = createElement("p");
    row.append(
      createElement("strong", "", `${metric.label}: `),
      document.createTextNode(metric.description),
    );
    return row;
  }));
}

function optionLabel() {
  return "All values";
}

async function getOptions(familyId, dimensionId) {
  const gameSet = gameSetRequest();
  const key = `${gameSet}:${familyId}:${dimensionId}`;
  if (!optionCache.has(key)) {
    optionCache.set(key, fetchJson(`/api/options?family=${encodeURIComponent(familyId)}&dimension=${encodeURIComponent(dimensionId)}&gameSet=${encodeURIComponent(gameSet)}`));
  }
  return optionCache.get(key);
}

async function populateFilter(select, familyId, dimensionId, activeFamilyId = familyId) {
  try {
    const { options } = await getOptions(familyId, dimensionId);
    if (!select.isConnected || currentFamily !== activeFamilyId) return;
    const allOption = createElement("option", "", optionLabel());
    allOption.value = "";
    const optionElements = options.map(({ value, label }) => {
      const option = createElement("option", "", label);
      option.value = value;
      return option;
    });
    select.replaceChildren(allOption, ...optionElements);
    select.disabled = false;
  } catch (error) {
    if (!select.isConnected || currentFamily !== activeFamilyId) return;
    const failedOption = createElement("option", "", "Options unavailable");
    failedOption.value = "";
    select.replaceChildren(failedOption);
    select.disabled = true;
  }
}

function specialFilterSpecs(familyId) {
  if (!["advanced", "good_at_bat"].includes(familyId)) return SPECIAL_FILTERS[familyId];
  const selected = advancedCatalog.find((entry) => entry.id === elements.advancedSelect.value)
    ?? advancedCatalog[0];
  return [
    ...SPECIAL_FILTERS.advanced,
    ...(selected?.resultFilters ?? []).map((filter) => ({
      ...filter,
      input: "iri",
      optionDimension: filter.optionDimension ?? filter.id,
    })),
  ];
}

function renderSpecialFilters(familyId) {
  const container = {
    advanced: elements.advancedFilterControls,
    good_at_bat: elements.advancedFilterControls,
    derived_metrics: elements.derivedFilterControls,
    empty_games: elements.emptyGamesFilterControls,
  }[familyId];
  const controls = specialFilterSpecs(familyId).map((spec) => {
    const wrapper = createElement("div", "filter-field");
    const label = createElement("label", "", spec.label);
    const select = document.createElement("select");
    label.htmlFor = `filter-${familyId}-${spec.id}`;
    select.id = label.htmlFor;
    select.dataset.filter = spec.id;
    select.dataset.input = spec.input;
    select.disabled = true;
    const loadingOption = createElement("option", "", "Loading values…");
    loadingOption.value = "";
    select.append(loadingOption);
    wrapper.append(label, select);
    void populateFilter(select, spec.optionFamily, spec.optionDimension ?? spec.id, familyId);
    return wrapper;
  });
  container.replaceChildren(...controls);
}

function filtersFrom(container) {
  return Object.fromEntries([...container.querySelectorAll("select[data-filter]")]
    .filter((select) => select.value)
    .map((select) => [
      select.dataset.filter,
      select.dataset.input === "integer" ? Number.parseInt(select.value, 10) : select.value,
    ]));
}

function renderBuilder() {
  const family = catalog[currentFamily];
  const defaults = DEFAULT_SELECTIONS[currentFamily];
  const dimensionChoices = Object.entries(family.dimensions).map(([id, dimension]) =>
    createChoice("dimension", id, dimension.label, defaults.dimensions.includes(id)));
  const metricChoices = Object.entries(family.metrics).map(([id, metric]) =>
    createChoice("metric", id, metric.label, defaults.metrics.includes(id), metric.description));
  elements.dimensionChoices.replaceChildren(...dimensionChoices);
  elements.metricChoices.replaceChildren(...metricChoices);
  elements.metricChoices.onchange = renderMetricHelp;
  renderMetricHelp();

  const filters = Object.entries(family.dimensions).flatMap(([dimensionId, dimension]) => {
    if (!dimension.hasOptions) return [];
    const wrapper = createElement("div", "filter-field");
    const label = createElement("label", "", dimension.label);
    const select = document.createElement("select");
    label.htmlFor = `filter-${currentFamily}-${dimensionId}`;
    select.id = label.htmlFor;
    select.dataset.filter = dimensionId;
    select.dataset.input = dimension.input;
    select.disabled = true;
    const loadingOption = createElement("option", "", "Loading values…");
    loadingOption.value = "";
    select.append(loadingOption);
    wrapper.append(label, select);
    void populateFilter(select, currentFamily, dimensionId);
    return [wrapper];
  });
  elements.filterControls.replaceChildren(...filters);
}

function configureFamily(familyId) {
  currentFamily = familyId;
  renderFamilyTabs();
  const isEmptyGames = familyId === "empty_games";
  const isGoodAtBat = familyId === "good_at_bat";
  const isAdvanced = familyId === "advanced" || isGoodAtBat;
  const isDerived = familyId === "derived_metrics";
  elements.form.hidden = isEmptyGames || isAdvanced || isDerived;
  elements.emptyGamesBuilder.hidden = !isEmptyGames;
  elements.advancedBuilder.hidden = !isAdvanced;
  elements.derivedBuilder.hidden = !isDerived;
  elements.builderTitle.textContent = isEmptyGames
    ? "Answer a reviewed question"
    : isGoodAtBat
      ? "Explore plate appearance quality"
    : isAdvanced
      ? "Answer a reviewed question"
      : isDerived ? "Build a metric" : `Explore ${catalog[familyId]?.label?.toLowerCase() ?? "baseball"}`;
  elements.resultsTitle.textContent = isEmptyGames || familyId === "advanced"
    ? activeQuestionRecipe()?.label ?? "Results"
    : "Results";
  for (const disclosure of document.querySelectorAll(".refine-disclosure")) disclosure.open = false;
  if (isAdvanced) {
    renderAdvancedBuilder(isGoodAtBat);
    renderSpecialFilters(familyId);
  } else if (isDerived) {
    renderDerivedBuilder();
    renderSpecialFilters("derived_metrics");
  } else if (isEmptyGames) {
    renderEmptyGameBuilder();
    renderSpecialFilters("empty_games");
  } else {
    renderBuilder();
  }
}

function selectedValues(name) {
  return [...elements.form.querySelectorAll(`input[name="${name}"]:checked`)]
    .map((input) => input.value);
}

function buildRequest() {
  const metrics = selectedValues("metric");
  if (metrics.length === 0) {
    throw new Error("Select at least one measurement.");
  }
  const filters = {};
  for (const select of elements.filterControls.querySelectorAll("select[data-filter]")) {
    if (!select.value) continue;
    filters[select.dataset.filter] = select.dataset.input === "integer"
      ? Number.parseInt(select.value, 10)
      : select.value;
  }
  return {
    family: currentFamily,
    dimensions: selectedValues("dimension"),
    metrics,
    filters,
    gameSet: gameSetRequest(),
    dateScope: dateScopeRequest(),
    limit: 250,
  };
}

function setStage(stage) {
  elements.emptyState.hidden = stage !== "empty";
  elements.loadingState.hidden = stage !== "loading";
  elements.errorState.hidden = stage !== "error";
  elements.tableWrap.hidden = stage !== "table";
}

function humanizeVariable(value) {
  return value
    .replace(/([a-z0-9])([A-Z])/gu, "$1 $2")
    .replaceAll("_", " ")
    .replace(/^./u, (letter) => letter.toUpperCase());
}

function resultVariables(payload) {
  const variables = payload.head?.vars ?? [];
  const visible = payload.meta?.visibleColumns ?? [];
  if (visible.length > 0) {
    const known = new Set(variables);
    return visible.filter((variable) => known.has(variable));
  }
  const preferred = payload.meta?.columnOrder ?? [];
  const known = new Set(variables);
  const ordered = preferred.filter((variable) => known.has(variable));
  const included = new Set(ordered);
  return [...ordered, ...variables.filter((variable) => !included.has(variable))];
}

function iriSummary(value) {
  const parts = value.split("/").filter(Boolean);
  return parts.slice(-2).join(" / ");
}

function cellValue(binding, variable, meta) {
  const value = binding?.value ?? "—";
  if ([
    "plateAppearanceQuality", "outcomeRating", "contactRating",
    "grindRating", "situationalRating", "averagePlateAppearanceQuality",
  ].includes(variable) && binding) {
    const number = Number(value);
    if (Number.isFinite(number)) return number.toFixed(3).replace(/^0/u, "");
  }
  if (variable === "derivedValue" && binding && meta.derivedMetric) {
    const number = Number(value);
    if (Number.isFinite(number)) {
      const formatted = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(number);
      return meta.derivedMetric.resultKind === "percentage" ? `${formatted}%` : formatted;
    }
  }
  if (variable === "emptyGamePercentage" && binding) {
    const number = Number(value);
    if (Number.isFinite(number)) return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(number)}%`;
  }
  if (binding?.type === "uri") return iriSummary(value);
  if (/dateTime$/u.test(binding?.datatype ?? "")) {
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  }
  return value.replaceAll("_", " ");
}

function isNumericBinding(binding) {
  return /(?:integer|decimal|double|float|long|int)$/u.test(binding?.datatype ?? "")
    || (binding?.type === "literal" && /^-?\d+(?:\.\d+)?$/u.test(binding.value));
}

function renderMeta(meta) {
  const values = [
    `${meta.rowCount} row${meta.rowCount === 1 ? "" : "s"}`,
    `${meta.durationMs} ms`,
    `${meta.route ?? humanizeVariable(meta.layer ?? "authoritative")} route`,
    "Read only",
  ];
  if (meta.cached) values.splice(2, 0, "Cached result");
  if (meta.definition === "reviewed-empty-game-analysis") values.splice(3, 0, "Reviewed Empty Games definition");
  if (meta.analysisLabel) values.splice(3, 0, meta.analysisLabel);
  if (["positive-evidence", "completeness-gated", "integrity-audit", "decision-support"].includes(meta.definition)) {
    values.splice(3, 0, humanizeVariable(meta.definition));
  }
  const filterCount = Object.keys(meta.filters ?? {}).length;
  if (meta.truncatedAt && meta.totalRowCount > meta.truncatedAt) {
    values.splice(3, 0, `Showing ${meta.truncatedAt} of ${meta.totalRowCount} rows`);
  }
  if (filterCount > 0) values.splice(3, 0, `${filterCount} active filter${filterCount === 1 ? "" : "s"}`);
  if (meta.dateScope?.startDate) {
    values.splice(3, 0, `${dateLabel(meta.dateScope.startDate)} – ${dateLabel(meta.dateScope.endDate)}`);
    values.splice(4, 0, `${meta.dateScope.gameCount} scoped game${meta.dateScope.gameCount === 1 ? "" : "s"}`);
  }
  if (meta.dateScope?.gameSet) {
    const gameSetLabels = {
      regular_season: "Regular season",
      preseason: "Preseason",
      postseason: "Postseason",
      exhibition: "Exhibition",
      all_star: "All-Star games",
    };
    values.splice(3, 0, gameSetLabels[meta.dateScope.gameSet] ?? humanizeVariable(meta.dateScope.gameSet));
  }
  if (meta.derivedMetric) {
    values.splice(3, 0, humanizeVariable(meta.derivedMetric.resultKind));
    values.splice(4, 0, `${humanizeVariable(meta.derivedMetric.grain)} grain`);
  }
  if (meta.limitation) values.push(meta.limitation);
  elements.resultMeta.replaceChildren(...values.map((value) => createElement("span", "meta-chip", value)));
  elements.resultMeta.hidden = false;
}

function renderResults(payload, { resetSort = false } = {}) {
  if (resetSort) currentSort = null;
  const variables = resultVariables(payload);
  const sourceBindings = payload.results?.bindings ?? [];
  const bindings = currentSort
    ? sortBindings(sourceBindings, currentSort.column, currentSort.direction)
    : sourceBindings;
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const variable of variables) {
    const label = payload.meta?.columnLabels?.[variable] ?? humanizeVariable(variable);
    const heading = document.createElement("th");
    heading.scope = "col";
    const isCurrent = currentSort?.column === variable;
    heading.setAttribute("aria-sort", isCurrent
      ? currentSort.direction === "desc" ? "descending" : "ascending"
      : "none");
    const button = createElement("button", "table-sort-button");
    button.type = "button";
    button.title = isCurrent && currentSort.direction === "desc"
      ? `Sort ${label} low to high`
      : `Sort ${label} high to low`;
    button.append(
      createElement("span", "", label),
      createElement("span", "sort-indicator", isCurrent
        ? currentSort.direction === "desc" ? "↓" : "↑"
        : "↕"),
    );
    button.addEventListener("click", () => {
      currentSort = {
        column: variable,
        direction: isCurrent && currentSort.direction === "desc" ? "asc" : "desc",
      };
      renderResults(payload);
    });
    heading.append(button);
    headerRow.append(heading);
  }
  const hasPlateAppearanceDetail = variables.includes("plateAppearanceQuality")
    && sourceBindings.some((row) => row.plateAppearance?.value);
  if (hasPlateAppearanceDetail) {
    const heading = createElement("th", "evidence-heading", "Evidence");
    heading.scope = "col";
    headerRow.append(heading);
  }
  thead.append(headerRow);

  const tbody = document.createElement("tbody");
  for (const row of bindings) {
    const tableRow = document.createElement("tr");
    for (const variable of variables) {
      const binding = row[variable];
      const cell = createElement("td", isNumericBinding(binding) ? "numeric" : "");
      const value = createElement("span", binding?.type === "uri" ? "iri-value" : "", cellValue(binding, variable, payload.meta));
      if (binding?.type === "uri") value.title = binding.value;
      cell.append(value);
      tableRow.append(cell);
    }
    if (hasPlateAppearanceDetail) {
      const cell = createElement("td", "evidence-cell");
      const button = createElement("button", "evidence-link", "View plate appearance");
      button.type = "button";
      button.addEventListener("click", () => openPlateAppearanceEvidence(row, payload.meta));
      cell.append(button);
      tableRow.append(cell);
    }
    tbody.append(tableRow);
  }
  elements.resultsTable.replaceChildren(thead, tbody);
  elements.queryCode.textContent = payload.query ?? "";
  elements.queryInspector.hidden = false;
  elements.exportButton.disabled = bindings.length === 0;
  renderMeta(payload.meta);
  setStage("table");
}

const PLATE_APPEARANCE_EVIDENCE_GROUPS = Object.freeze([
  ["Game and people", ["game", "plateAppearance", "batterLabel", "pitcherLabel"]],
  ["Result and PAQ", ["outcome", "hitType", "plateAppearanceQuality", "plateAppearanceQualityBand", "outcomeRating", "grindRating", "situationalRating", "goodAtBat"]],
  ["Pitches and contact", ["pitches", "balls", "strikes", "swings", "bunts", "contacts", "fouls", "foulTips"]],
  ["Runner resolutions", ["runnerRuns", "runnerOuts", "safeResolutions", "productiveOtherRunner"]],
  ["Timing", ["startTime", "endTime", "durationMinutes"]],
]);

function openPlateAppearanceEvidence(row, meta) {
  const groups = PLATE_APPEARANCE_EVIDENCE_GROUPS.flatMap(([title, variables]) => {
    const facts = variables.flatMap((variable) => {
      const binding = row[variable];
      if (!binding) return [];
      const wrapper = createElement("div", "evidence-fact");
      wrapper.append(
        createElement("dt", "", meta.columnLabels?.[variable] ?? humanizeVariable(variable)),
        createElement("dd", binding.type === "uri" ? "iri-value" : "", cellValue(binding, variable, meta)),
      );
      if (binding.type === "uri") wrapper.querySelector("dd").title = binding.value;
      return [wrapper];
    });
    if (facts.length === 0) return [];
    const section = createElement("section", "evidence-section");
    section.append(createElement("h3", "", title), createElement("dl", "evidence-list"));
    section.querySelector("dl").append(...facts);
    return [section];
  });
  elements.plateAppearanceEvidence.replaceChildren(...groups);
  elements.plateAppearanceDialog.showModal();
}

function showError(message) {
  elements.errorMessage.textContent = message;
  setStage("error");
}

async function runQuery() {
  let request;
  try {
    request = buildRequest();
  } catch (error) {
    showError(error.message);
    return;
  }
  elements.runButton.disabled = true;
  elements.exportButton.disabled = true;
  elements.resultMeta.hidden = true;
  elements.queryInspector.hidden = true;
  setStage("loading");
  try {
    const payload = await fetchJson("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    lastResponse = payload;
    renderResults(payload, { resetSort: true });
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    elements.runButton.disabled = false;
  }
}

async function runEmptyGames() {
  elements.runEmptyGamesButton.disabled = true;
  elements.exportButton.disabled = true;
  elements.resultMeta.hidden = true;
  elements.queryInspector.hidden = true;
  setStage("loading");
  try {
    const payload = await fetchJson("/api/canned/empty-games", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis: elements.emptyGamesAnalysis.value,
        filters: filtersFrom(elements.emptyGamesFilterControls),
        gameSet: gameSetRequest(),
        dateScope: dateScopeRequest(),
      }),
    });
    lastResponse = payload;
    renderResults(payload, { resetSort: true });
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    elements.runEmptyGamesButton.disabled = false;
  }
}

async function runDerivedMetric() {
  if (elements.derivedNumerator.value === elements.derivedDenominator.value) {
    showError("Choose two different base measures.");
    return;
  }
  elements.runDerivedButton.disabled = true;
  elements.exportButton.disabled = true;
  elements.resultMeta.hidden = true;
  elements.queryInspector.hidden = true;
  setStage("loading");
  try {
    const payload = await fetchJson("/api/derived", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        numerator: elements.derivedNumerator.value,
        denominator: elements.derivedDenominator.value,
        filters: filtersFrom(elements.derivedFilterControls),
        gameSet: gameSetRequest(),
        dateScope: dateScopeRequest(),
      }),
    });
    lastResponse = payload;
    renderResults(payload, { resetSort: true });
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    renderDerivedContract();
  }
}

async function runAdvanced() {
  const id = elements.advancedSelect.value;
  if (!advancedCatalog.some((entry) => entry.id === id)) {
    showError("Choose a reviewed advanced question.");
    return;
  }
  elements.runAdvancedButton.disabled = true;
  elements.exportButton.disabled = true;
  elements.resultMeta.hidden = true;
  elements.queryInspector.hidden = true;
  setStage("loading");
  try {
    const payload = await fetchJson("/api/advanced", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id,
        view: id === GOOD_AT_BAT_QUERY_ID
          ? currentFamily === "good_at_bat" ? elements.paqView.value : selectedAdvancedView
          : undefined,
        minimumPlateAppearances: id === GOOD_AT_BAT_QUERY_ID
          && (currentFamily === "good_at_bat" ? elements.paqView.value : selectedAdvancedView) === "player_averages"
          ? Number.parseInt(elements.paqMinimumPa.value, 10)
          : undefined,
        filters: filtersFrom(elements.advancedFilterControls),
        gameSet: gameSetRequest(),
        dateScope: dateScopeRequest(),
      }),
    });
    lastResponse = payload;
    renderResults(payload, { resetSort: true });
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    elements.runAdvancedButton.disabled = false;
  }
}

function csvField(value) {
  const text = String(value ?? "");
  return /[",\r\n]/u.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function exportCsv() {
  if (!lastResponse) return;
  // The table is intentionally concise, but export preserves the full
  // reviewed evidence row for downstream inspection and reproducibility.
  const variables = lastResponse.head?.vars ?? resultVariables(lastResponse);
  const sourceRows = lastResponse.results?.bindings ?? [];
  const rows = currentSort
    ? sortBindings(sourceRows, currentSort.column, currentSort.direction)
    : sourceRows;
  const lines = [
    variables.map(csvField).join(","),
    ...rows.map((row) => variables.map((variable) => csvField(row[variable]?.value)).join(",")),
  ];
  const blob = new Blob([`${lines.join("\r\n")}\r\n`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `baseballo-${currentFamily}-results.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function copyQuery() {
  await navigator.clipboard.writeText(elements.queryCode.textContent);
  showToast("Query copied to clipboard");
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  void runQuery();
});

elements.exploreSubject.addEventListener("change", () => configureFamily(elements.exploreSubject.value));
elements.questionType.addEventListener("change", () => selectQuestion(elements.questionType.value));

elements.resetButton.addEventListener("click", () => {
  renderBuilder();
  showToast("Question reset");
});

elements.exportButton.addEventListener("click", exportCsv);
elements.runEmptyGamesButton.addEventListener("click", () => void runEmptyGames());
elements.runDerivedButton.addEventListener("click", () => void runDerivedMetric());
elements.runAdvancedButton.addEventListener("click", () => void runAdvanced());
elements.resetEmptyGamesButton.addEventListener("click", () => {
  renderEmptyGameBuilder();
  renderSpecialFilters("empty_games");
  showToast("Filters reset");
});
elements.resetAdvancedButton.addEventListener("click", () => {
  if (currentFamily === "good_at_bat") elements.paqView.value = "plate_appearances";
  elements.paqMinimumPa.value = "1";
  renderAdvancedBuilder(currentFamily === "good_at_bat");
  renderSpecialFilters(currentFamily);
  showToast("Filters reset");
});
elements.resetDerivedButton.addEventListener("click", () => {
  renderDerivedBuilder();
  renderSpecialFilters("derived_metrics");
  showToast("Derived metric reset");
});
elements.advancedSelect.addEventListener("change", () => {
  selectedQuestionId = elements.advancedSelect.value;
  renderAdvancedDefinition();
  renderSpecialFilters(currentFamily);
});
elements.emptyGamesAnalysis.addEventListener("change", renderEmptyGameDefinition);
elements.paqView.addEventListener("change", () => {
  selectedAdvancedView = elements.paqView.value;
  elements.paqMinimumPaField.hidden = selectedAdvancedView !== "player_averages";
});
elements.derivedNumerator.addEventListener("change", renderDerivedContract);
elements.derivedDenominator.addEventListener("change", renderDerivedContract);
elements.copyQueryButton.addEventListener("click", () => void copyQuery());
elements.plateAppearanceDialogClose.addEventListener("click", () => elements.plateAppearanceDialog.close());
elements.plateAppearanceDialog.addEventListener("click", (event) => {
  if (event.target === elements.plateAppearanceDialog) elements.plateAppearanceDialog.close();
});
elements.gameSet.addEventListener("change", () => {
  optionCache.clear();
  configureFamily(currentFamily);
  void refreshDateScope().catch((error) => showError(error.message));
});
elements.datePreset.addEventListener("change", () => {
  const custom = elements.datePreset.value === "custom";
  elements.customDateFields.hidden = !custom;
  if (!custom) void refreshDateScope().catch((error) => showError(error.message));
});
for (const input of [elements.dateStart, elements.dateEnd]) {
  input.addEventListener("change", () => {
    if (elements.dateStart.value && elements.dateEnd.value) {
      void refreshDateScope().catch((error) => showError(error.message));
    }
  });
}
elements.suggestionList.addEventListener("click", (event) => {
  const questionButton = event.target.closest("button[data-question]");
  if (questionButton) {
    selectQuestion(questionButton.dataset.question);
    return;
  }
  const button = event.target.closest("button[data-preset]");
  if (!button) return;
  configureFamily(button.dataset.preset);
  if (catalog[button.dataset.preset]) {
    void runQuery();
  }
});

async function initialize() {
  try {
    const [{ families }, { queries }, derived, emptyGames, status] = await Promise.all([
      fetchJson("/api/catalog"),
      fetchJson("/api/advanced/catalog"),
      fetchJson("/api/derived/catalog"),
      fetchJson("/api/empty-games/catalog"),
      fetchJson("/api/status"),
    ]);
    catalog = families;
    advancedCatalog = queries;
    derivedCatalog = derived;
    emptyGameCatalog = emptyGames;
    questionRecipes = buildQuestionRecipes(advancedCatalog, emptyGameCatalog);
    setConnection(status);
    selectQuestion(selectedQuestionRecipeId);
    await refreshDateScope();
    setStage("empty");
  } catch (error) {
    setConnection({ connected: false, games: 0 });
    showError(error.message);
  }
}

void initialize();
