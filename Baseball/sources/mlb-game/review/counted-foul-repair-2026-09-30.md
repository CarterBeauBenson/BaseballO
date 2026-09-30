# Targeted counted-foul completion

The retained pitch/count report for game 822678 identifies four missing
second-foul Strike Processes: `a8a521e8-5c98-3216-8178-a5db33e788ef` (PA 24),
`b07a974b-b52c-3b29-a222-dfdd53368c06` (PA 60),
`cf8e99a6-2b56-3f58-82f3-9fcc8450b2a0` (PA 63), and
`8d63d019-5ea1-3e6e-8421-681bc4441a46` (PA 70).
Their existing pitch, contact and foul patterns are present. The count profile
withholds the game because the additional strike pattern is absent.

The source-owned `Complete Recorded Counted Foul Strikes` NiFi processor reads
that existing terminal evidence and records exact game/pitch identities in its
runtime repair inventory. Game 822678 must succeed before the worker advances
to other recorded instances of the same missing-class failure. It inspects at
most 25 uncached games per tick, repairs one game at a time, and allows two
attempts per implementation. Unsupported selectors remain failed and visible.

This implements the already accepted
[M1/M3/M4 mappings](../../../archive/design-records/mlb-game-counted-foul-completion/README.md)
and the user's [targeted acquisition permission](../../../archive/design-records/metric-repair-scope-2026-09-30/answers.md).
It adds no ontology terms, mapping rules, semantic pins or source family.
Retained responses take priority. If unavailable, only a game named in the
repair manifest is fetched from its existing MLB endpoint, with a distinct hash.

The unchanged context selector must select every requested pitch, and its
identity, count, outcome and clock evidence must agree with the retained
census. RML runs only the five existing counted-foul strike maps for those
events. The existing additive transaction checks the affected PAs with the
count profile, scopes authoritative SHACL to the affected facts, preserves
unrelated admissions and triples, and updates that game's derived query index.
The normal admission owner then refreshes its evidence for SQL. Newly fetched
raw bytes are retired only after promotion and census retention; failed inputs
remain available for the bounded retry.

Focused developer verification uses an existing M3 fixture and the production
RMLMapper: one selected foul produces exactly 14 triples, no neighboring event
is mapped, and changed source evidence is rejected. This does not establish
that every game or season reference is complete; live results belong to NiFi.
