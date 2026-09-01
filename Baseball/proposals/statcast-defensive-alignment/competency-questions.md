# Competency questions

1. Which Fielder Persons and field-relative Sites constitute the actual
   infield configuration classified by `if_fielding_alignment`?
2. Which Fielder Persons and Sites constitute the outfield configuration?
3. Can generic Site individuals nested in a Baseball Field Site be identified
   from the provider evidence without inventing fixed baseball-position Sites?
4. Does `located in` plus common participation in a Stasis adequately scope
   each player-site relation to the reviewed interval?
5. What Temporal Interval does the alignment Stasis occupy relative to the
   Pitch Act: pre-pitch setup, release, the whole pitch, or another window?
6. Are the infield and outfield labels nominal measurements of one complete
   defensive Stasis or two subset Stases?
7. Which official value set, decision rules, and versioned Reference System
   define each category token?
8. Does a category represent observed geometry, a provider classification of
   a tactical instruction, or both?
9. How are shifts occurring during delivery or fielder motion handled?
10. Can missing, not tracked, and provider `Standard` values be distinguished
    without treating missing as Standard?
11. Can fielder identities be reconstructed from authoritative lineup and
    substitution history without ingesting duplicate Statcast fielder columns?
12. Can the Statcast alignment graph be removed without deleting players,
    field, Pitch Act, lineup, or game facts?

## Negative tests

- A category token is not a class of Pitch, player, Team, or field Site.
- A Nominal Measurement ICE is not the defensive configuration itself.
- An Object Aggregate of fielders alone does not encode relative locations.
- `located in` without temporal/context evidence is not projected across the
  whole Game.
- A generic Stasis is not claimed sufficient until the condition it preserves
  is independently represented.
- Missing/untracked does not become `Standard` or another provider category.
- Fielder ID columns already derivable from MLB-game are not remapped.
