# Automatic count awards: bounded implementation proof

The accepted question 5 scope was published in `6344630` before executable
changes. The [decision](../../../archive/design-records/automatic-count-awards/review.json)
reuses existing Ball/Strike processes, judgments, decisions and rules. It adds
no ontology term or object property.

The real one-PA RMLMapper fixture is PA 45 of game 823518, July 22, 2026.
An automatic strike has its own process, judgment, decision and source record.
It has no Pitch Act, pitched motion, guessed named umpire or exact judgment
interval. Explicitly supported preceding/following pitches retain their order.
The canonical SPARQL evidence query and SQL materializer preserve this award.
Adversarial missing decisions, wrong kinds, fictitious pitches, guessed agents,
cycles and wrong PA containment fail the owning source SHACL contract.

The whole immutable game also passed actual RMLMapper 8.1.0 and the complete
Jena source SHACL profile: 34,083 triples, 82 PAs, 323 actual Pitch Acts and one
automatic strike. The source-to-RDF membership verifier passed. The retained
[result](result.json) pins the inputs and the artifacts used for that proof.
These are isolated developer artifacts; no graph was promoted by this check.

Focused checks passed: five automatic-award source/RML/query/SQL tests, three
recovery calculation tests, ten source-reconciliation tests, nine reconciled
runner-history tests, thirteen existing mapping-completion tests, twenty-three
canonical metric tests and thirty-nine metric UI/API tests (102 total).

The recovery reducer now accepts admitted automatic awards in an ordered count
history. They can establish two strikes and terminate a PA, while adding zero
pitches to the recovery numerator. Full ordered count histories, review and
termination coverage, and complete eligible player populations are still
required. This proof does not release a Recovery Quality leaderboard.

## Source reconciliation repair

Investigating the July 18 game 824088 fixture exposed a dictionary lookup that
inserted an absent bottom half while comparing inning membership. A later
check then treated the unplayed half as played with missing runs. Nonmutating
lookups preserve the existing absence policy; no null score becomes zero.
The immutable game now reconciles, and the regression checks the absent half.

Game 824087's candidate award remains withheld because a later pitch in that
PA has unresolved review evidence. Intentional-walk `VB` counter rows remain
withheld: four provider count updates do not establish four umpire acts.

The existing NiFi lane invokes this context, RML, mechanical membership check
and source SHACL before promotion. Its active asynchronous recovery request
continues to own corpus refresh and serving materialization. No schedule or
pipeline topology changed.
