# Source evidence

The ingest exposed four distinct payload patterns in completed 2026 MLB
`feed/live` responses.

| MLB game(s) | Observed source pattern | Evidential limit |
| --- | --- | --- |
| `831470`, `831634`, `831640`, `832043` | A boxscore official has a stable MLB `id` and official type but no `fullName`. | Do not invent a name or reject the identified Person and role. |
| `831566`, `831587`, `831595`, `831788`, `831951` | A play description states that a named player challenged a `pitch result` and states the resulting call, but some records omit explicit `confirmed`, `overturned`, or `upheld` wording. | Represent the review evidence; do not infer an outcome category absent from the source. |
| `831526` | `allPlays` contains an administrative `game_advisory` entry and fewer terminal plate-appearance results than play-array entries. | An administrative entry is not automatically a completed Plate Appearance. |
| `831629` | A Plate Appearance contains a pitch and then `Status Change - Delayed: Rain`. | Preserve the incomplete Plate Appearance and pitch; represent the delay separately. |

The evidence supports source-specific extraction rules. It does not support a
new universal for every provider field, an invented terminal plate-appearance
result, or a weather-causation assertion.
