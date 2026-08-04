# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T11:42:45.5207373Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 29736 triples
- Query-index graph: 6981 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `0c59bb559cb50fafd79c6e0f1a5740ced1962d6156ff4ee039cbbd630a2eecd3`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 28.082 | 7.548 | 3.72x |
| outcomes-by-player | 58 | 16.775 | 10.315 | 1.626x |
| pitches-by-pitcher-and-venue | 6 | 14.476 | 8.797 | 1.646x |
| pitch-summary-by-pitcher | 6 | 44.566 | 12.662 | 3.52x |
| batted-balls-by-batter-and-venue | 22 | 17.213 | 8.922 | 1.929x |
| events-by-player | 75 | 31.928 | 10.349 | 3.085x |
| runs-by-season-and-venue | 1 | 6.308 | 5.179 | 1.218x |
| games-by-team-and-season | 2 | 5.904 | 5.394 | 1.095x |
| umpire-assignments | 4 | 5.436 | 5.292 | 1.027x |
| available-players | 22 | 6.763 | 6.691 | 1.011x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
