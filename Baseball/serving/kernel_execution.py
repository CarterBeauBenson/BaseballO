"""Prepare fixed SPARQL arithmetic once, then supply each VALUES population.

The authoritative query text is the cache key. This caches parsing, not metric
values, graph facts or admission decisions. Per-query locks protect RDFLib's
mutable algebra; input rows are removed after every evaluation.
"""
from functools import lru_cache
from threading import RLock

from rdflib import Graph, Literal
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.processor import prepareQuery


@lru_cache(maxsize=32)
def prepared(text, width):
    placeholder='('+' '.join(['UNDEF']*width)+')'
    query=prepareQuery(text.replace('# INPUT_ROWS',placeholder).replace('# PEER_ROWS',placeholder))
    slots=[]
    def visit(value):
        if isinstance(value,CompValue) and value.name=='values':
            rows=value['res']
            if len(rows)!=1 or len(rows[0])!=width or any(v!='UNDEF' for v in rows[0].values()):
                raise ValueError('Metric kernel has an unexpected VALUES layout')
            slots.append((value,tuple(rows[0]),rows))
        if isinstance(value,dict):
            for child in value.values():visit(child)
        elif isinstance(value,(list,tuple)):
            for child in value:visit(child)
    visit(query.algebra)
    expected=1+('# PEER_ROWS' in text)
    if len(slots)!=expected:raise ValueError('Metric kernel VALUES population is missing')
    return query,slots,RLock()


def execute(text,columns,rows):
    query,slots,lock=prepared(text,len(columns))
    if not rows:return []
    values=[tuple('UNDEF' if row.get(c) is None else Literal(row[c]) for c in columns) for row in rows]
    with lock:
        try:
            for node,variables,_ in slots:
                node['res']=[dict(zip(variables,row)) for row in values]
            return [{str(k):v.toPython() for k,v in row.asdict().items()} for row in Graph().query(query)]
        finally:
            for node,_,original in slots:node['res']=original
