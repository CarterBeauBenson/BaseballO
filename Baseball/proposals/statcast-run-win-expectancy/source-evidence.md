# Source evidence

The archived accepted Statcast inventory classifies:

- `delta_run_exp` as genuinely additional provider run-expectancy output;
- `home_win_exp` as genuinely additional provider probability output;
- `delta_home_win_exp` as deterministically derivable from retained before and
  after home-win expectancy at the reviewed event boundary; and
- `bat_win_exp` as deterministically derivable from home-win expectancy and
  batting side.

This package preserves those decisions. It does not reopen game score, base
occupancy, outs, inning, batting side, actual runs, or game-result fields that
MLB-game already owns or can derive.

Existing vocabulary supplies Baseball Game, Plate Appearance, Pitch Act, Run
Process, generic Process, Algorithm, Act of Data Transformation, Probability
Measurement ICE,
Estimate ICE, Point Estimate ICE, `has input`, `has output`, `prescribed by`,
`is about`, `is a measurement of`, and direct decimal values.

The existing actual Run Process is an institutionally counted process that
adds a run. It cannot serve as a merely possible future run when none occurred.
Likewise, no accepted current class identifies a possible home-team-winning
game outcome or the counterfactual/process aggregate whose likelihood is being
measured. Exact provider state timing and whether `delta_run_exp` includes runs
scored during the event remain source-evidence questions.

The outputs support some provider computation Process, but the reviewed
evidence does not identify a causally active Agent at that Process grain. The
draft therefore withholds an Act of Data Transformation type.
