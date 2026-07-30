# Implemented event process chain

\`\`\`mermaid
flowchart LR
    PITCHER["Pitcher person"] -->|"participates in"| PITCH["PitchAct"]
    PITCH -->|"precedes"| PM["PitchBallMotionProcess"]
    BATTER["Batter person"] -->|"participates in"| SWING["SwingAct or BuntAct"]
    SWING -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| RESULT["most-specific counted result"]
    RESULT -->|"has occurrent part"| J["authorized Judgment Act"]
    J -->|"has output"| D["Decision ICE"]
    D -->|"is about"| RESULT
    RECORD["BaseballEventRecord"] -->|"is about"| PITCH
    RECORD -->|"is about"| PM
    RECORD -->|"is about"| SWING
    RECORD -->|"is about"| CONTACT
    RECORD -->|"is about"| MOTION
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
    RECORD -->|"is about"| RESULT
\`\`\`

This is the implemented counted-hit backbone. Swing-and-miss, foul, foul tip, error, out, sacrifice, runner safe/out/run, and stolen-base paths differ where their source evidence and institutional judgments differ; each has a discrete diagram in patterns/.
