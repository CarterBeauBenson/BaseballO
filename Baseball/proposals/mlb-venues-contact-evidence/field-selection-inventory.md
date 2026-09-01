# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| 'location.phone' | authoritative duplicate; excluded by default | Admit only after a DSQ and endpoint/numbering-system model are accepted. |
| venue 'id' | identity/join-only | Does not make the Venue the telephone endpoint or operator. |
| address country | nearby evidence, not sufficient | Cannot silently determine numbering normalization or endpoint identity. |
| operator Organization | not identified by phone string | No ownership/control assertion. |
| null/absent phone | resolved absence | Emit nothing. |

Potential class gap: a telephone-number identifier or contact-channel pattern
only if admitted. No new object property is currently justified.

