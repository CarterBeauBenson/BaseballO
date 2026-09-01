# Decisions needed

Answer each decision explicitly.

| ID | Question | Proposed answer |
| --- | --- | --- |
| MASS-01 | Does MLB 'weight' measure CCO Mass rather than CCO Weight? | Yes. Mass inheres in the Person; CCO Weight is not used. |
| MASS-02 | Is the source unit sufficiently established? | Yes. Treat the reported value as pounds and use the accepted Pound Measurement Unit. |
| MASS-03 | Does the response evidence a Measurement Process? | No. Emit only a response-versioned Measurement ICE; no agent, instrument, method, act, or measurement time is invented. |
| MASS-04 | What is stable across observations? | Reuse one Person-scoped Mass Quality; content-version the Measurement ICE so changed reports do not overwrite prior authoritative evidence. |
| MASS-05 | How are bad or missing values handled? | Null or absent emits nothing. A present nonnumeric or nonpositive value is quarantined before RML; later source SHACL validates only emitted RDF. |

Acceptance of these answers would still require a later source-specific
Mermaid review before executable mapping.

