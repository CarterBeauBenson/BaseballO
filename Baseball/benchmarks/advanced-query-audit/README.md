# Advanced-query audit

This directory records deterministic result-set evidence for the 17 advanced
semantic analytics over the eight completed games from 2026-08-03. The audit
scopes every query to those eight authoritative named graphs and records source,
mapping, catalog, query, and canonical row-set hashes.

Generate the baseline while the corpus is loaded in local Fuseki:

```powershell
Baseball\scripts\pipeline\audit-advanced-queries.ps1
```

Verify current queries and results without rewriting the baseline:

```powershell
Baseball\scripts\pipeline\audit-advanced-queries.ps1 -VerifyBaseline
```

Unlike the original canned-query audit, zero rows are permitted for cataloged
discovery queries where the sample may contain no match. Integrity-audit rows
are counted as findings, not execution failures.

The current baseline executes all 17 cataloged queries. The integrity audit
returns three explicit generic-only terminal outcomes—two `pickoff_1b` and one
`caught_stealing_2b`—for ontological review; these are findings rather than
missing-rule assertions or failed execution.
