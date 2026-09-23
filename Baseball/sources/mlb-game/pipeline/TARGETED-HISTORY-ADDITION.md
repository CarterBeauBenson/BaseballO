# Q7 targeted history repair

The user accepted [Q7](../../../archive/design-records/mlb-game-zero-episode-history-isolation/README.md)
in commit `400f1ef2fb62`, before implementation. Future ingestion isolates an
empty personal history when it is the only issue in that half-inning. Complete
other histories retain their existing identities and episode membership. The
half-inning and zero-episode runner remain withheld.

`nifi/provision-history-addition.ps1` installs the bounded repair in the existing
MLB Game group. `pipeline/targeted-history-addition.ps1` takes the normal per-game
lock and invokes the Python component for the two approved game promotions.
After completion, timer ticks are no-ops. A failed implementation gets at most
two attempts; terminal results are under
`state/pipeline/control/mlb-game/history-addition/`.

The component reads the retained reconciliation inventories; it acquires no
source response and does not rerun the game mapping. It executes only the
existing PersonalRunnerProcess, PersonalRunnerInterval and
PersonalRunnerMembership maps on the selected missing histories. The owning
history SHACL checks the full expected history membership in the existing graph
plus this delta. Other retained source shapes are rechecked against that union;
their source decisions and producer fingerprints remain unchanged. Missing
source completeness remains withheld. The repair receipt distinguishes the
new graph validation from the original source census.

The authoritative write is an additive Graph Store POST. A comparison checks
that the result is exactly the original graph plus the RML delta. Only these
games' derived query indexes are regenerated. The normal promotion event
notifies downstream materializers. Their prepared SQL remains the UI input.
RDFLib literal normalization is disabled during export so timestamp spelling,
fractional precision and other existing lexical forms stay unchanged.

The ordinary graph-pair transaction retains recovery snapshots until the
promotion marker is durable. A failed or interrupted uncommitted repair restores
the preceding graph pair; a committed repair emits any missing promotion event
on retry. Raw inputs, original source evidence and earlier immutable promotion
artifacts are preserved. The RML manifest explicitly identifies a retained
base plus targeted delta; its nested addition receipt carries the new context
and mapping execution hashes. Legacy mapping provenance describes the base,
not a fictitious full rerun.
