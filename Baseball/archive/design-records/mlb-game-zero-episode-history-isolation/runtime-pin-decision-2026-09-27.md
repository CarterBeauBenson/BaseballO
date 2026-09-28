# Q7 runtime-pin correction: September 27, 2026

The user was asked to approve this exact correction: update only the MLB-game
context-builder hash in `Baseball/governance/semantic-freeze.json` to the
already reviewed Q7 file (`023b6594…`), permitting NiFi to run that file without
changing ontology, RML, SHACL or source code. After the assistant explained
that the correction remained unapplied pending this approval, the user replied:

> please jsut fix the prblem

This direction accepts the specifically presented runtime-pin correction.
It does not ratify the frozen ontology or authorize a new semantic change.

The implementation is limited to
`runtimeAdmissions[mlb-game].artifacts.contextBuilder.sha256`:

- Previous: `169fd44a4dee436747d11c9201f8a8d5ea8c772f8c7ea6acaacfddb069d1a464`
- Accepted: `023b659409d204d3e7cca1eaab5f9563744a6f54a8cac72b8a6c56ac79faba98`

The accepted value is already recorded in `protectedArtifacts` and matches the
Q7 context-builder implementation in commit `efcd9cb`. Keep all other runtime
pins, protected artifacts, review records and semantic statuses unchanged.
After the existing runtime-admission check, NiFi owns the bounded proof and
September 17–26 acquisition recovery already requested by the user. This does
not authorize an unrelated RDF rebuild.

This decision is committed and published before applying the runtime correction.
