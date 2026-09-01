# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T18:02:28.0673236Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6538 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 226.908 | 8.456 | 26.834x |
| outcomes-by-player | 58 | 18.894 | 11.642 | 1.623x |
| outcomes-by-season | 11 | 584.31 | 6.248 | 93.52x |
| plate-appearances-by-player-and-season | 22 | 42.727 | 7.486 | 5.708x |
| three-true-outcomes-by-player | 14 | 8.893 | 6.801 | 1.308x |
| extra-base-hits-by-player | 7 | 5.996 | 5.303 | 1.131x |
| home-runs-by-player-and-venue | 2 | 5.516 | 4.748 | 1.162x |
| multi-hit-games | 6 | 19.833 | 5.43 | 3.652x |
| total-bases-by-player-and-season | 13 | 179.569 | 5.678 | 31.625x |
| hitless-games-by-player | 9 | 57.768 | 11.596 | 4.982x |
| pitches-by-pitcher-and-venue | 6 | 15.989 | 9.532 | 1.677x |
| pitch-summary-by-pitcher | 6 | 48.728 | 14.617 | 3.334x |
| batted-balls-by-batter-and-venue | 22 | 19.749 | 9.035 | 2.186x |
| events-by-player | 75 | 29.838 | 10.406 | 2.867x |
| runs-by-season-and-venue | 1 | 38.829 | 3.881 | 10.005x |
| games-by-team-and-season | 2 | 4.758 | 3.8 | 1.252x |
| umpire-assignments | 4 | 4.558 | 4.39 | 1.038x |
| available-players | 22 | 5.656 | 5.191 | 1.09x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
