# Authority RDF query modules

This catalog provides small reusable SPARQL graph patterns over source-owned,
promoted RDF. It is intentionally separate from the MLB-game query-index
catalog: identity and persistent-entity attributes come from authority graphs,
while event analytics come from the disposable per-game index.

The nodes preserve BaseballO's accepted semantic shapes. For example,
`height-quality` binds a Height quality inhering in a Person and
`decimal-measurement` binds the Measurement ICE, value, and unit that measure
that quality. `proper-name` binds the Proper Name ICE that designates an entity
and its text. Neither node flattens those structures into direct Person
properties.

## Available primary grains

| Node | Owning source graphs |
| --- | --- |
| `person` | MLB People |
| `organization` | MLB Teams, Leagues, and Divisions |
| `venue` | MLB Venues |
| `calendar-date-day` | MLB People, Leagues, and Transaction evidence |

Reusable enrichments cover proper names, nicknames, provider identifiers,
height, mass, numeric measurement ICEs, batting/throwing dispositions and their
nominal measurements, position descriptions, venue coordinates, capacity, and
playing surfaces. Each catalog entry declares its required and provided
variables, allowed source modules, cardinality, and exact fragment hash.

## Composition rules

- A query uses one primary grain and an ordered list of allowlisted
  enrichments.
- Every enrichment's inputs must already be bound, and no node may rebind an
  existing variable.
- All selected nodes must share at least one approved source lane. The compiler
  calculates that intersection and requires the query spec to declare it
  exactly.
- Graph IRIs must belong to the selected source prefixes. Unscoped compilation
  emits an explicit prefix filter; bounded execution emits concrete or
  `VALUES`-scoped graph clauses.
- Every result projects `authorityGraph`, and every SQL key contains it.
  Rematerialization uses `replace-source-graph`, so corrections do not append a
  second current version of the same graph partition.
- Modules are mandatory graph patterns. Optional UI attributes should be
  materialized as separate grains and joined in SQL, not combined into one
  cross-product-heavy query.

The checked-in specifications demonstrate People names, People heights,
Organization names, and Venue capacities. They are compilation contracts, not
automatic UI-route admission. NiFi should run admitted specifications after
their source graphs promote, store the resulting reusable grains, and record
the compiler manifest. UI routing still requires end-to-end RDF/SQL
equivalence for the consuming feature.
