# Source-independent implementation boundary

```mermaid
flowchart LR
  Evidence[Authoritative MLB-game RDF] --> Gate[Source SHACL]
  Gate --> Index[Rebuildable indexed RDF]
  Index --> Equivalence[Equivalence checks]
  Equivalence --> SQL[Derived SQL serving grains]
  Evidence --> Research[Live research SPARQL]
  SQL --> Explorer[Routine Explorer]
```

The arrows describe dependency and promotion order. They do not introduce ontology relations. The authoritative RDF remains persistent; the indexed RDF and SQL products remain rebuildable.
