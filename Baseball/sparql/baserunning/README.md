# Baserunning queries

This family reports runs, reviewed source event labels, stolen bases, outs, and
resolution categories from mapped runner acts and runner-resolution processes.
Every counted outcome requires its corresponding judgment act. Stolen bases
are identified by `StolenBaseProcess` plus `StolenBaseJudgmentAct`, not by
parsing a source string. Source event labels remain only where the UI needs the
source-backed event grouping.

The reviewed runner currently accelerates `events-by-player` and
`runs-by-season-and-venue` after exact corpus equivalence and index-freshness
checks. Other baserunning queries remain canonical authoritative reads pending
their own evidence.
