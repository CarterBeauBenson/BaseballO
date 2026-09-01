# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| Team/League/Division `active` | authoritative duplicate; provider metadata | Exclude from world-side Organization status. |
| League `seasonState` | genuinely additional provider state; unresolved | Manifest or information-only unless exact Season Plan semantics are documented. |
| Team `allStarStatus` | authoritative duplicate; unresolved code | Exclude pending a DSQ, code list, bearer, and time scope. |
| resource IDs | identity/join-only | Join the provider record to the canonical Organization. |
| retrieval time/hash | provenance | Required if provider-state evidence is retained. |
| null/absent value | resolved absence | Emit nothing. |

No class or object-property gap exists under the proposed manifest-only policy.
Any world-side institutional history requires a separate evidenced proposal.
