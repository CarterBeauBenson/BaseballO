# Accepted player metric presentation decisions

On September 15, 2026, Carter Beau Benson answered the six player-presentation
questions below. This records the answers before implementation. Existing
event formulas, exact arithmetic, eligibility, reference populations, and
source-admission requirements continue to apply.

1. **Batting scores:** average per eligible PA is the player headline; expose
   the total in the expanded view. User: "Yes". This applies to PA-grain scores;
   it does not change the denominators of established rate metrics.
2. **PAQ percentiles:** average the player's individual eligible PA percentiles.
   For example, 60 and 80 yield 70. Preserve the accepted season reference
   population. User: "Yes". Do not substitute the percentile of a player's mean.
3. **Run construction:** assign each run's depth and breadth to the scoring
   runner for display and average across that player's runs. This describes
   construction, including teammates' contributions; it does not transfer
   those contributions to the scorer. User: "Yes".
4. **Defensive depth and breadth:** average across defensive resolutions in
   which the defender actually acted. This describes participated-in sequences,
   not established individual defensive skill. User: "Yes".
5. **Reviews:** attribute the displayed review statistics to the player whose
   batting or baserunning outcome the decision affects: batter for ball/strike,
   runner for out/safe. An overturn does not automatically credit that player
   with causing the correction. User: "YEs". Existing separate review mechanisms
   and eligible-decision denominators remain unchanged. Unsupported affected-
   player links remain evidence gaps.
6. **Role breadth:** the user responded, "I do not know why we want to show the
   user role stuff? That should be backend stuff, I think". Keep role-realization
   computation and evidence in the backend and remove its public metric card.
   The proposed average-role headline was not accepted.

These are analytical presentation decisions. They introduce no object property,
ontology term, world-side identity policy, new source family, RML authorization,
semantic-freeze update, or declaration of source completeness. Numerical
non-batting participation minimums and missing input evidence remain unresolved.
