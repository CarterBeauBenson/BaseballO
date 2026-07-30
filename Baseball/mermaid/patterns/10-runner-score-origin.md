# Run scored from an unrecorded starting base

\`\`\`mermaid
flowchart LR
    ACT["BaserunningAct<br/>source start absent"] -->|"precedes"| TOUCH["BaseTouchingProcess"]
    TOUCH -->|"has participant"| RUNNER["Runner person"]
    TOUCH -->|"has participant"| HOME["HomePlate"]
    TOUCH -->|"precedes"| RUN["RunProcess"]
    RUN -->|"has occurrent part"| J["RunJudgmentAct"]
    J -->|"has input"| RULE["RunRule"]
    J -->|"has output"| D["RunDecisionICE"]
    D -->|"is about"| RUN
    RECORD["Runner Event Record"] -->|"is about"| RUN
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
\`\`\`

The origin variant uses an origin key because MLB does not supply movement.start. It does not invent a starting base.
