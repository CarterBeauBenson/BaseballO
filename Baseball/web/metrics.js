const byId = id => document.getElementById(id);
let catalog, selected, lastResult, activeRequest, examples, dashboardResult, dashboardRequest, refreshTimer;
const node = (tag, text) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; return element; };

export function displayFraction(value, places = 2) {
  if (!value) return 'Unavailable';
  const numerator = BigInt(value.numerator), denominator = BigInt(value.denominator);
  if (denominator <= 0n) throw new Error('Invalid fraction');
  const negative = numerator < 0n, magnitude = negative ? -numerator : numerator;
  const scale = 10n ** BigInt(places);
  const rounded = (magnitude * scale * 2n + denominator) / (denominator * 2n);
  return `${negative && rounded ? '-' : ''}${rounded / scale}${places ? '.' + String(rounded % scale).padStart(places, '0') : ''}`;
}

export function formatMetricValue(value, unit) {
  if (!value) return 'Unavailable';
  if (unit === 'proportion') return displayFraction({ numerator: String(BigInt(value.numerator) * 100n), denominator: value.denominator }, 1) + '%';
  const counts = ['trajectories', 'acts', 'players', 'episodes', 'role types', 'games'];
  return displayFraction(value, counts.includes(unit) && value.denominator === '1' ? 0 : 2);
}

export function resultHeadline(result, unit) {
  if (result.status === 'available') return result.value ? formatMetricValue(result.value, unit) :
    Number.isFinite(result.approximateValue) ? result.approximateValue.toFixed(3) : 'Unavailable';
  const count = result.consequences?.length ?? 0;
  return count ? `${count} supported award consequence${count === 1 ? '' : 's'}` : 'Unavailable';
}

export function resultPresentation(payload, metric) {
  const result = payload.metric, coverage = result.coverage ?? {};
  if ((coverage.games ?? payload.graphCount) === 0) return { state: 'empty', badge: 'No games selected',
    headline: 'No games in this date range', message: 'Choose dates within the loaded range shown below.' };
  if (result.status === 'available') return { state: 'available', badge: 'Result available',
    headline: resultHeadline(result, metric.unit), message: 'Result ready for the stated evidence population.' };
  if (result.runs?.length) return { state: 'partial', badge: 'Complete individual run results',
    headline: result.runs.length === 1 ? formatMetricValue(result.runs[0].value, metric.unit) : `${result.runs.length} run results`,
    message: `Showing ${result.runs.length} complete scoring histories. Other observed runs may remain unresolved.` };
  if (result.consequences?.length) return { state: 'partial', badge: 'Limited play results',
    headline: result.consequences.length === 1 ? formatMetricValue(result.consequences[0].value, metric.unit) : resultHeadline(result, metric.unit),
    message: `Showing ${result.consequences.length} supported award play${result.consequences.length === 1 ? '' : 's'}.` };
  return { state: 'unavailable', badge: 'Evidence incomplete', headline: 'Result unavailable',
    message: result.gaps?.includes('EMPTY_DENOMINATOR') ? 'No eligible resolved evidence is available for this calculation in the selection.' :
      'The selected evidence does not support a score yet. The remaining requirements are listed below.' };
}

export function resultDateLabel(payload) {
  const scope = payload.dateScope ?? {};
  const period = scope.startDate && scope.endDate ? `${scope.startDate} to ${scope.endDate}` : 'Dates not reported';
  return `${scope.gameSet === 'all_star' ? 'All-Star' : scope.gameSet === 'regular_season' ? 'Regular season' : 'Selected games'} · ${period}`;
}

export function displayPlayer(labels, graph, player) {
  return labels?.find(row => row.graph === graph && row.entity === player)?.label ?? `Player #${player.split('/').at(-1)}`;
}

export function exampleAnswer(result, unit, unitLabel = unit) {
  if (result.status !== 'available') return 'Example result: unavailable (no defined denominator).';
  if (unit === 'games' && result.value?.numerator === '1' && result.value.denominator === '1') unitLabel = 'game';
  if (result.value) return `Example result: ${formatMetricValue(result.value, unit)}${unit === 'proportion' ? '' : ' ' + unitLabel}. Exact: ${result.value.numerator}/${result.value.denominator}.`;
  return `Example result: approximately ${result.approximateValue.toFixed(3)} ${unitLabel}. Logarithmic results are approximate; channel counts remain exact.`;
}

function renderExampleCase() {
  const entry = examples?.metrics[selected.id], item = entry?.cases[Number(byId('example-choice').value)];
  byId('example-formula').textContent = entry?.formula ?? '';
  byId('example-title').textContent = item?.title ?? '';
  byId('example-explanation').textContent = item?.explanation ?? 'Worked examples are unavailable. You can still inspect selected-game evidence below.';
  byId('example-equation').textContent = item?.equation ?? '';
  byId('example-answer').textContent = item ? exampleAnswer(item.result, selected.unit, selected.presentation?.unitLabel) : '';
}

function renderExamples() {
  const cases = examples?.metrics[selected.id]?.cases ?? [];
  const choice = byId('example-choice');
  choice.replaceChildren(...cases.map((item, index) => {
    const option = node('option', item.title); option.value = String(index); return option;
  }));
  choice.value = '0';
  choice.hidden = byId('example-choice-label').hidden = cases.length < 2;
  renderExampleCase();
}

