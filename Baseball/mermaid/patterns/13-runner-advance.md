# Runner advances safely from a recorded base

```mermaid
flowchart LR
    SOURCE["RunnerAdvanceSource<br/>not out; start = 1B/2B/3B;<br/>end is not score"] --> ACTMAP["RunnerAdvanceActMap"]
    SOURCE --> RESMAP["RunnerAdvanceResolutionMap"]
    SOURCE --> RECORDMAP["RunnerAdvanceRecordMap"]

    ACTMAP --> ACT["/runner-act/advance/{runner}/{playIndex}/{eventType}/{start}/{end}<br/>a BaserunningAct"]
    ACT -->|"has agent"| RUNNER["Runner person"]
    ACT -->|"realizes"| ROLE["BaserunnerRole"]
    ROLE -->|"inheres in"| RUNNER
    ACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    ACT -->|"occurrent part of"| GAME["BaseballGame"]

    RESMAP --> SAFE["/runner-resolution/advance/{same composite key}<br/>a RunnerResolutionProcess<br/>a SafeProcess"]
    SAFE -->|"asserted: preceded by"| ACT
    SAFE -->|"has participant"| RUNNER
    SAFE -->|"occurs at"| FIELD
    SAFE -->|"occurrent part of"| GAME

    RECORDMAP --> RECORD["/runner-record/advance/{same composite key}"]
    RECORD -->|"is about"| SAFE
    RECORD -->|"dcterms:identifier"| TYPE["details.eventType"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    ACT -.->|"no plate-appearance link"| PA["PlateAppearance"]
    ACT -.->|"advance embedded in act IRI"| BAKED["Outcome-shaped act identity"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,ACTMAP,RESMAP,RECORDMAP source;
    class ACT act;
    class SAFE,RECORD outcome;
    class PA,BAKED gap;
```

## Evaluation

This is materially distinct from reach because both starting and ending bases
participate in identity. As with reach, successful status is represented by a
separate `SafeProcess`, but the act path still depends on the movement category
and the RML has no direct plate-appearance edge.
