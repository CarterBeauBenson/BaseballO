# Three batting-progress metrics from one complete game

The unchanged, already validated game 824087 RDF passes two independent Jena
SHACL admissions: the complete 90-resolution runner census and all 73 official
PAs with their final roster/player/team totals. Explicitly identified PR
substitution among other players preserves the unchanged batter's PA. It does
not resolve multi-batter statistical-credit cases.

The canonical Jena query supplies every PA's complete supported progress.
Offensive Reach, Hidden Help Rate and Empty Games then produce exact player
results in the declared one-game developer scope. Existing SPARQL kernels own
their participant counts, applicable PA numerator/denominator and Empty Game
classification. Independent positive running contributes to the runner's
Empty Game classification without benefiting the batter. The SQL-retained
evidence produces exactly the same results.

`result.json` preserves source/RDF/implementation hashes, both source admission
reports, exact player results and the common per-PA contribution trace. No
source statistic supplies a score and no schedule row was fabricated. Public
date-range queries correctly remain withheld without separate schedule
admission. This is not a live dashboard completion claim.

Focused checks passed: 17 progress/source/SHACL/player tests, 19 existing
metric/run-serving tests and 43 dashboard/API tests, plus PowerShell parsing
of the NiFi source stage. Negative cases include wrong source PA credit,
missing resolution/participant/destination, unknown positive attribution,
safe-then-out continuation, absent schedule or source proof, and SQL proof
corruption. Source conformance still precedes promotion in NiFi; the existing
asynchronous recovery owns corpus refresh and materialization.
