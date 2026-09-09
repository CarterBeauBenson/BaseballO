# A1 field selection

Owner: existing `mlb-game` source. No new API or graph product.

| Field | Selection | Use / missing behavior |
| --- | --- | --- |
| `gamePk` | Identity/join-only | Reuse the existing game scope. |
| `about.atBatIndex` | Identity/join-only | Reuse PA and runner structural scope. |
| Runner array position | Identity/join-only | Reuse current runner-resolution identity; never coalesce rows here. |
| `about.isComplete` | Already supplied | Restrict the initial addition to completed results. |
| `result.eventType` | Already supplied | Recognized contact-result evidence; unknown or non-contact result omitted. |
| `playEvents[].isPitch` | Already supplied | Reuse the current pitch source boundary. |
| `playEvents[].details.isInPlay` | Already supplied | Reuse the current terminal in-play condition. |
| `playEvents[].details.call.code` | Already supplied | Reuse X/D/E terminal in-play selection. |
| `playEvents[].index` | Identity/join-only | Explicit index must uniquely identify the terminal pitch within the PA. |
| `playEvents[].playId` | Identity/join-only | Reuse the contact-play individual; missing identifier omits association. |
| `runners[].details.playIndex` | Identity/join-only | Exact terminal-event join; missing or ambiguous association omitted. |
| `runners[].details.eventType` | Already supplied | Restrict initial association to the same recognized contact-result category; independent/mixed/unknown categories omitted. |
| `runners[].movement.isOut` | Already supplied | Must be a boolean to identify an existing resolution; null placeholder omitted. |
| `runners[].movement.start` | Already supplied | Reuse existing reach/advance resolution selection only. |
| `runners[].movement.end` | Already supplied | Reuse existing score resolution selection only; no new destination assertion. |

Selection is not an attribution formula. No field supplies a new ontology
class, causal assertion, new state identity, or absence claim.
