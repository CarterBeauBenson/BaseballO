# Time information and temporal regions

\`\`\`mermaid
flowchart LR
    GAME["BaseballGame"] -->|"occupies temporal region"| GI["Game temporal interval"]
    PA["PlateAppearance"] -->|"occupies temporal region"| PI["Plate-appearance temporal interval"]
    PITCH["PitchAct"] -->|"occupies temporal region"| EI["Pitch temporal interval"]
    PI -->|"temporal part of"| GI
    EI -->|"temporal part of"| PI
    TS["BaseballTimestampICE"] -->|"designates"| INSTANT["BaseballEventTemporalInstant"]
    TS -->|"is about"| EVENT["Game, PlateAppearance, or PitchAct"]
    TS -->|"has datetime value"| VALUE["source timestamp literal"]
\`\`\`

Timestamp ICEs, temporal instants, intervals, and baseball events are distinct individuals.
