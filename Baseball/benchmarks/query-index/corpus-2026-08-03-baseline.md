# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-04T18:03:45.3396865Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 228576 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `53c64863b8f154fd867958b43bca0e2535798111aadd7fcc7f95fa6f44db4daa`
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 255.879 | 58.117 | 227.04 | 23.311 | 9.74x |
| outcomes-by-player | 422 | 151.634 | 52.019 | 91.434 | 38.338 | 2.385x |
| outcomes-by-season | 15 | 586.084 | 10.877 | 586.001 | 10.342 | 56.662x |
| plate-appearances-by-player-and-season | 158 | 109.469 | 23.929 | 61.104 | 25.322 | 2.413x |
| three-true-outcomes-by-player | 121 | 32.324 | 16.961 | 33.803 | 19.339 | 1.748x |
| extra-base-hits-by-player | 39 | 10.844 | 7.688 | 11.331 | 6.624 | 1.711x |
| home-runs-by-player-and-venue | 26 | 9.924 | 7.431 | 9.878 | 6.486 | 1.523x |
| multi-hit-games | 39 | 167.927 | 9.266 | 156.772 | 8.281 | 18.932x |
| total-bases-by-player-and-season | 93 | 228.613 | 19.387 | 231.786 | 15.823 | 14.649x |
| hitless-games-by-player | 65 | 509.701 | 71.979 | 496.394 | 58.356 | 8.506x |
| pitches-by-pitcher-and-venue | 62 | 80.938 | 32.468 | 71.838 | 33.619 | 2.137x |
| pitch-summary-by-pitcher | 62 | 339.168 | 71.452 | 310.183 | 64.146 | 4.836x |
| batted-balls-by-batter-and-venue | 157 | 93.871 | 26.338 | 94.481 | 27.676 | 3.414x |
| events-by-player | 549 | 231.492 | 73.645 | 226.267 | 61.36 | 3.688x |
| runs-by-season-and-venue | 8 | 39.967 | 5.364 | 39.678 | 5.562 | 7.134x |
| games-by-team-and-season | 16 | 6.893 | 4.862 | 5.916 | 5.144 | 1.15x |
| umpire-assignments | 32 | 8.138 | 7.824 | 6.42 | 6.377 | 1.007x |
| available-players | 158 | 22.28 | 14.986 | 13.953 | 13.653 | 1.022x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
