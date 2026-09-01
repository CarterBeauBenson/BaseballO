# Field and consequence inventory

| Field or semantic component | Current evidence status | Option A | Option B |
| --- | --- | --- | --- |
| MLB league `id` | accepted organization identity | Always map the League Organization independently. | Always map the League Organization independently. |
| `season` or `seasonDateInfo.seasonId` | valid season-code evidence | Retain for request/provenance evidence until a complete reviewed phase pair exists; do not emit the Season subgraph. | Key and emit Baseball Season, Baseball Season Plan, and season-code Identifier. |
| complete regular-season pair | accepted Phase evidence | Emit Season, Plan, regular-season Phase, identifier, and admitted date evidence. | Add the regular-season Phase to the already admitted Season/Plan subgraph. |
| complete postseason pair | accepted Phase evidence | Emit Season, Plan, postseason Phase, identifier, and admitted date evidence. | Add the postseason Phase to the already admitted Season/Plan subgraph. |
| one member of an accepted pair | valid date but incomplete Phase evidence | Emit no Season/Plan/date subgraph in this release. | Emit the Plan-part Date Identifier and Day, but no Phase. |
| other valid `*Date` field | accepted Plan date evidence only | Emit only when another complete pair admits the Plan. | Emit as Plan-part date evidence when the Season/Plan is admitted by season code. |
| malformed present date | invalid source value | Quarantine before RML. | Quarantine before RML. |
| Date/Day-to-Phase relation | unresolved | Prohibited. | Prohibited. |
| team/league/division membership | outside this question | No effect. | No effect. |

No source field, provider code, new class, or new property is proposed. The
decision changes only the evidential threshold for emitting an already
accepted Season/Plan graph and the matching source-SHACL cardinality.
