# Graph-native metrics roadmap

Status: accepted implementation direction; attribution semantics and the
explicit policy decisions below remain unratified.

BaseballO will rebuild its offensive analytics around connected baseball
processes rather than weighted outcome checklists. The foundational analytical
object is the batter-attributed consequence structure of a plate appearance:
which offensive trajectories progressed, completed, remained active, eroded,
or were destroyed.

This roadmap does not approve a new ontology term, object property, identity
policy, RML assertion, or SHACL constraint. Those changes remain subject to the
repository's semantic review sequence.

## Target metric architecture

- Trajectory Fulfillment Score (TFS) is the foundational plate-appearance
  consequence measure.
- PAQ-2 is a league-relative percentile derived from TFS.
- PAQ-A compares a plate appearance with others beginning in the same occupied
  base and out state.
- Offensive Reach, Hidden Help, Rally Kill, Opportunity Erosion, Empty Games,
  and Contribution Path Diversity reuse the same attributed-consequence grain.
- Canonical analytical meaning remains in version-controlled SPARQL and metric
  contracts over authoritative RDF.
- SQLite contains rebuildable reusable facts and metric results for ordinary
  Explorer use. It is not semantic authority.
- Every public metric retains a human-readable explanation path to the
  supporting processes, judgments, decisions, and source records.
- PAQ-1.0 remains frozen and reproducible as a historical experimental metric.

## Execution checklist

### 0. Preserve the current baseline

- [ ] Freeze PAQ-1.0 without changing its existing query or meaning.
- [ ] Preserve its current SQL and UI behavior while PAQ-2 is developed.
- [ ] Capture representative PAQ-1 result and performance evidence.
- [ ] Introduce PAQ-2 under a distinct version and route.

### 1. Review the attribution contract

- [ ] Inventory current RDF paths for Batter Acts, Plate Appearances,
  Batted-Ball Play Processes, runner resolutions, start states, destinations,
  outs, judgments, decisions, and replay reviews.
- [ ] Determine whether accepted BFO, CCO, and BaseballO relations can express
  batter-linked consequences without a convenience object property.
- [ ] Draft a source-independent Mermaid proposal before changing RML.
- [ ] Distinguish batter-linked consequences from independent steals, caught
  stealing, pickoffs, balks, wild pitches, passed balls, and defensive
  indifference occurring during the same plate appearance.
- [ ] Cover batted-ball consequences and non-contact results such as walks,
  hit-by-pitch, and interference.
- [ ] Represent terminal runner destination and attributable out count through
  explicit RDF paths.
- [ ] Preserve original and operative decisions when replay changes a result.
- [ ] Obtain explicit ontologist review of the resulting graph pattern.

The reviewed pattern must answer:

1. Which runner resolutions follow from the batter-linked result?
2. Which runner resolutions occurred independently during the same plate
   appearance?
3. What state did each affected offensive participant occupy immediately
   before the consequence?
4. Did each participant finish safe at a base, score, become out, or remain
   unchanged?
5. How many outs were created by the batter-attributed consequence?
6. Which offensive trajectories remained active afterward?

### 2. Extend and prove the MLB-game graph

- [ ] Implement only the approved MLB-game RML additions.
- [ ] Translate the accepted graph contract into MLB-game SHACL.
- [ ] Keep TFS and PAQ out of authoritative source RML.
- [ ] Add fixtures for every required attribution and trajectory edge case.
- [ ] Run a one-game RML, SHACL, and semantic inspection proof.
- [ ] Run a small diverse-game proof before historical reconstruction.
- [ ] Reacquire historical payloads transiently through NiFi and replace graph
  pairs only after their new versions validate.

### 3. Build one reusable trajectory grain

- [ ] Produce one plate-appearance consequence row.
- [ ] Produce one affected-participant row per plate appearance.
- [ ] Retain participant identity and batter-versus-existing-runner status.
- [ ] Retain start state, terminal state, progress, destruction, alive-after
  status, attributable outs, and opportunity erosion.
