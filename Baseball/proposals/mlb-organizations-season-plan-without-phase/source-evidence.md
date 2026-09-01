# Source and repository evidence

The accepted MLB organizations contract identifies a Baseball Season and
Baseball Season Plan by `(MLB league ID, season code)`. It creates only the
regular-season and postseason Phase individuals, and only when the matching
start and end dates are both present and valid. Null and absent optional
selected fields are permitted.

The current executable context builder implements these rules in two separate
steps:

- `Baseball/sources/mlb-leagues/mapping/prepare-context.py` adds a
  Season record whenever it resolves a league ID and season code; and
- it adds a Phase record only when both fields of a reviewed pair are present.

The current source SHACL profile then requires every emitted Baseball Season
Plan to prescribe at least one Baseball Season Phase. Consequently, a valid
response with a season code and no complete accepted pair yields a mapped Plan
that the same module rejects.

The accepted ontology defines Baseball Season as a BFO Process, Baseball
Season Phase as a BFO Process, and Baseball Season Plan as a CCO Plan that
prescribes some Baseball Season and some Baseball Season Phase. Option B does
not deny that existential structure; it asks whether one source graph may be
locally incomplete. Option A asks the source mapping to withhold the typed
subgraph until the accepted local evidence is present.

This is a source-evidence and closed-validation decision. It does not reopen
the classification of Season as Process, invent a generic season act, infer a
League participant, or authorize a temporal boundary relation.
