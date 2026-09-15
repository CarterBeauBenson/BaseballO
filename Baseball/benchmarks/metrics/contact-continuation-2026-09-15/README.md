# B2 real contact continuation proof

The accepted example in game 824315 PA 6 now maps all six runner resolutions
into its existing Batted Ball Play. RML output has **38,422 triples**, exactly
three additional BFO parthood assertions over the prior 38,419-triple proof.
All domain identities are reused. Authoritative Jena SHACL and the independent
parameterized B2 source-owned SHACL both conform.

The source-selection tests reject missing membership, independent passed-ball
progress, unresolved review, substitutions, duplicate indexes, conflicting
classifications and wrong-person membership. Adversarial SHACL rejects a
missing scoring resolution and an extra resolution. The one-record actual RML
proof passed before the whole-game proof.

`inspection.rq` is a bounded inspection of the accepted PA 6 example, whose
complete admitted surviving paths all positively advance. It identifies two
surviving positive personal histories and excludes the batter's out-ending
history, giving Offensive Reach **2**. It is not a general positivity adapter.
`result.json` binds the immutable source and tested RDF hashes.

NiFi now owns the same B2 validation in its source-SHACL stage before promotion.
This developer proof did not promote RDF, refresh the corpus or populate a
player leaderboard. Complete PA/reference populations and the newly accepted
additional mapping work remain unfinished. Shared strikeout/runner-out
attribution is unresolved after the user's hit-and-run counterexample.
