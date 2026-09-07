# MLB teams source module

This detachable module owns only the MLB Teams endpoint lifecycle. Its own API
connector acquires transient team responses, runs its own context gate, RML,
and SHACL, and promotes only to the `mlb-teams` authority namespace. It does
not depend on the Games connector to discover or acquire Teams.

The accepted graph surface is unchanged from the team branch of the former
organization contract: Team identity and name, plus identifiers and names for
League and Division records nested in that same response. Nested records add
no affiliation or membership relation. Their identifiers allow independently
promoted Team RDF to seed the League and Division connectors through the
triple store.

NiFi owns proof, bounded retry, quarantine, promotion, provenance, and
transient cleanup. Leagues and Divisions have their own API connectors and do
not receive payloads or run requests from this lane. Shared identifiers meet
only after independent RDF promotion.

The `MLB Teams` NiFi group passed its bounded proof, has an enabled 05:00
Eastern trigger, and promotes one source-owned authority graph per scope. It
does not build a Game query-index graph or invoke the Game serving materializer.
Current run status belongs to source-local terminal NiFi evidence, not this
module contract.
