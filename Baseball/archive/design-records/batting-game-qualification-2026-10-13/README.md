# Batting qualification uses participation in 40% of team games

On October 13, 2026, Carter Beau Benson requested a 40% game-participation
minimum for batting rates and confirmed:

> At least one plate appearance in 40% of team games

A batting game is a distinct selected game in which the player has at least
one official plate appearance. Walk-only games count. Multiple PAs in the
same game do not create additional batting games.

Replace the former 3.1-PA-per-team-game batting minimum with
`ceil(2 * selectedTeamGames / 5)` batting games: 1 of 1, 3 of 7, 12 of 30,
and 65 of 162. Use the complete selected team schedule, not only games in
which the player appeared. Preserve the accepted multiple-team denominator:
the largest selected team total or the player's distinct evidenced game
exposure, whichever is greater.

The same rule supplies the batting qualification alternative for Contribution
Mix. Existing activity-specific observation minimums remain in place. Empty
Games remains a count with no appearance minimum. Complete selected-range
metric observations remain required; a smaller participation threshold neither
fills missing scores nor changes any metric numerator or denominator.

Show batting-game participation, the minimum, and PA totals with player results.
Apply this filter consistently to top fives, full rankings, and metric details.
Read existing prepared player/game rows; do not trigger SPARQL, source recovery,
RML execution, or RDF rebuilding from this presentation change.

This acceptance record is published before its implementation.
