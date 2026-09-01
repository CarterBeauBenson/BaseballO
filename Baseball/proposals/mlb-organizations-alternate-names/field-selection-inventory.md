# Field inventory and de-duplication

| Field | Disposition | Consequence |
| --- | --- | --- |
| canonical 'name' | already mapped | No change here. |
| 'teamName', 'clubName' | authoritative duplicate; unresolved | Candidate Proper Names only after bearer/name kind review. |
| 'franchiseName' | duplicate; bearer unresolved | Block until Team versus franchise-continuity identity is decided. |
| 'locationName' | duplicate; ambiguous component | Do not treat text as a geographic identity. |
| 'shortName', 'nameShort' | duplicate; unresolved | Candidate alternate names, not automatically preferred/official. |
| assembled display label | derived | Build in serving/UI from accepted names. |
| null/absent value | resolved absence | Emit nothing. |

No class or object-property gap exists for an accepted alternate Proper Name.
A franchise-continuity entity would be a separate genuine class/identity gap.

