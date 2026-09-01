# Field and identity inventory

| Field or component | Status | Proposed handling |
| --- | --- | --- |
| transaction `person.id` | identity/join-only | Preserve in the content-versioned row hash; resolve to exactly one canonical Person only under the accepted option. |
| transaction `person.fullName` | diagnostic duplicate | Never choose resource kind from the name and never publish the name from this lane. |
| `data/player/{id}` | existing canonical path kind | Use directly only if Option A's provider guarantee is accepted or Option B uniquely resolves it. |
| `data/person/{id}` | existing canonical path kind | Use only if Option B uniquely resolves it. |
| MLB Person Non-Name Identifier | existing authority pattern | Under Option B, use its designation as authority evidence; do not copy its triples into the transaction graph. |
| transaction row DICE | accepted information grain | May be about the uniquely resolved Person; remains content-versioned independently. |
| Player Role | outside this decision | Never infer from resource kind or a transaction mention. |
| Person name/type publication | owned by MLB people | Prohibited in the transaction graph. |
| unresolved or conflicting identity | unresolved policy | Quarantine or retain the row without Person aboutness, according to the ontologist's answer; never hardcode a fallback. |
| Death participant | conditionally admitted | Requires both the accepted Death-code pin and unique canonical Person resolution. |

The choice concerns identity resolution only. It introduces no new universal,
object property, data property, or equivalence assertion.
