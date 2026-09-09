# Runner episodes and decision destinations

The four local runner object properties were withdrawn on 2026-09-09.
The [runner structural correction](../../../archive/design-records/runner-structural-correction/README.md) supersedes the earlier shortcut design.

`runnerEpisodes` pairs each supported existing movement act with its existing
resolution. `RunnerEpisodeMap` asserts the two occurrent parts and the PA;
`RunnerEpisodeAgentMap` identifies the act's agent, whose persistent Baserunner
Role already supplies the bearer/realization path. The source record is about
both parts and the episode. SHACL checks uniqueness, same runner, PA, field,
precedence and provenance.

`safeDecisionDestinations` supplies the sole destination Base referent of a
completed, non-out row's existing Safe Decision ICE. The judgment output
remains about its own Safe Process and additionally the counted destination.
The Base has its explicit source code identifier. A generic decision about
some Base does not suffice: this path uses the reviewed Safe Decision contract.

Walk/HBP completion rows no longer produce award links. The award directive
pattern is declared and validated, but this source does not yet establish
particular directive content/prescription. The award-completion query requires
that full path and the same counted safe destination. Run completions still
need destination evidence; no award binding is inferred merely from scoring.
