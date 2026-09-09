# Shared-play erosion boundary

Status: **proposed metric convention; not accepted or executable**.
Prepared 2026-09-08 after the user asked to resolve question three.

## Recommended bounded decision

For a non-inning-ending shared play containing a batter-attributed out and
independent safe advances or scoring, evaluate erosion against the evidenced
actual state after the shared play. Attribute progress and destruction only
to the batter's admitted consequences; use only batter-attributed outs in
the erosion numerator. Independent advances remain context, not progress
credit. A participant who has scored receives no survivor erosion.

This defines a metric evaluation boundary. It does not claim that the
independent advance occurred before the out, infer a temporal ordering from
a shared provider index, or assert batter causation of the independent event.
Do not project a fictional unchanged runner state into authoritative RDF.

The supplied specification defines erosion using the maturity of participants
still alive after the consequence. The unresolved issue is which end boundary
applies when consequences overlap. Using the shared play's evidenced end makes
that explicit while retaining the existing formula. It allows independent
advancement to affect the context in which an attributed out is evaluated;
the resulting contextual dependence is intentional in this proposal.

## Exact comparisons

These are conditional policy examples, not published TFS values or claims
that the complete graph evidence contract is already implemented.

| Scenario, one out beforehand and one batter-attributed out | Evaluate using bases before both events | Proposed actual shared-play end |
| --- | --- | --- |
| Strikeout; independent wild pitch advances first to second | `-1/4 - (1/3)(1/2) = -5/12` | `-1/4 - (1/2)(1/2) = -1/2` |
| Strikeout; independent wild pitch scores second and advances first to third | `-1/4 - (1/2 + 1/3)(1/2) = -2/3` | `-1/4 - (1)(1/2) = -3/4` |

The second example is anchored in checked-in
[`822693.json`](../../../data/raw/samples/2026-08-25/822693.json), PA 36,
SHA-256 `c2701c7de786df80013b21b36d74e8c5d6f6b1d0063bfab86d83ce6f5fb5fe02`:

- PA 35 reports one out, runner 664983 at first and 687597 at second.
- PA 36 runner row 0 records batter 694249 out, `outNumber=2`.
- Row 1 records runner 687597 from second to score, `wild_pitch`, scoring true.
- Row 2 records runner 664983 from first to third, `wild_pitch`, safe.
- All three rows use event index 4. The terminal pitch has out count 1;
  the PA count is 2, and `postOnThird` explicitly names 664983.
- These records do not establish the relative resolution times within event 4.

Under the recommendation, the scored runner gets neither batter progress
credit nor survivor erosion. The runner now on third gets erosion `1/2`,
and the batter gets destruction `1/4`, giving the conditional total `-3/4`.

## Admission limits

Require a reviewed common-play boundary, complete relevant participant and
resolution evidence, an evidenced out count before that boundary, a distinct
operative batter-attributed out, and no independent out within the group.
An index match alone does not prove all those conditions. Keep the criterion
for admitting a common boundary separate from this scoring convention.

This bounded proposal does not settle simultaneous independent outs,
inning-ending stranding, walk-off truncation, operative replay changes, or
uncaught-third-strike cases without an evidenced batter out. Preserve unknown
scores whenever those unresolved facts matter. The previously accepted
stranded-runner policy remains in force, with its evidence requirements.

No new class, property, RML, SHACL or metric execution is admitted here.
After acceptance, analytical regressions can encode this convention; graph
constraints still require a reviewed evidence pattern before source mapping.
