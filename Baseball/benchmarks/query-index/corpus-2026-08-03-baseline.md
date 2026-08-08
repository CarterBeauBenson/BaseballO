# Query-index corpus benchmark: 2026-08-03

Generated: 2026-08-08T03:17:48.4289265Z

This benchmark covers the eight completed 2026-08-03 games and excludes the older development fixture. Initial executions validate exact authoritative/indexed row equivalence and prime each path. Repeated timings alternate execution order.

- Authoritative graphs: 8, 231806 triples
- Query-index graphs: 8, 52944 triples
- Repeated samples per query and layer: 20
- Corpus SHA-256: `f8fdda9a115e4bdd971ce2ab203a444ad674835531d7a84d89401f0b13346ab9`
- Query-index contract SHA-256: `a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629`

| Query | Rows | Initial authoritative (ms) | Initial indexed (ms) | Authoritative median (ms) | Indexed median (ms) | Median ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hits-by-player-and-venue | 93 | 4541.35 | 45.228 | 4397.185 | 15.712 | 279.862x |
| outcomes-by-player | 422 | 69.648 | 33.982 | 73.246 | 31.339 | 2.337x |
| outcomes-by-season | 15 | 17303.46 | 10.208 | 18108.088 | 11.127 | 1627.401x |
| plate-appearances-by-player-and-season | 158 | 1292.35 | 63.407 | 1211.284 | 21.504 | 56.328x |
| three-true-outcomes-by-player | 121 | 48.524 | 18.505 | 32.223 | 18.993 | 1.697x |
| extra-base-hits-by-player | 39 | 17.315 | 7.264 | 14.139 | 6.136 | 2.304x |
| home-runs-by-player-and-venue | 26 | 12.329 | 6.086 | 11.389 | 6.239 | 1.825x |
| multi-hit-games | 39 | 120.397 | 7.937 | 126.151 | 6.742 | 18.711x |
| total-bases-by-player-and-season | 93 | 4667.95 | 21.634 | 4203.409 | 11.74 | 358.042x |
| hitless-games-by-player | 65 | 445.822 | 56.985 | 405.859 | 49.712 | 8.164x |
| pitches-by-pitcher-and-venue | 62 | 71.711 | 35.981 | 70.496 | 31.706 | 2.223x |
| pitch-summary-by-pitcher | 62 | 376.469 | 68.793 | 291.638 | 65.692 | 4.439x |
| batted-balls-by-batter-and-venue | 157 | 132.076 | 24.183 | 91.484 | 24.646 | 3.712x |
| events-by-player | 549 | 161.622 | 47.096 | 176.492 | 38.428 | 4.593x |
| runs-by-season-and-venue | 8 | 1104.355 | 7.023 | 1128.594 | 6.545 | 172.436x |
| games-by-team-and-season | 16 | 26.921 | 6.849 | 28.006 | 5.518 | 5.075x |
| umpire-assignments | 32 | 8.435 | 6.904 | 5.75 | 5.88 | 0.978x |
| available-players | 158 | 21.035 | 15.347 | 14.329 | 13.521 | 1.06x |

A ratio above 1 means the indexed median was faster. These loopback measurements include request handling and JSON serialization. Separate direct TDB2 execution captures are stored under `tdb2-execution/`.
