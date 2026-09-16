# D1: project the accepted defensive acts into the MLB game graph

Accepted by Carter Beau Benson on 2026-09-16: **?Approve D1 and M3/M4.?**
See [the decision record](user-decision.md). Q6 already accepts the four existing act kinds, actual agents,
distinct performances and supported order. D1 supplies the concrete identity
and source projection that Q6 did not enumerate. It changes no metric meaning,
ontology term, object property or pipeline topology.

## Accepted scope

The [mapping contract](mapping-contract.md) and both Mermaid shapes are
accepted, including stable performance identity and persistent Fielder Roles.
The decision authorizes the owning context, RML, IRI policy, source SHACL and
scoped proof-pin updates. It does not globally ratify the semantic freeze.

The first bounded cases are a named single-fielder fly/line/pop catch, an
explicitly described ground-ball fielding and throw, an explicitly described
relay, and a described tag reconciled with the runner outcome. Ambiguity remains
an explicit gap. A putout or assist credit alone never supplies a performance.
Unsupported extra acts, tags, chronology and a complete play are not inferred.

For example, game 822693 PA 2 describes Nasim Nunez throwing to Abimelec Ortiz
for a groundout. It supports the named fielding/throw/receipt pattern after
structured reconciliation. The out label alone does not establish a separate
tag's exact timing relative to the catch: base contact and receipt can overlap.
D1 does not turn that uncertainty into a four-node `precedes` chain.

## Competency questions and required checks

1. Which particular defensive acts belong to this batted-ball play, and who
   acts? Require source-supported act identity, actual agency and the same
   person's persistent Fielder Role, all within the owning game graph.
2. Is a Catch Attempt also typed Fielding Attempt? Keep one individual. A later
   throw by the same person is a different individual.
3. What order is actually supported? Assert BFO `precedes` only for supported
   non-overlapping order. Narrative mention order is not sufficient on its own.
4. Is the sequence complete? Partial positive evidence can be represented,
   but source/graph admission must independently enumerate all eligible plays
   and certify their required acts, agents and, for depth, order. Silence is
   not zero. Unknown plays cannot disappear from a player average.
5. Do participants without batting appearances remain eligible? Yes: reuse
   the independent, already implemented full roster proof and the accepted
   defensive observation minimum. No new role or batting threshold is added.

The serving consumer and tests use existing vocabulary without depending on
the accepted IRI template. They cannot populate the live
defensive cards before the source projection and population proof are ready.

Read the [inventory and source evidence](source-evidence.md),
[world-side shape](source-independent-mermaid.md) and
[MLB projection](source-specific-mermaid.md).
