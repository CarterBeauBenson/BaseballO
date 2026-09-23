"""Resumable per-game SQL partitions for the report builder.

Exact prepared parameterized writes and source row sequences are retained.
Publication still runs the report builder's existing SQL checks. This cache
never writes authority or serves HTTP, and corruption falls back to extraction.
"""
from contextlib import closing
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import time
import zlib

LIMIT=128*1024*1024


class RecordingConnection:
    def __init__(self,connection): self.connection=connection;self.commands=None
    def __getattr__(self,name): return getattr(self.connection,name)
    def execute(self,sql,parameters=()):
        result=self.connection.execute(sql,parameters)
        if self.commands is not None and sql.lstrip().split(None,1)[0].upper() in {'INSERT','UPDATE','DELETE','REPLACE'}:
            self.commands.append([sql,list(parameters)])
        return result
    def executemany(self,sql,parameters):
        if self.commands is None: return self.connection.executemany(sql,parameters)
        rows=list(parameters)
        result=self.connection.executemany(sql,rows)
        self.commands.extend([sql,list(row)] for row in rows)
        return result
    def __enter__(self): self.connection.__enter__();return self
    def __exit__(self,*args): return self.connection.__exit__(*args)


class ReportCache:
    def __init__(self,path):
        self.path=Path(path);self.stats=dict(hits=0,misses=0,discarded=0,written=0)
        self.enabled=True
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(self.path,timeout=5)) as db,db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE IF NOT EXISTS report_game (graph TEXT,identity TEXT,payload_sha TEXT,payload BLOB,touched INTEGER,PRIMARY KEY(graph,identity))')
        except (OSError,sqlite3.Error): self.enabled=False

    def load(self,graph,identity):
        if not self.enabled:
            self.stats['misses']+=1;return None
        try:
            with closing(sqlite3.connect(self.path,timeout=5)) as db:
                row=db.execute('SELECT payload_sha,payload FROM report_game WHERE graph=? AND identity=?',(graph,identity)).fetchone()
            if row:
                with gzip.GzipFile(fileobj=io.BytesIO(row[1])) as stream: raw=stream.read(LIMIT+1)
                if len(raw)>LIMIT or hashlib.sha256(raw).hexdigest()!=row[0]: raise ValueError('Report partition checksum mismatch')
                result=json.loads(raw)
                if set(result)!={'commands','summary','sourceRows'}: raise ValueError('Invalid report partition')
                self.stats['hits']+=1;return result
        except (OSError,ValueError,EOFError,zlib.error,sqlite3.Error): self.stats['discarded']+=1
        self.stats['misses']+=1;return None

    def store(self,graph,identity,commands,summary,source_rows):
        if not self.enabled: return
        raw=json.dumps(dict(commands=commands,summary=summary,sourceRows=source_rows),sort_keys=True,separators=(',',':')).encode()
        if len(raw)>LIMIT: return
        try:
            with closing(sqlite3.connect(self.path,timeout=5)) as db,db:
                db.execute('INSERT OR REPLACE INTO report_game VALUES (?,?,?,?,?)',
                    (graph,identity,hashlib.sha256(raw).hexdigest(),gzip.compress(raw,compresslevel=1,mtime=0),time.time_ns()))
                db.execute('DELETE FROM report_game WHERE graph=? AND identity NOT IN '
                    '(SELECT identity FROM report_game WHERE graph=? ORDER BY touched DESC LIMIT 3)',(graph,graph))
            self.stats['written']+=1
        except (OSError,sqlite3.Error): pass

    @staticmethod
    def replay(connection,partition):
        for sql,parameters in partition['commands']: connection.execute(sql,parameters)
