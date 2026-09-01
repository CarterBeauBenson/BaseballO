# Source evidence

The accepted MLB-game packages establish the evidence boundary used here:

- pitch-type and batted-ball trajectory values are nominal classifications
  made within versioned provider Reference Systems;
- only the current authoritative classification participates in rebuildable
  query-index subtype materialization;
- MLB game-type codes classify reviewed season phases contained in a season;
- event records are identified by Identifier ICEs and are about the entities
  and processes described by the source; and
- provider coordinates remain information-space values until their frame is
  grounded to a Baseball Field.

The existing query corpus was inspected for direct `dcterms:identifier` and
`dcterms:type` dependencies. Those occurrences identify the bounded consumers
that must migrate with the accepted RML contract.
