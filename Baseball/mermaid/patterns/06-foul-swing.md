# Foul ball and conditionally counted foul strike

\`\`\`mermaid
flowchart LR
    SWING["SwingAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FOUL["FoulBallProcess"]
    FOUL -->|"has occurrent part"| FJ["FoulBallJudgmentAct"]
    FJ -->|"has input"| FR["FairFoulRule"]
    FJ -->|"has output"| FD["FoulDecisionICE"]
    FD -->|"is about"| FOUL
    FJ -->|"precedes"| FC["FoulCallAct"]
    FC -->|"has input"| FD
    FOUL -.->|"only CountedFoulSource; precedes"| STRIKE["separate StrikeProcess"]
    STRIKE -->|"has occurrent part"| SJ["StrikeJudgmentAct"]
    SJ -->|"has output"| SD["StrikeDecisionICE"]
\`\`\`

The RML always generates the foul classification for code F. It generates the separate strike only for unambiguous first-counted-foul records where count.strikes equals 1. Event-local MLB data cannot distinguish every second counted foul from a two-strike foul, so ambiguous cases are not asserted as strikes.
