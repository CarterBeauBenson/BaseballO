# Field inventory and de-duplication

| Field family | Disposition | Consequence |
| --- | --- | --- |
| address line strings | authoritative duplicate; blocked | Candidate exact Address ICE content only after address identity/structure is accepted. |
| city/state/country strings | authoritative duplicate; blocked | Never mint geographic entities from text alone. |
| state abbreviation/postal code | authoritative duplicate; unresolved | Candidate identifiers only under pinned systems and target regions/sites. |
| venue 'id' | identity/join-only | Reuse canonical Venue; does not make it identical to an Address or Site. |
| request season/response hash | provenance | Versions evidence without inventing a validity interval. |
| null/absent component | resolved absence | No placeholder, empty literal, or unknown entity. |

Potential class gap: source-independent Postal/Street Address ICE with an
identity criterion and designation target. No new object property is proposed.

