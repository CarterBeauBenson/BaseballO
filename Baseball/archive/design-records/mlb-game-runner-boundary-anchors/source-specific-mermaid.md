# Proposed owning-source projection

```mermaid
flowchart TD
  Source["Complete final MLB game feed"] --> Inventory["Exhaustive runner/event census"]
  Inventory --> Action["Unique actionPlayId + event kind + outcome runner"]
  Inventory --> PR["Explicit PR: half + outgoing + incoming Persons"]
  Inventory --> Placed["Explicit placement: half + Person"]
  Action --> Check["Reconcile outcomes, membership, boundaries and corrections"]
  PR --> Check
  Placed --> Check
  Check -->|"supported"| Key["C3 token in existing C1 lifetime key"]
  Check -->|"ambiguous"| Gap["Retained unresolved lifetime; population withheld"]
  Key --> RML["Existing source-owned personal-history RML"]
  RML --> SHACL["Owning SHACL: exact same-person episode/half/interval membership"]
  SHACL --> Promotion["NiFi graph-pair promotion with bound proof"]
  Promotion --> Query["SPARQL, SQL and existing metric consumers"]
```

Arrows here show processing dependencies, not proposed RDF predicates. The
source module and accepted API -> RML -> SHACL -> Fuseki -> query -> SQL -> UI
lifecycle are unchanged. No executable C3 implementation exists before review.
