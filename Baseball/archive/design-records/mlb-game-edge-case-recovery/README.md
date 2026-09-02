# MLB-game edge-case recovery decision

Accepted decision record for four source-evidenced MLB Games edge cases that
blocked otherwise valid records during the 2026 season ingest:

- an official identified by stable MLB identifier without a supplied name;
- a pitch-result challenge whose description does not state confirmed or
  overturned;
- an incomplete plate appearance interrupted by another game event; and
- a rain-delay advisory occurring during a game.

The package introduces no ontology terms and no source-specific substitute for
an entity in reality. It authorizes only the named MLB-game mapping, source
SHACL, fixture, and admission updates recorded in `review.json`.

Operational retry and quarantine-replay policy is not a semantic assertion and
is documented by the MLB-game NiFi contract rather than this decision record.
