# Source-independent Mermaid

Status: **under review — design only**

The diagrams use only accepted classes and relations. Solid semantic edges are
candidate RDF for the corresponding option, not authorized triples. Dashed
arrows point to decision or evidence gates and are not object properties.

## Option A — complete-pair gate

```mermaid
flowchart LR
    RESPONSE[MLB league response\nDescriptive ICE]
    CODE[League ID + season code]
    PAIR[Complete accepted Phase date pair]
    GATE{Both identity and\ncomplete-pair evidence?}
    SEASON[Baseball Season\nProcess]
    PLAN[Baseball Season Plan]
    PHASE[Baseball Season Phase\nProcess]

    RESPONSE -.-> CODE
    RESPONSE -.-> PAIR
    CODE -.-> GATE
    PAIR -.-> GATE
    GATE -.->|yes: admit subgraph| SEASON
    PLAN -->|prescribes| SEASON
    PLAN -->|prescribes| PHASE
    PHASE -->|occurrent part of| SEASON
```

If the complete pair is absent, none of `SEASON`, `PLAN`, or `PHASE` is
emitted from that response. The current SHACL minimum of one prescribed Phase
remains correct for every emitted Baseball Season Plan.

## Option B — season-code evidence with a locally incomplete graph

```mermaid
flowchart LR
    RESPONSE[MLB league response\nDescriptive ICE]
    CODE[League ID + season code]
    SEASON[Baseball Season\nProcess]
    PLAN[Baseball Season Plan]
    PAIR[Optional complete accepted\nPhase date pair]
    PHASE[Baseball Season Phase\nProcess]

    RESPONSE -.-> CODE
    CODE -.->|identity evidence| SEASON
    CODE -.->|identity evidence| PLAN
    PLAN -->|prescribes| SEASON
    RESPONSE -.-> PAIR
    PAIR -.->|when complete| PHASE
    PLAN -->|when emitted: prescribes| PHASE
    PHASE -->|when emitted: occurrent part of| SEASON
```

The absence of `PHASE` in one response graph is not an RDF assertion that the
Plan has no Phase. Source SHACL would allow zero locally asserted reviewed
Phases and continue to validate every Phase that is present.

## Invariants under both options

```mermaid
flowchart LR
    DATE[Calendar Date Identifier]
    DAY[Day]
    PHASE[Baseball Season Phase]
    BLOCK[No reviewed temporal\nboundary relation]

    DATE -->|designates| DAY
    DATE -.-> BLOCK
    DAY -.-> BLOCK
    BLOCK -.-> PHASE
```

Neither option licenses a Date-to-Phase or Day-to-Phase edge, a partial-pair
Phase, or an institutional membership assertion.
