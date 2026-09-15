# Existing batting and team-context graph paths

The [capture](result.json) checks the unchanged, hash-pinned M1/M2 game 824315
RDF using Jena and the same canonical evidence query as SQL and the live
fallback. All extracted bindings survive SQL storage exactly.

The query finds all 52 player/team pairs in the source boxscore roster. Of
these, 32 players have no batting result. Every pair has its matching home or
away Team Role in that particular game. It also preserves the 77 adjudicated
batting results and their asserted result types, judgments, decisions and
source records. The existing three resolved review results are unchanged.

This disproves absence of the basic game/player/team path. It does not prove
complete selected-game coverage, future missing-game membership or official
PA credit. Those interpretation and admission conditions are specified by
[B1](../../../proposals/batting-leaderboard-admission/README.md), still awaiting
the ontologist's decision. No qualifier or leaderboard is released here.

Focused validation: 10 batting-context/aggregation tests, 11 serving tests,
4 shared-dashboard tests and 37 Node dashboard/API tests. This proof used
`tests/prove_pitch_review_serving.py --include-batting-context`; it additionally
compares the exact source roster pairs and the full stored evidence bindings.
The captured JSON retains counts and fingerprints rather than duplicating the
full disposable query output. Source/RDF hashes make the check reproducible.
