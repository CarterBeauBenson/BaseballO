# Authoritative canned-query corpus audit

Generated: 2026-08-04T14:41:37.1270662Z

This baseline covers the eight completed 2026-08-03 games only. The older checked-in development fixture is deliberately excluded. Every query is executed against an explicit `VALUES ?graph` allowlist, so joins cannot cross games or use query-index graphs.

- Authoritative graphs: 8
- Authoritative triples: 228571
- Canned queries: 48
- Non-empty queries: 48
- Zero-row queries: 0
- Queries with duplicate result rows: 0
- Corpus SHA-256: `030e601dceb5d4d525d7dee6f756d284daeff5615621e1703c46fd3ec66dcb46`

| Query | Rows | Distinct | Duplicates | Row-set SHA-256 | Time (ms) |
| --- | ---: | ---: | ---: | --- | ---: |
| `sparql/baserunning/events-by-player.rq` | 549 | 549 | 0 | `950187d12e288a885f1f8dd8cb2f54297660c42e2d001d31e9e45c17416930b1` | 151.184 |
| `sparql/baserunning/outs-by-player.rq` | 152 | 152 | 0 | `325809fda17d982f855bc3b6c5ecb2c2416fa8efc7b06b0c43d39217405867d8` | 14.081 |
| `sparql/baserunning/resolutions-by-season.rq` | 3 | 3 | 0 | `f182e637df62e798d8a808f2db11ef5ef856988f1971c32816f6ebb25a932eb8` | 93.27 |
| `sparql/baserunning/runs-by-player-and-season.rq` | 70 | 70 | 0 | `6ccbc92acefd9c50e20c6a5bacda1388d2eafabb9d024bd247940668f38de7c4` | 37.946 |
| `sparql/baserunning/runs-by-season-and-venue.rq` | 8 | 8 | 0 | `5de3bb1d8e25bd15abe9185e90a56cda87b6eb0a9d341bfe688a9257edf5b49b` | 33.18 |
| `sparql/baserunning/stolen-bases-by-player.rq` | 11 | 11 | 0 | `ba84cdfacc33d56ecd9c63f2c7bdfcd854bc70b31366fe470e9f02eda44e2929` | 3.928 |
| `sparql/batting/extra-base-hits-by-player.rq` | 39 | 39 | 0 | `e3acccdacb20a0e59607b30246d98372c6a4fe4af101d55e587538370de2ce6a` | 9.239 |
| `sparql/batting/hitless-games-by-player.rq` | 65 | 65 | 0 | `98e6f167b3198d432c3a90d45e0a6acafd39d17b8d30759c61dc43f4e3f532f2` | 290.724 |
| `sparql/batting/home-runs-by-player-and-venue.rq` | 26 | 26 | 0 | `e29110dbbe988a5668ab2668a186b6b2967e050c5164efe5fba2d408f59b156c` | 7.378 |
| `sparql/batting/multi-hit-games.rq` | 39 | 39 | 0 | `126c6ead6a5792c8e8a0ae6ebbfe43c3fdb84c3b7f82d8dfe949e3320bf5efbd` | 99.946 |
| `sparql/batting/outcomes-by-player.rq` | 422 | 422 | 0 | `a4dc59b870ce26882afac2305320c0a333ee30a0ffd6eaba2a728607392a75b0` | 59.346 |
| `sparql/batting/outcomes-by-season.rq` | 15 | 15 | 0 | `b13eed444493bc3439911d7912fd3a381bfb0f919e004cfa975c6d53bba3fd17` | 461.387 |
| `sparql/batting/plate-appearances-by-player-and-season.rq` | 158 | 158 | 0 | `91c65127c83228346803e0a1144b43baeb2a388806c93073758f48c82a8234b8` | 46.982 |
| `sparql/batting/three-true-outcomes-by-player.rq` | 121 | 121 | 0 | `8c6facd5a06c6a22633d26e7e617ec8c63674f6656c9d4c9511eb27b0e9dba5c` | 26.984 |
| `sparql/batting/total-bases-by-player-and-season.rq` | 93 | 93 | 0 | `bc640ccf7452c3b5b7c5f62e2b66805513aea76d8a8f6b63c8bda1a013184f3e` | 121.212 |
| `sparql/empty-games-prototype.rq` | 21 | 21 | 0 | `36075811a466e16397d58236be9628437e4e01ed8fe46d0e4dfee93be19ad0ba` | 337.397 |
| `sparql/games/games-by-season-and-venue.rq` | 8 | 8 | 0 | `e95a28d0377926380837f66c2b0eba2c241d936a9062468dd83f54d5dc8391f9` | 4.062 |
| `sparql/games/games-by-team-and-season.rq` | 16 | 16 | 0 | `1a5f30ae5342cf5e46abdab2d6c54bc952b8f6d538ea19846e619af41cebc791` | 5.579 |
| `sparql/games/game-timeline.rq` | 8 | 8 | 0 | `2d30a5417c0142a15a93bd21a3b094559fc2368cae9711410be880e9e263fdcd` | 3.611 |
| `sparql/games/home-away-games-by-team.rq` | 16 | 16 | 0 | `4cbd8c2df8013a65e27c4c1617d1c972df933ee843a90b622d733521ec57f4aa` | 4.526 |
| `sparql/games/matchups-by-season.rq` | 8 | 8 | 0 | `7c232842c80857731e51aadb606ddfedf49c0308c311c7258470f5f3d24dc58f` | 5.746 |
| `sparql/games/official-scorer-assignments.rq` | 8 | 8 | 0 | `76a24db469c040d899bc516f6fd02e3d44e13dbdd63cbb07f73beea95f3845a2` | 4.119 |
| `sparql/games/umpire-assignments.rq` | 32 | 32 | 0 | `edcc7bcbfbd9eec6c22c2d1a3ffda24bccf8ec7f280efb36af7c3cdb9b8a07b5` | 4.953 |
| `sparql/hits-by-game.rq` | 8 | 8 | 0 | `7eee5f18f970432435b958aca26bec8ff0bd53c96d45156534560a6e33e1f25e` | 99.533 |
| `sparql/hits-by-player-and-season.rq` | 93 | 93 | 0 | `ed1b42e7eb293fdc813266fd702b8b898b27d81dbc536c64beedaf31dcfedbe7` | 164.872 |
| `sparql/hits-by-player-and-venue.rq` | 93 | 93 | 0 | `c530a4fe128b022fa766f1706b1cbaae37e400431ee971f890c5aa042ea81d03` | 215.605 |
| `sparql/hits-by-season.rq` | 1 | 1 | 0 | `e03dd17d7884a2161aaca25104824e25e0f2b93a52beca121e20c4b9d0a706e8` | 151.947 |
| `sparql/hits-by-season-and-venue.rq` | 8 | 8 | 0 | `a3ec9e4a0cd910dbefd111320b6dcf26fec2f599923aa7acedaffcb7695911c4` | 117.071 |
| `sparql/hit-types-by-season.rq` | 4 | 4 | 0 | `cf0c90c185dfcd7a34081ddaa06f3d25e78706b676a6d813ba989f5d6ba39efe` | 117.908 |
| `sparql/options/available-baserunners.rq` | 159 | 159 | 0 | `642a77d80337eb59fcb33689f4a5b3356470488586e4045cf0ba72be9c5d6ccc` | 24.161 |
| `sparql/options/available-baserunning-events.rq` | 26 | 26 | 0 | `83261a4de123a5ff9962605dc3688466f7485c62e60f6bdb710f5778d08e5011` | 149.938 |
| `sparql/options/available-batting-outcomes.rq` | 15 | 15 | 0 | `83127648378d44d142ffc13e1b7e7f1acff5fd2932d2d6925afee9d56f9a2dea` | 18.906 |
| `sparql/options/available-games.rq` | 8 | 8 | 0 | `cfa2de8f8851a7f7a8a9c0c2ad1bcf9146ed66c1acb4470c51dc08d1b5eb746a` | 4.771 |
| `sparql/options/available-hit-types.rq` | 4 | 4 | 0 | `3ed3ec1a4694326c85abc61a8fee991cc2c2cf92e388cfb22155ed0e169744fa` | 8.046 |
| `sparql/options/available-official-scorers.rq` | 8 | 8 | 0 | `1dc13feeee228fa6a11d257c7d5b5af18b70955d842daa8ce32ae7614def5686` | 4.837 |
| `sparql/options/available-pitchers.rq` | 62 | 62 | 0 | `6711f8221c0895ce9937cf93443f95f03d736687df0374755450cf5153ccad03` | 33.774 |
| `sparql/options/available-players.rq` | 158 | 158 | 0 | `235fa0bb7f4935f667ca9d579f92d105d59da8f5b2483195e41e747c230241db` | 12.226 |
| `sparql/options/available-seasons.rq` | 1 | 1 | 0 | `e0ad9fd985e8fb68739a480156466aff3703a743a85f78edc6a08b3dd569e827` | 4.27 |
| `sparql/options/available-teams.rq` | 16 | 16 | 0 | `06a2920e1e7a698814bb9cfed8c98c173cf9f0a797faad0b0c7095d600da3bd4` | 4.726 |
| `sparql/options/available-umpires.rq` | 32 | 32 | 0 | `fd02b5a50ab6023c3abd5db9ae4bdacb62e0729f830d6a96bd04ef7ee221424d` | 4.777 |
| `sparql/options/available-venues.rq` | 8 | 8 | 0 | `f72a49e9496d8b2d23c147582d90e93d1b871f5c331023fba486551d599d7cd2` | 3.928 |
| `sparql/pitching/balls-and-strikes-by-pitcher.rq` | 122 | 122 | 0 | `4973fa04a7d9f4f183565efaee445bd1e7b09310c6602b853057b133c09288f7` | 297.352 |
| `sparql/pitching/batted-balls-by-batter-and-venue.rq` | 157 | 157 | 0 | `ecf7046db239a74d44dc287dd72fdcc9aac634307db03fd872b774405dcd4e9e` | 77.991 |
| `sparql/pitching/pitches-by-pitcher-and-season.rq` | 62 | 62 | 0 | `97f047d087e1acd05bb79a63cedf9916c69b62c208c987a887023e67b2acf9d2` | 96.981 |
| `sparql/pitching/pitches-by-pitcher-and-venue.rq` | 62 | 62 | 0 | `2c314d57faac8e18d74e27434a48529622d434b628dfa70597dbefb8b2f2128e` | 66.639 |
| `sparql/pitching/pitches-per-plate-appearance.rq` | 62 | 62 | 0 | `7e18fa028792f03e57670616abb0089f9d80e37ad7c3c45277c18804ff03c05e` | 51.858 |
| `sparql/pitching/pitch-summary-by-pitcher.rq` | 62 | 62 | 0 | `384c48ae11f55812c4056c3dad3ca355de460c6e66874082487103c7f3b4204a` | 240.613 |
| `sparql/pitching/swings-by-batter.rq` | 157 | 157 | 0 | `83eb106356942de6111efe5ea74ead43a1242dc4062900144b7727c69f848edf` | 16.498 |

Row-set hashes preserve term type, datatype, language, variable name, unbound values, and duplicate multiplicity while ignoring response order. Timings are diagnostic loopback observations, not benchmark claims.
