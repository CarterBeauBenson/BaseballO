# W3: final walk and hit-by-pitch award selection

**Accepted by Carter Beau Benson on October 3, 2026. This decision is published before activation.**

Five retained plate appearances have a complete final award and an unambiguous
batter advance to first, but the selector omits their existing award pattern.
W3 authorizes the bounded source-selection repair below and additive execution
for those five PAs. It introduces no classes, properties or identity policies.

| Game / PA | Final award | Selection gap |
| --- | --- | --- |
| 822972 / 14 | Nick Fortes, hit by pitch | Completed field review overturned the earlier call. |
| 823052 / 54 | Joc Pederson, hit by pitch | Completed field review upheld the call. |
| 823523 / 34 | Mookie Betts, intentional walk | Three physical balls precede the last VB counter. |
| 823048 / 52 | Lars Nootbaar, intentional walk | A timer ball, physical ball, two steals and a pinch hitter precede the last two VB counters. |
| 823350 / 98 | Bryan Reynolds, intentional walk | Pitching change and automatic-runner placement precede four VB counters. |

The exact retained-response hashes and selected runner identities are in
[evidence.json](evidence.json). The review-only [patch](selection.patch) and
[focused check](check.py) operate on a temporary copy of the context builder.
They do not run RML, acquire source data or write graph data.

The focused check passed on October 3 Eastern: all five exact awards are
selected, contradictory variants remain excluded, and mixed-pitch walks
remain outside the zero-pitch classification. This is candidate-selection
evidence, not a promoted graph or complete count/history admission.

MLB permits an intentional walk during an ongoing plate appearance.
([MLB intentional-walk definition](https://www.mlb.com/glossary/standard-stats/intentional-walk))
Hit-by-pitch calls are reviewable.
([MLB replay-review definition](https://www.mlb.com/glossary/rules/replay-review))
The proposed attribution still depends on the retained final source evidence;
these rules alone do not establish any particular award.

## Accepted competency-question answers

1. Can a reconciled final hit-by-pitch award use the existing award pattern
   after a completed review? **Yes.** Reuse the accepted final-field-review
   reconciliation. An unfinished, contradictory or unaccounted review remains
   excluded. This does not infer the original call or add review judgments.
2. Must an intentional walk begin at a 0-0 count? **No.** The final VB suffix
   must advance the immediately preceding valid count consecutively to four
   balls without changing strikes or outs. Require the complete final
   intentional-walk result and exact safe first-base runner join.
3. Must that award wait for every earlier event's entire history to be
   admitted? **No.** Earlier plays retain their independent evidence status.
   The final award does not certify a preceding steal, replacement, placement,
   timer violation, physical pitch census or personal history. In particular,
   the two earlier steals in 823048 are not caused by this walk.
4. Are VB counter records pitches or separate timer judgments? **No.** Keep
   every actual pitch and independently evidenced automatic count award.
   A PA with actual pitches must never be classified as a zero-pitch walk.
5. Does this approve a graph replacement or repair every problem in these
   games? **No.** Add only missing selected award facts and their accepted
   dependencies. Existing unrelated rejections remain visible.

The accepted world-side pattern is shown in the
[source-independent diagram](source-independent-mermaid.md), reusing the
[final award decision](../runner-award-origin-final-decision/user-decision.md).

## Field selection inventory

| Source fields | Classification | Use |
| --- | --- | --- |
| Game, PA, runner index, player and event index | Existing identity/join evidence | Preserve current IRIs; require one exact terminal runner join. |
| Completed PA, final result and post-first player | Already supplied | Existing final award and safe first-base checks. |
| Review disposition, narrative and final pitch call | Already supplied; selection debt | Reuse the accepted completed-field-review reconciliation for HBP. |
| Event indexes, pitch flags, VB call and count | Already supplied; selection debt | Consecutive terminal counter suffix, unchanged strikes/outs, valid boundary count. |
| Earlier pitches, administrative events and runner rows | Already supplied | Keep their own accepted owners; never turn them into the award or its credit. |
| Force flag, movement reason and destination | Already supplied | Keep existing forced-advance requirements; never infer a force from occupancy alone. |
| Number of delivered pitches or remaining VB counters | Deterministically derivable | Validation mechanics only; no new RDF count entities. |
| New endpoints, fields, vocabulary or spatial assertions | None | No expansion requested. |

## Exact selection and activation boundary

The shared award selector retains its current seasons, completed-result,
unique runner-resolution, matching batter/post-first identity, terminal-event
join, movement and force checks. HBP may pass only the existing completed
final-field-review helper with no remaining review issues. Other reviewed
award kinds retain their current checks.

For an intentional walk, the terminal VB suffix must contain one to four
contiguous records ending the PA. All event indexes must be contiguous.
The suffix starts from the immediately preceding count, or 0-0 if it starts
the PA; balls must increase exactly once per counter to four. Strikes stay
in 0..2 and outs in 0..2, unchanged through the suffix and equal to the final
PA count. Every suffix record explicitly has `isPitch=false`, `type=no_pitch`,
call `VB`, ball true, strike/in-play/out/review false, no substitution and no
scoring play. Its nonterminal records have no runner rows. Contradictory
indexes, counts, review evidence, flags or runner joins withhold selection.

Earlier events need not belong to W1's zero-pitch prefix whitelist to support
this final award. This is the accepted semantic boundary: independently
evidenced final attribution is not a certificate of complete earlier history.
The existing zero-pitch helper is unchanged by the prepared context patch.
The count owner must retain physical pitches and real count judgments when
consuming the final-award classification; it may not silently drop them.

On named acceptance, first archive and publish the decision. Then apply the
context patch and only its scoped freeze/manifest pins and exact producer
compatibility references; preserve every prior proof's status and provenance.
Generalize the existing NiFi award owner to the five listed selections,
reusing its seven award/rule maps and W2's four selected runner-dependency maps.
Use the existing HBP result type for HBP validation, not Walk Process, and
scope SHACL to the actual affected facts and prerequisites. Each existing
source lane retains its independent conformance requirements.

NiFi must enumerate the missing triples against the promoted graph, validate
the addition with the owning SHACL, promote by addition, and refresh affected
admissions and derived SQL through their existing owners. No whole-game RML,
whole-game replacement, API reacquisition or season rebuild is included.
823350 has separate history conflicts; W3 does not resolve those conflicts.

The user accepted **W3 final-award selection and its scoped context pin
update**, with the five additive repairs above, by replying "Approve and fix
the runner history" to the pending W3 request and status explanation. This
also directs continued runner-history repair within already accepted patterns;
it does not silently replace C3/Q7 identity or persistence decisions.
