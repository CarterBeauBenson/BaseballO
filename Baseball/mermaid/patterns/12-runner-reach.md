# Runner reaches a base safely from origin

\`\`\`mermaid
flowchart LR
    ACT["BaserunningAct<br/>source start absent"] -->|"precedes"| TOUCH["BaseTouchingProcess"]
    TOUCH -->|"has participant"| RUNNER["Runner person"]
    TOUCH -->|"has participant"| BASE["Base identified by movement.end"]
    TOUCH -->|"precedes"| SAFE["SafeProcess"]
    SAFE -->|"has occurrent part"| J["SafeJudgmentAct"]
    J -->|"has input"| RULE["SafeRule"]
    J -->|"has output"| D["SafeDecisionICE"]
    D -->|"is about"| SAFE
\`\`\`

The safe process is a separate institutional outcome. The BaserunningAct is not typed or named as successful.
