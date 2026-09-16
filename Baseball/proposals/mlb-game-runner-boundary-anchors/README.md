# C3: stable runner-history boundaries without pitch IDs

Status: **under review, not authorized for execution**. This package extends
the existing C1 instance-identity contract. It proposes no ontology classes,
object properties, data properties or new pipeline stages.

The user has already accepted separate personal histories ending on an out,
score, replacement or inning end. That decision is not being reopened. The
remaining mapping problem is concrete: MLB sometimes supplies `actionPlayId`
instead of `playId`, and supplies neither for a pinch runner or placed runner.
The current admitted serialization accepts pitch `playId` anchors only.

**Requested decision:** accept the three bounded anchor forms and correction
policy in [mapping-contract.md](mapping-contract.md), allowing the existing
C1 RML to represent those histories with the same accepted graph shape.
This is approval of particular identity and mapping scope, not permission to
invent relations or reinterpret the metrics.

## Competency questions

1. Does a non-pitch runner out end the existing personal history? Yes, when
   its complete movement/out record, runner, event association and final
   outcome reconcile. The proposed composite anchor distinguishes the action
   from an associated pitch; `actionPlayId` is not treated as a pitch ID.
2. Does a pinch runner inherit the replaced person's earlier episodes? No.
   Replacement ends one person's history and begins the other's at the
   supported base. Both keep their own existing episodes and persistent Roles.
3. Does placement on second create a fictitious walk or first-to-second
   advance? No. It supplies an entry boundary for that person's history;
   only later, independently evidenced runner episodes are members.
4. Does an administrative base field create a physical location or Safe
   judgment? No. This package adds neither. Existing PA-start and metric
   boundary proofs remain separate and may still withhold those calculations.
5. What happens on ambiguity or correction? Duplicate anchors, uncertain
   lifecycle alignment, missing times or unsupported episode membership keep
   the affected half withheld. Do not renumber existing histories silently.

## Implementation after acceptance

Record and publish the decision before executable changes. Then update the
owning context and IRI policy, existing RML inputs as required, and source
SHACL for exact Person/whole/episode/half/interval membership. First prove the
individual action-out, replacement and placement fixtures, then a whole game.
NiFi owns subsequent corpus validation, promotion and SQL refresh.

Implementation scope: `scripts/pipeline/prepare-rml-context.py`,
`sources/mlb-game/mapping/iri-policy.yaml`,
`sources/mlb-game/mapping/mlb-game.rml.ttl`, owning source SHACL and admission
components, mapping coverage/provenance, focused tests and serving consumers
of the already accepted pattern. No ontology edit or global freeze ratification.

This package does **not** resolve the missing forced-runner state at the third
out in game 823826 PA 61, ambiguous PA header times, all review mechanisms,
defensive completeness or a complete season population. Those are documented
separately rather than concealed by an expanded anchor policy.
