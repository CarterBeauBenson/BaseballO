# In-play swing and fair batted-ball play

\`\`\`mermaid
flowchart LR
    SWING["SwingAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| RESULT["plate-appearance result"]
    MOTION -->|"precedes"| RESULT
    PLAY["BattedBallPlayProcess"] -->|"has occurrent part"| CONTACT
    PLAY -->|"has occurrent part"| MOTION
    PLAY -->|"has occurrent part"| FAIR
    PLAY -->|"has occurrent part"| RESULT
    FAIR -->|"has occurrent part"| J["FairBallJudgmentAct"]
    J -->|"has output"| D["FairDecisionICE"]
    D -->|"is about"| FAIR
    J -->|"precedes"| CALL["FairCallAct"]
    CALL -->|"has input"| D
    MOTION -->|"occurs at"| LOCATION["BattedBallLocationSite when coordinates exist"]
\`\`\`

Codes X, D, and E use this shared structure unless the enclosing result is sac_bunt, in which case the implemented bunt pattern is used instead.
