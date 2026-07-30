# Baseball artifacts as process participants

\`\`\`mermaid
flowchart LR
    BALL["pitch-scoped Baseball"]
    PITCH["PitchAct"]
    PITCH -->|"has participant"| BALL
    PM["PitchBallMotionProcess"] -->|"has participant"| BALL
    CONTACT["BatBallContactProcess"] -->|"has participant"| BALL
    BM["BattedBallMotionProcess"] -->|"has participant"| BALL
    CATCH["BallCatchingProcess"] -->|"has participant"| BALL
    SWING["SwingAct or BuntAct"] -->|"has participant"| BAT["pitch-scoped BaseballBat"]
    CONTACT -->|"has participant"| BAT
    TOUCH["BaseTouchingProcess"] -->|"has participant"| BASE["Base or HomePlate"]
    TOUCH -->|"has participant"| RUNNER["Runner person"]
\`\`\`

Event-scoped artifact IRIs keep the physical participants stable throughout each represented pitch or runner movement without claiming cross-event artifact identity.
