# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-06T01:14:15.6606798Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 231018 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `1ff333648f64a285dfb4af4138e82b9211192522116ad2433c1a035134496deb`
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 271.391 | 64.55 | 260.164 | 25.063 | 10.38x |
| outcomes-by-player | 422 | 117.243 | 51.404 | 115.364 | 53.007 | 2.176x |
| outcomes-by-season | 15 | 715.111 | 10.669 | 645.045 | 11.492 | 56.13x |
| plate-appearances-by-player-and-season | 158 | 70.489 | 28.209 | 69.189 | 26.262 | 2.635x |
| three-true-outcomes-by-player | 121 | 43.989 | 19.881 | 37.565 | 21.375 | 1.757x |
| extra-base-hits-by-player | 39 | 12.298 | 7.373 | 13.074 | 7.809 | 1.674x |
| home-runs-by-player-and-venue | 26 | 11.833 | 14.117 | 10.199 | 6.798 | 1.5x |
| multi-hit-games | 39 | 207.462 | 10.099 | 166.62 | 8.979 | 18.557x |
| total-bases-by-player-and-season | 93 | 240.628 | 16.076 | 248.498 | 16.306 | 15.24x |
| hitless-games-by-player | 65 | 575.92 | 76.895 | 435.95 | 52.886 | 8.243x |
| pitches-by-pitcher-and-venue | 62 | 77.458 | 39.87 | 76.87 | 34.632 | 2.22x |
| pitch-summary-by-pitcher | 62 | 352.623 | 68.672 | 333.974 | 69.903 | 4.778x |
| batted-balls-by-batter-and-venue | 157 | 142.96 | 27.189 | 98.756 | 28.935 | 3.413x |
| events-by-player | 549 | 236.849 | 43.701 | 257.892 | 47.966 | 5.377x |
| runs-by-season-and-venue | 8 | 57.77 | 8.619 | 58.532 | 8.105 | 7.222x |
| games-by-team-and-season | 16 | 8.468 | 7.832 | 8.926 | 8.125 | 1.099x |
| umpire-assignments | 32 | 8.648 | 10.461 | 8.162 | 8.333 | 0.979x |
| available-players | 158 | 20.523 | 42.831 | 19.258 | 19.12 | 1.007x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
