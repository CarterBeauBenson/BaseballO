# Advanced semantic analytics

This directory contains 17 exploratory analytics built from the full event
patterns in the authoritative game graphs. They are not shortcut/index queries,
and they do not flatten the graph. Each query starts from the act, process,
participant, temporal, containment, or adjudication evidence that supports its
claim.

The machine-readable catalog is
[`advanced-query-catalog.json`](advanced-query-catalog.json). The catalog's
`semanticMode` field is part of the query contract:

- `positive-evidence` counts only explicitly mapped evidence. A missing event is
  not interpreted as a baseball fact.
- `completeness-gated` uses absence or a mapped denominator and therefore states
  its coverage boundary in the query comments and catalog.
- `integrity-audit` returns structural defects and generic-only terminal outcome
  coverage gaps. Zero rows is the ideal outcome, but nonzero rows are useful
  findings rather than query failures.

## Query suite

| Query | What it exposes | Semantic mode |
|---|---|---|
| `plate-appearance-fingerprint.rq` | One PA row with outcome, duration, pitch, swing, contact, call, and runner-resolution counts | Positive evidence |
| `grinder-index.rq` | Transparent PA effort score plus its component counts and duration | Positive evidence |
| `swing-to-result-funnel.rq` | Pitch-to-swing-to-contact-to-terminal-result conversion by batter | Positive evidence |
| `whiff-and-take-profiles.rq` | Swings without contact and pitches without swings | Completeness-gated |
| `batter-pitcher-matchup-profiles.rq` | PA, pitch, swing, contact, hit, walk, and strikeout totals for each matchup | Positive evidence |
| `productive-plate-appearances.rq` | Non-hit PAs with explicit safe/run movement by another runner | Positive evidence |
| `contact-conversion.rq` | Terminal-contact conversion to hits, outs, errors, choices, and sacrifices | Positive evidence |
| `half-inning-rally-anatomy.rq` | PA, hit, walk, runner-resolution, and run counts within each half inning | Positive evidence |
| `game-action-density.rq` | Event counts per game and per mapped minute | Positive evidence |
| `scorer-classification-profile.rq` | Official-scorer judgment classifications | Positive evidence |
| `umpire-call-profile.rq` | On-field umpire pitch call versus operative replay call | Positive evidence |
| `review-outcome-profile.rq` | Review initiation, optional challenger evidence, supported transition, and final outcome | Positive evidence |
| `hit-diversity.rq` | Players with explicit single, double, triple, and home-run evidence | Positive evidence |
| `base-destination-profile.rq` | Safe/run destinations from explicit base-touching processes | Positive evidence |
| `steal-attempt-efficiency.rq` | Mapped attempts, successes, caught-stealing, and unresolved attempts | Completeness-gated |
| `unproductive-contact-games.rq` | Contact games without a reviewed positive contact contribution | Completeness-gated |
| `event-chain-integrity.rq` | Missing successors, judgments, decisions, and expected rules, plus generic-only terminal outcomes | Integrity audit |

## Deliberate non-claims

The current mapping does not support reliable leverage or win-probability
analytics, numeric pitch location or spray coordinates, official RBI/earned-run
or left-on-base continuity, or exact pitch-count state for every pitch. Those
ideas are recorded as blocked in the catalog rather than approximated from
unrelated fields. Adding them requires new source-to-RDF evidence and review;
it is not a query-writing problem alone.

MLB review descriptions identify whether a call was confirmed, upheld, or
overturned, but do not provide the original ruling as a separate structured
field. The mapping now creates a distinct reviewed-decision ICE only when the
final structured state is one of the accepted ball/strike or out/safe
alternatives: affirming reviews retain that decision type and overturned
reviews use its modeled binary opposite. Non-pitch reviews still do not identify
the individual base umpire whose call was reviewed, so no unsupported official
is assigned. Pitch reviews use the game’s identified home-plate umpire for the
on-field judgment and keep the replay decision separate.

Run the reproducible eight-game audit with:

```powershell
Baseball\scripts\pipeline\audit-advanced-queries.ps1
```

The audit permits zero rows only where the catalog explicitly says that an
empty result is meaningful for the sampled corpus.
