import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { readOfficialGameMetadata, mapGameDateIndex } from '../server.mjs';

const graphPrefix = 'https://w3id.org/baseball/graph/game/';

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'baseballo-game-dates-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const samplesRoot = join(root, 'samples');
  const stateRoot = join(root, 'state');
  const fixturePath = join(root, 'fixture.json');
  await mkdir(join(samplesRoot, 'historical'), { recursive: true });
  await mkdir(join(stateRoot, 'pipeline', 'manifests'), { recursive: true });
  await writeFile(join(samplesRoot, 'historical', 'schedule.json'), JSON.stringify({ dates: [{ games: [
    { gamePk: 1, officialDate: '2026-08-25', gameType: 'R' },
  ] }] }));
  await writeFile(fixturePath, JSON.stringify({ gamePk: 566279, gameData: { datetime: { officialDate: '2019-04-01' } } }));
  async function manifest(id, values = {}, text) {
    await writeFile(join(stateRoot, 'pipeline', 'manifests', `game-${id}-rml.json`), text ?? JSON.stringify({
      gamePk: String(id), graphIri: `${graphPrefix}${id}`, officialDate: '2026-09-13', gameType: 'R', ...values,
    }));
  }
  return { options: { stateRoot, samplesRoot, fixturePath }, manifest };
}

test('current compact manifests expose new dates only for queried authoritative games', async (t) => {
  const { options, manifest } = await fixture(t);
  await manifest(2);
  await manifest(3); // Prepared input with no promoted graph.
  const metadata = await readOfficialGameMetadata(options);
  assert.equal(metadata.get('2').date, '2026-09-13');
  const index = mapGameDateIndex({ results: { bindings: [1, 2].map((id) => ({
    game: { value: `https://baseballontology.org/data/game/${id}` }, graph: { value: `${graphPrefix}${id}` },
  })) } }, metadata);
  assert.deepEqual(index.map(({ date }) => date), ['2026-08-25', '2026-09-13']);
  assert.equal(index.some(({ graph }) => graph.endsWith('/3')), false);
});

test('current source metadata overrides old schedules and keeps explicit classifications', async (t) => {
  const { options, manifest } = await fixture(t);
  await manifest(1, { gameType: 'A' });
  await manifest(2, { gameType: 'S' });
  await manifest(3, { gameType: null });
  await manifest(566279); // Development fixture never enters the season.
  const metadata = await readOfficialGameMetadata(options);
  assert.equal(metadata.get('1').date, '2026-09-13');
  assert.equal(metadata.get('1').gameSet, 'all_star');
  assert.equal(metadata.get('2').gameSet, 'other');
  assert.equal(metadata.has('3'), false);
  assert.equal(metadata.get('566279').gameSet, 'fixture');
  assert.equal(metadata.get('566279').date, '2019-04-01');
});

test('malformed or mismatched compact records cannot assign a date to another game', async (t) => {
  const { options, manifest } = await fixture(t);
  await manifest(2, { gamePk: '3' });
  await manifest(4, { graphIri: `${graphPrefix}5` });
  await manifest(6, {}, '{');
  await manifest(7, {}, 'null');
  await manifest(8, { officialDate: null });
  await manifest(9, {}, '\uFEFF' + JSON.stringify({ gamePk: '9', graphIri: `${graphPrefix}9`, officialDate: '2026-09-13', gameType: 'R' }));
  const metadata = await readOfficialGameMetadata(options);
  assert.deepEqual([...metadata.keys()].sort(), ['1', '566279', '9']);
});

test('legacy acquisition records without a game type never default to regular season', async (t) => {
  const { options } = await fixture(t);
  const legacy = join(options.stateRoot, 'pipeline', 'manifests', 'acquisition', 'games', '2026', '09');
  await mkdir(legacy, { recursive: true });
  await writeFile(join(legacy, '2.json'), JSON.stringify({ gamePk: 2, scheduleDate: '2026-09-13' }));
  await writeFile(join(legacy, '1.json'), JSON.stringify({ gamePk: 1, scheduleDate: '2026-09-13', gameType: 'S' }));
  const metadata = await readOfficialGameMetadata(options);
  assert.equal(metadata.get('2').gameSet, 'other');
  assert.equal(metadata.get('2').gameType, '');
  assert.equal(metadata.get('1').gameSet, 'other');
});

test('historical schedules and fixture remain usable without local pipeline state', async (t) => {
  const { options } = await fixture(t);
  const metadata = await readOfficialGameMetadata({ ...options, stateRoot: join(options.stateRoot, 'absent') });
  assert.equal(metadata.get('1').date, '2026-08-25');
  assert.equal(metadata.get('566279').gameSet, 'fixture');
});
