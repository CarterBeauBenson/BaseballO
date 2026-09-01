# MLB divisions source module

This detachable module owns only the MLB Divisions endpoint lifecycle. Its own
API connector acquires Division responses and owns its context, RML, SHACL,
graph namespace, retry, quarantine, provenance, and transient cleanup. It does
not depend on the Teams or Games connectors.

The accepted graph surface contains Division identity and name plus the League
identity and name nested in that Division response. It adds no affiliation or
membership relation and contains no League-season mapping.

The `MLB Divisions` NiFi group passed its bounded proof, has an enabled 05:00
Eastern trigger, and received the 2026 corpus request on 2026-09-01. It
promotes its own authority graph and remains operationally independent of the
Teams and Leagues groups.
