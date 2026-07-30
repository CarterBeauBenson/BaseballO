# Fielder's choice classification

\`\`\`mermaid
flowchart LR
    ACT["SwingAct or BuntAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| FC["FieldersChoiceProcess result individual"]
    FC -->|"has occurrent part"| J["FieldersChoiceJudgmentAct"]
    J -->|"has participant"| SCORER["Official scorer"]
    J -->|"has input"| RULE["FieldersChoiceRule"]
    J -->|"has output"| D["FieldersChoiceDecisionICE"]
    D -->|"is about"| FC
    OTHER["Another runner OutProcess"] -.->|"may coexist through runner mapping"| FC
\`\`\`

The batter result and another runner's out remain distinct counted process individuals.
