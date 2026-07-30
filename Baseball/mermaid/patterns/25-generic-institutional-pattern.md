# Generic counted institutional pattern

\`\`\`mermaid
flowchart LR
    UNDERLYING["Intentional act or physical process"] -->|"precedes when source supports order"| COUNTED["BaseballInstitutionalProcess"]
    COUNTED -->|"has occurrent part"| J["BaseballAdjudicationAct"]
    J -->|"has input when typed rule is known"| RULE["BaseballRule"]
    J -->|"has output"| D["BaseballDecisionICE"]
    D -->|"is about"| COUNTED
    J -->|"precedes when communication is mapped"| CALL["BaseballCallAct"]
    CALL -->|"has input"| D
    RECORD["BaseballEventRecord"] -->|"is about"| UNDERLYING
    RECORD -->|"is about"| COUNTED
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
    RECORD -->|"is about"| CALL
\`\`\`

Every plate-appearance result gets this constitutive judgment and decision pattern. Pitch, fair/foul, runner, and scorer outcomes add more specific judgment and decision types.