export function selectionFromUrl(url) {
  const p = new URL(url).searchParams, preset = p.get('preset'), gameSet = p.get('gameSet');
  const validDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value ?? '') && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  const selection = { preset: ['one_day','seven_days','thirty_days','season_to_date'].includes(preset) ? preset : 'one_day',
    gameSet: gameSet === 'all_star' ? gameSet : 'regular_season' };
  if (preset === 'custom' && validDate(p.get('startDate')) && validDate(p.get('endDate')) && p.get('startDate') <= p.get('endDate')) {
    Object.assign(selection, { preset, startDate: p.get('startDate'), endDate: p.get('endDate') });
  }
  return selection;
}

function saveSelection() {
  const url = new URL(location.href); url.search = ''; url.hash = selected.id;
  url.searchParams.set('gameSet', byId('game-set').value);
  url.searchParams.set('preset', byId('date-preset').value);
  if (byId('date-preset').value === 'custom') for (const key of ['start', 'end']) url.searchParams.set(key + 'Date', byId(key + '-date').value);
  history.replaceState(null, '', url);
}

function invalidateSelection() {
  clearTimeout(refreshTimer);
  activeRequest?.abort(); activeRequest = null; lastResult = null;
  dashboardRequest?.abort(); dashboardRequest = null; dashboardResult = null;
  byId('dashboard-overview').hidden = true; byId('download-dashboard').disabled = true;
  byId('load-dashboard').disabled = false;
  byId('dashboard-status').textContent = 'Selection changed. Updating the dashboard…';
  renderList();
  byId('result').hidden = true; byId('download-result').disabled = true;
  byId('run-metric').disabled = false;
  byId('request-status').textContent = 'Selection changed. Inspect the metric to load matching results.';
  renderRequirements(selected.requires); saveSelection();
}

export function movementEvidenceLabel(coverage) {
  return `${coverage.withRunnerEpisodeRecordBinding}/${coverage.observedPairs} movements have runner, episode and record bindings`;
}

function renderGameCoverage(games = []) {
  byId('game-coverage').hidden = !games.length;
  const target = byId('game-coverage-table'); target.replaceChildren();
  if (!games.length) return;
  const table = node('table'), head = node('thead'), heading = node('tr'), body = node('tbody');
  for (const label of ['Game', 'Observed PAs', 'Movement evidence', 'Single origin value', 'Award evidence', 'Scored award consequences']) {
    const cell = node('th', label); cell.scope = 'col'; heading.append(cell);
  }
  head.append(heading);
  for (const game of games) {
    const row = node('tr'), movement = game.runnerMovements;
    for (const value of [game.graph.split('/').at(-1), game.observedPlateAppearances,
      movementEvidenceLabel(movement), movement.withOneMetricOriginBinding,
      movement.withCausalRequiredAwardBinding, game.supportedAwardConsequences]) row.append(node('td', String(value)));
    body.append(row);
  }
  table.append(head, body); target.append(table);
}

export function consequencePresentation(metricId) {
  if (metricId === 'offensive-reach') return {
    label: 'Consequence Offensive Reach',
    math: 'Offensive Reach counts distinct trajectories with positive attributed progress. The supported loaded Walk/HBP chain advances the batter and all three existing runners: 1 + 1 + 1 + 1 = 4 trajectories. Each trajectory counts once.',
    places: 0,
  };
  return {
    label: 'Plate Appearance Contribution · award play',
    math: 'Contribution = progress − direct loss − lost opportunity. For this four-runner force chain: HOME → 1B contributes 1/4; 1B → 2B contributes 1/3; 2B → 3B contributes 1/2; 3B → score contributes 1. All four resolve safely or score, so the loss terms are zero. Total: 25/12, displayed as 2.08.',
    places: 2,
  };
}

function renderConsequences(results = [], metricId = 'tfs', labels = []) {
  const presentation = consequencePresentation(metricId);
  const target = byId('award-consequences');
  target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  target.append(node('h3', 'Supported award consequences'),
    node('p', 'Scores for the batter and forced-runner advances caused by each listed Walk/HBP.'));
  const math = node('details');
  math.append(node('summary', 'Show math'), node('p', presentation.math));
  target.append(math);
  const table = node('table'), head = node('thead'), heading = node('tr'), body = node('tbody');
  for (const label of ['Game / PA source index', 'Batter', presentation.label, 'Evidence']) {
    const cell = node('th', label); cell.scope = 'col'; heading.append(cell);
  }
  head.append(heading);
  for (const result of results) {
    const row = node('tr');
    row.append(node('td', `${result.graph.split('/').at(-1)} / ${result.plateAppearance.split('/').at(-1)}`),
      node('td', displayPlayer(labels, result.graph, result.batter)),
      node('td', `${displayFraction(result.value, presentation.places)} (${result.value.numerator}/${result.value.denominator})`));
    const evidence = node('td'), detail = node('details');
    detail.append(node('summary', 'Trace four advances'));
    const advances = node('ul');
    for (const movement of result.movements) {
      advances.append(node('li', `${displayPlayer(labels, result.graph, movement.runner)}${movement.runner === result.batter ? ' (batter)' : ''}: ${movement.metricOrigin === '0' ? 'HOME' : movement.originCode} → ${movement.hasRunType === 'true' ? 'score' : movement.destinationCode}`));
    }
    const records = node('details'); records.append(node('summary', 'Technical evidence'), node('pre', JSON.stringify({
      award: result.award, components: result.components, movements: result.movements,
    }, null, 2)));
    detail.append(advances, records);
    evidence.append(detail); row.append(evidence);
    ['Game / PA index', 'Batter', presentation.label, 'Evidence'].forEach((label, index) => { row.children[index].dataset.label = label; });
    body.append(row);
  }
  table.append(head, body); target.append(table);
}

