# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| 'location.elevation' | authoritative duplicate; blocked | Admit only after Altitude semantics, bearer, unit, and datum are accepted. |
| venue 'id' | identity/join-only | Scopes evidence but does not identify the Altitude-bearing Site. |
| field dimension Foot fact | different field semantics | Does not prove elevation unit. |
| request season/response hash | provenance | Versions evidence; no season-long assertion. |
| null/absent value | resolved absence | Emit no Altitude subgraph. |
| malformed present value | invalid if admitted | Quarantine before RML. |

Altitude and measurement classes already exist. Potential class/identity gap:
the specific venue/field reference Site that bears the Altitude. No new object
property is needed.

