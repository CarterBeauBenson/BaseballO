# Source evidence

MLB describes automated pitch classification as spanning the pitch-tracking
era and distinguishes fastballs, breaking balls, and offspeed pitches. MLB's
2025 description lists fourteen current Statcast types: four-seam fastball,
sinker, cutter, slider, sweeper, slurve, curveball, knuckle-curve, slow curve,
changeup, splitter, forkball, screwball, and knuckleball. MLB separately
documents Eephus as a historical and still recognized pitch type.

- <https://www.mlb.com/glossary/miscellaneous/pitch-tracking-era>
- <https://www.mlb.com/news/mlb-pitch-arsenals-are-bigger-than-ever-in-2025>
- <https://www.mlb.com/glossary/pitch-types/eephus>

The provider descriptions repeatedly identify variation and overlap in grip,
speed, spin, and movement. The class identity is therefore the reviewed
institutional nominal classification of the Pitch Act, not a fabricated
necessary physical signature.

Because provider classifications can be revised, persistent historical
classification evidence is not an OWL classification trigger. Only a selected
current classification produces an explicit type in a rebuildable reasoning
graph; replacing that type does not erase the earlier source evidence.

The checked MLB Games evidence contains `hitData.trajectory` values
`ground_ball`, `line_drive`, `fly_ball`, and `popup`. Those values describe the
ensuing batted-ball trajectory, so the proposed world-side bearer is the
Batted-Ball Motion Process.
