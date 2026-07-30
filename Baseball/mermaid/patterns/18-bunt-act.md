# Source-supported bunt

\`\`\`mermaid
flowchart LR
    SOURCE["plate appearance result.eventType = sac_bunt"] --> BUNT["BuntAct"]
    BUNT -->|"has participant"| BATTER["Batter person"]
    BUNT -->|"realizes"| ROLE["game-scoped BatterRole"]
    BUNT -->|"has participant"| BAT["BaseballBat"]
    BUNT -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| RESULT["SacrificeBuntProcess"]
\`\`\`

For sac_bunt results, the terminal in-play pitch is excluded from the generic SwingAct sources and mapped as BuntAct.
