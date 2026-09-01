# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| 'mlbDebutDate' | authoritative duplicate; information/diagnostic | Do not create a Debut Act or Game identity from a date alone. |
| authoritative Game participation | richer persistent RDF | Candidate basis for a derived earliest qualifying participation view. |
| Person 'id' | identity/join-only | Reuse canonical Person. |
| date lexical value | provider evidence | Validate before any mapping; null emits nothing. |
| time since debut | derived | Calculate downstream from accepted date/query time. |

No Debut class gap is established if debut remains a derived first-
participation view. No object property is proposed.

