# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T17:01:36.2637932Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228576 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `0c78cc555471897c1df3a1d5cea3fa08f5316c6dc8a751583c9ab91701104529`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 252.674 | 57.876 | 251.487 | 26.008 | 9.67x |
| outcomes-by-player | 422 | 155.193 | 51.058 | 112.038 | 53.929 | 2.078x |
| outcomes-by-season | 15 | 643.904 | 13.114 | 619.358 | 12.386 | 50.005x |
| plate-appearances-by-player-and-season | 158 | 75.201 | 28.43 | 66.208 | 27.702 | 2.39x |
| three-true-outcomes-by-player | 121 | 46.415 | 53.5 | 36.237 | 21.728 | 1.668x |
| extra-base-hits-by-player | 39 | 19.214 | 7.231 | 13.049 | 7.839 | 1.665x |
| home-runs-by-player-and-venue | 26 | 11.088 | 10.293 | 10.623 | 7.657 | 1.387x |
| multi-hit-games | 39 | 175.524 | 8.626 | 166.66 | 9.346 | 17.832x |
| total-bases-by-player-and-season | 93 | 225.35 | 17.821 | 239.358 | 16.324 | 14.663x |
| pitches-by-pitcher-and-venue | 62 | 107.404 | 43.79 | 98.914 | 45.175 | 2.19x |
| pitch-summary-by-pitcher | 62 | 406.95 | 80.103 | 320.645 | 67.958 | 4.718x |
| batted-balls-by-batter-and-venue | 157 | 101.568 | 27.45 | 97.258 | 29.261 | 3.324x |
| events-by-player | 549 | 251.248 | 46.061 | 286.766 | 48.759 | 5.881x |
| runs-by-season-and-venue | 8 | 55.838 | 9.481 | 55.569 | 7.467 | 7.442x |
| games-by-team-and-season | 16 | 8.46 | 7.66 | 9.76 | 8.184 | 1.193x |
| umpire-assignments | 32 | 9.562 | 8.791 | 9.069 | 9.128 | 0.994x |
| available-players | 158 | 33.228 | 24.393 | 19.15 | 18.85 | 1.016x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
