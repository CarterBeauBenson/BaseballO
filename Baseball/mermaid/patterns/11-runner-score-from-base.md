# Runner scores from a recorded base

```mermaid
flowchart LR
    SOURCE["RunnerScoreBaseSource<br/>not out; end = score;<br/>start = 1B or 2B or 3B"] --> ACTMAP["RunnerScoreBaseActMap"]
    SOURCE --> RESMAP["RunnerScoreBaseResolutionMap"]
    SOURCE --> RECORDMAP["RunnerScoreBaseRecordMap"]

    ACTMAP --> ACT["/runner-act/score/{runner}/{playIndex}/{eventType}/{start}<br/>a BaserunningAct"]
    ACT -->|"has agent"| RUNNER["Runner person"]
    ACT -->|"realizes"| ROLE["BaserunnerRole"]
    ROLE -->|"inheres in"| RUNNER
    ACT -->|"occurs at"| FIELD["BaseballFieldSite"]
    ACT -->|"occurrent part of"| GAME["BaseballGame"]

    RESMAP --> RUN["/runner-resolution/score/{same composite key}<br/>a RunnerResolutionProcess<br/>a RunProcess"]
    RUN -->|"asserted: preceded by"| ACT
    RUN -->|"has participant"| RUNNER
    RUN -->|"occurs at"| FIELD
    RUN -->|"occurrent part of"| GAME

    RECORDMAP --> RECORD["/runner-record/score/{same composite key}"]
    RECORD -->|"is about"| RUN
    RECORD -->|"dcterms:identifier"| TYPE["details.eventType"]
    FIELD -->|"located in"| VENUE["BaseballVenue"]

    ACT -.->|"no plate-appearance link"| PA["PlateAppearance"]
    ACT -.->|"score embedded in act IRI"| BAKED["Outcome-dependent act identity"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class SOURCE,ACTMAP,RESMAP,RECORDMAP source;
    class ACT act;
    class RUN,RECORD outcome;
    class PA,BAKED gap;
```

## Evaluation

This is separate from the origin-score pattern because the starting base is a
material part of the composite identity. It still types the act neutrally and
the resolution as `RunProcess`, but the `/score/` act path encodes the result.
The repeated `&&`/`||` JSONPath filter also relies on processor operator
precedence and should remain in compatibility tests.
