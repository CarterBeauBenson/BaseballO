# Error classification

\`\`\`mermaid
flowchart LR
    ACT["SwingAct or BuntAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| ERROR["ErrorProcess result individual"]
    ERROR -->|"has occurrent part"| J["ErrorJudgmentAct"]
    J -->|"has participant"| SCORER["Official scorer"]
    J -->|"realizes"| ROLE["OfficialScorerRole"]
    J -->|"has input"| RULE["ErrorRule"]
    J -->|"has output"| D["ErrorDecisionICE"]
    D -->|"is about"| ERROR
    GAP["FieldingAttemptAct and BallControlFailureProcess"] -.->|"not inferred from result alone"| ERROR
\`\`\`

The scoring classification is mapped when result.eventType is field_error. Fielding acts remain absent until stable credit identity and ancestor context are available.
