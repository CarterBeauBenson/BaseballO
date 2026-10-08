# F9: five missing counted-foul strikes in four games

Status: **under review**. The executable context is unchanged. The proposed
generic selector repair passed five focused checks over the retained inputs.

## Concrete decision

Approve the four selections below, their scoped context fingerprints, and
NiFi's additive repair of the five inventoried Strike Process patterns and
existing dependencies. Future ingestion uses the same corrected selectors.
Reuse the five existing counted-foul maps and their source-owned SHACL; no
new ontology terms, object properties, identity policy or graph replacement.
Do not reacquire these inputs or rebuild any game or season.

| Retained game / PA | Proposed selection correction | Missing strikes |
| --- | --- | --- |
| 823013 / 62 | A completed, unchanged record-keeping review wraps one completed HBP review. Inspect that substantive review and the final foul-bunt count; do not assume the wrapper is the HBP review or infer their temporal order. Both dispositions must be explicit. | 2 |
| 823804 / 54 | The final double-steal narrative says the second runner “steals home.” Accept that wording only with the explicit stolen-base-home movement, scoring flag, runner identity and reconciled counters. | 1 |
| 824118 / 35 | A completed catcher-pickoff review has an association to one earlier pitch, no movement/out, and unchanged counts. Reconcile this neutral record without inventing a standalone pickoff identity or a Safe judgment. | 1 |
| 824744 / 62 | The batting-order substitution names the outgoing rostered player without a position word. Make that word optional while retaining exact names/IDs, incoming pitcher participation, unchanged counts/outs and no runner movement. | 1 |

The exact source hashes, failed owner records and selected pitch identities are
in [evidence.json](evidence.json). [selection.patch](selection.patch) contains
the complete candidate. No reviewed call is assigned to a player and no
original ruling is inferred. Unknown or contradictory review dispositions,
ambiguous associations, unexplained counts and conflicting participants remain
excluded.

MLB's official source identifies `I` as hit by pitch and `K` as record keeping.
([MLB review reasons](https://statsapi.mlb.com/api/v1/reviewReasons))
MLB also identifies tag and hit-by-pitch calls as reviewable.
([MLB replay review](https://www.mlb.com/glossary/rules/replay-review))
Those references explain the source vocabulary; the exact final counts,
participants and movements come from the four retained game responses.

## Existing source selection inventory

| Fields | Disposition and use |
| --- | --- |
| Pitch IDs, final calls, count flags, counters and timestamps | Existing authoritative facts; preserve identities and the promoted count census. |
| Nested review records, explicit completion/disposition and event association | Existing selection coverage debt; account for each supported final effect without mapping new review facts. |
| Runner IDs, movement types/bases, scoring flags and narrative | Existing joins; “steals home” must corroborate its own explicit scoring movement. |
| Roster IDs/names, batting slot and actual pitch participants | Existing joins; an omitted position word cannot supply or replace identity evidence. |
| New API fields, sources or derived ontology vocabulary | None. |

## Reused world-side pattern

Reuse the already accepted [M3/M4 source-independent shape](../../archive/design-records/mlb-game-counted-foul-completion/source-independent-mermaid.md)
and [source-specific projection](../../archive/design-records/mlb-game-counted-foul-completion/source-specific-mermaid.md).
The Pitch Act, bunt/contact/foul processes where applicable, operative Strike
Process, Strike Judgment Act, Strike Decision ICE, Strike Rule, containment
and source record support retain their existing types and relations. The
candidate changes source selection only; it adds no review or pickoff pattern.

## Focused check and execution

`python -B Baseball/proposals/mlb-game-counted-foul-edge-completion/check.py`
loads the candidate in a temporary module. All five exact strikes pass the
existing foul worker's selection against the promoted source census. Negative
checks reject incomplete/extra reviews, contradictory runner effects, broken
pitch associations, unknown names/participants and changed counters. No RDF
is written by this check.

After named approval is recorded and published separately, activate the patch,
update only affected context pins and the existing compatibility chain, then
let the enabled foul owner retry its four recorded cases. Existing successful
jobs remain completed. NiFi's existing RML, SHACL and additive promotion own
runtime execution. Successful selection is not a claim that promotion or any
metric population is complete.
