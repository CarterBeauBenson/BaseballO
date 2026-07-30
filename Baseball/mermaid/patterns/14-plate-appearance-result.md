# Plate-appearance result and constitutive adjudication

\`\`\`mermaid
flowchart LR
    PA["PlateAppearance"] -->|"has occurrent part"| RESULT["one result individual"]
    RESULT -->|"has occurrent part"| J["BaseballAdjudicationAct"]
    J -->|"has output"| D["BaseballDecisionICE"]
    D -->|"is about"| RESULT
    RECORD["Result Event Record"] -->|"is about"| RESULT
    RECORD -->|"is about"| J
    RECORD -->|"is about"| D
    TYPES["eventType overlays"] -->|"add most specific rdf:type"| RESULT
    TYPES --> HIT["Single, Double, Triple, HomeRun"]
    TYPES --> OUT["BattedBallOut, ForceOut, Strikeout, DoublePlay"]
    TYPES --> OTHER["Walk, HitByPitch, Error, FieldersChoice, Sacrifice, Balk, Interference"]
    AUTH["typed judgment overlay"] --> J
    AUTH --> SCORER["scorer + scoring rule when source supports it"]
    AUTH --> UMPIRE["umpire rule; named person only when supported"]
\`\`\`

Subclass outcomes reuse the one result IRI. The RML does not create a separate HitProcess beside a SingleProcess, or a separate OutProcess beside a ForceOutProcess.
