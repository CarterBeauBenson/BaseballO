# Decisions needed

| ID | Question | Decision options |
| --- | --- | --- |
| COUNT-01 | Is each value planned, maximum, or observed? | Classify `numGames`, `numTeams`, wildcard-team, and playoff-team values separately. |
| COUNT-02 | What entity is counted? | Baseball Games, Baseball Teams, qualifying Teams, or another explicitly evidenced grain. |
| COUNT-03 | What Season/Phase scopes the value? | Require accepted Season or Phase identity; a request parameter is provenance only. |
| COUNT-04 | Can an observed value be derived? | Prefer a rebuildable RDF-derived result when authoritative events/affiliations suffice. |
