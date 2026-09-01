# Source and repository evidence

The current MLB game payload includes embedded team, person, and venue
descriptions. The accepted organization, people, and venue proposal inventories
therefore classified much of the standalone endpoint surface as an
authoritative duplicate rather than a new assertion type.

The current game RML emits reference types, identifiers, names, and venue field
site facts in the same graph as game events. Existing SPARQL, query-index, and
serving queries also obtain several labels from MLB-game graphs. Consequently,
ownership cannot be changed by merely adding four new mappings or deleting
triples from the game mapping.

On 2026-08-29 the ontologist approved the following division:

- `mlb-game` owns game and event facts and canonical identity links;
- `mlb-organizations` owns organization and season reference facts;
- `mlb-people` owns person reference and descriptive facts;
- `mlb-venues` owns venue reference and physical facts; and
- `mlb-transactions` owns transaction records and supported processes.

This is compatible with the repository's detachable-source architecture: raw
API payloads remain transient, every source validates and promotes
independently, and cross-source integration occurs only in the authoritative
triple store. It also requires a coordinated compatibility cutover because
routine queries must continue to return canonical IDs even when a reference
module is disconnected or a label is temporarily unavailable.
