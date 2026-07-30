# Called ball

\`\`\`mermaid
flowchart LR
    PITCH["PitchAct"] -->|"precedes"| MOTION["PitchBallMotionProcess"]
    MOTION -->|"precedes"| BALL["BallProcess"]
    BALL -->|"has occurrent part"| J["BallJudgmentAct"]
    J -->|"has participant"| U["Home-plate umpire"]
    J -->|"realizes"| UR["game-scoped UmpireRole"]
    J -->|"has input"| RULE["BallRule"]
    J -->|"has output"| D["BallDecisionICE"]
    D -->|"is about"| BALL
    J -->|"precedes"| CALL["BallCallAct"]
    CALL -->|"has input"| D
    RECORD["Pitch Event Record"] -->|"is about"| PITCH
    RECORD -->|"is about"| MOTION
    RECORD -->|"is about"| BALL
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
    RECORD -->|"is about"| CALL
\`\`\`

Codes B and *B share this implemented pattern. Ball-in-dirt remains a ball classification; it does not create a different act type.
