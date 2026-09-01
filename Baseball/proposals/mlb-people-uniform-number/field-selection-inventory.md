# Field inventory and de-duplication

| Field or evidence | Disposition | Design consequence |
| --- | --- | --- |
| 'primaryNumber' | authoritative duplicate; blocked | Never a Person quality or globally stable identifier. |
| person 'id' | identity/join-only | Identifies the bearer of an independently established Player Role. |
| 'currentTeam.id' | identity/join-only; temporally unresolved | Insufficient by itself to identify a stint or assignment act. |
| transaction Number Change description | separate source; unstructured | Cannot be parsed into a Code Identifier without a reviewed extraction contract. |
| roster/game number evidence | separate source grains | May corroborate a time-bounded designation after source ownership is reviewed. |
| null/empty number | absence or invalid input | Null emits nothing; a present empty value fails input validation. |

No class or object-property gap exists. The blocker is Player Role/stint
identity plus source evidence for assignment and temporal scope.

