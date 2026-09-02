# Source-independent Mermaid

Solid edges are the proposed required shape. The weather branch is deliberately
dashed until a weather source supplies world-side causal evidence.

```mermaid
flowchart LR
    MLB[MLB Organization]
    ACT[Baseball Game Postponement Act]
    OLD[Input Baseball Game Schedule Plan]
    NEW[Output Baseball Game Schedule Plan]
    OLDID[Original Temporal Interval Identifier]
    NEWID[Revised Temporal Interval Identifier]
    OLDT[Original planned Temporal Interval]
    NEWT[Revised planned Temporal Interval]
    GAME[one Baseball Game]
    REASON[Nominal Measurement ICE]
    RS[MLB postponement-reason Reference System]
    PERF[Game-contained player Processes and Acts]
    WEATHER[future weather Process or Quality]

    ACT -->|has agent| MLB
    ACT -->|has input| OLD
    ACT -->|has output| NEW
    OLD -->|prescribes| GAME
    NEW -->|prescribes| GAME
    OLD -->|has continuant part| OLDID
    NEW -->|has continuant part| NEWID
    OLDID -->|designates| OLDT
    NEWID -->|designates| NEWT
    OLDT -->|precedes| NEWT
    REASON -->|is a measurement of| ACT
    REASON -->|uses reference system| RS
    GAME -->|has occurrent part| PERF
    WEATHER -. future corroboration .->|is cause of| ACT
```

The same-Game constraint on the input and output Plans is identity-bearing. It
must later be enforced in source SHACL and tested with SPARQL; two unrelated
Plans as input and output do not satisfy this pattern.

The Act need not precede the whole Game in every possible postponement case. A
game may have begun before being postponed. Pregame temporal ordering may be
asserted only when the evidence establishes it.
