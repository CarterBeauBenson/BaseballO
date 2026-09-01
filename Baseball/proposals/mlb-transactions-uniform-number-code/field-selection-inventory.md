# Field inventory and de-duplication

| Field/evidence | Disposition | Consequence |
| --- | --- | --- |
| exact Number Change code | genuinely additional; information-only | Preserve provider classification. |
| description | unstructured number evidence | Do not parse without separate extraction review. |
| `person.id` | identity/join-only | Does not make the number intrinsic to Person. |
| Team IDs | optional evidence | Do not infer assignment Agent/context from mention alone. |
| effective date | candidate Day evidence | Does not create an assignment interval or Role boundary. |

Boundary consequence: none for continuous Player Role identity. A later
accepted assignment may change only the Role's Code Identifier designation.
