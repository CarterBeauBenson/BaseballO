# Competency questions

| ID | Question | Accepted answer |
| --- | --- | --- |
| TWO-WAY-01 | What does MLB primary-position code `Y` describe? | A Person who bears both a persistent Pitcher Role and a persistent Fielder Role. |
| TWO-WAY-02 | Does the code establish a primitive Two-Way Player class? | No. The provider description is about the Person and the two Roles. |
| TWO-WAY-03 | What is the identity scope of the entities? | The Position Description is response-scoped; the Pitcher Role and Fielder Role use the Person's persistent Role identities. |
| TWO-WAY-04 | Does the people response establish realization? | No. Realization requires evidence of an appropriate Process or Act and is not asserted from the position description. |

## Negative tests

- Code `Y` never types the Person as a source-shaped player subclass.
- The Position Description never realizes either Role.
- The mapping never mints response-scoped Pitcher or Fielder Roles.
- The two Roles must inhere in the same Person described by the Position Description.
