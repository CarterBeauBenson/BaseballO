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
  ],
});

const elements = {
  connectionPill: document.querySelector("#connection-pill"),
  connectionText: document.querySelector("#connection-text"),
  gameCount: document.querySelector("#game-count"),
  builderTitle: document.querySelector("#builder-title"),
  familyTabs: document.querySelector("#family-tabs"),
  datePreset: document.querySelector("#date-preset"),
  customDateFields: document.querySelector("#custom-date-fields"),
  dateStart: document.querySelector("#date-start"),
  dateEnd: document.querySelector("#date-end"),
  dateScopeStatus: document.querySelector("#date-scope-status"),
  form: document.querySelector("#query-form"),
  emptyGamesBuilder: document.querySelector("#empty-games-builder"),
  emptyGamesFilterControls: document.querySelector("#empty-games-filter-controls"),
  runEmptyGamesButton: document.querySelector("#run-empty-games-button"),
  resetEmptyGamesButton: document.querySelector("#reset-empty-games-button"),
  advancedBuilder: document.querySelector("#advanced-builder"),
  advancedFilterControls: document.querySelector("#advanced-filter-controls"),
  advancedSelect: document.querySelector("#advanced-query-select"),
  advancedMode: document.querySelector("#advanced-mode"),
  advancedClaim: document.querySelector("#advanced-claim"),
  advancedEvidenceNote: document.querySelector("#advanced-evidence-note span"),
  runAdvancedButton: document.querySelector("#run-advanced-button"),
  resetAdvancedButton: document.querySelector("#reset-advanced-button"),
  dimensionChoices: document.querySelector("#dimension-choices"),
  metricChoices: document.querySelector("#metric-choices"),
  metricHelp: document.querySelector("#metric-help"),
  filterControls: document.querySelector("#filter-controls"),
  runButton: document.querySelector("#run-button"),
  resetButton: document.querySelector("#reset-button"),
  exportButton: document.querySelector("#export-button"),
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
  toast: document.querySelector("#toast"),
};

let catalog = {};
let advancedCatalog = [];
let currentFamily = "batting";
let lastResponse = null;
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
  const search = new URLSearchParams(request);
  elements.dateScopeStatus.textContent = "Resolving loaded game datesâ€¦";
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
    ? `${dateLabel(scope.startDate)} â€“ ${dateLabel(scope.endDate)} Â· ${scope.gameCount} loaded game${scope.gameCount === 1 ? "" : "s"}`
    : "No dated authoritative games are loaded.";
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

function setConnection({ connected, games }) {
  elements.connectionPill.classList.toggle("connected", connected);
  elements.connectionPill.classList.toggle("disconnected", !connected);
  elements.connectionText.textContent = connected ? "Local graph connected" : "Graph unavailable";
  elements.gameCount.textContent = connected
    ? `${games} loaded game${games === 1 ? "" : "s"} ready to explore`
    : "Start Fuseki to explore loaded games";
}

function renderFamilyTabs() {
  const families = [
    ...Object.entries(catalog),
    ["advanced", { label: "Advanced" }],
    ["empty_games", { label: "Empty Games" }],
  ];
  const buttons = families.map(([familyId, family]) => {
    const button = createElement("button", "", family.label);
    button.type = "button";
    button.dataset.family = familyId;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(familyId === currentFamily));
    button.addEventListener("click", () => configureFamily(familyId));
    return button;
  });
  elements.familyTabs.replaceChildren(...buttons);
}

function advancedModeLabel(mode) {
  return {
    "positive-evidence": "Positive evidence / Authoritative only",
    "completeness-gated": "Completeness-gated / Authoritative only",
    "integrity-audit": "Integrity audit / Authoritative only",
  }[mode] ?? "Authoritative semantic query";
}

function renderAdvancedDefinition() {
  const selected = advancedCatalog.find((entry) => entry.id === elements.advancedSelect.value)
    ?? advancedCatalog[0];
  if (!selected) return;
  elements.advancedSelect.value = selected.id;
  elements.advancedMode.textContent = advancedModeLabel(selected.semanticMode);
  elements.advancedClaim.textContent = selected.claim;
  elements.advancedEvidenceNote.textContent = selected.semanticMode === "positive-evidence"
    ? "This query counts explicit mapped evidence and does not turn missing events into facts."
    : selected.semanticMode === "completeness-gated"
      ? "This query uses absence or a mapped denominator only within its documented source-coverage boundary."
      : "Every returned row is a structural finding. Zero rows is the ideal result, not missing data.";
}

