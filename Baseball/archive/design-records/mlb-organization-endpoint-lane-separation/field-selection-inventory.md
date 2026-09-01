# Field-selection inventory

| Connector | Source fields retained from the accepted contract | Treatment |
|---|---|---|
| `mlb-teams` | Root Team identifier and canonical name; selected nested Organization identifiers and names already admitted by the team-response contract | Existing accepted assertions, partitioned into the team connector |
| `mlb-leagues` | Root League identifier and canonical name; selected nested Division identifiers and names; league season, season-date, Phase, Plan, and Day evidence | Existing accepted assertions, partitioned into the league connector |
| `mlb-divisions` | Root Division identifier and canonical name; selected nested League identifier and name already admitted by the division-response contract | Existing accepted assertions, partitioned into the division connector |
| Cross-endpoint fields | No payload bytes or execution contexts are shared between connectors | Prohibited |
| New or previously deferred fields | None | Unresolved and unmapped until separately reviewed |

Nested identifiers exposed by an endpoint remain evidence from that endpoint;
they do not create affiliation or membership relations. Repeated world-side
identity assertions can converge on the same accepted Team, League, or
Division IRI in the triple store while retaining source-specific Response ICEs
and graph provenance.
