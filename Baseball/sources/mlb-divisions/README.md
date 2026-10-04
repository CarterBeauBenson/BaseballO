# MLB divisions source module

This detachable module owns only the MLB Divisions endpoint lifecycle. Its own
API connector acquires Division responses and owns its context, RML, SHACL,
graph namespace, retry, quarantine, provenance, and transient cleanup. It does
not depend on the Teams or Games connectors.

The accepted graph surface contains Division identity and name plus the League
identity and name nested in that Division response. It adds no affiliation or
membership relation and contains no League-season mapping.

The `MLB Divisions` NiFi group passed its bounded proof, has an enabled 05:00
Eastern trigger, promotes its own authority graph, and remains operationally
independent of the Teams and Leagues groups. Current run status belongs to
source-local terminal NiFi evidence, not this module contract.

## Input contract

The connector accepts a strict UTF-8 object with a non-empty `divisions`
array. Selected values are root `id/name`, optional `league.id/name`, and the
existing MLB `sport.id` guard. Other response fields remain unmapped.

The execution context is `divisions-context.json`. Invalid selected values are
quarantined before RML; successful raw and context bytes remain transient.
