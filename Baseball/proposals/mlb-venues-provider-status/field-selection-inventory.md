# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| 'active' | authoritative duplicate; provider metadata | Exclude from world-side RDF; optional provenance value only. |
| venue 'id' | identity/join-only | Joins the provider record to the Venue without transferring status semantics. |
| retrieval time/response hash | provenance | Required if information-layer status is ever retained. |
| physical closure/demolition/operation evidence | not supplied | No inference. |
| null/absent status | resolved absence | Emit nothing. |

No class or object-property gap exists under the proposed manifest-only
disposition. A later DSQ requiring provider-resource history would need a
separate information-layer proposal.

