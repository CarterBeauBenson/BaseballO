# Source and repository evidence

The accepted combined module already distinguishes the three MLB endpoint
families mechanically:

- `/api/v1/teams/{teamId}` returns a root `teams` collection;
- `/api/v1/leagues/{leagueId}` returns a root `leagues` collection; and
- `/api/v1/divisions/{divisionId}` returns a root `divisions` collection.

Before this decision, `sources/mlb-organizations/nifi/lane.json` acquired those
three endpoint families under one lifecycle, and
`mapping/prepare-context.py --endpoint-family` selected which root collection
was being transformed. The combined RML used the resulting endpoint-family
value in Response ICE identity. This demonstrates that the sources are already
distinguishable without changing their accepted world-side graph patterns.

The repository's detachable-source rule requires independent acquisition,
mapping, source validation, promotion, retry, quarantine, and provenance
boundaries when a connector must be independently disconnectable. The clean
reset left no promoted legacy organization graph that requires migration.

The split therefore partitions the existing accepted implementation by MLB
endpoint family. It does not admit new fields, ontology terms, object
properties, data properties, or world-side relations.
