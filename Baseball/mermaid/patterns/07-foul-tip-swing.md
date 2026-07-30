# Foul tip

\`\`\`mermaid
flowchart LR
    SWING["SwingAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    CONTACT -->|"precedes"| CATCH["BallCatchingProcess"]
    CATCH -->|"precedes"| FT["one individual:<br/>FoulTipProcess<br/>and StrikeProcess"]
    FT -->|"has occurrent part"| J["FoulTipJudgmentAct"]
    J -->|"has input"| RULE["StrikeRule"]
    J -->|"has output"| D["FoulTipCallICE"]
    D -->|"is about"| FT
    PLAY["BattedBallPlayProcess"] -->|"has occurrent part"| CONTACT
    PLAY -->|"has occurrent part"| MOTION
    PLAY -->|"has occurrent part"| CATCH
    PLAY -->|"has occurrent part"| FT
\`\`\`

Unlike the ordinary foul pattern, the foul-tip and strike classifications use one RDF individual with both types.
