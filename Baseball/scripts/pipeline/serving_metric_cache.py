"""Disposable per-game calculations; current source admission always runs first.

This cache is owned by NiFi's serving materializer. It stores no authority and
cannot admit a graph, a source proof, a selected period or a player population.
Only exact evidence, exact validated proof inputs and identical calculation
code may reuse a product. Candidate SQL validation and publication still run.
"""
from contextlib import closing
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zlib

MAX_BYTES = 64 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


class MetricProductCache:
    def __init__(self, path, implementation_sha256):
        self.path = Path(path)
        self.implementation_sha256 = implementation_sha256
        self.stats = dict(hits=0, misses=0, bypassed=0, discarded=0)
        self.enabled = True
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('''CREATE TABLE IF NOT EXISTS game_product (
                    graph TEXT PRIMARY KEY, identity_sha256 TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, payload BLOB NOT NULL)''')
        except (OSError, sqlite3.Error):
            self.enabled = False

    def calculate(self, *, graph, rows, admissions, compute):
        if not self.enabled:
            self.stats['bypassed'] += 1
            return compute()
        identity = sha(canonical(dict(version=1, graph=graph, rows=rows,
            admissions=admissions, implementation=self.implementation_sha256)))
        try:
            with closing(sqlite3.connect(self.path, timeout=5)) as db:
                row = db.execute('SELECT identity_sha256,payload_sha256,payload '
                    'FROM game_product WHERE graph=?', (graph,)).fetchone()
            if row and row[0] == identity:
                with gzip.GzipFile(fileobj=io.BytesIO(row[2])) as stream:
                    raw = stream.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES or sha(raw) != row[1]:
                    raise ValueError('Metric cache checksum mismatch')
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError('Invalid metric product')
                self.stats['hits'] += 1
                return result
        except (OSError, EOFError, ValueError, TypeError, sqlite3.Error, zlib.error):
            self.stats['discarded'] += 1
        self.stats['misses'] += 1
        result = compute()
        if not isinstance(result, dict):
            raise ValueError('Invalid metric product cannot enter the serving cache')
        raw = canonical(result)
        if len(raw) <= MAX_BYTES:
            try:
                with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
                    # Retain one product per graph, never every historical version.
                    db.execute('INSERT OR REPLACE INTO game_product VALUES (?,?,?,?)',
                        (graph, identity, sha(raw), gzip.compress(raw, compresslevel=1, mtime=0)))
            except (OSError, sqlite3.Error):
                pass  # Recomputable acceleration must not become a build dependency.
        return result