- [ ] Retain supporting process and source-record IRIs.
- [ ] Retain metric, source-scope, completeness, contribution-policy, and
  reference-population versions.
- [ ] Do not reduce the serving product to final rendered scores.

### 4. Implement canonical metric contracts

- [ ] `trajectory-fulfillment-score.rq`
- [ ] `offensive-reach.rq`
- [ ] `hidden-help-rate.rq`
- [ ] `rally-kill-rate.rq`
- [ ] `opportunity-erosion.rq`
- [ ] `paq-2-core.rq`
- [ ] `paq-a.rq`
- [ ] `empty-game-damage.rq`
- [ ] `contribution-path-diversity.rq`
- [ ] `adjudication-volatility.rq`
- [ ] `review-dependence-rate.rq`
- [ ] Add every query to the metric catalog and source-scope catalog.
- [ ] Treat incomplete or unknown consequences as unknown, never as zero.

### 5. Extend the SQL serving layer

- [ ] Preserve the existing PAQ-1 serving columns for compatibility.
- [ ] Add versioned offensive-trajectory facts.
- [ ] Add versioned plate-appearance metric facts.
- [ ] Add normalized metric evidence sufficient for a `Why?` explanation.
- [ ] Add reference-population and percentile facts.
- [ ] Add indexes for plate appearance, player, game, season, state, and metric
  version.
- [ ] Recompute season percentile rankings from persisted trajectory facts
  after new games arrive rather than rereading every historical RDF graph.
- [ ] Promote only immutable validated serving builds.

The intended nightly sequence is:

```text
promoted game graphs
-> per-game trajectory SPARQL
-> reusable SQL facts
-> season-wide percentile refresh
-> validation
-> immutable serving-build promotion
```

### 6. Prove equivalence and preserve evidence

- [ ] Verify all mandatory trajectory fixtures and expected TFS values.
- [ ] Compare authoritative RDF and indexed RDF wherever an index is used.
- [ ] Compare canonical metric results and candidate SQL.
- [ ] Test ties, midranks, incomplete games, unknown result classes, replay
  changes, forced advances, and independent runner events.
- [ ] Benchmark authoritative SPARQL, indexed RDF, and SQL.
- [ ] Admit each Explorer route independently.
- [ ] Keep live SPARQL available as the research and fail-open path.

### 7. Release PAQ-2 as the first visible slice

- [ ] Show individual plate appearances.
- [ ] Show player mean and median PAQ.
- [ ] Show PAQ-A, top-quartile rate, bottom-quartile rate, and distribution.
- [ ] Support game, bounded stretch, and season views.
- [ ] Support a minimum-plate-appearance threshold for rankings.
- [ ] Link aggregate results to individual plate appearances.
- [ ] Render a human-readable `Why?` explanation from persisted evidence.
- [ ] Move the route to SQL only after end-to-end equivalence succeeds.

### 8. Expand after the vertical slice

- [ ] Empty Game Rate and Empty Game Damage.
- [ ] Offensive Reach.
- [ ] Hidden Help Rate.
- [ ] Rally Kill Rate and Rally Kill Severity.
- [ ] Contribution Path Diversity.
- [ ] Adjudication Volatility and Review Dependence Rate.

Later work remains gated by additional authoritative evidence:

- exact pitch-count state before Recovery Quality and PAQ-2.1;
- accepted fielding-act identity before Resolution Depth and Defender Breadth;
- cross-plate-appearance runner continuity before Run Construction Depth and
  Run Construction Breadth.

## Decisions still requiring explicit review

1. Whether PAQ-2 definitively uses a 0-100 percentile display, superseding the
   earlier `.000-1.000` display convention.
2. Whether the default reference population is all eligible MLB regular-season
   plate appearances in the selected season.
3. Whether reaching safely on an error or fielder's choice counts as positive
   progress for Empty Game classification.
4. Whether TFS components are retained with exact rational precision and
   rounded only for display. Exact internal precision is recommended.

Until those decisions and the attribution graph are approved, this directory
contains planning documentation only and no executable metric query.
