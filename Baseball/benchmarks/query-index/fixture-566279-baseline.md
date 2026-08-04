# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T17:02:46.7661140Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6538 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 234.996 | 7.853 | 29.924x |
| outcomes-by-player | 58 | 18.618 | 11.207 | 1.661x |
| outcomes-by-season | 11 | 619.441 | 5.528 | 112.055x |
| plate-appearances-by-player-and-season | 22 | 44.112 | 7.202 | 6.125x |
| three-true-outcomes-by-player | 14 | 7.477 | 6.014 | 1.243x |
| extra-base-hits-by-player | 7 | 5.445 | 4.491 | 1.212x |
| home-runs-by-player-and-venue | 2 | 4.771 | 3.979 | 1.199x |
| multi-hit-games | 6 | 20.072 | 4.696 | 4.274x |
| total-bases-by-player-and-season | 13 | 188.023 | 5.601 | 33.57x |
| pitches-by-pitcher-and-venue | 6 | 16.171 | 9.314 | 1.736x |
| pitch-summary-by-pitcher | 6 | 49.782 | 15.509 | 3.21x |
| batted-balls-by-batter-and-venue | 22 | 20.43 | 8.915 | 2.292x |
| events-by-player | 75 | 36.111 | 12.092 | 2.986x |
| runs-by-season-and-venue | 1 | 51.184 | 4.874 | 10.501x |
| games-by-team-and-season | 2 | 5.08 | 4.296 | 1.182x |
| umpire-assignments | 4 | 3.907 | 4.051 | 0.964x |
| available-players | 22 | 5.712 | 5.389 | 1.06x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
