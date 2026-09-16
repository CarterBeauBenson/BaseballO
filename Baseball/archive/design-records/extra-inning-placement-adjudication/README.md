# Extra-inning placement adjudication

On 2026-09-16 Carter Beau Benson resolved the zero-movement placed-runner
case: “It is a different act. It is a judicative act that puts the runner on
second in extra innings. And the other one you can figure out yourself”.

This records that named decision before implementation. It supersedes C3's
minimum-one-RunnerResolutionEpisode limitation for an independently evidenced
extra-inning placement. It does not authorize a new ontology term or predicate.

## Implementation of the decision

Reuse BaseballAdjudicationAct and BaseballDecisionICE. The distinct placement
judgment is an initial occurrent part of the existing personal BFO Process;
the output decision is about that personal process, its runner and the existing
second-base artifact. The judgment is prescribed by the extra-inning placement
BaseballRule. This uses the existing adjudication/output/aboutness pattern;
it makes no new physical-location, entitlement-relation or movement assertion.
No individual umpire or event-specific Role is invented when the action record
does not identify one. The rule establishes the adjudicative responsibility.

Use the accepted C3 game/inning/half/Person placement anchor for the judgment,
decision and source-record identities. Preserve all existing lifetime keys
and movement-episode identities. Keep source observation times as bounds.
The initial implementation binds the rule to the verified 2026 edition.

A placed runner who never moves still has a personal history with this
adjudication as a part. He has zero movement episodes and receives no advance,
Safe judgment, run, batting credit or independent-running credit for placement.
Source-owned SHACL requires the exact placement evidence and rejects arbitrary
empty histories, different runners/bases, fabricated running acts and missing
decisions. Other C3 source, identity and temporal checks remain in force.

## Third-out tracker repair

The other case is ordinary engineering under the accepted stranded-runner
policy: after a reconciled third out, last observed base values are not a live
occupancy snapshot. End the remaining personal histories at that supported
boundary without inventing a movement, destination or Out for a stranded runner.
Keep occupancy conflict rejection before the third out and reject subsequent
state-changing events. This is not a new semantic approval attributed to the user.

## Competency questions

1. What begins a placed runner's history? The distinct placement adjudication.
2. Can that history have no movement episode? Yes, with the positive placement
   judgment/output pattern and fully reconciled ending boundary.
3. Does placement earn positive metric credit? No; existing movement-based
   analytical queries continue to select actual supported episodes only.
4. Does a missing runner movement on the third-out play imply an advance? No.
   The terminal history can be complete without claiming an unreported advance.

The source and graph checks are focused developer evidence; corpus promotion,
serving refresh and repository validation remain asynchronous NiFi stages.
