# Source-independent Mermaid

```mermaid
flowchart LR
    TZID[Time Zone Identifier]
    SYSTEM[Candidate IANA time-zone<br/>Reference System ICE]
    RULES[Candidate civil-time rule content<br/>world-side target unresolved]
    RECORD[Descriptive ICE]
    OFFSET[UTC-offset information]
    INSTANT[Reference Temporal Instant]

    TZID -->|uses reference system| SYSTEM
    RECORD -->|has continuant part| TZID
    TZID -.->|designation target requires review| RULES
    OFFSET -.->|reference time required| INSTANT
```

The diagram does not use a Spatial Region or assert an unscoped offset. The
designation target and identity of the time-zone rule content remain explicit
review blockers.
