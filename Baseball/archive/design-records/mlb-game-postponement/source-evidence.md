# Source evidence

## Checked MLB schedule case

MLB game `824621` occurs twice in the 2026 season schedule response:

| Schedule container | Relevant MLB evidence |
| --- | --- |
| `2026-04-02` | `gamePk` 824621; `officialDate` 2026-04-03; detailed state `Postponed`; reason `Inclement Weather`; revised date 2026-04-03 |
| `2026-04-03` | the same `gamePk` 824621; detailed state `Final`; `rescheduledFrom` 2026-04-02; completed makeup description |

The checked `feed/live` response identifies the completed game on 2026-04-03.
The two schedule appearances therefore provide revision history for one Game;
they do not support two Baseball Game individuals.

The schedule parser currently admits both rows because it tests only
`status.abstractGameState == "Final"`. MLB gives the postponed row that
abstract state even though its detailed state is `Postponed`.

## Rule and terminology evidence

- The current Official Baseball Rules group suspended, postponed, and tie games
  separately in Rule 7.02:
  <https://img.mlbstatic.com/mlb-images/image/upload/mlb/ub08blsefk8wkkd2oemz.pdf>
- MLB's rules glossary describes a suspended game as one stopped early and
  completed later from the point of termination:
  <https://www.mlb.com/glossary/rules/suspended-game>

These sources support keeping postponement distinct from delay,
suspension/resumption, cancellation, and a second Game identity.
