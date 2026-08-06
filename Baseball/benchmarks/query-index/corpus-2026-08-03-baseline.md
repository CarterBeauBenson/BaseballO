# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-06T02:51:55.4275780Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 231670 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `4547508cde87ff1d529146941cd126d6f3a33679b16fbba430c336e456308469`
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 374.882 | 31.701 | 360.049 | 32.658 | 11.025x |
| outcomes-by-player | 422 | 160.289 | 64.302 | 156.95 | 71.114 | 2.207x |
| outcomes-by-season | 15 | 1145.438 | 28.792 | 1194.639 | 20.083 | 59.485x |
| plate-appearances-by-player-and-season | 158 | 176.734 | 53.126 | 118.82 | 47.054 | 2.525x |
| three-true-outcomes-by-player | 121 | 86.362 | 33.174 | 67.566 | 34.534 | 1.957x |
| extra-base-hits-by-player | 39 | 21.256 | 13.138 | 21.656 | 11.789 | 1.837x |
| home-runs-by-player-and-venue | 26 | 16.55 | 11.174 | 17.525 | 12.019 | 1.458x |
| multi-hit-games | 39 | 259.754 | 13.676 | 285.964 | 15.118 | 18.915x |
| total-bases-by-player-and-season | 93 | 334.074 | 26.301 | 338.977 | 21.646 | 15.66x |
| hitless-games-by-player | 65 | 873.273 | 102.13 | 811.059 | 100.051 | 8.106x |
| pitches-by-pitcher-and-venue | 62 | 177.423 | 63.108 | 179.793 | 64.168 | 2.802x |
| pitch-summary-by-pitcher | 62 | 606.891 | 167.952 | 623.959 | 147.563 | 4.228x |
| batted-balls-by-batter-and-venue | 157 | 267.25 | 51.699 | 223.111 | 52.323 | 4.264x |
| events-by-player | 549 | 494.354 | 106.625 | 417.611 | 87.56 | 4.769x |
| runs-by-season-and-venue | 8 | 81.571 | 10.627 | 81.205 | 10.365 | 7.835x |
| games-by-team-and-season | 16 | 11.174 | 9.503 | 10.92 | 9.645 | 1.132x |
| umpire-assignments | 32 | 17.832 | 16.014 | 11.323 | 11.636 | 0.973x |
| available-players | 158 | 41.825 | 30.587 | 24.98 | 25.372 | 0.985x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
