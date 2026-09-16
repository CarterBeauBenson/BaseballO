# Empty Game Damage: keep independent running with its player

The SQL consumer now admits completely evidenced successful steals as having
no independent damage. It still counts their positive contribution for the
runner when determining whether that runner's game was empty, even if the
steal occurred during another player's PA. Other players' damage remains
calculable; the batter receives no credit for the steal.

A movement simultaneously attributed to contact/award and independent running
now withholds the contribution instead of silently choosing batting credit.
Unknown running ownership, independent outs and interrupted turns continue to
block the complete Empty Game Damage population. This implements accepted
metric policy without changing source RML, identity, ontology or object properties.

## Focused verification

Eighteen tests passed in `test_empty_game_damage`, `test_contribution_players`
and `test_contribution_sql`. Coverage includes a runner with otherwise empty
batting PAs stealing during a teammate's PA, exact SQL retention, agreement
with the Empty Games count, missing schedule proof, unknown ownership,
conflicting contact attribution, a runner out and an interrupted turn.

The [real-game regression](result.json) reuses the validated unchanged RDF
for game 823098 and reruns the owning B1, resolution and boundary SHACL proofs,
canonical Jena extraction and exact SQL retention. All **70/70** PA
contributions remain complete. The source and RDF hashes are recorded.

Two supported steals are retained separately: Dominic Canzone (686527) at PA 7 and
Julio Rodriguez (677594) at PA 45. **The game's Empty Game Damage player
population remains withheld**, because PA 68 has a separate movement whose
positive contribution ownership is unresolved. This real-game check validates
the retained gate, not a populated live leaderboard or a full selected day.
The exact cross-player classification improvement is proven by the SQL fixture.

The existing NiFi recovery workflow owns publication of refreshed serving
results. No source corpus was manually promoted and no schedule was changed.
