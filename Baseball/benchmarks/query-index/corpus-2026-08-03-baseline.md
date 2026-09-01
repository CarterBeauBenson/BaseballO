# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-11T22:17:48.9698921Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 246191 triples
- Query-index graphs: 8, 52992 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `00750b1a95f155b47ffaaff6b15e3cf69cd03c4ee97701aff50c38d335930c34`
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-season | 1 | 4526.398 | 6.368 | 4559.811 | 5.704 | 799.406x |
| hits-by-player-and-venue | 93 | 4836.245 | 15.023 | 4809.72 | 20.3 | 236.932x |
| outcomes-by-player | 422 | 95.116 | 33.188 | 80.695 | 30.471 | 2.648x |
| outcomes-by-season | 15 | 19181.296 | 10.924 | 19030.143 | 9.891 | 1923.986x |
| plate-appearances-by-player-and-season | 158 | 1250.051 | 23.373 | 1254.711 | 22.539 | 55.668x |
| three-true-outcomes-by-player | 121 | 45.866 | 27.911 | 29.093 | 16.317 | 1.783x |
| extra-base-hits-by-player | 39 | 9.655 | 4.58 | 9.672 | 5.388 | 1.795x |
| home-runs-by-player-and-venue | 26 | 9.751 | 5.71 | 7.895 | 5.231 | 1.509x |
| multi-hit-games | 39 | 175.888 | 11.593 | 113.271 | 6.483 | 17.472x |
| total-bases-by-player-and-season | 93 | 4690.151 | 10.647 | 4715.823 | 10.906 | 432.406x |
| hitless-games-by-player | 65 | 375.239 | 57.255 | 345.978 | 42.62 | 8.118x |
| pitches-by-pitcher-and-venue | 62 | 68.458 | 30.899 | 64.35 | 29.027 | 2.217x |
| pitch-summary-by-pitcher | 62 | 329.535 | 56.006 | 260.015 | 59.519 | 4.369x |
| batted-balls-by-batter-and-venue | 157 | 81.887 | 32.159 | 80.181 | 23.675 | 3.387x |
| events-by-player | 549 | 169.351 | 34.013 | 167.528 | 37.938 | 4.416x |
| runs-by-season-and-venue | 8 | 1174.141 | 7.576 | 1173.406 | 5.699 | 205.897x |
| games-by-team-and-season | 16 | 74.487 | 4.167 | 70.831 | 4.048 | 17.498x |
| umpire-assignments | 32 | 5.911 | 4.604 | 5.235 | 4.498 | 1.164x |
| available-players | 158 | 15.455 | 12.682 | 11.502 | 11.26 | 1.021x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
