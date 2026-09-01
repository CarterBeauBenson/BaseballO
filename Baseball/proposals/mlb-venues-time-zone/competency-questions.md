# Decisions needed

| ID | Question | Decision options |
| --- | --- | --- |
| TIMEZONE-01 | Is 'timeZone.id' an IANA Time Zone Identifier? | Require a pinned identifier system and code validation. |
| TIMEZONE-02 | What does 'tz' represent? | Identifier alias, daylight/standard abbreviation, or display string; establish code system and date scope. |
| TIMEZONE-03 | What time scopes 'offset'? | Retrieval time, requested season, current legal offset, or another provider definition. |
| TIMEZONE-04 | What time scopes 'offsetAtGameTime'? | Require a particular Game or explicit reference instant; a venue response alone must not invent one. |
| TIMEZONE-05 | Which values enter authoritative RDF? | Prefer stable identifier semantics; retain unscoped offsets only in provenance or block them. |
| TIMEZONE-06 | What does the identifier designate without using CCO Spatial Region semantics? | Review a source-independent civil-time rule or reference-system target; do not inherit the imported spatial-region account. |
