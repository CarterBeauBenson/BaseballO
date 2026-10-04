# H4: complete two supported runner-review selections

**Review-only candidate. The active context and RDF are unchanged.**

Two retained games still lose supported histories because the selector rejects
their final reviewed source records. This repairs source selection within the
accepted H3 review and C3 runner-boundary patterns. It creates no classes or
properties, changes no source bytes, and authorizes no graph replacement.

| Case | Recorded problem | Candidate repair |
| --- | --- | --- |
| 823200, PA 76 | A completed HBP review leaves an ordinary foul-tip strike (`O`), no movement and unchanged outs. The existing HBP-review selector omits that pitch code. | Accept the final reconciled strike under the existing completed-review checks. Preserve the pitch, count, participants and original times. |
| 823523, PA 72 | A reviewed catcher pickoff at third has `actionPlayId`, an explicit final pickoff result and one matching third-out row, but no standalone `playId`. | Reuse C3's existing `action/{association}/{eventType}/{runner}` token after verifying the unique associated pitch, exact runner/out/base join and completed review. Do not treat the associated pitch ID alone as pickoff identity. |

The candidate recovers six personal histories in the first game's top ninth
and two in the second game's top ninth. Existing history identities and
episode allocations must remain unchanged. The second game's boundary source
then fully reconciles; its existing boundary maps may add missing supported
PA-start facts after the owning SHACL passes.

## Decisions requested

Approve H4's two selection repairs and only their affected context fingerprints
in the existing semantic freeze/runtime pins. Execute additive repairs for the
eight missing histories and their existing dependencies, plus missing accepted
boundary facts in 823523. Reuse the retained inputs in `evidence.json` and the
existing NiFi owners. No API reacquisition, whole-game replacement or rebuild.

## Source selection and modeling

- Review dispositions, pitch call, counters, final result and runner rows are
  already supplied by MLB game inputs. These are omissions in the current lane.
- `actionPlayId`, result event type, runner identity and event association are
  existing identity/join evidence under C3. The full game collision census
  remains mandatory; array index and timestamp do not become identities.
- Reuse accepted Person, generic personal Process, Runner Resolution Episode,
  Baserunning Act, Out Process, Temporal Interval, and their existing relations.
- No review subject, original call, fictional movement, strict temporal order,
  or PA-start stasis follows merely from the review or association ID.
- C3 administrative boundary limits, Q7 empty pinch-runner exclusions, and Q6
  incomplete-source limits remain unchanged.

The source-independent structure is the accepted
[C3 mapping contract](../../archive/design-records/mlb-game-runner-boundary-anchors/mapping-contract.md)
and [H3 review contract](../../sources/mlb-game/review/rml-selection-repair-2026-10-01.md).
`selection.patch` is the exact candidate change; `check.py` tests it in a
temporary module. It does not activate the candidate or write live RDF.
