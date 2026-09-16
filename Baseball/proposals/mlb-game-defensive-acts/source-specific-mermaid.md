# D1 MLB projection (review only)

```mermaid
flowchart TD
  Source["Existing immutable MLB payload"]
  Contact["Unique supported contact playId"]
  Text["Final description plus matching runner/credit evidence"]
  Selection["Reconciled particular performances and exact witnesses"]
  RML["Owning mlb-game RML"]
  Graph["Existing batted play, Persons and persistent Fielder Roles; particular acts"]
  Check["Owning source SHACL: exact act / agent / role / order census"]
  Promotion["Existing graph-pair promotion"]
  Query["Canonical existing-term SPARQL"]
  SQL["Exact participating-player means, gated by complete population and roster"]
  Source --> Contact
  Source --> Text
  Contact --> Selection
  Text --> Selection
  Selection --> RML
  RML --> Graph
  Graph --> Check
  Check --> Promotion
  Promotion --> Query
  Query --> SQL
```

This illustrates the already accepted lifecycle, not a new lane or an RDF
schema. Selection is proposed for review; no executable D1 selector or RML
is installed by this package. Whole-play completeness is a separate positive
proof, and unselected plays remain visible to its census.
