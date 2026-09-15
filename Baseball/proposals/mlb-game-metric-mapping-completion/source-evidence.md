# Source evidence for the completion review

Inspected September 15, 2026. Source path:
`data/raw/samples/2026-08-23/824315.json`, SHA-256
`5fcc75d37a20a516d312b3bfb3d5cefb4371ebafa639851ff16173d9b1a6607c`.
The retained source bytes are unchanged. Revision `20260823_222717` reports
Final. This is a bounded source inspection, not a source promotion or season
coverage proof. `source-capture.json` contains the exact diagnostic rows.

## Concrete mapping omissions

1. `CountedFoulSource` currently selects ordinary fouls only when
   `count.strikes == 1`. The file explicitly calls second-strike fouls
   ambiguous under an event-local read. The enclosing event sequence resolves
   27 **candidate** 1-to-2 transitions in this game. That is an omission in
   contextual mapping coverage, not absent provider counters.
2. Current `reviewed_play_context` is entered from PA `about.hasReview` and
   a matching result narrative. Pitch context receives review information
   only for a terminal pitch in a PA-level pitch-result review. This does not
   cover the two explicit nonterminal reviewed pitches below. Their enclosing
   result narratives describe a single and a double play, respectively.

## Positive and negative cases

| Case | Source evidence | Consequence |
| --- | --- | --- |
| PA 2, event 1 | Pitch `cc230907-649e-3bb5-bd54-335087113c53`: F, 0 balls/2 strikes. Event 0 has 0 balls/1 strike and ends `2026-08-23T19:18:04.316Z`; event 1 starts `19:18:19.358Z`. | Positive single-case candidate for M1; complete-prefix gates still apply. |
| PA 35 | Ordinary foul events after the count already reaches two strikes remain at two. An intervening batter timeout is present. | Do not map every F with post-count 2 as a new Strike Process or drop non-pitch records before reconciliation. |
| PA 36, event 5 | Pitch `4edb573f-e278-3f46-a0a2-c2a87cef6afb`, Ball, `inProgress=false`, `isOverturned=false`, player 664954. | Affirmed called-pitch review, distinct from the eventual single. |
| PA 43, event 0 | Pitch `349a9764-76e7-374c-ae7d-e73adedef1a9`, Ball, same explicit completion/affirmation flags and player 664954. | Affirmed called-pitch review, distinct from the later double play. |
| PA 12 | Play-level review, `reviewType=MF`, final unchanged disposition, narrative challenge at first base. | Preserve the separate existing out/safe review; do not attach it to an arbitrary pitch. |
| PA 35 terminal event | Pitch counter reports 1 out; completed PA reports 2; batter movement reports out number 2. | Never reuse the pitch counter as post-consequence outs. |
| PA 43 fielding | Tovar to Ritter to Norby in the description, with separate assist/putout credits on two runner outcomes. | Defensive evidence exists; enumerate exactly which intentional acts are supported before typing or claiming completeness. |

Player 664954 is Brett Sullivan, the catcher in the inspected review events.
His mention does not identify the affected batter. The provider token `MJ`
is retained as evidence in the capture, not promoted as an ontology class
or treated as a documented mechanism code by this review.

The diagnostic scan finds 413 total play events, 360 pitches, 27 ordinary
fouls with an immediately preceding strike count of 1 and current count of 2,
and 46 ordinary fouls with preceding and current count 2. Admission requires
more than this scan. In particular, candidate rows in reviewed or otherwise
unreconciled prefixes must remain withheld under M1.

## Primary web resources checked

An ordinary foul cannot supply the third strike. See
[MLB's strikeout glossary](https://www.mlb.com/glossary/standard-stats/strikeout).
Foul tips have different third-strike treatment. See
[MLB's foul-tip glossary](https://www.mlb.com/glossary/rules/foul-tip).
These support keeping ordinary fouls, foul tips and bunt cases separate.

[Savant's ABS documentation](https://baseballsavant.mlb.com/abs-metrics-documentation)
defines eligible challenge opportunities using adverse calls, available
challenges and exclusions. The existence of a reviewed-pitch record is not
a complete opportunity population, and a final challenge count is not the
state at every earlier event. No new review denominator is admitted here.

The prior [source-availability correction](../graph-native-metric-suite-batch-review/source-availability-correction-2026-09-15.md)
contains the wider PA, runner, defensive and review evidence. This package
turns two identified omissions into explicit mapping contracts; it does not
reverse that correction or claim that the other source fields are absent.
