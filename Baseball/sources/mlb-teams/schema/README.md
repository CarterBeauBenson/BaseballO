# Selected MLB Teams contract

The connector accepts a strict UTF-8 object with a non-empty `teams` array. A
root Team requires a positive `id`; selected optional values are canonical
`name`, `league.id/name`, `division.id/name`, and `sport.id` for the existing
MLB baseball guard. Other response fields remain unmapped.

Null optional fields emit nothing. Invalid identifiers, duplicate JSON keys,
invalid Unicode, non-finite numbers, or a non-MLB sport quarantine the input.
The execution context is `teams-context.json`; it is transient and is not a
semantic authority.
