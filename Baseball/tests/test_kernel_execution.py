"""Prepared SPARQL preserves the textual executor's exact VALUES semantics."""
from concurrent.futures import ThreadPoolExecutor
from decimal import localcontext
import unittest
from rdflib import Graph,Literal
from test_metric_suite_serving import M


def textual(metric,rows):
    entry=next(e for e in [*M.catalog()['metrics'],*M.catalog()['components']] if e['id']==metric)
    values='\n'.join('('+' '.join('UNDEF' if r.get(c) is None else Literal(r[c]).n3()
        for c in entry['inputColumns'])+')' for r in rows)
    query=(M.ROOT/entry['authoritativeQuery']).read_text().replace('# INPUT_ROWS',values).replace('# PEER_ROWS',values)
    with localcontext() as context:
        context.prec=180
        return [{str(k):v.toPython() for k,v in r.asdict().items()} for r in Graph().query(query)]


class KernelExecution(unittest.TestCase):
    def test_dynamic_populations_nulls_and_peer_ranks_match_text_queries(self):
        cases=[('tfs',[dict(key='scope',participant='one',start=1,end=3,terminal='safe',creditProgress=True,
                    creditOut=False,outsBefore=1,attributedOuts=1),
                dict(key='scope',participant='two',start=0,end=None,terminal='out',creditProgress=False,
                    creditOut=True,outsBefore=1,attributedOuts=1)]),
            ('resolution-depth',[dict(key='scope',act='a',next='b',agent='one'),
                                 dict(key='scope',act='b',next=None,agent='two')]),
            ('paq-2',[dict(key='a',cohort='cohort',scoreN=10**65+1,scoreD=10**66+3),
                       dict(key='b',cohort='cohort',scoreN=10**65+2,scoreD=10**66+3)]),
            ('empty-game-rate',[dict(key='quotes " and new\nline',game='g',plateAppearances=1,positiveEpisodes=0)])]
        for metric,rows in cases:
            with self.subTest(metric=metric):
                for population in (rows,rows[:1],list(reversed(rows)),rows):
                    self.assertEqual(sorted(M.run_kernel(metric,population),key=str),sorted(textual(metric,population),key=str))
                self.assertEqual(M.run_kernel(metric,[]),[])
        # A reused plan cannot retain another game's VALUES in parallel callers.
        jobs=[('empty-game-rate',[dict(key=str(i),game='g',plateAppearances=1,positiveEpisodes=i%2)]) for i in range(8)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            actual=list(pool.map(lambda job:M.run_kernel(*job),jobs))
        self.assertEqual(actual,[textual(*job) for job in jobs])


if __name__=='__main__':unittest.main()
