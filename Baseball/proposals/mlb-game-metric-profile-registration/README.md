# Register existing MLB metric validation profiles

Status: draft; no user approval is recorded here.

The focused source-scope check fails because the MLB module catalog lists
only `authoritative.ttl`, while five additional source-owned validation
profiles exist in that module. Four predate this change; the fifth supports
complete pitch/count admission for Recovery. This is an ownership registration
repair, not another source family or a change to metric meaning.

## Exact requested decision

Approve `mlb-game-metric-profile-registration`: add these five paths to the
existing `mlb-game.shacl` list in `sources/source-modules.json`, retaining its
existing authoritative profile, and update **only that catalog's protected
artifact hash** and the resulting protected-set digest in the semantic freeze,
with this named decision as provenance:

- `sources/mlb-game/shacl/batting-admission.ttl`
- `sources/mlb-game/shacl/contact-continuation.ttl`
- `sources/mlb-game/shacl/runner-resolution-admission.ttl`
- `sources/mlb-game/shacl/scoring-run-admission.ttl`
- `sources/mlb-game/shacl/pitch-count-admission.ttl`

The exact proposed catalog is [source-modules.proposed.json](source-modules.proposed.json).
All other catalog values remain unchanged. The freeze remains
`frozen-unratified`, with `ratified: false`; no unrelated pin or semantic
approval status changes. This does not approve the separate M3/M4 proposal.

The repository instruction requiring this named decision is:
"Never refresh a semantic freeze, curation-debt baseline, or admitted semantic
fingerprint unless the user explicitly accepts the named review package in
the current conversation." The catalog appears in the current freeze's
`protectedArtifacts`, so ordinary registration alone cannot finish the repair.

## Evidence and scope

`tests/test_sparql_source_scopes.py` invokes the unchanged repository validator
and reports: `Every active source SHACL must be owned exactly once in the
catalog`. No check is being removed or weakened. The source module, pipeline
group, graph boundary, authoritative RDF, mapping, ontology, identity policies
and acquisition schedule remain unchanged by the proposed registration.

Each listed profile belongs to the existing MLB game source. The new count
profile constrains existing Pitch, Strike, judgment, decision and timestamp
paths against independently enumerated final source records. It adds no
object property or other ontology term. Source counter values are validation
expectations, never serving scores. Existing E1, B1 and Q5 decisions govern
the evidence; unresolved source cases withhold metric admission.

This repair admits ownership, not complete data. Recovery's complete-season
and selected-period qualification gates must still pass, and twelve other
public player producers remain unfinished. The reference-game proof does not
certify a live season or populate nineteen leaderboards.

After acceptance, record and push the named decision before changing the
catalog or its protected pin, then rerun the focused ownership/scope check.
