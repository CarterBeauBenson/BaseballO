# Batter act

```mermaid
flowchart LR
    SOURCE["PlaySource<br/>$.liveData.plays.allPlays[*]"] --> MAP["BatterActMap"]
    MAP --> ACT["/game/{gamePk}/plate-appearance/{atBatIndex}/batter-act<br/>a BatterAct"]

    ACT -->|"has agent"| BATTER["/player/{batter.id}"]
    ACT -->|"realizes"| ROLE["/player/{batter.id}/role/batter<br/>a BatterRole"]
    ROLE -->|"inheres in"| BATTER

    ACT -->|"occurs at"| FIELD["/venue/{venue.id}/baseball-field<br/>a BaseballFieldSite"]
    FIELD -->|"located in"| VENUE["/venue/{venue.id}<br/>a BaseballVenue"]

    ACT -->|"occurrent part of"| PA["PlateAppearance"]
    PA -->|"occurrent part of"| HALF["HalfInning"]
    HALF -->|"occurrent part of"| INNING["Inning"]
    INNING -->|"occurrent part of"| GAME["BaseballGame"]

    RESULT["Plate-appearance result process<br/>success or failure"] -->|"occurrent part of"| PA
    ACT -.->|"no result relation emitted"| RESULT

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef act fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef outcome fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef context fill:#f3e8ff,stroke:#805ad5,color:#2d1b4e;
    class SOURCE,MAP source;
    class ACT act;
    class RESULT outcome;
    class BATTER,ROLE,FIELD,VENUE,PA,HALF,INNING,GAME context;
```

## Evaluation

- The act class and IRI are outcome-neutral: the same pattern is used whether
  the batter later hits, walks, strikes out, or records another result.
- Person, role, location, and plate-appearance containment are all explicit and
  directionally correct.
- A separate `SwingAct` individual may occur in the same plate appearance, but
  it is not related to this overall batter-act individual. Both independently
  point to the plate appearance, batter, role, and field site.
- Because `SwingAct` is already a subclass of `BatterAct`, the intended identity
  and parthood distinction between this broad act and each swing needs review.
