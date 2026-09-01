# Field selection and identity inventory

| Evidence | Disposition | Consequence |
| --- | --- | --- |
| `officialDate` | additional local baseball-date evidence | Calendar Date Identifier designates the venue-local official Day. |
| game UTC `dateTime` | already supplied temporal evidence | Preserve UTC instant evidence and its reference system independently. |
| venue IANA time zone | authority-backed reference evidence | Use for local conversion; do not replace the source UTC value. |
| transaction `date`, `effectiveDate`, `resolutionDate` | institutional Day evidence | Preserve each field identity; no timezone or exact instant is invented. |
| canonical Day IRI | source-neutral identity | Key by reviewed temporal-reference-system and interval identity, never provider. |
| daily named graph | derived operational product | Replace atomically per source/day; retain manifests and provenance. |

No class or property IRI is proposed.

