# K1: complete the existing compound double-play result

Status: accepted on September 30, 2026, through the user's narrow RML repair
authorization and explicit yes to the targeted reacquisition question naming
these five games. See [the exact decisions](../metric-repair-scope-2026-09-30/answers.md).
No new class, object property, data property or entity identity is proposed.

## Proposed decision

For a positively reconciled `strikeout_double_play`, type the existing combined
PA result as `DoublePlayProcess` and connect its exactly two existing
`OutProcess` instances using CCO `has process part` (`cco:ont00001777`).
Both out identities, their participants and their adjudication patterns must
already be present and agree with the selected source rows. The accepted
Double Play definition concerns two counted outs in one continuous play; it
does not require a batted ball. The overlay explicitly requires exactly two
Out Process parts through that same accepted relation.

The combined result remains the same `plate-appearance/{index}/result` entity.
Do not type it as `StrikeoutProcess` merely because one part of the play is a
strikeout. Do not introduce a new constituent identity in this repair.

Align the B1 source expectation and its RDF qualification query with this
specific Double Play result. B1 already admits Double Play as a recognized
completed result. Keep the full PA / Batter Act / persistent Batter Role /
bearer / result / judgment / decision / record pattern, exact membership,
per-player official PA reconciliation and team exposure checks. A generic
institutional result alone remains insufficient. This changes the expected
specific classification, not the official PA denominator or metric formulas.

Allow a bounded refresh of the **five named MLB game responses below** through
the existing source-owned acquisition stage, because their transient raw
responses are retired. Retain the new response's separate hash; it must not be
relabeled as the original promotion input. Use only the selected compound
result and out rows for RML. This is not permission to rerun whole-game RML,
replace a graph or rebuild the corpus. Other games require separate scope.

## Recorded evidence and exact initial scope

September 29 retained B1 censuses identify these completed outcomes:

| Game | PA | Batter ID | Original promoted source SHA-256 |
| --- | --- | --- | --- |
| 823327 | 46 | 802139 | `342c7da559bc12080245500d879b140a3014970cd9c1c8160e7ee3c1eca26973` |
| 823489 | 6 | 641355 | `152c4b726fe40f92846608f815228b680aa3c2b4f18992ea01538199830a9508` |
| 824301 | 40 | 672695 | `34973fcc711eb0857b3c33d05f6c2ef47b5736c548bef935de94f2b71d0de204` |
| 824302 | 17 | 694249 | `aac643b8f8363e87f5e3c9d197627ecc07133bbb0e40a87191ba8a1a5d90d174` |
| 824866 | 42 | 663886 | `5a9757ef6e0fc36795ceae2a2e945cc39da111ce9966c8f30e3c8dc1fac909d4` |

All five censuses record `strikeout_double_play` but expect `StrikeoutProcess`.
The existing RML `Result_strikeout_Source` selects ordinary `strikeout` only;
the common `PlateAppearanceResultMap` supplies the generic combined result.
The original manifest input paths no longer exist. No transient response,
quarantine `input.json` or matching checked-in sample was present for these five
games at this check. Census evidence locates the debt; it is not a substitute
RML source.

A read of the promoted graph for 823327 / PA 46 confirmed:

- `plate-appearance/46/result` is a `BaseballInstitutionalProcess`, with its
  existing result judgment, decision and source record.
- `runner-resolution/out/46/0` is an `OutProcess` involving batter 802139.
- `runner-resolution/out/46/1` is an `OutProcess` involving runner 691026.
- Both out processes are already parts of PA 46, but the combined result
  lacks the proposed Double Play type and process-part links.

The other four cases are candidates, not assertions that their full graph
patterns already pass. For the checked example the proposed delta is three
triples: one existing class assertion and two existing process-part relations.
Missing dependencies stop that candidate instead of widening the addition.

## Selection and de-duplication inventory

| Owning MLB field/evidence | Classification | Use |
| --- | --- | --- |
| Game and PA indexes | Identity/join-only | Reuse existing result and runner-resolution identities. |
| `result.eventType` and final description | Already supplied; mapping coverage debt | Confirm the compound result and one continuous play; the provider label alone is insufficient. |
| Terminal pitch ID/index, count and result flags | Already supplied; identity/join-only | Reconcile the strikeout and both out rows to the same terminal event. |
| Runner IDs, `movement.isOut`, out numbers and `details.playIndex` | Already supplied; mapping coverage debt | Require exactly two distinct counted outs, one for the batter and one for the existing runner, with no intervening separate play. |
| Boxscore PA and team totals | Already supplied | Existing B1 reconciliation only; never a source of SQL metric values. |
| Missing strikeout constituent identity or further dependencies | Unresolved/out of scope | Do not create them as part of K1. |

Require a final reconciled response, unambiguous terminal-event association,
three strikes, exactly two distinct source out rows and a two-out increment
that fits the inning. Reject conflicting descriptions, source corrections
that change the matched entities, extra outs, missing referents or unclear
continuity. Temporal array position alone does not prove continuous play.

## Competency questions

1. Does the combined adjudicated result satisfy the accepted Double Play
   pattern when its two counted outs and continuous-play evidence reconcile?
   Proposed answer: yes, with those exact Out Processes as its process parts.
2. Does that make the entire combined result a Strikeout Process?
   Proposed answer: no; K1 makes no such assertion.
3. Does B1 count the completed turn once through this specific admitted
   Double Play result? Proposed answer: yes, retaining all other B1 checks.
4. Does K1 assign the other runner's out to a failed hit-and-run strategy?
   Proposed answer: no. Existing attribution requirements remain independent.
5. Does approval authorize an all-season RDF rebuild or new properties?
   Proposed answer: no; only the named five-game acquisition and selected delta.

## Execution after acceptance

Record and publish the named decision before changing source selection/RML.
Use the existing MLB lane and additive graph-pair transaction, beginning with
823327 / PA 46. Validate the selected full pattern through the owning SHACL,
preserve unrelated triples and original source provenance, then refresh only
that game's query index and affected SQL products. Preserve all other failed
checks. A successful addition is not evidence that all 19 metrics are populated.

See the [source-independent shape](source-independent-mermaid.md). This
package changes RML source selection and asserted compound-result structure;
the recorded approval precedes implementation under [AGENTS.md](../../../../AGENTS.md).