function renderAdvancedBuilder() {
  const options = advancedCatalog.map((entry) => {
    const option = createElement("option", "", entry.label);
    option.value = entry.id;
    return option;
  });
  elements.advancedSelect.replaceChildren(...options);
  renderAdvancedDefinition();
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
  const key = `${familyId}:${dimensionId}`;
  if (!optionCache.has(key)) {
    optionCache.set(key, fetchJson(`/api/options?family=${encodeURIComponent(familyId)}&dimension=${encodeURIComponent(dimensionId)}`));
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

function renderSpecialFilters(familyId) {
  const container = familyId === "advanced"
    ? elements.advancedFilterControls
    : elements.emptyGamesFilterControls;
  const controls = SPECIAL_FILTERS[familyId].map((spec) => {
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
    void populateFilter(select, spec.optionFamily, spec.id, familyId);
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
  const isAdvanced = familyId === "advanced";
  elements.form.hidden = isEmptyGames || isAdvanced;
  elements.emptyGamesBuilder.hidden = !isEmptyGames;
  elements.advancedBuilder.hidden = !isAdvanced;
  elements.builderTitle.textContent = isEmptyGames
    ? "Review empty games"
    : isAdvanced ? "Explore advanced analytics" : "Shape your question";
  if (isAdvanced) {
    renderAdvancedBuilder();
    renderSpecialFilters("advanced");
  } else if (isEmptyGames) {
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

function iriSummary(value) {
  const parts = value.split("/").filter(Boolean);
  return parts.slice(-2).join(" / ");
}

function cellValue(binding) {
  const value = binding?.value ?? "—";
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
    "Authoritative graph",
    "Read only",
  ];
  if (meta.definition === "reviewed-prototype") values.splice(3, 0, "Reviewed prototype");
  if (["positive-evidence", "completeness-gated", "integrity-audit"].includes(meta.definition)) {
    values.splice(3, 0, humanizeVariable(meta.definition));
  }
  const filterCount = Object.keys(meta.filters ?? {}).length;
  if (filterCount > 0) values.splice(3, 0, `${filterCount} active filter${filterCount === 1 ? "" : "s"}`);
  if (meta.dateScope?.startDate) {
    values.splice(3, 0, `${dateLabel(meta.dateScope.startDate)} â€“ ${dateLabel(meta.dateScope.endDate)}`);
    values.splice(4, 0, `${meta.dateScope.gameCount} scoped game${meta.dateScope.gameCount === 1 ? "" : "s"}`);
  }
  elements.resultMeta.replaceChildren(...values.map((value) => createElement("span", "meta-chip", value)));
  elements.resultMeta.hidden = false;
}

function renderResults(payload) {
  const variables = payload.head?.vars ?? [];
  const bindings = payload.results?.bindings ?? [];
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const variable of variables) {
    headerRow.append(createElement("th", "", humanizeVariable(variable)));
  }
  thead.append(headerRow);

  const tbody = document.createElement("tbody");
  for (const row of bindings) {
    const tableRow = document.createElement("tr");
    for (const variable of variables) {
      const binding = row[variable];
      const cell = createElement("td", isNumericBinding(binding) ? "numeric" : "");
      const value = createElement("span", binding?.type === "uri" ? "iri-value" : "", cellValue(binding));
      if (binding?.type === "uri") value.title = binding.value;
      cell.append(value);
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
    renderResults(payload);
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
        filters: filtersFrom(elements.emptyGamesFilterControls),
        dateScope: dateScopeRequest(),
      }),
    });
    lastResponse = payload;
    renderResults(payload);
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    elements.runEmptyGamesButton.disabled = false;
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
        filters: filtersFrom(elements.advancedFilterControls),
        dateScope: dateScopeRequest(),
      }),
    });
    lastResponse = payload;
    renderResults(payload);
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
  const variables = lastResponse.head?.vars ?? [];
  const rows = lastResponse.results?.bindings ?? [];
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
  showToast("SPARQL copied to clipboard");
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  void runQuery();
});

elements.resetButton.addEventListener("click", () => {
  renderBuilder();
  showToast("Question reset");
});

elements.exportButton.addEventListener("click", exportCsv);
elements.runEmptyGamesButton.addEventListener("click", () => void runEmptyGames());
elements.runAdvancedButton.addEventListener("click", () => void runAdvanced());
elements.resetEmptyGamesButton.addEventListener("click", () => {
  renderSpecialFilters("empty_games");
  showToast("Filters reset");
});
elements.resetAdvancedButton.addEventListener("click", () => {
  elements.advancedSelect.selectedIndex = 0;
  renderAdvancedDefinition();
  renderSpecialFilters("advanced");
  showToast("Filters reset");
});
elements.advancedSelect.addEventListener("change", renderAdvancedDefinition);
elements.copyQueryButton.addEventListener("click", () => void copyQuery());
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
  const button = event.target.closest("button[data-preset]");
  if (!button) return;
  configureFamily(button.dataset.preset);
  if (!["empty_games", "advanced"].includes(button.dataset.preset)) {
    void runQuery();
  }
});

async function initialize() {
  try {
    const [{ families }, { queries }, status] = await Promise.all([
      fetchJson("/api/catalog"),
      fetchJson("/api/advanced/catalog"),
      fetchJson("/api/status"),
    ]);
    catalog = families;
    advancedCatalog = queries;
    setConnection(status);
    renderFamilyTabs();
    renderBuilder();
    await refreshDateScope();
    await runQuery();
  } catch (error) {
    setConnection({ connected: false, games: 0 });
    showError(error.message);
  }
}

void initialize();
