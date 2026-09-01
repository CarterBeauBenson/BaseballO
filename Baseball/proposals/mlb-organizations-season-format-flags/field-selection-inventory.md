# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| `hasWildCard`, `hasSplitSeason`, `hasPlayoffPoints`, related flags | genuinely additional; unresolved | Block until each flag's Directive ICE meaning and false semantics are accepted. |
| season/league identifiers | identity/join-only | Reuse accepted Season and Plan scope. |
| organization nesting | owned by membership proposals | Do not encode affiliation here. |
| null/absent optional flag | resolved absence | Emit nothing. |

Potential class gap: source-independent format-directive content. No object
property gap is demonstrated.