export function runMetricPresentation(metricId) {
  return metricId === 'run-construction-breadth' ? {
    heading:'Run Contributors', singular:'contributor', plural:'contributors', unit:'players',
    description:'Each score counts distinct offensive players whose supported contributions advanced this scoring runner. Each contributor counts once.',
  } : {heading:'Scoring History Length', singular:'episode', plural:'episodes', unit:'episodes',
    description:'Each score counts the state-changing episodes in one complete scoring-runner history. Held-base observations add no depth.'};
}

function renderRunResults(results = [], labels = [], metricId = 'run-construction-depth') {
  const target = byId('run-results'); target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  const presentation=runMetricPresentation(metricId);
  target.append(node('h3', presentation.heading), node('p', presentation.description));
  const base = value => value === 0 ? 'HOME' : value === 4 ? 'score' : value + 'B';
  for (const result of results) {
    const card = node('article'), title = node('h4', displayPlayer(labels, result.graph, result.runner));
    const trace = node('details'); trace.append(node('summary', 'Trace the episodes'));
    const list = node('ul');
    for (const episode of result.episodes) list.append(node('li',
      `${base(episode.start)} → ${base(episode.end)}${episode.changesState ? '' : ' (no state change)'} · PA source index ${episode.episode.split('/').at(-2)}`));
    trace.append(list);
    const technical = node('details'); technical.append(node('summary', 'Technical evidence'), node('pre', JSON.stringify(result, null, 2)));
    card.append(title, node('strong', `${formatMetricValue(result.value, presentation.unit)} ${result.value.numerator === result.value.denominator ? presentation.singular : presentation.plural}`),
      node('p', `Game ${result.graph.split('/').at(-1)} · Run ${result.run.split('/').slice(-2).join('/')}`), trace, technical);
    if (Array.isArray(result.contributors)) card.insertBefore(node('p', result.contributors.length ?
      'Contributors: '+result.contributors.map(player => displayPlayer(labels,result.graph,player)).join(', ') :
      'No credited positive contribution in this fully accounted scoring history.'), trace);
    target.append(card);
  }
}

function facts(target, entries) {
  target.replaceChildren(...entries.map(([label, value]) => { const item = node('div'); item.append(node('dt', label), node('dd', String(value))); return item; }));
}

function gapDetails(gap, affected = false) {
  const detail = node('details');
  detail.append(node('summary', gap.title), node('p', gap.question), node('p', gap.direction));
  const id = node('p', gap.id); id.className = 'gap-id'; detail.append(id);
  if (affected) detail.append(node('p', 'Used by: ' + catalog.metrics.filter(m => m.requires.includes(gap.id)).map(m => m.label).join(', ')));
  return detail;
}

function renderRequirements(ids) {
  const registered = new Map(catalog.gapRegister.gaps.map(g => [g.id, g]));
  byId('metric-gaps').replaceChildren(...(ids.length ? ids.map(id => registered.has(id) ? gapDetails(registered.get(id)) : node('p', id.replaceAll('_', ' '))) :
    [node('p', selected.id === 'adjudication-volatility' ? 'This result covers explicitly resolved mapped replay reviews. Unresolved reviews are reported separately.' : 'No additional requirements were reported for this result.')]));
}

function choose(metric) {
  activeRequest?.abort(); activeRequest = null;
  selected = metric; lastResult = null;
  byId('download-result').disabled = true;
  byId('metric-title').textContent = metric.label;
  byId('metric-version').textContent = catalog.groups.find(group => group.id === metric.presentation.group).label;
  byId('metric-definition').textContent = metric.userDefinition;
  byId('metric-question').textContent = metric.presentation.question;
  byId('metric-reading').textContent = metric.presentation.reading;
  facts(byId('metric-facts'), [['Reported as', metric.presentation.unitLabel], ['Scope', metric.presentation.scopeLabel],
    ...(metric.presentation.playerSummary ? [['Player leaderboard', metric.presentation.playerSummary]] : []),
    ['Reference', metric.presentation.reference]]);
  byId('metric-technical').textContent = `${metric.technicalLabel} · ${metric.id} · Version ${metric.version}. ${metric.technicalDefinition} Technical unit: ${metric.unit}.`;
  byId('result').hidden = true;
  byId('request-status').textContent = metric.liveAdapter === 'loaded-award-consequences' ?
    'Inspect supported loaded Walk/HBP consequences and the remaining metric requirements.' :
    metric.liveAdapter.startsWith('personal-run-histories') ? 'Inspect scoring histories, contributors and qualified player averages.' :
    metric.liveAdapter === 'complete-batting-progress-players' ? 'Inspect qualified player results for the selected period.' :
    metric.requires.length ? 'Inspect the selected games to see supported results and their coverage.' : 'Inspect the selected mapped review population.';
  byId('run-metric').disabled = false;
  renderRequirements(metric.requires);
  renderExamples();
  document.querySelectorAll('#metric-list button').forEach(button => button.setAttribute('aria-current', String(button.dataset.id === metric.id)));
  saveSelection();
  const result = dashboardResult?.metrics.find(result => result.metricId === metric.id);
  if (result) {
    const { metrics, ...context } = dashboardResult;
    showResult({ ...context, metric: result });
  }
}

