const DEFAULT_SELECTIONS = Object.freeze({
  batting: {
    dimensions: ["player"],
    metrics: ["hits", "home_runs"],
  },
  pitching: {
    dimensions: ["pitcher"],
    metrics: ["pitches", "strikes"],
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

const elements = {
  connectionPill: document.querySelector("#connection-pill"),
  connectionText: document.querySelector("#connection-text"),
  gameCount: document.querySelector("#game-count"),
  builderTitle: document.querySelector("#builder-title"),
  familyTabs: document.querySelector("#family-tabs"),
  form: document.querySelector("#query-form"),
  emptyGamesBuilder: document.querySelector("#empty-games-builder"),
  runEmptyGamesButton: document.querySelector("#run-empty-games-button"),
  dimensionChoices: document.querySelector("#dimension-choices"),
  metricChoices: document.querySelector("#metric-choices"),
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
let currentFamily = "batting";
let lastResponse = null;
let toastTimer;
const optionCache = new Map();

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
    ["empty_games", { label: "Empty Games" }],
  ];
  const buttons = families.map(([familyId, family]) => {
    const button = createElement("button", "", family.label);
    button.type = "button";
    button.dataset.family = familyId;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(familyId === currentFamily));
    button.addEventListener("click", () => {
      configureFamily(familyId);
      if (familyId === "empty_games") void runEmptyGames();
    });
    return button;
  });
  elements.familyTabs.replaceChildren(...buttons);
}

function createChoice(kind, id, label, selected) {
  const wrapper = createElement("div", "choice");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = kind;
  input.value = id;
  input.id = `${kind}-${id}`;
  input.checked = selected;
  const labelElement = createElement("label", "", label);
  labelElement.htmlFor = input.id;
  wrapper.append(input, labelElement);
  return wrapper;
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

async function populateFilter(select, familyId, dimensionId) {
  try {
    const { options } = await getOptions(familyId, dimensionId);
    if (!select.isConnected || currentFamily !== familyId) return;
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
    if (!select.isConnected || currentFamily !== familyId) return;
    const failedOption = createElement("option", "", "Options unavailable");
    failedOption.value = "";
    select.replaceChildren(failedOption);
    select.disabled = true;
  }
}

function renderBuilder() {
  const family = catalog[currentFamily];
  const defaults = DEFAULT_SELECTIONS[currentFamily];
  const dimensionChoices = Object.entries(family.dimensions).map(([id, dimension]) =>
    createChoice("dimension", id, dimension.label, defaults.dimensions.includes(id)));
  const metricChoices = Object.entries(family.metrics).map(([id, metric]) =>
    createChoice("metric", id, metric.label, defaults.metrics.includes(id)));
  elements.dimensionChoices.replaceChildren(...dimensionChoices);
  elements.metricChoices.replaceChildren(...metricChoices);

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
  elements.form.hidden = isEmptyGames;
  elements.emptyGamesBuilder.hidden = !isEmptyGames;
  elements.builderTitle.textContent = isEmptyGames ? "Review empty games" : "Shape your question";
  if (!isEmptyGames) renderBuilder();
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
    const payload = await fetchJson("/api/canned/empty-games");
    lastResponse = payload;
    renderResults(payload);
  } catch (error) {
    lastResponse = null;
    showError(error.message);
  } finally {
    elements.runEmptyGamesButton.disabled = false;
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
elements.copyQueryButton.addEventListener("click", () => void copyQuery());
elements.suggestionList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-preset]");
  if (!button) return;
  configureFamily(button.dataset.preset);
  if (button.dataset.preset === "empty_games") {
    void runEmptyGames();
  } else {
    void runQuery();
  }
});

async function initialize() {
  try {
    const [{ families }, status] = await Promise.all([
      fetchJson("/api/catalog"),
      fetchJson("/api/status"),
    ]);
    catalog = families;
    setConnection(status);
    renderFamilyTabs();
    renderBuilder();
    await runQuery();
  } catch (error) {
    setConnection({ connected: false, games: 0 });
    showError(error.message);
  }
}

void initialize();
