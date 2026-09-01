# Advanced-query audit

This directory preserves deterministic result-set evidence for the 17 advanced
semantic analytics over the eight completed games from 2026-08-03. The audit
scopes every query to those eight authoritative named graphs and records source,
mapping, catalog, query, and canonical row-set hashes.

Generate a candidate capture outside the repository while the corpus is loaded
in local Fuseki:

```powershell
Baseball\scripts\pipeline\audit-advanced-queries.ps1 `
  -OutputDirectory "$env:LOCALAPPDATA\BaseballO\state\benchmarks\advanced-query-audit-candidate"
```

Do not overwrite the checked-in capture. After review, preserve a new run under
a new capture identity and update the evidence register separately.

Verify current queries and results without rewriting the baseline:

```powershell
Baseball\scripts\pipeline\audit-advanced-queries.ps1 -VerifyBaseline
```

Unlike the original canned-query audit, zero rows are permitted for cataloged
discovery queries where the sample may contain no match. Integrity-audit rows
are counted as findings, not execution failures.

The JSON and Markdown artifacts are pinned by
[`../query-audit-evidence-register.json`](../query-audit-evidence-register.json).
The register retains their original `raw-bytes-v1` query identities and records
a separate reviewed `canonical-text-v1` compatibility set; it does not relabel
the historical capture.

The preserved capture executes all 17 cataloged queries. The integrity audit
returns three explicit generic-only terminal outcomes—two `pickoff_1b` and one
`caught_stealing_2b`—for ontological review; these are findings rather than
missing-rule assertions or failed execution.
