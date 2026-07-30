# Counted hit

\`\`\`mermaid
flowchart LR
    ACT["SwingAct or BuntAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| HIT["Single, Double, Triple, or HomeRun result individual"]
    HIT -->|"has occurrent part"| J["HitJudgmentAct"]
    J -->|"has participant"| SCORER["Official scorer"]
    J -->|"realizes"| ROLE["game-scoped OfficialScorerRole"]
    J -->|"has input"| RULE["HitRule"]
    J -->|"has output"| D["HitDecisionICE"]
    D -->|"is about"| HIT
\`\`\`

The most specific hit class is added to the one plate-appearance result individual. No duplicate parent HitProcess individual is minted.
