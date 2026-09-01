# Source-independent consumer shape

```mermaid
flowchart LR
  Record[Event Record ICE] -->|is about| World[Real-world entity or Process]
  Identifier[Identifier ICE] -->|designates| Record
  Nominal[Nominal Classification ICE] -->|designates| World
  Nominal -->|uses reference system| Reference[Versioned Reference System]
  World --> Index[Rebuildable query-index fact]
  Nominal -->|current selection only| Index
  Index --> SQL[Persistent derived SQL grain]
  SQL --> Explorer[Routine Explorer]
  World --> Research[Live research SPARQL]
  Reference --> Research
```

Historical nominal evidence remains queryable in the authoritative graph. The
arrow from nominal evidence to the query index is a current-state selection,
not an OWL equivalence and not a claim that historical classifications vanish.