export function unresolvedRunRows(results = []) {
  const reasons = {
    MISSING_PERSONAL_SCORING_HISTORY: 'A complete history for this scoring runner is missing.',
    PERSONAL_HISTORY_MEMBER_COVERAGE: 'An episode in the runner’s history is missing its movement evidence.',
    CONFLICTING_PERSONAL_HISTORY: 'The history has conflicting runner or game information.',
    CONFLICTING_SEGMENT_STATE: 'The movement evidence gives conflicting base states.',
    UNSUPPORTED_SCORING_HISTORY: 'The runner’s identity or terminal outcome is unresolved.',
    UNSUPPORTED_SEGMENT_END: 'A movement’s ending base or outcome is unresolved.',
    UNSUPPORTED_SEGMENT_ORIGIN: 'A movement’s starting base is unresolved.',
    SCORING_HISTORY_TERMINAL_COVERAGE: 'The history does not establish one counted run.',
    AMBIGUOUS_SCORING_HISTORY: 'More than one personal history claims this run.',
    UNSUPPORTED_RUN_CONTRIBUTOR: 'An advancing episode lacks one supported contribution channel.',
    UNSUPPORTED_BATTING_CREDIT_CLASSIFICATION: 'An advancing episode lacks a resolved batting-credit classification.',
    UNSUPPORTED_CONTRIBUTION_DIRECTION: 'An episode does not establish positive progress toward scoring.',
  };
  return results.map(result => ({ game: result.graph.split('/').at(-1),
    run: result.run.split('/').slice(-2).join('/'),
    reason: [...new Set((result.gaps ?? []).map(gap => reasons[gap] ?? 'Additional history evidence is required.'))].join(' '),
    evidence: result }));
}

function renderUnresolvedRuns(results = []) {
  const target = byId('unresolved-run-results'); target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  target.append(node('h3', 'Scoring histories needing more evidence'), node('p',
    'These counted runs have no score yet. They remain part of the selection and prevent a complete aggregate.'));
  const table = node('table'), head = node('thead'), header = node('tr'), body = node('tbody');
  const columns = ['Game', 'Run', 'Missing evidence'];
  header.append(...columns.map(label => node('th', label))); head.append(header);
  for (const result of unresolvedRunRows(results)) {
    const row = node('tr'), detail = node('td'); detail.append(node('p', result.reason));
    const evidence = node('details'); evidence.append(node('summary', 'Technical evidence'),
      node('pre', JSON.stringify(result.evidence, null, 2))); detail.append(evidence);
    row.append(node('td', result.game), node('td', result.run), detail);
    columns.forEach((label, index) => { row.children[index].dataset.label = label; });
    body.append(row);
  }
  table.append(head, body); target.append(table);
}

function renderRunnerBoundaries(results = [], labels) {
  const target = byId('runner-boundaries'); target.replaceChildren(); target.hidden = !results.length;
  if (!results.length) return;
  target.append(node('h3', 'Supported runner base states'), node('p',
    'Complete personal histories support these unchanged bases through the listed plate appearances. These are inputs to scoring; they do not establish all runners, a complete PA score, or player eligibility.'));
  const table = node('table'), head = node('thead'), header = node('tr'), body = node('tbody');
  const columns = ['Runner', 'Game / plate appearance', 'Base throughout PA'];
  header.append(...columns.map(label => { const cell = node('th', label); cell.scope = 'col'; return cell; })); head.append(header);
  for (const result of results) {
    const row = node('tr');
    row.append(node('td', displayPlayer(labels, result.graph, result.runner)),
      node('td', `${result.graph.split('/').at(-1)} / ${result.plateAppearance.split('/').at(-1)}`),
      node('td', ['Unknown', 'First', 'Second', 'Third'][result.basePosition] ?? 'Unknown'));
    columns.forEach((label, index) => { row.children[index].dataset.label = label; }); body.append(row);
  }
  table.append(head, body); target.append(table);
}

function scheduleDashboardLoad() {
  invalidateSelection();
  const scope = selectedScope().dateScope;
  if (!byId('metric-form').checkValidity() ||
      (scope.preset === 'custom' && (!scope.startDate || !scope.endDate || scope.startDate > scope.endDate))) {
    byId('dashboard-status').textContent = 'Choose a valid start and end date to load the dashboard.';
    return;
  }
  refreshTimer = setTimeout(() => byId('metric-form').requestSubmit(), 400);
}

