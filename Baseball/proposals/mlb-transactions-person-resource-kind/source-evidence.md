# Source and repository evidence

The accepted transaction source contract says that `person.id` conditionally
joins a row to the canonical Person and that the lane does not publish Person
types or names. Its Mermaid diagram labels the target simply `Person`. The
accepted people source contract, however, keys Person IRIs by both MLB person
resource kind and provider ID and preserves the established `player` and
`person` path kinds already used by MLB-game RDF.

The current transaction implementation makes a stronger choice than that
review record:

- `Baseball/sources/mlb-transactions/mapping/prepare-context.py` constructs
  `https://baseballontology.org/data/player/{personId}` for row aboutness and
  for the optional Death participant;
- its IRI policy names only the player path; and
- its SHACL patterns allow only the player path for transaction Persons.

No checked-in accepted source evidence establishes that the transaction
endpoint excludes officials, managers, coaches, or any other Person whose
canonical graph identity uses the `person` path. A fixture containing a player
cannot prove a population-wide endpoint guarantee.

Option A therefore requires corpus or authoritative provider evidence for the
endpoint guarantee. Option B instead reuses the already promoted identifier
designation pattern as the resolution input. That resolution must occur at
the authoritative integration boundary and must not make transaction RML or
source SHACL consume another module's mapping, SHACL, or raw payload.
