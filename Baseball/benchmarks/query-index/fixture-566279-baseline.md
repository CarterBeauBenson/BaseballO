# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T17:11:14.5327627Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6538 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 233.611 | 7.484 | 31.215x |
| outcomes-by-player | 58 | 18.945 | 10.72 | 1.767x |
| outcomes-by-season | 11 | 602.151 | 5.349 | 112.573x |
| plate-appearances-by-player-and-season | 22 | 43.837 | 6.761 | 6.484x |
| three-true-outcomes-by-player | 14 | 7.457 | 5.882 | 1.268x |
| extra-base-hits-by-player | 7 | 5.45 | 4.796 | 1.136x |
| home-runs-by-player-and-venue | 2 | 4.191 | 3.827 | 1.095x |
| multi-hit-games | 6 | 20.26 | 4.845 | 4.182x |
| total-bases-by-player-and-season | 13 | 184.524 | 5.591 | 33.004x |
| hitless-games-by-player | 9 | 56.047 | 11.8 | 4.75x |
| pitches-by-pitcher-and-venue | 6 | 15.834 | 9.283 | 1.706x |
| pitch-summary-by-pitcher | 6 | 50.316 | 15.25 | 3.299x |
| batted-balls-by-batter-and-venue | 22 | 21.541 | 9.18 | 2.347x |
| events-by-player | 75 | 34.518 | 11.131 | 3.101x |
| runs-by-season-and-venue | 1 | 39.439 | 4.071 | 9.688x |
| games-by-team-and-season | 2 | 4.596 | 3.603 | 1.276x |
| umpire-assignments | 4 | 4.182 | 3.772 | 1.109x |
| available-players | 22 | 4.898 | 4.8 | 1.02x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
