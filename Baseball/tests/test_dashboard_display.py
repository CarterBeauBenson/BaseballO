"""Names come from the selected game graphs, without a season-sized label response."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'serving'))
import dashboard_display as D


class DashboardDisplay(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('BASEBALLO_TEST_JENA_CLASSPATH'), 'requires deployed Jena')
    def test_bulk_names_bind_players_from_the_selected_graph(self):
        from rdflib import Dataset,URIRef,Literal,RDFS
        import test_legacy_paq_query as legacy
        data=Dataset(); graph='https://w3id.org/baseball/graph/game/101'
        player=URIRef('https://baseballontology.org/data/player/1')
        data.graph(URIRef(graph)).add((player,RDFS.label,Literal('Selected player')))
        data.graph(URIRef(graph)).add((URIRef('https://baseballontology.org/data/team/1'),RDFS.label,Literal('Team')))
        data.graph(URIRef(graph+'2')).add((player,RDFS.label,Literal('Outside selection')))
        rows=legacy.LegacyPaqQueryTests.run_query(self,data,D.query(graph))
        self.assertEqual([(r['graph']['value'],r['entity']['value'],r['label']['value']) for r in rows],
                         [(graph,str(player),'Selected player')])

    def test_names_are_compact_scoped_and_ambiguous_names_are_withheld(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE game_dimension(graph_iri TEXT PRIMARY KEY,official_date TEXT,game_set TEXT)')
            D.initialize(db)
            db.executemany('INSERT INTO game_dimension VALUES (?,?,?)',
                [('g1','2026-09-21','regular_season'),('g2','2026-09-22','regular_season'),
                 ('old','2025-09-21','regular_season')])
            db.executemany('INSERT INTO dashboard_display_label VALUES (?,?,?)',
                [('g1','p1','One'),('g2','p1','One'),('old','p1','Old name'),
                 ('g1','p2','Two'),('g2','p2','Conflicting name'),('g2','p3','Outside player graphs')])
            players=[dict(player=p,graphs=g,playerLabel='stale') for p,g in
                     [('p1',['g1','g2']),('p2',['g1','g2']),('p3',['g1'])]]
            result=dict(metrics=[dict(playerResults=players)])
            display=D.read(db,dict(gameSet='regular_season',startDate='2026-09-21',endDate='2026-09-22'),result)
            self.assertEqual(players[0]['playerLabel'],'One')
            self.assertNotIn('playerLabel',players[1]);self.assertNotIn('playerLabel',players[2])
            self.assertEqual(display['namedPlayers'],1);self.assertEqual(display['conflictingPlayers'],1)
            self.assertEqual(display['labels'],[])
            self.assertNotIn('Old name',json.dumps(result))


if __name__=='__main__':unittest.main()
