# F8: finish counted-foul substitution and paired-review selection

Status: **accepted on October 4, 2026; implementation follows separately**. No new classes or object properties.

## Decision requested

The user accepted the enclosed context-selection patch and its scoped context fingerprint
updates. Use the existing counted-foul NiFi owner and unchanged five strike maps
to add the **eight missing second-foul strikes in seven games** listed below.
Preserve retained raw bytes, existing graph facts and all unrelated games.
This is a targeted addition, with no source acquisition or game/corpus rebuild.

The old and candidate hashes, exact retained inputs and existing SHACL/source
censuses are in [evidence.json](evidence.json). The implementation is review-only
in [selection.patch](selection.patch); it does not change the active context.

## Competency questions and source evidence

| Question | Evidence and proposed answer |
| --- | --- |
| Must a batting-slot replacement identify the departing pitcher? | No. In 823355/75, 823400/78, 823429/80 and /93, 823452/65 and 823465/67, the pitching-change narrative identifies the actual pitcher pair. `replacedPlayer` may identify a different lineup player. Match the unique rostered pitcher names separately; verify the batting slot and any explicitly named fielding replacement. |
| Can a count-neutral pitching change follow a pitch? | Yes, when the exact rostered pitcher pair, unchanged count/outs and subsequent incoming pitcher reconcile. In 823420/38, Hunter Dobbins throws a ball, then Caleb Ferguson replaces him after an injury delay at 1-0. The later second-foul strike is independently supported. Multiple or contradictory pitching changes remain excluded. |
| Can one description contain two separately completed reviews? | Yes. In 823396/80, the overturned MJ pitch review and upheld MA tag review have separate records joined by the actual pitch ID. Reconcile each disposition and its effects. Do not apply the word “overturned” to both acts. |

## Field selection and duplication inventory

| Existing MLB fields | Disposition |
| --- | --- |
| Pitch IDs, event indexes, final pitch counts and call codes | Already authoritative; preserve existing event identity and the selected count census. |
| `player`, `replacedPlayer`, `position`, `battingOrder`, pitching-change description, team pitcher list and roster names | Existing source selection coverage debt. Resolve actual pitching participation separately from lineup replacement; no new source or participant relation. |
| `actionPlayId`, `reviewDetails`, review descriptions and final runner movements | Existing review coverage debt. Require a unique associated pitch and two compatible, explicitly completed dispositions. |
| Existing pitch/strike/decision IRIs and accepted relations | Reuse the accepted M3/M4 and F5 pattern; no new vocabulary or identity rule. |
| Earlier pitch's pitcher after a mid-PA replacement | Separate P1 finding. This package selects the later foul only; it does not correct already asserted pitching participants. |

The accepted pattern is shown in
[source-independent-mermaid.md](source-independent-mermaid.md).

## Focused result and execution

`python Baseball/archive/design-records/mlb-game-foul-substitution-review-completion/check.py`
passes four grouped regression checks: all eight exact selections through the
existing foul worker, contradictory lineup/pitcher evidence, mid-PA count and
pitch ordering, and incomplete/contradictory/unjoined reviews. The check runs the
draft in a temporary directory and writes no RDF. It preserves the selected
source census's identities, clocks and outcomes. This is selection evidence,
not a claim of promotion.

After named acceptance is committed and pushed separately, activate the patch,
update only affected semantic/runtime context pins and existing compatibility
records, and let the enabled foul-addition owner perform its bounded retry.
Its existing RML subset and count SHACL own validation and promotion. Record
each actual promotion before calling these seven jobs repaired.
