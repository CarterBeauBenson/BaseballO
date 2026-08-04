# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T12:55:04.6739487Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6617 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `7807830133195722973e44886269e090859f37ff3b6b84a27150a4b0e75c3efd`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 29.668 | 7.709 | 3.848x |
| outcomes-by-player | 58 | 17.806 | 10.318 | 1.726x |
| pitches-by-pitcher-and-venue | 6 | 16.69 | 9.448 | 1.767x |
| pitch-summary-by-pitcher | 6 | 52.204 | 14.978 | 3.485x |
| batted-balls-by-batter-and-venue | 22 | 22.168 | 9.947 | 2.229x |
| events-by-player | 75 | 38.109 | 12.287 | 3.102x |
| runs-by-season-and-venue | 1 | 11.09 | 5.037 | 2.202x |
| games-by-team-and-season | 2 | 5.612 | 5.293 | 1.06x |
| umpire-assignments | 4 | 6.569 | 6.299 | 1.043x |
| available-players | 22 | 7.348 | 7.395 | 0.994x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
