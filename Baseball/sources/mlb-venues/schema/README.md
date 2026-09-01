# MLB venues source mechanics

[`mlb-venues-response.schema.json`](mlb-venues-response.schema.json) documents
the official response wrapper and the fields used by this approved module. It
allows additional provider fields because the API exposes a wider surface, but
additional fields are not licensed for RML.

[`fixtures/one-venue.json`](fixtures/one-venue.json) is synthetic and exists
only for deterministic mapping/SHACL checks. It is not a retained API response
and must never be promoted as authoritative data. The fixture intentionally
contains Unicode and excluded fields so tests can prove exact name handling and
absence of semantic leakage.

Runtime validation is stricter than structural JSON Schema where identity is
involved. `mapping/prepare-context.py` checks the requested season, response
hash, duplicate IDs, exact name handling, coordinate pair completeness and
ranges, positive capacity, pinned surface/roof values, and the difference
between a missing/null value and a present invalid value.
