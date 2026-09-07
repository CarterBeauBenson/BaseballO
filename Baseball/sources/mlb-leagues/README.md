# MLB leagues source module

This detachable module owns only the MLB Leagues endpoint lifecycle. Its own
API connector acquires League responses and performs its own context
preparation, RML, SHACL, promotion, retry, quarantine, provenance, and
transient cleanup. It does not depend on the Teams or Games connectors.

It preserves the accepted League branch: League and nested Division
identities and names, plus league-scoped Baseball Seasons, Plans, reviewed
regular-season and postseason Phases, Calendar Date Identifier evidence, and
Days. It emits no affiliation, membership, or direct Date-to-Phase boundary.

The `MLB Leagues` NiFi group passed its bounded proof, has an enabled 05:00
Eastern trigger, promotes its own authority graph, and remains operationally
independent of the Teams and Divisions groups. Current run status belongs to
source-local terminal NiFi evidence, not this module contract.