export function dashboardSummary(payload) {
  const summary = { games: payload.graphCount ?? payload.metrics[0]?.coverage?.games ?? 0,
    available: 0, partial: 0, unavailable: 0, empty: 0, populatedLeaderboards: 0 };
  for (const metric of payload.metrics) {
    const state = resultPresentation({ ...payload, metric }, { unit: '' }).state;
    summary[state]++;
    if (summary.games && metric.leaderboard?.status === 'available' && metric.leaderboard.rows?.length) {
      summary.populatedLeaderboards++;
    }
  }
  return summary;
}

export function metricCardPresentation(payload, metric) {
  const result = payload?.metric ?? payload?.metrics?.find(row => row.metricId === metric.id);
  if (!result) return {state:'unloaded',hasPlayers:false,hasResults:false,hasGaps:false,
    headline:'Not loaded',badge:'Load selected-game results'};
  const presentation = resultPresentation({...payload, metric:result}, metric);
  if (presentation.state === 'empty') return {...presentation,hasPlayers:false,hasResults:false,hasGaps:false};
  const board = result.leaderboard, groups = board?.groups ?? [board];
  const complete = groups.length > 0 && groups.every(group => ['available','empty'].includes(group?.status));
  const hasPlayers = board?.status === 'available' && Boolean(board.rows?.length);
  const state = {...presentation,hasPlayers,hasResults:hasPlayers || ['available','partial'].includes(presentation.state),
    hasGaps:!complete,noQualifiers:complete && !hasPlayers};
  if (hasPlayers) return {...state,state:complete ? 'available' : 'partial',
    badge:complete ? 'Player results available' : 'Some player results available',
    headline:`${board.rows.length} qualified ${board.groups ? 'player entries' : 'players'}`,
    message:complete ? 'Qualified player results are ready for this period.' : 'Player results are available for some review mechanisms; others remain incomplete.'};
  if (complete) return {...state,state:'empty',badge:'No qualifying players',headline:'Participation minimum not met',
    message:board.message ?? 'No players meet the participation minimum for this period.'};
  return state;
}

export function metricVisible(presentation, visibility) {
  return visibility === 'results' ? presentation.hasResults : visibility === 'gaps' ? presentation.hasGaps : true;
}

export function resultScopeLabel(result, presentation) {
  if (presentation.hasPlayers || presentation.noQualifiers) return presentation.message;
  if (result.status === 'available' || result.playerPopulationComplete === true) return result.scope ?? 'Selected evidence population';
  if (result.runs?.length) return 'Each listed score covers a complete individual run. Coverage of all runs in the selection remains incomplete.';
  if (result.consequences?.length) return 'These scores cover the shown award advances only. Full plate-appearance and population results remain unavailable.';
  return result.scope ?? 'Selected evidence population';
}

export function dashboardLoadStatus(payload) {
  const games = payload.graphCount ?? payload.metrics?.[0]?.coverage?.games ?? 0;
  if (!games) return 'No games in this selection. Try another date range.';
  const cards = (payload.metrics ?? []).map(metric => metricCardPresentation({...payload,metric},{unit:''}));
  const leaders = cards.filter(card => card.hasPlayers).length;
  const empty = cards.filter(card => card.noQualifiers).length;
  const incomplete = cards.filter(card => card.hasGaps).length;
  const messages = [leaders ? `${leaders} player leaderboard${leaders === 1 ? '' : 's'} loaded.` :
    `Game data loaded for ${games} game${games === 1 ? '' : 's'}, but no player leaderboards are available.`];
  if (empty) messages.push(`No players meet the participation minimum for ${empty} leaderboard${empty === 1 ? '' : 's'}.`);
  if (incomplete) messages.push(`${incomplete} leaderboard${incomplete === 1 ? ' still has' : 's still have'} incomplete player results.`);
  if (leaders) messages.push('Select a card to see all qualified players and their evidence.');
  return messages.join(' ');
}

export function matchesMetric(metric, term, group = 'all') {
  const searchable = [metric.label, metric.technicalLabel, metric.id, metric.presentation?.question, metric.presentation?.summary].join(' ').toLowerCase();
  return (group === 'all' || metric.presentation?.group === group) && searchable.includes(term.trim().toLowerCase());
}

export function metricRanking(payload, metric) {
  const result = payload?.metrics?.find(row => row.metricId === metric.id) ?? payload?.metric;
  const board = result?.leaderboard;
  return { rows: board?.status === 'available' ? board.rows.map(row => ({ ...row,
    context: row.qualificationLabel ?? `${row.plateAppearances} PA · minimum ${row.minimumPA} PA` })) : [],
    groups: board?.groups ?? [],
    scope: 'qualified players', order: board?.order ?? '', qualification: board?.qualification?.rule ?? '',
    unit: board?.unit ?? metric.unit, summaryKind: board?.summaryKind ?? (metric.id === 'empty-game-rate' ? 'count' : 'mean'),
    message: !result ? 'Loading player rankings…' : board?.message ?? 'Complete player scores are not yet available for this period.' };
}

