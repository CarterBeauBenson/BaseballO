# MLB transaction Person resource-kind resolution

Status: **under review — design only**

This package asks how `person.id` in an MLB transaction row resolves to the
canonical BaseballO Person IRI. The accepted MLB people identity policy
preserves two established canonical path kinds, `data/player/{id}` and
`data/person/{id}`. The current transaction implementation always constructs
`data/player/{id}`, but the accepted transaction review calls the target only
the canonical Person and contains no evidence that every transaction Person
must have the `player` resource kind.

The decision is between:

- **Option A — provider guarantee:** accept only after evidence establishes
  that transaction `person.id` always identifies a player-kind Person, making
  `data/player/{id}` the reviewed deterministic identity; or
- **Option B — authority resolution:** resolve the ID against promoted
  canonical Person identifiers and pass the unique canonical Person IRI into
  the transaction execution context. RML consumes that IRI and never
  hardcodes a resource kind.

This package proposes no new class or property. It does not authorize a
cross-source RML file, a Person type or name assertion in the transactions
graph, or a Player Role inference. Until one option and its unresolved-identity
behavior are accepted, corpus transaction promotion must not treat the
hardcoded `/player/` choice as an established semantic fact.
