# Field inventory and de-duplication

| Field | Disposition | Consequence |
| --- | --- | --- |
| 'teamCode' | authoritative duplicate; unresolved | Candidate Code Identifier under its own provider system. |
| 'fileCode' | duplicate; navigation/code ambiguity | Exclude unless provider semantics prove an identifier. |
| Team/League/Division 'abbreviation' | duplicate; unresolved | Review target and system per resource family. |
| League 'orgCode' | duplicate; unresolved | Candidate Code Identifier under a distinct system. |
| resource IDs | already mapped identity | Do not replace canonical MLB numeric identifiers. |
| link/path tokens | identity/join-only or navigation | Never treat as domain codes. |
| null/absent code | resolved absence | Emit nothing. |

No class or object-property gap is demonstrated. Reference System individuals
require source-specific review but are not proposed ontology IRIs.

