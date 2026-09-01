# Source-independent connector boundaries

```mermaid
flowchart LR
  TAPI[MLB Teams endpoint] --> TACQ[Teams acquisition]
  TACQ --> TRML[Teams RML]
  TRML --> TSHACL[Teams SHACL]
  TSHACL --> TGRAPH[Teams authority graph]

  LAPI[MLB Leagues endpoint] --> LACQ[Leagues acquisition]
  LACQ --> LRML[Leagues RML]
  LRML --> LSHACL[Leagues SHACL]
  LSHACL --> LGRAPH[Leagues authority graph]

  DAPI[MLB Divisions endpoint] --> DACQ[Divisions acquisition]
  DACQ --> DRML[Divisions RML]
  DRML --> DSHACL[Divisions SHACL]
  DSHACL --> DGRAPH[Divisions authority graph]

  TGRAPH --> KG[Authoritative triple store]
  LGRAPH --> KG
  DGRAPH --> KG

  ENGINE[Source-neutral NiFi stage engine] -. mechanics only .-> TACQ
  ENGINE -. mechanics only .-> LACQ
  ENGINE -. mechanics only .-> DACQ
```

Solid paths are independently stoppable source lifecycles. The dotted reuse is
limited to source-neutral execution mechanics. No RML, SHACL, transient input,
quarantine, or graph namespace crosses a solid lane boundary.