export function rankingScore(row, unit) {
  if (row.value) return {text:formatMetricValue(row.value, unit),
    evidence:`${row.value.numerator}/${row.value.denominator}`, title:`Exact: ${row.value.numerator}/${row.value.denominator}`};
  if (Number.isFinite(row.approximateValue) && Array.isArray(row.channelCounts)) {
    const evidence = row.channelCounts.join(' / ');
    return {text:`≈ ${row.approximateValue.toFixed(3)}`, evidence,
      title:`Exact positive channel counts (own batting / helping runners / independent running): ${evidence}. Logarithmic score and ordering are approximate.`};
  }
  return {text:'Unavailable', evidence:'', title:''};
}

function rankingPreview(payload, metric) {
  const ranking = metricRanking(payload, metric), list = node('span'); list.className = 'card-ranking';
  if (ranking.groups.length) {
    for (const group of ranking.groups) {
      list.append(node('strong', group.label));
      list.append(rankingPreview({metric:{leaderboard:group}}, metric));
    }
    return list;
  }
  if (!ranking.rows.length) {
    list.append(node('span', ranking.message), node('small', ranking.qualification));
    return list;
  }
  const heading = node('span', `Top ${Math.min(5, ranking.rows.length)} · ${ranking.summaryKind === 'count' ? 'count' : 'average'} in selected period`); heading.className = 'ranking-caption';
  list.append(heading);
  for (const row of ranking.rows.slice(0, 5)) {
    const line = node('span'); line.className = 'ranking-row';
    const person = node('span'); person.className = 'ranking-person';
    person.append(node('span', row.name), node('small', row.context));
    const display = rankingScore(row, ranking.unit);
    const score = node('span', display.text); score.className = 'ranking-score';
    score.title = display.title;
    line.append(node('span', String(row.rank)), person, score); list.append(line);
  }
  list.append(node('small', `${ranking.order} · ${ranking.rows.length} qualified players`));
  return list;
}

function renderRanking(payload, metric) {
  const ranking = metricRanking(payload, metric), target = byId('metric-ranking');
  target.replaceChildren(); target.hidden = false;
  if (!ranking.rows.length) {
    target.append(node('h3', 'Player leaderboard'), node('p', ranking.message), node('p', ranking.qualification));
    return;
  }
  target.append(node('h3', `All ${ranking.rows.length} ranked ${ranking.scope}`),
    node('p', `${ranking.order}. Ties share a rank. ${ranking.qualification}`));
  for (const group of ranking.groups.filter(group => group.status !== 'available')) {
    target.append(node('p', `${group.label}: ${group.message} ${group.qualification?.rule ?? ''}`));
  }
  const table = node('table'), head = node('thead'), header = node('tr'), body = node('tbody');
  for (const label of ['Rank', 'Player / participation minimum', `${ranking.summaryKind === 'count' ? 'Count' : 'Average'} · ${metric.presentation.unitLabel}`,
    metric.id === 'contribution-path-diversity' ? 'Exact channel counts' : 'Exact value']) {
    const cell = node('th', label); cell.scope = 'col'; header.append(cell);
  }
  head.append(header);
  for (const row of ranking.rows) {
    const line = node('tr'), person = node('td'); person.append(node('span', row.name), node('small', row.context));
    if (row.mechanismLabel) person.append(node('small', row.mechanismLabel));
    const display = rankingScore(row, ranking.unit), evidence = node('td', display.evidence); evidence.title = display.title;
    line.append(node('td', String(row.rank)), person, node('td', display.text), evidence); body.append(line);
  }
  table.append(head, body); target.append(table);
}

function renderList() {
  const term = byId('metric-search').value.trim().toLowerCase();
  const visibility = byId('metric-visibility').value;
  const group = byId('metric-group').value;
  const ordered = catalog.groups.flatMap(group => catalog.metrics.filter(metric => metric.presentation.group === group.id));
  const buttons = ordered.filter(m => matchesMetric(m, term, group)).flatMap(metric => {
    const result = dashboardResult?.metrics.find(result => result.metricId === metric.id);
    const presentation = metricCardPresentation(dashboardResult, metric);
    if (!metricVisible(presentation, visibility)) return [];
    const button = node('button'); button.type = 'button'; button.dataset.id = metric.id;
    const hasLeaders = presentation.hasPlayers;
    button.dataset.state = presentation.state;
    const category = node('small', catalog.groups.find(group => group.id === metric.presentation.group).label); category.className = 'card-category';
    const question = node('p', metric.presentation.question); question.className = 'card-question';
    button.append(category, node('span', metric.label), question);
    button.setAttribute('aria-current', String(selected?.id === metric.id));
    const scope = result?.consequences?.length ? `${result.consequences.length} award play${result.consequences.length === 1 ? '' : 's'}` :
      result?.runs?.length ? `${result.runs.length} complete scoring histories` :
      result?.coverage?.resolvedReviews !== undefined ? `${result.coverage.resolvedReviews} resolved mapped reviews` : metric.presentation.scopeLabel;
    if (!hasLeaders) button.append(node('strong', presentation?.headline ?? 'Not loaded'),
      node('small', presentation?.badge ?? 'Load selected-game evidence'),
      node('small', `${scope} · ${metric.presentation.unitLabel}`));
    button.append(rankingPreview(dashboardResult, metric));
    const more = node('small', 'View all results and evidence →'); more.className = 'card-more'; button.append(more);
    button.addEventListener('click', () => {
      choose(metric); byId('metric-detail').focus({ preventScroll: true }); byId('metric-detail').scrollIntoView({ block: 'start' });
    });
    return [button];
  });
  byId('metric-list').replaceChildren(...buttons);
  byId('metric-list-empty').hidden = Boolean(buttons.length);
}

