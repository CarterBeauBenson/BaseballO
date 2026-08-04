# Canned-query corpus audit

This directory records the authoritative result contract for all 48 canned
queries across the eight completed 2026-08-03 games. The development fixture
`566279` is deliberately excluded from this corpus baseline.

Generate a reviewed replacement baseline from the repository root with Fuseki
running and all eight authoritative graphs loaded:

```powershell
powershell -ExecutionPolicy Bypass -File `
  Baseball/scripts/pipeline/audit-canned-queries.ps1
```

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
is the machine-verifiable artifact. Timings in both files are diagnostic
observations rather than benchmark claims.
