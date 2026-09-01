# MLB people uniform number

Status: **under review — design only**

BaseballO already has Uniform Number Assignment Act, Code Identifier, Player
Role, Baseball Team, and the accepted relations needed for a realist uniform
number assignment. The unresolved issue is evidence: a person record's
'primaryNumber' is a current-looking snapshot and does not itself identify the
assignment Act, Team agent, or effective interval.

This package asks whether the field may support only an information-level
number designation, whether it must wait for transaction/roster evidence, and
how repeated team stints affect the designated Player Role. It does not create
a number quality of the Person.

The field already appears in the MLB game payload. No executable change is
authorized.