function selectedScope() {
  const dateScope = { preset: byId('date-preset').value };
  if (dateScope.preset === 'custom') { dateScope.startDate = byId('start-date').value; dateScope.endDate = byId('end-date').value; }
  return { dateScope, gameSet: byId('game-set').value };
}

async function loadDashboard(event) {
  event.preventDefault();
  invalidateSelection();
  const controller = new AbortController(); dashboardRequest = controller;
  byId('load-dashboard').disabled = true;
  byId('dashboard-status').textContent = `Reading one shared evidence selection for all ${catalog.metrics.length} metrics…`;
  try {
    const response = await fetch('/api/metrics/dashboard', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(selectedScope()), signal: controller.signal });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error ?? 'Dashboard request failed.');
    if (dashboardRequest !== controller) return;
    const expected = new Set(catalog.metrics.map(metric => metric.id));
    if (!Array.isArray(payload.metrics) || payload.metrics.length !== expected.size ||
        new Set(payload.metrics.map(metric => metric.metricId)).size !== expected.size ||
        payload.metrics.some(metric => !expected.has(metric.metricId))) throw new Error('Dashboard response is incomplete.');
    dashboardResult = payload;
    const summary = dashboardSummary(payload);
    facts(byId('dashboard-summary'), [['Selected games', summary.games],
      ['Populated player leaderboards', `${summary.populatedLeaderboards} of ${payload.metrics.length}`]]);
    byId('dashboard-dates').textContent = resultDateLabel(payload);
    const coverage = payload.metrics[0].coverage ?? {}, movement = coverage.runnerMovements;
    byId('dashboard-coverage').textContent = `${coverage.observedEntities?.plate_appearance ?? 0} observed plate appearances · ${coverage.observedEntities?.run ?? 0} observed runs` +
      (movement ? ` · ${movement.withPersonalTrajectoryBinding ?? 0} of ${movement.observedPairs} movement pairs linked to a personal history.` : '.') +
      ' Coverage of eligible events may still be incomplete.';
    byId('dashboard-overview').hidden = false; byId('download-dashboard').disabled = false;
    byId('dashboard-status').textContent = dashboardLoadStatus(payload);
    renderList();
    if (!activeRequest) choose(selected);
  } catch (error) {
    if (dashboardRequest === controller && error.name !== 'AbortError') byId('dashboard-status').textContent = error.message;
  } finally {
    if (dashboardRequest === controller) { byId('load-dashboard').disabled = false; dashboardRequest = null; }
  }
}

function download(name, payload) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const link = node('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function showResult(payload) {
  lastResult = payload;
  const result = payload.metric;
  const presentation = metricCardPresentation(payload, selected);
  byId('result').dataset.state = presentation.state;
  byId('result-badge').textContent = presentation.badge;
  byId('result-dates').textContent = resultDateLabel(payload);
  const loaded = payload.dateScope ?? {};
  byId('loaded-dates').textContent = loaded.availableStartDate && loaded.availableEndDate ?
    `Loaded dates: ${loaded.availableStartDate} to ${loaded.availableEndDate}.` : '';
  byId('score-value').textContent = presentation.headline;
  const eventHeadline = !presentation.hasPlayers && !presentation.noQualifiers;
  const single = eventHeadline && presentation.state === 'partial' && result.consequences?.length === 1 ? result.consequences[0] : null;
  const singleRun = eventHeadline && result.runs?.length === 1 ? result.runs[0] : null;
  const displayed = eventHeadline ? result.value ?? single?.value ?? singleRun?.value : null;
  byId('score-exact').textContent = displayed ? `Exact: ${displayed.numerator}/${displayed.denominator}` : '';
  byId('result-subject').textContent = single ?
    `${displayPlayer(payload.display?.labels, single.graph, single.batter)} · Game ${single.graph.split('/').at(-1)} · PA source index ${single.plateAppearance.split('/').at(-1)}` :
    singleRun ? `${displayPlayer(payload.display?.labels, singleRun.graph, singleRun.runner)} · Game ${singleRun.graph.split('/').at(-1)}` : '';
  byId('result-scope').textContent = resultScopeLabel(result, presentation);
  byId('coverage-details').open = presentation.state === 'empty' || selected.id === 'adjudication-volatility';
  const coverage = result.coverage ?? {};
  renderGameCoverage(coverage.byGame);
  renderConsequences(result.consequences, result.metricId, payload.display?.labels);
  renderRunResults(result.runs, payload.display?.labels, result.metricId);
  renderUnresolvedRuns(result.unresolvedRuns);
  renderRunnerBoundaries(result.runnerBoundaryStates, payload.display?.labels);
  renderRanking(payload, selected);
  facts(byId('coverage'), [['Games', coverage.games ?? payload.graphCount ?? 0],
    ...(coverage.supportedAwardConsequences !== undefined ? [
      ['Supported award consequences', coverage.supportedAwardConsequences],
      ['Observed PAs without a scored award result', coverage.observedPAsWithoutSupportedAwardConsequence],
      ['Selected games with no evidence rows', coverage.selectedGraphsWithoutEvidence]] : []),
    ...(coverage.runnerBoundaryProjection ? [['Supported unchanged runner states', coverage.runnerBoundaryProjection.unchangedRunnerPAs]] : []),
    ...(coverage.resolvedReviews !== undefined ? [['Resolved reviews', coverage.resolvedReviews], ['Unresolved reviews', coverage.unresolvedReviews]] : []),
    ...(coverage.supportedRuns !== undefined ? [['Complete scoring histories', coverage.supportedRuns], ['Observed runs without a result', coverage.observedRunsWithoutResult]] : [])]);
  byId('result-evidence').textContent = JSON.stringify({ coverage, components: result.components ?? {}, evidence: result.evidence ?? [],
    runnerBoundaryStates: result.runnerBoundaryStates,
    implementation: payload.implementationSha256, corpus: payload.corpusFingerprint ?? payload.serving?.corpusFingerprint,
    dateScope: payload.dateScope, execution: payload.execution, display: payload.display }, null, 2);
  renderRequirements(result.gaps ?? []);
  byId('result').hidden = false;
  byId('download-result').disabled = false;
  byId('request-status').textContent = presentation.message;
}

