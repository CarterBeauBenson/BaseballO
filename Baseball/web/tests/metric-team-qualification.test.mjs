import assert from 'node:assert/strict';
import {test} from 'node:test';
import {DatabaseSync} from 'node:sqlite';
import {mkdtempSync,mkdirSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {selectedTeamMinimums} from '../metric-team-qualification.mjs';
import {playerLeaderboard} from '../query-builder/metric-suite-query-builder.js';

test('selected team schedules exclude a one-game leader without changing its average', t => {
  const state=mkdtempSync(join(tmpdir(),'baseballo-team-minimum-'));
  t.after(()=>rmSync(state,{recursive:true,force:true}));
  const id='20260929T000000Z-dashboard-123456abcdef';
  mkdirSync(join(state,'serving/dashboard/builds'),{recursive:true});
  const db=new DatabaseSync(join(state,'serving/dashboard/builds',id+'.sqlite'));
  db.exec(`CREATE TABLE dashboard_build(build_id TEXT,corpus_fingerprint TEXT,status TEXT);
    CREATE TABLE game_dimension(graph_iri TEXT,official_date TEXT,game_set TEXT);
    CREATE TABLE dashboard_player_game(graph_iri TEXT,player TEXT,team TEXT);
    INSERT INTO dashboard_build VALUES ('${id}','corpus','validated');`);
  const player=n=>'https://baseballontology.org/data/player/'+n;
  for(let n=1;n<=7;n++) {
    db.prepare('INSERT INTO game_dimension VALUES (?,?,?)').run('g'+n,'2026-09-0'+n,'regular_season');
    db.prepare('INSERT INTO dashboard_player_game VALUES (?,?,?)').run('g'+n,player(3),'B');
    if(n<=6) db.prepare('INSERT INTO dashboard_player_game VALUES (?,?,?)').run('g'+n,player(2),'A');
  }
  db.prepare('INSERT INTO dashboard_player_game VALUES (?,?,?)').run('g1',player(1),'A');
  db.prepare('INSERT INTO dashboard_player_game VALUES (?,?,?)').run('g1',player(4),'A');
  db.prepare('INSERT INTO dashboard_player_game VALUES (?,?,?)').run('g2',player(4),'B');
  db.close();
  const scope={gameSet:'regular_season',startDate:'2026-09-01',endDate:'2026-09-07'};
  const rows=[[1,3,1,9],[2,24,6,1],[3,20,7,2],[4,22,2,3]].map(([id,pa,games,value])=>({
    player:player(id),metricId:'offensive-reach',status:'available',completeParticipation:true,
    dateScope:scope,plateAppearances:pa,teamGames:games,
    aggregate:{kind:'mean',sum:{numerator:String(value),denominator:'1'},count:1}}));
  const input={serving:{publication:'dashboard',buildId:id,corpusFingerprint:'corpus'},dateScope:scope,
    metric:{playerPopulationComplete:true,playerResults:rows}};
  const output=selectedTeamMinimums(input,state);
  const board=playerLeaderboard(output.metric,{id:'offensive-reach',higherIs:'better'},scope);
  assert.deepEqual(board.rows.map(r=>[r.player,r.minimumPA]),[[player(4),22],[player(2),19]]);
  assert.equal(board.belowMinimum,2);
  assert.deepEqual(output.metric.playerResults[0].aggregate,rows[0].aggregate);
  assert.equal(rows[0].qualificationTeamGames,undefined);
  const oneDay={...input,dateScope:{...scope,endDate:'2026-09-01'},metric:{...input.metric,playerResults:[rows[0]]}};
  assert.equal(selectedTeamMinimums(oneDay,state).metric.playerResults[0].qualificationTeamGames,1);
  assert.throws(()=>selectedTeamMinimums({...input,serving:{...input.serving,corpusFingerprint:'wrong'}},state),/same published dashboard/);
});
