# Schedule qualification: postponed occurrence outside the requested range

The January 1–September 15 refresh response was complete: its root total,
per-date totals and all **2,788 returned occurrences** reconciled. Game 823543
appeared in the May 23 schedule block as explicitly postponed, with a September
22 `officialDate` and reschedule timestamp. The qualification adapter treated
that future date as evidence that the entire response was incomplete.

The corrected adapter retains an explicitly postponed or cancelled occurrence
on its returned schedule date, with `final:false` and `unplayed:true`. It never
adds that occurrence to played-game exposure. Played, live or unknown-status
rows outside the requested official-date range still withhold completeness.
Root totals, daily totals, unique date blocks and requested dates remain checked.

The [bounded proof](result.json) exercises the actual response in temporary
state. Its source hash is identical to the original batch response. Complete
calendar dates change from **0 to 258**, and all 2,788 occurrences remain
accounted for. The original batch is unchanged, the repair is idempotent, and
no game requests or live-state writes occur in this developer check.

The existing NiFi pending-batch worker owns production correction. It reacquires
at most one affected range per invocation and retains a separate hash-addressed
coverage snapshot. It does not repeat game acquisition, mapping or promotion.
Two failed transport attempts retain the exact failed response in source-local
quarantine. The SQL builder merges current snapshots by observation time; it
does not acquire schedules. Newer incomplete batch evidence cannot be hidden
by an older successful correction.

Focused tests cover parser rejection cases, immutable provenance, failed-input
retention, retry bounds, stale-code rejection and a full offline SQL candidate.
The candidate test verifies that the snapshot hash reaches SQL and the postponed
game does not enter the expected-game population. This corrects calendar
provenance; it does not admit unresolved PA, runner, defensive or review inputs.
