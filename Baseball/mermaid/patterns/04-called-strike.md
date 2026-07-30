# Called strike

\`\`\`mermaid
flowchart LR
    PITCH["PitchAct"] -->|"precedes"| MOTION["PitchBallMotionProcess"]
    MOTION -->|"precedes"| STRIKE["StrikeProcess"]
    STRIKE -->|"has occurrent part"| J["StrikeJudgmentAct"]
    J -->|"has participant"| U["Home-plate umpire"]
    J -->|"realizes"| UR["game-scoped UmpireRole"]
    J -->|"has input"| RULE["StrikeRule"]
    J -->|"has output"| D["StrikeDecisionICE"]
    D -->|"is about"| STRIKE
    J -->|"precedes"| CALL["StrikeCallAct"]
    CALL -->|"has input"| D
    RECORD["Pitch Event Record"] -->|"is about"| PITCH
    RECORD -->|"is about"| MOTION
    RECORD -->|"is about"| STRIKE
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
    RECORD -->|"is about"| CALL
\`\`\`

Only source code C generates the explicit StrikeCallAct.
