# Canned-query corpus audit

This directory preserves the authoritative result capture for all 48 canned
queries across the eight completed 2026-08-03 games. The development fixture
`566279` is deliberately excluded from this historical corpus capture.

Generate a candidate capture outside the repository from the repository root,
with Fuseki running and all eight authoritative graphs loaded:

```powershell
powershell -ExecutionPolicy Bypass -File `
  Baseball/scripts/pipeline/audit-canned-queries.ps1 `
  -OutputDirectory "$env:LOCALAPPDATA\BaseballO\state\benchmarks\canned-query-audit-candidate"
```

Do not overwrite the checked-in capture. After review, preserve a new run under
a new capture identity and update the evidence register separately.

Verify the live graph results against the checked-in baseline without rewriting
it:

```powershell
powershell -ExecutionPolicy Bypass -File `
  Baseball/scripts/pipeline/audit-canned-queries.ps1 `
  -VerifyBaseline
```

The audit injects an explicit allowlist containing the eight authoritative
named graphs into every query. It records source and mapping hashes, graph
triple counts, query hashes, result variables, row counts, duplicate counts,
and order-independent row-set hashes. Canonical rows preserve RDF term type,
datatype, language, unbound values, and duplicate multiplicity.

[`corpus-2026-08-03-baseline.md`](corpus-2026-08-03-baseline.md) is the readable
summary. [`corpus-2026-08-03-baseline.json`](corpus-2026-08-03-baseline.json)
is the machine-verifiable artifact.
[`../query-audit-evidence-register.json`](../query-audit-evidence-register.json)
pins both files, their capture commit and timestamp, the original
`raw-bytes-v1` query-hash convention, and the reviewed
`canonical-text-v1` compatibility set used for cross-platform verification.
Compatibility metadata does not rewrite the captured hashes. Timings in both
files are diagnostic observations rather than benchmark claims.

The preserved capture covers 246,191 authoritative triples. All 48 queries
return at least one row, none returns duplicate result rows, and Empty Games
returns 26 reviewed candidate rows after intentional-walk coverage was added to
the completeness profile.
