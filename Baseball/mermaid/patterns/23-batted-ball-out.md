# Batted-ball and force-out result

\`\`\`mermaid
flowchart LR
    ACT["SwingAct or BuntAct"] -->|"precedes"| CONTACT["BatBallContactProcess"]
    CONTACT -->|"precedes"| MOTION["BattedBallMotionProcess"]
    MOTION -->|"precedes"| FAIR["FairBallProcess"]
    FAIR -->|"precedes"| OUT["BattedBallOutProcess, ForceOutProcess, or DoublePlay subtype"]
    OUT -->|"has occurrent part"| J["OutJudgmentAct"]
    J -->|"has input"| RULE["OutRule"]
    J -->|"has output"| D["OutDecisionICE"]
    D -->|"is about"| OUT
    WHO["Specific adjudicating umpire"] -.->|"not identified by play result"| J
\`\`\`

The RML maps the counted out and its judgment structure but does not assign the home-plate umpire to field or base calls.
