# Source-specific review projection

This diagram describes selection and validation steps, not ontology predicates.
It changes neither the module boundary nor the accepted lifecycle.

```mermaid
flowchart TD
  A[Final MLB game revision and complete source census]
  B[Every PA event and runner join accounted for]
  C[M3: explicitly neutral prefix or consistent completed operative review]
  D[M4: explicit counted foul bunt with actual bunt/contact support]
  E[Existing pitch-scoped Strike Process, judgment, decision and rule pattern]
  F[Owning source SHACL plus exact source-to-RDF census]
  G[Existing graph-pair promotion]
  H[Existing queries, SQL and metric population gates]
  A --> B
  B --> C
  B --> D
  C --> E
  D --> E
  E --> F
  F --> G
  G --> H
```

For game 824087, candidate pitch IDs come from PA/event pairs 37/3, 64/2,
65/2 and 72/0. Exact identities are retained in `source-capture.json`.
Unsupported prefixes stay withheld. The final review call supports the
operative count; this does not create an original review judgment.
