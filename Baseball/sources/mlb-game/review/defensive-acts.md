# D1 implementation

The [accepted contract](../../../archive/design-records/mlb-game-defensive-acts/mapping-contract.md)
was published in `e4166c1` before executable changes. The owning context
selects separately evidenced performances and retains source spans and credit
pointers. RML maps actual agents, persistent Fielder Roles, play parthood and
record aboutness. A Catch Attempt and its Fielding Attempt superclass share
one identity. Neither credit array order nor performance indices assert time
order. No new class or object property is declared.

Source SHACL binds the exact selected identity, type, agent, role, bearer,
contact-play and precedence census, including rejection of missing and extra
facts. It validates positive performances independently of full population
coverage. The complete raw contact inventory includes unsupported plays.
Only a complete population can receive an admitted player-ranking proof.

The existing NiFi SHACL stage runs this profile before promotion and retains
its sidecars. The promotion marker binds their hashes to the source and RDF.
The materializer checks those hashes and the implementation fingerprint, then
passes proof metadata to the existing SQL consumer. Metric values come from
canonical SPARQL, never source-side counters. Older promotions without the
proof remain ineligible for these means. Partial population coverage does not
stop promotion of correctly modeled positive facts. A selected-act conformance
failure does stop promotion.

Before replacing a mapped game, context compares its last retained defensive
performance census. Stable aligned identities persist; changes to established
performance segmentation or agent/type alignment quarantine the correction.
That conservative branch requires resolution before it can replace the prior
graph. It does not renumber old acts or invent a correction identity policy.

See the [bounded source/RDF/query/SQL proof](../../../benchmarks/metrics/d1-defensive-mapping-2026-09-16/README.md)
for evidence and the still-unresolved complete populations. Explicit ground
field/throw/receipt and tag grammar have synthetic positive/negative tests;
they are not claimed as additional real-feed observations in the proof game.
