# Human acts not instantiated by the direct RML

```mermaid
flowchart TB
    FIELDING["FieldingCreditSource"] --> FROLE["FielderRoleMap<br/>FielderRole inheres in player"]
    FROLE -.->|"no stable credit identity / parent context"| FACT["FieldingAct not mapped"]

    OFFICIAL["OfficialSource"] --> UROLE["UmpireRoleMap<br/>UmpireRole inheres in person"]
    BALL["Ball / Strike / Fair / Foul / Out / Safe / Run processes"] -.->|"ontology meanings require adjudication parts"| JUDGMENTS["Judgment acts not mapped"]
    UROLE -.->|"role not realized in a mapped judgment act"| JUDGMENTS

    SCORER["gameData.officialScorer"] --> SROLE["OfficialScorerRoleMap"]
    SROLE -.->|"no scoring-judgment act instance"| SCOREACT["ScoringJudgmentAct not mapped"]

    INPLAY["In-play codes X/D/E"] --> SWING["Always maps SwingAct"]
    INPLAY -.->|"bunt evidence not distinguished"| BUNT["BuntAct not mapped"]

    RUNNER["Runner records, including stolen_base event types"] --> BRACT["Generic BaserunningAct"]
    RUNNER -.->|"specific attempt and resolution absent"| STEAL["StealAttemptAct and StolenBaseProcess not mapped"]

    PITCH["PitchAct"] -.->|"physical motion layer absent"| PMOTION["PitchBallMotionProcess not mapped"]

    classDef source fill:#e8eef9,stroke:#4f6fa8,color:#17233a;
    classDef present fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef gap fill:#fde2e2,stroke:#a33,color:#4a1111,stroke-dasharray:5 5;
    class FIELDING,OFFICIAL,SCORER,INPLAY,RUNNER source;
    class FROLE,UROLE,SROLE,SWING,BRACT,PITCH present;
    class FACT,JUDGMENTS,SCOREACT,BUNT,STEAL,PMOTION gap;
```

## Evaluation

- Fielding credits currently license only a career `FielderRole`; no person is
  connected as agent of a fielding act.
- Umpires and the official scorer bear roles, but those roles have no mapped
  realization in judgment acts. Institutional result processes are typed
  without explicit judgment-act parts in the instance graph.
- Every X/D/E event becomes `SwingAct`. If the source includes bunts under
  those codes, the mapping overstates swinging and misses `BuntAct`.
- Stolen-base ontology concepts exist, but the direct runner mapping remains
  generic and relies on source identifiers for stolen-base queries.

These are mapping and source-identity gaps. They are not authorization to alter
the ontology; the repository guardrail leaves ontology decisions to the owner.
