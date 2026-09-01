# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| `numGames`, `numTeams` | genuinely additional candidate; unresolved | Distinguish planned target from observed total and identify the scoped grain. |
| wildcard/playoff-team counts | genuinely additional candidate; unresolved | Require qualification semantics and phase scope. |
| authoritative Games/memberships | richer RDF/derived | Prefer for observed totals when complete. |
| season/league IDs | identity/join-only | Reuse accepted identities. |
| null/absent value | resolved absence | Emit nothing. |

No object-property gap is demonstrated. Specialized planned-count content is a
class question only after field semantics are established.
