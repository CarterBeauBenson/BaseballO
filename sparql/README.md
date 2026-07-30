# SPARQL

Statistical totals and absence-based classifications belong here, not in RML-generated instance data.

## Empty Games prototype

[`empty-games-prototype.rq`](empty-games-prototype.rq) is an executable review query, not yet the final product definition. It uses the source-backed `BatterAct` for offensive participation and treats the following mapped evidence as a contribution:

- single, double, home run, or walk;
- sacrifice fly or fielder's choice;
- a baserunning event whose source identifier begins with `stolen_base`.

The query excludes entire games containing a plate-appearance result type outside the mapping's current eleven-value completeness profile. That prevents an unknown result from silently becoming an empty game.

One important limitation remains: runner records are not explicitly linked to their enclosing plate appearance. The prototype therefore cannot attribute an ordinary batter out that moves another runner to that batter. Its output must be treated as candidates for review, not a published statistic.

The project owner is needed before promotion to a canned UI query to approve the contribution policy: productive outs, reach-on-error, hit-by-pitch, fielder's choice, sacrifice types, steals/caught stealing, pinch runners, and any minimum offensive-participation threshold.
