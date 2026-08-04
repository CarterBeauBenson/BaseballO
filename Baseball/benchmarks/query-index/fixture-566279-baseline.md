# Query-index exploratory benchmark: game 566279

Generated: 2026-08-04T14:52:26.3312034Z

This is a single checked-in fixture measurement, not a multi-game scale claim. Initial executions validate exact result equivalence and prime each query path; repeated timings alternate authoritative/indexed execution order.

- Authoritative graph: 28419 triples
- Query-index graph: 6617 triples
- Repeated samples per query and layer: 20
- Query-index contract SHA-256: `bfbfcdb4aa60b3819353d538a0a0076e50a2d14e110b6f6b4db50bb9e2f85b37`

| Query | Rows | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 13 | 117.74 | 4.477 | 26.299x |
| outcomes-by-player | 58 | 10.476 | 6.55 | 1.599x |
| pitches-by-pitcher-and-venue | 6 | 9.158 | 5.514 | 1.661x |
| pitch-summary-by-pitcher | 6 | 28.622 | 8.835 | 3.24x |
| batted-balls-by-batter-and-venue | 22 | 11.937 | 5.087 | 2.347x |
| events-by-player | 75 | 20.931 | 7.102 | 2.947x |
| runs-by-season-and-venue | 1 | 30.473 | 2.811 | 10.841x |
| games-by-team-and-season | 2 | 3.388 | 2.624 | 1.291x |
| umpire-assignments | 4 | 3.047 | 2.893 | 1.053x |
| available-players | 22 | 4.223 | 3.972 | 1.063x |

A ratio above 1 means the indexed median was faster. These numbers are useful for method validation only; migration decisions require additional deliberately supplied game fixtures and query-plan review.
