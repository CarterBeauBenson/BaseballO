# Field inventory and de-duplication

| Field | Disposition | Consequence |
| --- | --- | --- |
| 'timeZone.id' | authoritative duplicate; potentially mappable | Candidate Time Zone Identifier under a pinned IANA Reference System. |
| 'timeZone.tz' | authoritative duplicate; unresolved | Abbreviation/alias and temporal semantics required. |
| 'timeZone.offset' | authoritative duplicate; blocked | Do not assert without an observation/reference time. |
| 'offsetAtGameTime' | authoritative duplicate; blocked | Requires a particular Game/reference instant and source-grain review. |
| venue 'id' | identity/join-only | Reuse canonical Venue. |
| null/absent value | resolved absence | Emit nothing. |
| unknown identifier/malformed offset | invalid if admitted | Quarantine before RML. |

No class or object-property gap is demonstrated. The blocker is identifier
system and temporal reference evidence.

