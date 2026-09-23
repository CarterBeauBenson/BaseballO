import importlib.util
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('report_cache',Path(__file__).resolve().parents[1]/'scripts/pipeline/serving_report_cache.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class ReportPartitions(unittest.TestCase):
    def test_restart_replays_completed_writes_and_corruption_misses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cache.sqlite';cache=M.ReportCache(path)
            with sqlite3.connect(':memory:') as original,sqlite3.connect(':memory:') as rebuilt:
                for db in (original,rebuilt): db.execute('CREATE TABLE facts (id INTEGER PRIMARY KEY,value TEXT)')
                writer=M.RecordingConnection(original);writer.commands=[]
                writer.executemany('INSERT INTO facts VALUES (?,?)',[(1,'bound " value'),(2,None)])
                writer.execute('UPDATE facts SET value=? WHERE id=?',('changed',1))
                writer.execute('SELECT * FROM facts').fetchall()
                cache.store('game','version',writer.commands,{'rows':2},[['facts','source row']])
                restarted=M.ReportCache(path);partition=restarted.load('game','version')
                restarted.replay(rebuilt,partition)
                self.assertEqual(original.execute('SELECT * FROM facts').fetchall(),rebuilt.execute('SELECT * FROM facts').fetchall())
                self.assertIsNone(restarted.load('game','changed-evidence'))
            with closing(sqlite3.connect(path)) as db,db:
                db.execute("UPDATE report_game SET payload=?",(b'corrupt',))
            self.assertIsNone(restarted.load('game','version'))
            self.assertEqual(restarted.stats['discarded'],1)

    def test_unavailable_cache_does_not_block_sql_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            occupied=Path(tmp)/'file';occupied.write_text('not a directory')
            cache=M.ReportCache(occupied/'cache.sqlite')
            self.assertIsNone(cache.load('g','v'))
            cache.store('g','v',[],{},[])


if __name__=='__main__':unittest.main()
