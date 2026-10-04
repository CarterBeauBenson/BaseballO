# P1: actual pitching participation during a plate appearance

Status: **under review, not active**. No new ontology terms or object properties.

## Decision requested

Use the explicitly evidenced pitcher for each physical Pitch Act, rather than
assigning the final PA matchup pitcher to all pitches. Retain the existing
career-persistent Pitcher Role and its bearer/stasis dependencies. Include each
actual pitcher as a participant in the enclosing Plate Appearance. This does
not change official pitching-stat responsibility or assert that an earlier
pitcher participated in the final institutional result.

For a mid-PA substitution, reconstruct the ordered pitcher segments from the
event indexes, the explicit incoming player and the unique rostered pitcher
pair named by the change. Treat a batting-slot `replacedPlayer` separately.
Require the chain to agree with the final matchup and the supported pitch
membership. Unknown or contradictory joins cannot default earlier pitches to
the final pitcher; withhold the unsupported attribution and report its exact
scope through the source lane. A generic preceding PA is not evidence of the
outgoing pitcher: it can belong to the opposite half-inning.

Accept the necessary RML selection/participant-map changes and scoped context
pins. For the one verified existing graph below, authorize **removing exactly
two wrong assertions and adding three supported assertions**. All other triples
survive. Other discovered cases require a concrete correction inventory before
mutation; this package does not authorize replacing any game or rebuilding the
corpus. The existing source lane owns targeted RML, SHACL and graph promotion.

## Verified witness and competency questions

The retained source for **823420 / PA 38** is pinned in
[evidence.json](evidence.json). Its first physical pitch has ID
`c02215cb-347f-32c0-9d72-8a4efe1d80c7` and makes the count 1-0. An injury
delay follows. Event 2 says “Pitching Change: Caleb Ferguson replaces Hunter
Dobbins.” Later pitches belong to Ferguson. The final matchup is Ferguson.

| Question | Supported answer |
| --- | --- |
| Who pitched before the change? | Hunter Dobbins, person 690928. |
| Who pitched after it? | Caleb Ferguson, person 657571. |
| Does a PA's final matchup establish every earlier pitch's participant? | No. Its scope does not override an explicit intervening replacement. |
| Does fixing this require a new Role per pitch? | No. Reuse each person's accepted career-persistent Pitcher Role. |
| Does this repair require deleting a game graph? | No. Correct the two exact pitch relations and add the missing PA participation. |

A bounded live read on October 4 found the first pitch incorrectly participating
with Ferguson and realizing his Pitcher Role. It also confirmed that Dobbins's
accepted Pitcher Role, bearer, stasis and temporal region already exist. The
PA lists Ferguson and batter Trea Turner (607208), but not Dobbins. The
baseball artifact's separate participation is correct and remains untouched.

## Field inventory and affected artifacts

| Fields or artifacts | Disposition |
| --- | --- |
| `matchup.pitcher`, ordered `playEvents`, pitching substitution `player`, roster pitcher IDs/names | Already authoritative MLB game fields; source-selection coverage debt. No additional API acquisition. |
| `replacedPlayer`, batting order and fielding-replacement description | Identity/join evidence with its own lineup scope; cannot substitute for the actual outgoing pitcher. |
| Pitch/PA IDs and persistent Person/Pitcher Role IRIs | Reuse existing identities. |
| `PitchActMap` participant and realization objects | Correct per-pitch context selection. |
| `PlateAppearanceMap` and Pitcher Role/stasis dependencies | Complete the same accepted pattern for actual earlier pitchers, including a pitcher who has no completed PA of his own. |
| PA institutional result and official boxscore responsibility | Separate existing semantics; no change proposed. |

## Reviewable graph correction and implementation boundary

[correction-preview.rq](correction-preview.rq) shows the exact known live delta.
It is a review artifact, **not an executable repair command**. Production
execution must use the NiFi owner's game lock and promotion transaction, bind
the current graph/source hashes, generate supported additions through RML,
apply the owning SHACL and refresh only the affected derived products. Reuse
the normal retry and recovery mechanism; do not send this preview directly to
Fuseki. Its conditional WHERE preserves unrelated facts and refuses a changed
pitch participant/role set.

The source-independent accepted structure is in
[source-independent-mermaid.md](source-independent-mermaid.md). Acceptance must
be recorded and pushed before the active source selection or context pins change.
