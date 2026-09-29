# W1: intentional walks after an unchanged-count prefix

**Under review. No implementation or semantic approval is recorded.**

The current selector requires exactly four events for a zero-pitch intentional
walk. It therefore omits the accepted walk-to-running attribution when a
non-pitch mound visit or pinch-runner replacement precedes the four VB counter
records. This is coverage debt in the existing MLB-game source lane.

## Decision requested

Admit the same existing intentional-walk award pattern when the four VB records
are preceded only by the precisely constrained events below. Repair affected
existing graphs by additive execution of the existing award maps. Preserve all
unrelated triples and derive affected SQL products through their NiFi owners.
No database rebuild, API reacquisition, new object property, class or identity
policy is requested. Approval would cover this selection rule and its ordinary
engineering consequences, not arbitrary administrative prefixes.

## Competency questions and proposed answers

1. Does a count-neutral mound visit or independently reconciled pinch-runner
   replacement turn an intentional walk into four delivered pitches? No.
2. Do four provider VB counter records prove four distinct umpire acts? No.
   Continue withholding that unsupported identity interpretation.
3. Can the existing Walk Process cause the batter's evidenced first-base
   Baserunning Act under the existing walk rule after that prefix? Yes, when
   the entire final source record passes the selection below.
4. Does this establish a missing PA-start stasis, a complete half-inning
   history or a review's effect? No. Their independent requirements remain.

The world-side pattern is the user's accepted
[runner-award final decision](../../archive/design-records/runner-award-origin-final-decision/user-decision.md),
shown in [the diagram](source-independent-mermaid.md). W1 requests review of
the additional source selection, not a different account of the award.

## Existing source evidence

Retained quarantine input: game 822864, run
`3011ddc6cb194b2ea53ec644bfcc5d4e/input.json`, SHA-256
`24adfc15c105909a4e09faedeb268cab6e58e5c3b630f1b7637af60f77c57b1e`.
This is an existing runtime witness, not a new acquisition or copied raw file.
The play is PA 54, August 8, 2026, top of the eighth, one out.

| Index | Explicit event | Balls | Strikes | Pitch? |
| --- | --- | --- | --- | --- |
| 0 | Pinch-runner Christian Franklin replaces Pete Alonso, base 2 | 0 | 0 | false |
| 1 | Mound visit | 0 | 0 | false |
| 2 | VB counter record | 1 | 0 | false |
| 3 | VB counter record | 2 | 0 | false |
| 4 | VB counter record | 3 | 0 | false |
| 5 | VB counter record | 4 | 0 | false |

The complete final PA result is `intent_walk`. Batter Jackson Holliday's
sole award runner row joins event 5, has no origin base, ends safely at 1B,
and agrees with `postOnFirst`. Neither prefix event records an out, score
or review. `pitchIndex` includes the four VB rows despite their explicit
`isPitch=false`; do not use that array as a delivered-pitch census.

The two existing selectors, `virtual_intentional_walk` in
`pitch-count-admission.py` and `runner_metric_evidence` in
`prepare-rml-context.py`, both require four total events indexed 0-3.
Changing only the former cannot supply the omitted award attribution.

## Field selection inventory

| Existing field | Classification | Proposed use |
| --- | --- | --- |
| `gamePk`, PA index, runner index, terminal `playIndex` | Identity/join-only | Retain current IRIs and exact terminal-event join. |
| Final PA result, completion, batter, post-first identity | Already supplied | Require the existing complete intentional-walk and batter-award checks. |
| Every event's index, `isPitch`, type and count | Already supplied; selection debt | Reconcile contiguous membership; prove no delivered pitch and no count-changing prefix. |
| Prefix event type and out/score/review flags | Already supplied; selection debt | Apply the bounded whitelist below. No event identity or agency is inferred from a label. |
| Replacement person IDs, PR position and base | Already supplied | Reuse the accepted C3 replacement reconciliation; do not reimplement or extend its identity rules. |
| VB call, ball/strike flags and terminal count | Already supplied | Preserve the existing four-row 1/2/3/4-ball, zero-strike counter checks. |
| Runner movement, award type, `movementReason` | Already supplied | Preserve existing complete award and forced-advance selection, including exclusions. |
| Prefix length and zero delivered-pitch total | Deterministically derivable | Selection mechanics only; no new RDF measurement or count-state individuals. |
| Event timestamps and descriptions | Already supplied | No new exact time, judgment identity, strategy or causal claim from these fields. |

## Exact selection boundary

- Require the existing complete, reconciled final PA and review/award checks,
  with unique contiguous event indexes and no delivered pitch anywhere.
- The final four records must satisfy every current VB sequence condition,
  using their positions within that final sequence for balls 1 through 4.
  The runner award must join the final event's actual index, not hardcoded 3.
- Every preceding event must explicitly be a non-pitch `action`, at 0 balls,
  0 strikes and the unchanged final out count, with no out, scoring play,
  ball/strike increment, contact or review evidence.
- Admit only `mound_visit` without substitution, or an `offensive_substitution`
  that the existing C3 logic independently reconciles as a pinch-runner
  replacement. A pinch hitter, unknown label, unresolved replacement or review
  remains outside W1. No prefix event is converted into a pitch or count award.
- Retain all existing award-attribution conditions for the batter and any
  forced runners. No new event-specific directive is created.

## Bounded implementation after acceptance

Use one shared selection routine for context construction and the count census
so they cannot disagree about this sequence. Keep the existing award RML maps:
`AwardCauseMap`, `AwardRequirementMap`, `AwardRequiredByMap`,
`AwardEvidenceRecordMap`, `AwardRuleEditionMap`, `AwardRuleIdentifierMap` and
`AwardRuleEditionIdentifierMap`. Their full accepted pattern remains required.

NiFi first proves this retained one-game witness with the owning SHACL and
existing count/award constraints scoped to the affected facts. Unrelated
whole-game admission failures remain unchanged. Its repair inventory must list exact
affected PA/runner identities and missing triples from retained source evidence.
Apply only missing selected award facts; do not replace game graphs or run a
whole-game RML transformation as a substitute for additive execution. Refresh
only affected query indexes, source admissions and derived SQL products after
promotion. Unknown identities or unrelated graph failures stay unresolved.

Reuse the additive promotion mechanics without reusing Q7's two-game semantic
authorization. W1 needs its own recorded acceptance before executable changes.
Previously admitted, unchanged count proofs may be reused only with exact
producer compatibility; prior failed proofs must actually pass their new checks.

This closes the identified zero-pitch/award-selection case. It does not claim
complete foul, defensive, review or season-percentile populations.
