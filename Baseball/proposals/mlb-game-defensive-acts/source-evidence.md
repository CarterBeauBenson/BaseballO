# D1 source evidence and field selection

Inspected September 16, 2026. Existing unchanged source:
`data/raw/samples/2026-08-25/822693.json`.
SHA-256: `c2701c7de786df80013b21b36d74e8c5d6f6b1d0063bfab86d83ce6f5fb5fe02`.
The source module remains `mlb-game`; no additional endpoint or source lane.

| PA | Existing contact play ID | Evidence and limitation |
| --- | --- | --- |
| 1 | `fd524208-dc38-3e7b-bc19-5ba61643673d` | Named flyout to Dylan Crews; sole putout 686611; batter out at matching event 4. Supports a catch, not an unseen throw. |
| 2 | `7e15b9e5-670f-3f12-abbf-c06434ba4822` | Named groundout from Nasim Nunez to Abimelec Ortiz; assist 683083 and putout 694673; batter out at event 2. Tag chronology is not supplied. |
| 3 | `2a85cc39-fff9-3f5b-8811-1fdeae52e2ec` | Named foul-territory popout to Hunter Goodman; putout 696100 at event 0. Foul territory does not remove the described catch. |
| 8 | `809d65da-b751-309d-8ce2-3d43f227a401` | Groundout to Abimelec Ortiz; sole putout. The credit alone does not enumerate a separate tag or its temporal extent. |
| 26 | `fdbd273e-8856-3864-9967-04e91ea2fb99` | Described Young-to-Vivas-to-Ford-to-House relay while Norby is out at third; initial fielded-ball evidence plus later assist/putout credits. Young's duplicate assist/outfield-assist labels are not two throws. Full act/order completeness still requires reconciliation. |

MLB credits assists for deflections as well as ordinary defensive handling;
assist counts cannot be treated as throw counts.
[MLB Assist](https://www.mlb.com/glossary/standard-stats/assist).
A putout may arise from a catch, base touch or runner tag.
[MLB Putout](https://www.mlb.com/glossary/standard-stats/putout).
These facts justify distinguishing performances from credits; they do not
independently establish what occurred in any particular play.

## Selection inventory

| Field | Classification | Use |
| --- | --- | --- |
| `gamePk`, contact `playId`, event `index` | Identity/join-only | Existing game, contact and runner association; missing stable contact ID blocks selection |
| `result.description` | Already supplied by authoritative MLB source; mapping-coverage debt | Evidence for particular named performances; no new field-specific ICE class |
| `result.eventType`, `isOut` | Already supplied | Reconcile existing adjudicated result; never sufficient alone for actual acts |
| `runners[].details.playIndex` | Identity/join-only | Relate supporting movement record to contact event |
| `runners[].credits[].player.id` | Already supplied / identity join | Reconcile names with persistent Persons; credits do not establish whole sequence |
| `runners[].credits[].credit`, `position` | Already supplied | Cross-check described action and participant; no one-act-per-credit conversion |
| `runners[].movement` | Already supplied | Reconcile actual supported runner outcome against the described play |
| payload player names/IDs and boxscore roster | Already supplied / identity join | Resolve agent and preserve independent complete team-game exposure |
| selected act index and supported precedence pairs | Deterministically derivable only within the reviewed D1 bound | Processor context, retaining exact source witnesses; no analytical score field |
| unmentioned actions, exact catch/tag overlap, exhaustive whole-play sequence | Unresolved | Keep explicit gap; do not infer from ordinary scoring credits or missing rows |

No genuinely additional provider field is proposed. Existing wider defensive
research remains in the [metric review](../graph-native-metric-suite-batch-review/defensive-source-research-2026-09-14.md).
