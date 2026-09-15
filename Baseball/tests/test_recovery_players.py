"""Complete season reference -> exact selected-period Recovery player means."""
import copy
from datetime import date,timedelta
import json
import sqlite3
import unittest

from rdflib import Dataset,Literal,URIRef,XSD
from test_pitch_count_admission import pitch_fixture
from test_batting_progress_players import BASE,BFO,CCO,GAME,PROOF
from test_metric_suite_serving import M,G1,bindings


def sample(game,steps):
    data,_=pitch_fixture();g=data.graph(G1)
    if steps==0:
        prefixes=[str(GAME)+'/pitch/pitch-'+str(i) for i in (2,3)]
        records=[str(GAME)+'/event-record/pitch/pitch-'+str(i) for i in (2,3)]
        for triple in list(g):
            if any(str(v).startswith(p) for v in (triple[0],triple[2]) for p in prefixes+records):g.remove(triple)
    elif steps==4:
        old=str(GAME)+'/pitch/pitch-2';old_record=str(GAME)+'/event-record/pitch/pitch-2'
        for i in (1,2):
            new=str(GAME)+'/pitch/extra-'+str(i);new_record=str(GAME)+'/event-record/pitch/extra-'+str(i)
            for s,p,o in list(g):
                if str(s).startswith(old) or str(s)==old_record:
                    def replace(v):
                        if not isinstance(v,URIRef):return v
                        return URIRef(str(v).replace(old_record,new_record).replace(old,new))
                    if p==CCO.ont00001767:
                        o=Literal(f'2026-08-01T12:03:{i*10+(1 if str(s).endswith("/end") else 0):02}Z',datatype=XSD.dateTime)
                    g.add((replace(s),p,replace(o)))
    result=Dataset();graph='https://w3id.org/baseball/graph/game/'+str(game)
    for s,p,o in g:
        def replace(v):
            return URIRef(str(v).replace(str(GAME),'https://baseballontology.org/data/game/'+str(game))) if isinstance(v,URIRef) else v
        result.graph(graph).add((replace(s),p,replace(o)))
    return graph,bindings(result,[graph])


def database(samples):
    conn=sqlite3.connect(':memory:');conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript((M.ROOT/'serving/schema.sql').read_text());M.initialize_sql(conn)
    for i,(graph,rows) in enumerate(samples,1):
        day=f'2026-08-0{i}';game=graph.rsplit('/',1)[-1]
        conn.execute('INSERT INTO game_dimension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (graph,'https://baseballontology.org/data/game/'+game,game,day,day+'T12:00:00Z',2026,'regular_season',None,None,None,None,None,None))
        M.materialize_game(conn,graph,rows,batting_admission=PROOF,pitch_count_admission=PROOF)
    day=date(2026,1,1)
    while day<=date(2026,8,3):
        games=[dict(gamePk=str(100+day.day),gameType='R',final=True,unplayed=False)] if day.month==8 else []
        text=M._json(dict(completeResponse=True,games=games))
        conn.execute('INSERT INTO metric_suite_schedule_coverage VALUES (?,?,?)',(day.isoformat(),text,M._hash(text)))
        day+=timedelta(days=1)
    return conn


SCOPE=dict(startDate='2026-08-02',endDate='2026-08-03',gameSet='regular_season')


class RecoveryPlayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.samples=[sample(101,0),sample(102,2),sample(103,4)]

    def query(self,conn):return M.query_sql(conn,dict(metricId='recovery-quality'),SCOPE)['metric']

    def test_season_rank_precedes_selected_range_mean_and_keeps_official_pa_minimum(self):
        with database(self.samples) as conn:
            result=self.query(conn)
            self.assertTrue(result['playerPopulationComplete'],result)
            player,=result['playerResults']
            self.assertEqual(player['value'],M.exact(75))
            self.assertEqual(player['aggregate'],dict(kind='mean',count=2,sum=M.exact(150)))
            self.assertEqual(player['plateAppearances'],2);self.assertEqual(player['teamGames'],2)
            self.assertEqual(result['referencePopulations'][0]['applicablePlateAppearances'],3)

    def test_missing_preselection_game_or_calendar_day_withholds_reference(self):
        for change in ('schedule','game','count'):
            with self.subTest(change=change),database(self.samples) as conn:
                if change=='schedule':conn.execute("DELETE FROM metric_suite_schedule_coverage WHERE official_date='2026-07-01'")
                elif change=='game':
                    # Keep the independent schedule; a loaded subset is insufficient.
                    conn.execute("UPDATE game_dimension SET game_set='fixture' WHERE game_pk='101'")
                else:
                    text=M._json(dict(status='withheld'))
                    conn.execute('UPDATE metric_suite_count_admission SET proof_json=?,proof_sha256=? WHERE graph_iri=?',(text,M._hash(text),G1))
                result=self.query(conn);self.assertFalse(result['playerPopulationComplete'])
                self.assertEqual(result['playerResults'],[])

    def test_changed_reference_score_or_proof_is_detected(self):
        for table,column in [('metric_suite_result','result_json'),('metric_suite_count_admission','proof_json')]:
            with self.subTest(table=table),database(self.samples) as conn:
                conn.execute(f'UPDATE {table} SET {column}=? WHERE graph_iri=?',('{}',G1))
                with self.assertRaisesRegex(M.EvidenceError,'checksum'):self.query(conn)

    def test_per_game_inputs_are_not_published_as_percentiles(self):
        with database(self.samples) as conn:
            result,=M.read_results(conn,G1,'recovery-quality')
            self.assertEqual(result['status'],'unavailable')
            self.assertTrue(result['recoveryInputs']['complete'])
            pa,=result['recoveryInputs']['plateAppearances']
            self.assertEqual(pa['value'],M.exact(0))
            rows=M.normalize_bindings(self.samples[0][1],[G1])
            denied=M.recovery_game_inputs(rows,graph=G1,batting_admission=PROOF,pitch_count_admission={})
            self.assertFalse(denied['complete']);self.assertEqual(denied['plateAppearances'],[])


if __name__=='__main__':unittest.main()
