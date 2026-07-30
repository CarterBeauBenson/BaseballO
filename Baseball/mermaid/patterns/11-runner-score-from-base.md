# Run scored from a recorded base

\`\`\`mermaid
flowchart LR
    ACT["BaserunningAct<br/>start 1B, 2B, or 3B"] -->|"precedes"| TOUCH["BaseTouchingProcess"]
    TOUCH -->|"has participant"| RUNNER["Runner person"]
    TOUCH -->|"has participant"| HOME["HomePlate"]
    TOUCH -->|"precedes"| RUN["RunProcess"]
    RUN -->|"has occurrent part"| J["RunJudgmentAct"]
    J -->|"has output"| D["RunDecisionICE"]
    D -->|"is about"| RUN
\`\`\`

This is distinct from the origin pattern because the stable source composite includes movement.start.
