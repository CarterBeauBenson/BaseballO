# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T16:51:11.0112095Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6538 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 232.328 | 7.671 | 30.287x |
| outcomes-by-player | 58 | 18.544 | 10.189 | 1.82x |
| outcomes-by-season | 11 | 605.973 | 5.553 | 109.125x |
| plate-appearances-by-player-and-season | 22 | 44.274 | 6.952 | 6.369x |
| three-true-outcomes-by-player | 14 | 7.795 | 6.336 | 1.23x |
| pitches-by-pitcher-and-venue | 6 | 12.902 | 7.517 | 1.716x |
| pitch-summary-by-pitcher | 6 | 38.365 | 11.753 | 3.264x |
| batted-balls-by-batter-and-venue | 22 | 16.132 | 7.37 | 2.189x |
| events-by-player | 75 | 28.969 | 9.931 | 2.917x |
| runs-by-season-and-venue | 1 | 40.353 | 3.966 | 10.175x |
| games-by-team-and-season | 2 | 4.911 | 3.958 | 1.241x |
| umpire-assignments | 4 | 4.332 | 4.204 | 1.03x |
| available-players | 22 | 6.055 | 5.946 | 1.018x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
