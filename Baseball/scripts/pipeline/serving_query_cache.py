"""Disposable query answers bound to independently verified graph-pair versions.

NiFi's materializer owns this cache. It neither admits a source nor bypasses
candidate validation or the final live corpus snapshot. Unscoped, external,
volatile or unrecognized query forms use the normal uncached executor.
"""
from functools import lru_cache
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import zlib

from rdflib import URIRef, Variable
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.processor import prepareQuery

SCOPE_IRIS={'urn:baseballo:cache:authoritative','urn:baseballo:cache:index'}
PURE_CASTS={'http://www.w3.org/2001/XMLSchema#'+name for name in
            ('integer','decimal','double','float','boolean','string','dateTime','date','time')}
PURE_FUNCTIONS=PURE_CASTS | {'http://www.w3.org/2005/xpath-functions#'+name+'-from-duration'
                            for name in ('days','hours','minutes','seconds')}
PARSE_LOCK=threading.Lock()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def sha(value):return hashlib.sha256(value).hexdigest()


def valid_select(value):
    return (isinstance(value,dict) and isinstance(value.get('results'),dict)
            and isinstance(value['results'].get('bindings'),list))


@lru_cache(maxsize=256)
def query_dependencies(normalized):
    """Return exactly the permitted named graphs read, or None if unbounded."""
    try:
        with PARSE_LOCK:algebra=prepareQuery(normalized).algebra
    except Exception:return None
    if algebra.name!='SelectQuery':return None
    clauses=algebra.get('datasetClause')
    # CompValue.get returns its argument name when absent, unlike plain dict.
    clauses=clauses if isinstance(clauses,list) else []
    explicit_named=bool(clauses) and all('named' in c and str(c['named']) in SCOPE_IRIS for c in clauses)
    if clauses and not explicit_named:return None
    dependencies=set()
    named={str(c['named']) for c in clauses}

    def visit(value,inside=False):
        if isinstance(value,CompValue):
            if value.name=='ServiceGraphPattern':return False
            if value.name=='Function' and str(value['iri']) not in PURE_FUNCTIONS:return False
            if value.name in {'Builtin_NOW','Builtin_RAND','Builtin_UUID','Builtin_STRUUID','Builtin_BNODE'}:return False
            if value.name=='Graph':
                term=value['term']
                if not ((isinstance(term,URIRef) and str(term) in SCOPE_IRIS)
                        or (isinstance(term,Variable) and explicit_named)):return False
                dependencies.update(named if isinstance(term,Variable) else [str(term)])
                return visit(value['p'],True)
            if value.name=='BGP' and value['triples'] and not inside:return False
            return all(visit(v,inside) for k,v in value.items() if k!='_vars')
        if isinstance(value,(list,tuple)):return all(visit(v,inside) for v in value)
        return True
    return frozenset(dependencies) if visit(algebra) else None


def scoped_query(normalized):
    return query_dependencies(normalized) is not None


class ServingQueryCache:
    def __init__(self,path):
        self.path=Path(path);self.lock=threading.Lock()
        self.stats=dict(hits=0,misses=0,bypassed=0,discarded=0)
        self.enabled=True
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('''CREATE TABLE IF NOT EXISTS scoped_answer (
                    graph TEXT NOT NULL,slot TEXT NOT NULL,identity_sha256 TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,payload BLOB NOT NULL,
                    PRIMARY KEY(graph,slot))''')
        except (OSError,sqlite3.Error):self.enabled=False

    def count(self,key):
        with self.lock:self.stats[key]+=1

    def query(self,*,endpoint,query,slot,promotion,fetch):
        graph=promotion.get('authoritativeGraph');index=promotion.get('queryIndexGraph')
        hashes=('promotionManifestSha256','authoritativeRdfSha256','queryIndexRdfSha256')
        valid=(isinstance(graph,str) and isinstance(index,str) and graph!=index
            and all(isinstance(promotion.get(k),str) and len(promotion[k])==64
                    and all(c in '0123456789abcdef' for c in promotion[k]) for k in hashes))
        normalized=query.replace('<'+str(graph)+'>','<urn:baseballo:cache:authoritative>')
        normalized=normalized.replace('<'+str(index)+'>','<urn:baseballo:cache:index>')
        dependencies=query_dependencies(normalized) if self.enabled and valid else None
        if dependencies is None:
            self.count('bypassed');return fetch()
        # Promotion evidence is checked by the caller on every build. The pure
        # SELECT answer depends on graph contents, not the date of that proof
        # or an index graph the query never reads.
        graph_versions={}
        for scope,iri,digest in [('authoritative',graph,'authoritativeRdfSha256'),
                                 ('index',index,'queryIndexRdfSha256')]:
            if 'urn:baseballo:cache:'+scope in dependencies:
                graph_versions[iri]=promotion[digest]
        identity=sha(canonical(dict(version=2,endpoint=endpoint,query=query,
                                    graphs=graph_versions)))
        try:
            with closing(sqlite3.connect(self.path,timeout=5)) as db:
                row=db.execute('SELECT identity_sha256,payload_sha256,payload FROM scoped_answer WHERE graph=? AND slot=?',
                    (graph,slot)).fetchone()
            if row and row[0]==identity:
                # A compressed payload is bounded before parsing even if the
                # disposable cache file was corrupted independently of SQL.
                import io
                with gzip.GzipFile(fileobj=io.BytesIO(row[2])) as stream:raw=stream.read(64*1024*1024+1)
                if len(raw)>64*1024*1024 or sha(raw)!=row[1]:raise ValueError('Cache checksum mismatch')
                result=json.loads(raw)
                if not valid_select(result):
                    raise ValueError('Invalid cached SELECT result')
                self.count('hits');return result
        except (OSError,EOFError,ValueError,sqlite3.Error,zlib.error):self.count('discarded')
        self.count('misses');result=fetch()
        if not valid_select(result):
            raise ValueError('Invalid SELECT result cannot enter the serving cache')
        raw=canonical(result)
        if len(raw)<=64*1024*1024:
            try:
                with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
                    db.execute('INSERT OR REPLACE INTO scoped_answer VALUES (?,?,?,?,?)',
                        (graph,slot,identity,sha(raw),gzip.compress(raw,compresslevel=1,mtime=0)))
            except (OSError,sqlite3.Error):pass  # Cache failure does not alter the query result.
        return result
