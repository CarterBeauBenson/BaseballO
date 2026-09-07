# Offensive analytics redesign notes

Status: working design notes for review. This document does not change any
live SPARQL, serving contract, SQL build, UI calculation, or PAQ-1.0 result.

## Purpose

The Explorer should organize offensive analysis around a small number of
plain-language analytical categories. Each category must answer a distinct
question. The interface should then let the user change the scope without
turning every scope into a separate statistic.

The intended scopes are:

- one plate appearance;
- one game;
- a selected stretch of games; and
- a season.

Not every category has a meaningful result at every scope. In particular,
Empty Game begins at game grain.

## Current category sketch

The design currently names four of the intended five primary offensive
categories. The fifth category is deliberately unresolved rather than being
invented during implementation.

### 1. Damage

Question: **How much offensive damage did the plate appearance produce?**

Damage is result-oriented. It should describe the offensive consequence of a
plate appearance rather than whether the hitter followed a good process.

Supported scopes:

- plate appearance: damage caused by that result;
- game: accumulated damage in the game;
- stretch: accumulated damage in the selected games; and
- season: accumulated damage in the season.

The precise damage formula remains to be reviewed. Its name, formula, game
state assumptions, aggregation rule, and version must be visible through
**Show math**.

### 2. Grind

Question: **How difficult did the hitter make the plate appearance for the
opposing pitcher?**

Grind describes the work imposed on the pitcher. It is not a substitute for
Damage and must not reward the same pitch several times merely because that
pitch was also a swing, contact, and foul. A revised definition should use
pitch-grain evidence and count each pitch once, with explicitly reviewed rules
for meaningful events such as two-strike fouls.

Supported scopes:

- plate appearance: grind imposed during that plate appearance;
- game: accumulated grind in the game;
- stretch: accumulated grind in the selected games; and
- season: accumulated grind in the season.

Both totals and per-plate-appearance averages may be useful, but the UI must
label them distinctly.

### 3. Plate Appearance Quality (PAQ)

Question: **How good was the hitter's process in this plate appearance?**

PAQ is intended to identify good-process hitters, not merely restate batting
average, slugging, or Damage. It should remain a familiar baseball-style
number from `.000` through `1.000`.

The next version should consider:

- outcome, including whether the hitter reached base or recorded a hit;
- the opportunity at the start of the plate appearance, including runners and
  outs;
- execution relative to that opportunity;
- Grind; and
- batted-ball quality when the ball was put in play, so hard contact directly
  at a fielder can receive process credit despite the out.

The current design preference is for outcome to account for approximately 60%
of PAQ, rather than the 80% used by PAQ-1.0. The allocation and calculation of
the remaining approximately 40% are unresolved. No new formula should be
implemented until the game-context evidence is corrected and the component
rules are reviewed.

Supported scopes:

- plate appearance: the individual PAQ score;
- game: average PAQ, accompanied by the plate-appearance count;
- stretch: average PAQ across the selected games, accompanied by the
  plate-appearance count; and
- season: average PAQ for the season, accompanied by the plate-appearance
  count.

A cumulative sum of PAQ scores must not be presented as though it were average
PAQ. Rankings need a user-selectable minimum plate-appearance threshold and
must show the denominator.

PAQ-1.0 must remain versioned and reproducible. PAQ-2.0 should be a new
analytical version rather than a silent mutation of historical results.

### 4. Empty Game

Question: **In how many games did the player contribute nothing offensively?**

Empty Game remains a full-game classification. It is not a plate-appearance
score.

Supported scopes:

- game: whether the player's game was empty under the reviewed contribution
  policy;
- stretch: Empty Game count and Empty Game ratio in the selected games; and
- season: Empty Game count and Empty Game ratio in the season.

The denominator for the ratio must be the player's eligible offensive games
under the reviewed participation and completeness rules. The UI must show both
the count and denominator alongside the ratio.

### 5. Unresolved category

The fifth primary offensive category has not yet been named or defined. It
must be selected because it answers an important question not already answered
by Damage, Grind, PAQ, or Empty Game. It must not be a renamed duplicate or a
general bucket added only to make the count equal five.

## Game-context query defect

The current game-context result is suspected to be wrong and must not be used
as a trusted PAQ-2.0 input until it is investigated.

The corrected contract should distinguish:

1. **Starting context:** the inning, half-inning, outs, occupied bases, score,
   and other reviewed state immediately before the plate appearance begins.
2. **Plate-appearance events:** pitches, runner events, contact, review events,
   and other events occurring during the plate appearance.
3. **Ending context:** the state produced after the plate appearance and its
   associated runner resolutions.

The query must not infer the starting opportunity from the ending state or
allow a runner resolution produced during the plate appearance to leak
backward into its starting context. Runner events that can end or alter a
plate appearance require explicit regression cases.

Before designing PAQ-2.0, the game-context work should:

- identify the exact accepted RDF evidence for starting outs, starting base
  occupation, inning/half-inning, and score;
- compare the query result with a small set of known plate appearances that
  exercise empty bases, multiple occupied bases, two outs, runs scoring,
  steals/caught stealing, inning-ending runner outs, and walk-off situations;
- separate missing evidence from a genuine zero or empty-base state;
- add the accepted graph constraints to SHACL when they are conformance rules,
  and keep analytical reconstruction/equivalence checks in SPARQL;
- materialize the corrected reusable context grain in SQL only after exact
  same-corpus equivalence is demonstrated; and
- preserve the authoritative live-SPARQL path and version the derived grain.

Whether inning-and-score leverage should change PAQ, or should be exposed as a
separate companion analytic, remains unresolved. Base/out opportunity belongs
in the context review either way.

## Implementation boundary

No formula or live query is approved by this note. The next implementation
sequence is:

1. diagnose and correct the game-context query without changing the underlying
   accepted RDF semantics;
2. review and name the fifth offensive category;
3. define Damage, Grind, PAQ-2.0, and Empty Game aggregation contracts at each
   supported scope;
4. review PAQ-2.0 component definitions, weights, missing-data behavior,
   normalization, caps, bands, and rounding;
5. prove the new SPARQL against known plate appearances and the persistent
   corpus;
6. let NiFi materialize versioned reusable grains into SQL;
7. demonstrate exact route equivalence before admitting each SQL-backed UI
   route; and
8. expose the categories as plain-language Questions with **Show math** and
   evidence drill-down.
