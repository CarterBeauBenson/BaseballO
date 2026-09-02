# Field selection and de-duplication inventory

| MLB `feed/live` evidence | Disposition | Accepted use |
| --- | --- | --- |
| `liveData.boxscore.officials[*].official.id` | identity/join-only | Stable identifier for the Person bearing the game-scoped Umpire Role. |
| `liveData.boxscore.officials[*].official.fullName` | optional descriptive evidence | Map the existing optional label/name pattern only when supplied. |
| `officialType` | already owned by MLB-game | Selects the accepted Umpire Role context; it is not a Person kind. |
| review/challenge play description | genuinely additional event evidence | Recognizes the Review Act, challenge, reviewed item, and decision record. |
| explicit `confirmed`, `overturned`, or `upheld` wording | genuinely additional classification evidence | Controls the review-outcome classification; absence remains unknown. |
| play `result.eventType = game_advisory` | event-grain discriminator | Prevents an advisory-only record from being counted as a completed Plate Appearance. |
| evidenced pitch within an interrupted play | already owned pitch evidence | Remains an occurrent part of an incomplete Plate Appearance. |
| action description `Status Change - Delayed: Rain` | genuinely additional game-process evidence | Supports a game-contained delay Process and source advisory ICE. |
| delay reason `Rain` | nominal provider classification | Remains an ICE about the delay; it does not assert a world-side weather cause. |
| fabricated terminal result or inferred review status | unsupported | Never generate. |

No field in this package is remapped from Statcast or another source module.
