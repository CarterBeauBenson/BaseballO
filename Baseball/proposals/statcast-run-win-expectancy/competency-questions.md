# Competency questions

1. What exact pre-pitch or pre-plate-appearance state conditions
   `home_win_exp`?
2. What possible Process or Process Aggregate is the home-win probability's
   measurement target without asserting a win that had not yet occurred?
3. Is `home_win_exp` evaluated before or after the row's pitch/event, and how
   is that boundary identified?
4. What future Run Process collection or remaining-inning outcome is estimated
   by the provider's run-expectancy model?
5. Does `delta_run_exp` equal after-state expectancy minus before-state
   expectancy, and does it include runs scored during the event?
6. Is `delta_run_exp` an Estimate ICE about the event, a derived comparison of
   two Estimate ICEs, or another target requiring ontology coverage?
7. Which versioned Algorithms, computation Processes, state definitions,
   training population, and season/method era produced the values, and what
   Agent evidence would justify typing a computation as an Act?
8. Which inputs are already authoritative MLB-game facts and must remain
   excluded from Statcast RML?
9. Can `delta_home_win_exp` be derived from approved before/after
   `home_win_exp` values rather than ingested?
10. Can `bat_win_exp` be derived from home-team expectancy and batting side?
11. How are null, untracked, not-applicable, and unavailable-model-era values
    distinguished?
12. Can these model outputs be removed without affecting actual Game, Run,
    scoring, or state evidence?

## Negative tests

- A Baseball Game is not a Probability Measurement ICE.
- A `RunProcess` is not minted merely because a model predicts future runs.
- The final actual winner is not substituted for the earlier possible target.
- `delta_run_exp` is not attached as a direct quality/literal of the pitch.
- A difference field is not treated as a primitive world quantity when it is
  deterministically computed from two model outputs.
- Provider model inputs already owned by MLB-game are not duplicated.
- A source row does not establish a model version or state boundary merely by
  field order.
- A computation is not typed as an Act without evidence for a causally active
  Agent at that computation's grain.
