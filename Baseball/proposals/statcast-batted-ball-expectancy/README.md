# Statcast batted-ball expectancy models

Status: **under review — design only**

This package isolates `estimated_ba_using_speedangle` (xBA) and
`estimated_woba_using_speedangle` (xwOBA). The accepted inventory classifies
both as genuinely additional model outputs. They are information produced by a
versioned computation, not intrinsic qualities of a Plate Appearance or
Batted-Ball Motion Process.

xBA is probability-like and CCO Probability Measurement ICE requires the
likelihood of a Process or Process Aggregate as its measurement target. xwOBA
is an expected weighted value over possible outcomes and season-dependent
weights. The current ontology does not yet supply reviewed identities for those
possible/model targets. This package exposes those gaps and does not invent an
`ExpectedHitProcess`, `xBAQuality`, or `xwOBAQuality`.

Duplicate launch speed, launch angle, result, person, and game facts remain
owned by MLB-game. This review does not reopen them or authorize cross-source
RML. The governance `sourceIndependentMermaid` bucket points to
`source-specific-mermaid.md`.
