# Swinging strike: no contact

\`\`\`mermaid
flowchart LR
    PITCH["PitchAct"] -->|"precedes"| MOTION["PitchBallMotionProcess"]
    PITCH -->|"precedes"| SWING["SwingAct"]
    SWING -->|"has participant"| BATTER["Batter person"]
    SWING -->|"realizes"| ROLE["game-scoped BatterRole"]
    SWING -->|"has participant"| BAT["BaseballBat"]
    SWING -->|"precedes"| STRIKE["StrikeProcess"]
    STRIKE -->|"has occurrent part"| J["StrikeJudgmentAct"]
    J -->|"has output"| D["StrikeDecisionICE"]
    D -->|"is about"| STRIKE
    ABSENT["No BatBallContactProcess is generated"]
\`\`\`

A swing-and-miss remains a neutral SwingAct. Failure is expressed by the absence of contact and the downstream counted StrikeProcess; no failed-swing class or IRI is created.