async function inspect(event) {
  event.preventDefault();
  if (!byId('metric-form').reportValidity()) return;
  activeRequest?.abort(); const controller = new AbortController(); activeRequest = controller;
  byId('run-metric').disabled = true; byId('result').hidden = true; lastResult = null;
  byId('download-result').disabled = true;
  byId('request-status').textContent = 'Reading metric evidence…';
  const dateScope = { preset: byId('date-preset').value };
  if (dateScope.preset === 'custom') { dateScope.startDate = byId('start-date').value; dateScope.endDate = byId('end-date').value; }
  try {
    const response = await fetch('/api/metrics/query', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metricId: selected.id, gameSet: byId('game-set').value, dateScope }), signal: controller.signal });
    const payload = await response.json(); if (!response.ok) throw new Error(payload.error ?? 'Metric request failed.');
    if (activeRequest !== controller) return;
    showResult(payload);
  } catch (error) {
    if (activeRequest === controller && error.name !== 'AbortError') byId('request-status').textContent = error.message;
  } finally {
    if (activeRequest === controller) { byId('run-metric').disabled = false; activeRequest = null; }
  }
}

async function start() {
  try {
    const response = await fetch('/api/metrics/catalog');
    if (!response.ok) throw new Error('The metric catalog could not be loaded.');
    catalog = await response.json();
    const initial = selectionFromUrl(location.href);
    byId('game-set').value = initial.gameSet; byId('date-preset').value = initial.preset;
    byId('start-date').value = initial.startDate ?? ''; byId('end-date').value = initial.endDate ?? '';
    const updateDates = () => document.querySelectorAll('.custom-date').forEach(label => {
      label.hidden = byId('date-preset').value !== 'custom'; label.querySelector('input').required = !label.hidden;
    });
    updateDates();
    byId('metric-group').append(...catalog.groups.map(group => { const option = node('option', group.label); option.value = group.id; return option; }));
    renderList(); choose(catalog.metrics.find(m => '#' + m.id === location.hash) ?? catalog.metrics[0]);
    byId('all-gaps').replaceChildren(...catalog.gapRegister.gaps.map(g => gapDetails(g, true)));
    byId('download-gaps').disabled = false;
    byId('download-gaps').addEventListener('click', () => download('baseballo-metric-gaps.json', catalog.gapRegister));
    byId('download-result').addEventListener('click', () => { if (lastResult) download(selected.id + '-result.json', lastResult); });
    byId('metric-search').addEventListener('input', renderList);
    byId('load-dashboard').disabled = false;
    byId('metric-form').addEventListener('submit', loadDashboard);
    byId('run-metric').addEventListener('click', inspect);
    byId('back-to-dashboard').addEventListener('click', () => {
      byId('metric-search').focus({ preventScroll: true }); document.querySelector('.dashboard').scrollIntoView({ block: 'start' });
    });
    byId('metric-visibility').addEventListener('change', renderList);
    byId('metric-group').addEventListener('change', renderList);
    byId('download-dashboard').addEventListener('click', () => { if (dashboardResult) download('baseballo-dashboard.json', dashboardResult); });
    byId('metric-form').addEventListener('input', scheduleDashboardLoad);
    byId('metric-form').addEventListener('change', scheduleDashboardLoad);
    byId('date-preset').addEventListener('change', updateDates);
    byId('example-choice').addEventListener('change', renderExampleCase);
    // Examples are presentation-only. Failure must not disable live inspection.
    fetch('/metric-examples.json').then(async response => {
      if (!response.ok) throw new Error('Examples unavailable');
      examples = await response.json(); renderExamples();
    }).catch(() => { examples = undefined; renderExamples(); });
    byId('metric-form').requestSubmit();
  } catch (error) {
    byId('metric-title').textContent = 'Metrics unavailable';
    byId('dashboard-status').textContent = error.message;
    byId('request-status').textContent = error.message;
  }
}

if (typeof document !== 'undefined') start();
