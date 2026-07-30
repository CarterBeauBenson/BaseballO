# Sacrifice fly and sacrifice bunt

\`\`\`mermaid
flowchart LR
    SWING["SwingAct"] -->|"sac_fly path"| CONTACT["BatBallContactProcess"]
    BUNT["BuntAct"] -->|"sac_bunt path"| CONTACT
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| SAC["SacrificeFlyProcess or SacrificeBuntProcess"]
    SAC -->|"has occurrent part"| J["SacrificeJudgmentAct"]
    J -->|"has participant"| SCORER["Official scorer"]
    J -->|"has input"| RULE["SacrificeRule"]
    J -->|"has output"| D["SacrificeDecisionICE"]
    D -->|"is about"| SAC
\`\`\`

SacrificeFlyProcess and SacrificeBuntProcess are the most specific types on the one result individual.
