# M1/M2 implementation

The [accepted decision](../../../archive/design-records/mlb-game-metric-mapping-completion/review.json)
was published in `027e47c` before these executable changes. No ontology class
or property was added. The MLB module's exact runtime pins were updated under
that named acceptance; the global baseline remains unratified.

## Counted fouls

The context builder reconciles the complete unfiltered event prefix against
the existing E1 source census. A supported ordinary 1-to-2 strike increment
joins the existing CountedFoulSource. The first-strike mapping remains, and a
2-to-2 ordinary foul creates no additional strike. Counters, timestamps,
substitutions, resets and unresolved reviews are checked before selection.
Non-pitch events are retained in that comparison.

Every selected counted foul has the existing Strike Process, Strike Judgment
Act, Strike Decision ICE, PA containment and source-record aboutness. The
source SHACL profile checks that pattern; the serialization verifier compares
the exact admitted pitch IDs, including detection of extra held-count strikes.

## Affirmed pitch reviews

Explicit completed non-overturned reviews of called balls/strikes are mapped
at their particular pitch. The operative pitch judgment is the review act,
with its existing operative decision and one counted outcome. A distinct
original judgment/decision pair preserves the on-field call. Both decisions
identify the same pitched motion. The original umpire's participation, agency
and role are kept on the original judgment rather than copied onto the review.

For duplicate PA/pitch narratives, context chooses the existing PA review
identity and redirects every operative judgment/decision reference to it.
Separate pitch reviews remain distinct. A contradictory or incomplete explicit
terminal review cannot reappear through the older PA-narrative route. Other
play-level out/safe reviews remain separate.

M2 does not infer the review mechanism from an undocumented provider token,
the reviewer from the challenger, or the affected hitter from a catcher ID.
Batting substitutions withhold affected-player assignment in the retained
mapping evidence. No player aggregate or full eligibility denominator is
created by this mapping extension.

## Execution and evidence

`run-rml.ps1`, already invoked by the MLB NiFi lane, runs the added mechanical
source-to-RDF verifier before accepting the RML output. Its manifest retains
the source hash, selected and withheld identities/reasons, and verifier hash.
NiFi runs source SHACL before graph-pair promotion, including when RML defers
that stage to the separate processor. The implementation requires no new
processor group, schedule or manual recurring command.

The [bounded proof](../../../benchmarks/metrics/m1-m2-mappings-2026-09-15/README.md)
records the actual RMLMapper and Jena result. It is a developer proof, not a
claim that the live corpus or dashboard has already refreshed. The existing
NiFi proof/refresh request remains responsible for asynchronous promotion and
serving materialization. Daily external acquisition stays at 05:00 Eastern.

The other [mapping inventory gaps](../../../archive/design-records/mlb-game-metric-mapping-completion/field-selection-inventory.md)
remain separate. In particular, M1 is not a complete general count-state
mapping, and M2 does not establish all eligible unreviewed decisions.

## M3/M4 completion, accepted September 16

The separate decision in `e4166c1` accepts reconciled non-scoring steals,
initial roster-resolved pitching changes and completed MJ operative reviews
in an ordinary counted-foul prefix. Every unfiltered event remains in the
retained prefix inventory; counter corrections and ambiguous joins withhold
the added strike. M2's original/operative review mapping is unchanged.

Counted L foul bunts reuse the existing `BuntAct` class and its contact/role
pattern. The review's prose ?Bunt Attempt Act? refers to that existing term;
no `BuntAttemptAct` class or new property is declared. First/second strikes
do not become strikeouts. A third requires the supported terminal strikeout
result. SHACL additionally enforces the existing Strike Rule input and field
location. Exact source/RDF membership includes the added foul-bunt strikes.
