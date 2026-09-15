# Substituted batting participation: real RML proof

Question 4 was accepted in `b4d4f88`; its scoped
[implementation record](../../../archive/design-records/substituted-batter-participation/review.json)
was pushed in `db602fe` before code changed.

Immutable game 824169, July 18, 2026, PA 31 contains an actual swinging strike
by Christian Walker, an injury delay, a PH substitution, and the remainder of
the PA batted by LaMonte Wade Jr. The previous final-matchup projection falsely
attributed Walker's swing to Wade. It now assigns the first pitch/swing to
Walker's Batter Act and the later pitches/swings to Wade's separate Batter Act,
both contained in the same PA and each realizing its person's persistent role.

The real one-PA RMLMapper proof passes the owning PA, Batter Act and batting
action SHACL shapes. Its adversarial cases reject a swing attached to the wrong
Batter Act and an act merging two people. The canonical SPARQL query and SQL
round trip retain both actual participants while keeping official PA credit
unverified. Pre-turn lineup changes do not manufacture an earlier Batter Act;
PR changes do not change the batter. Inconsistent PH identities, flags, indexed
membership and overlapping/absent substitution bounds fail preparation.

The whole-game proof passes RMLMapper 8.1.0, exact source-to-RDF membership and
the full Jena authoritative source SHACL profile: **36,833 triples, 88 PAs,
89 Batter Acts, 343 Pitch Acts, 159 swing/bunt acts, zero SHACL violations**.
It also retains 11 previously supported personal runner histories with 20
episode memberships. These are bounded source results, not a complete metric
population. The [result](result.json) pins the exact proof artifacts.

Focused checks: six new attribution/RML/query/SQL tests, ten existing official
batting-admission tests and six existing context edge-case tests passed.
The initial new action-agreement constraint also matched the bat artifact as
though it were a person; explicit existing Person/Batter Role type restrictions
corrected that query before the passing proofs. No conformance failure was
ignored or promoted.

NiFi's existing RML component now retains the selected participation inventory
and verifies its exact RDF census. Its expected Batter Act count is separate
from PA count. The existing official-credit gate still rejects unresolved
within-turn statistical assignment. No raw bytes, ontology, OP, acquisition
schedule, processor group or global ratification changed. This isolated check
did not promote a graph or populate a player leaderboard.

A final negative-case guard rejects a replacement with no supported batting
participation and checks automatic-award bounds across substitutions as well.
The six-test real RML/query/SQL suite passed again. Its full-game prepared
context has exactly the same SHA-256 as the whole-game proof input above;
`postProofGuardVerification` records the final builder hash and this byte
comparison without rewriting the original proof's provenance.
