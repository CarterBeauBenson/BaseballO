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
for the original evidence and its incomplete populations. The September 30
repair implements the already accepted compact named groundout pattern with
matched assist, first-base putout and batter identity. The unchanged 822693
fixture selects 59 acts across all 107 contact plays; 13 plays have complete
act evidence. Extra credits, a different out base and an unmatched runner
exclude the compact pattern. Unreported terminal touches remain unresolved.

NiFi's source-owned `Complete Approved D1 Defensive Acts` worker uses only the
four existing defensive maps over retained responses. Its first game, 822693,
completed on September 30 at 10:25 Eastern: 208 missing triples were added,
preserving all 31,703 prior triples. No source was reacquired. The existing
selected-act and authoritative SHACL checks ran before additive promotion;
unrelated admission expectations remained unchanged. Later inputs use the same
bounded, memory-aware worker, with failures retained for its limited retry.

The [September 30 metric decision](../../../archive/design-records/defensive-act-count-2026-09-30/README.md)
replaces strict sequence depth with distinct supported act count, displayed
as **Defensive Acts**. Overlapping acts count separately. Complete act evidence
is still required; the metric change does not assert temporal precedence or
complete the unresolved contact plays.
