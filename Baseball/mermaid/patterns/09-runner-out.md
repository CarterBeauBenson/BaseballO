# Runner out

```mermaid
flowchart LR
    SOURCE["RunnerOutSource<br/>runners[ movement.isOut = true ]"] --> ACTMAP["RunnerOutActMap"]
    SOURCE --> RESMAP["RunnerOutResolutionMap"]
    SOURCE --> RECORDMAP["RunnerOutRecordMap"]

    ACTMAP --> ACT["/runner-act/out/{runner}/{playIndex}/{eventType}/{outBase}/{outNumber}<br/>a BaserunningAct"]
    ACT -->|"has agent"| RUNNER["/player/{runner.id}"]
    ACT -->|"realizes"| ROLE["/player/{runner.id}/role/baserunner<br/>a BaserunnerRole"]
    ROLE -->|"inheres in"| RUNNER
    ACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    ACT -->|"occurrent part of"| GAME["BaseballGame"]

    RESMAP --> OUT["/runner-resolution/out/{same composite key}<br/>a RunnerResolutionProcess<br/>a OutProcess"]
    OUT -->|"asserted: preceded by"| ACT
    OUT -->|"has participant"| RUNNER
    OUT -->|"occurs at"| FIELD
    OUT -->|"occurrent part of"| GAME

    RECORDMAP --> RECORD["/runner-record/out/{same composite key}<br/>a BaseballEventRecord"]
    RECORD -->|"is about"| OUT
    RECORD -->|"dcterms:identifier"| TYPE["details.eventType"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    ACT -.->|"no plate-appearance link"| PA["PlateAppearance"]
    ACT -.->|"out is embedded in act IRI"| BAKED["Outcome-dependent act identity"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,ACTMAP,RESMAP,RECORDMAP source;
    class ACT act;
    class OUT,RECORD outcome;
    class PA,BAKED gap;
```

## Evaluation

The class separation is good: the runner performs a neutral `BaserunningAct`,
and a distinct `OutProcess` records the unsuccessful institutional resolution.
However, the act is selected only from an out record and its IRI contains
`/out/`. Success is therefore absent from the class but baked into identity.

The act and resolution are parts of the game rather than the enclosing plate
appearance. This prevents direct traversal from a runner out to the batter act
and plate-appearance result that supplied its play context.
