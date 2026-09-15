# Defensive and review evidence: concrete web research

Research date: September 14, 2026, America/New_York.

The user directed research instead of another questionnaire. The accepted
four-act example, actual role realization, independent-running attribution,
E1/C1/C2, separate review mechanisms, and batting qualification remain settled.
The September 14 assistant questionnaire is not an approval prerequisite for
this investigation, nor a record of accepted replacement policies.

## Correction to the previous blocker description

"Missing defensive evidence" was too broad. There are different evidence
products with different coverage. A failure to find a full act census in MLB
assist/putout credits does not establish that all public sources lack ordered
defensive information. Conversely, finding a sequence does not make each
symbol an intentional act or establish complete coverage of the current season.

### Retrosheet: accessible ordered evidence

Retrosheet documents throw sequences for pickoffs/caught stealing, relay
modifiers, and fielding sequences. Its `143/G1` example includes a deflection;
adjacent fielders therefore do not always imply a throw and catch. An unknown
fielder can be explicit. Its replay batter identifier is not necessarily the
player involved in the reviewed outcome.
[Event-file specification](https://www.retrosheet.org/eventfile.htm).

The parsed offering separately exposes `fseq`, `firstf`, fielders, source event
text, and full/deduced provenance. Those fields should not be collapsed into
assist totals. [Parsed-play specification](https://retrosheet.org/downloads/plays.html).
The inspected regular-season download catalog ends at 2025; it does not supply
the dashboard's September 2026 games.
[Release catalog](https://www.retrosheet.org/game.htm).

A bounded inspection of the published 2025 archive succeeded with HTTP 200:

- URL: `https://www.retrosheet.org/events/2025eve.zip`
- Response size: 2,527,926 bytes.
- SHA-256: `5ece2be6c8ec5b47b9d8d90f2ca533ceca7eee915c7e0997f9bd6d64b879303c`.
- Inspected member: `2025BAL.EVA`.
- Game `BAL202507291`, line 8460: event `CSH(262)` retains a repeated catcher
  position around the shortstop. Reducing that sequence to distinct fielders
  would discard information needed when researching repeated acts.
- Other inspected examples: `BAL202504020`, line 257, `PO1(13)`;
  `BAL202504130`, line 804, `POCS3(265)`.

These are source examples, not scored fixtures or promoted RDF. No archive was
ingested. The example's act count, complete causal structure, and MLB identity
join are not asserted. Source data are provided free by and copyrighted by
Retrosheet; its [data-use notice](https://retrosheet.org/downloads/plays.html)
specifies the attribution required for a downstream data product.

### Statcast: throwing and receiving products exist

The Arm Strength page offers individual-player throw inspection and a CSV
control. Its qualification counts vary by position: 100 throws for first base,
75 for second/short/third, and 50 for outfield. These support using the relevant
opportunity rather than batting PA for a throwing product; they do not validate
the assistant's proposed custom defensive-depth thresholds.
[Arm Strength](https://baseballsavant.mlb.com/leaderboard/arm-strength).

First Base Receiving covers 2021–2026 on the inspected page. It distinguishes
throws from second, short and third using location, runner speed and position
at receipt, with an eight-foot receiving-area restriction. Its filters and CSV
control establish a concrete receiving product, not a census of all defensive
acts. [First Base Receiving](https://baseballsavant.mlb.com/leaderboard/first-base-scoops-receiving).

Direct Python requests to the Arm Strength page and receiving CSV returned
HTTP 403. Their documentation was readable through web search/open, but
automated export access and event-level join coverage were not verified.
No credentials, access-control workaround, or alternate protected endpoint
was used. Record this as an access limitation, not absence of the data.

### FieldVision: public client, denied tracking request

MLB documents a tracking-based 3D viewer.
[Gameday 3D guide](https://www.mlb.com/news/mlb-gameday-3d-guide).

The linked public example is
`https://www.mlb.com/fieldvision-beta?gamePk=745340&playId=4f35220b-75e5-4abd-8cc7-eecf056d112e`.
Its public JavaScript was inspected for routing, without executing it or
collecting authentication material. It describes versioned manifests,
metadata, labels, plays, and binary tracking chunks. This establishes a
concrete technical lead, not a public bulk-data entitlement or an act ontology.

One unauthenticated request to its standalone client's configured endpoint,
`https://gcs-helper.bdata-gcp.mlbinfra.com/mannequin-data/745340/versions.json`,
returned **HTTP 401**. Investigation stopped at that access boundary. No
tracking payload or complete game coverage was obtained.

## Other factual gaps that research narrows

**ABS eligibility has official criteria.** Savant defines challenge opportunity
using an adverse called pitch, remaining challenges, and exclusions for a
position player pitching or technical unavailability. Its challenge rate uses
challengeable pitches, not only pitches actually challenged. This gives an
official route to the accepted eligible-decision denominator; remaining work
is exact source coverage, event state and graph admission. A source-defined
opportunity is distinct from its modeled strategic desirability.
[ABS definitions](https://baseballsavant.mlb.com/abs-metrics-documentation),
[ABS leaderboard](https://baseballsavant.mlb.com/leaderboard/abs-challenges).

**Official attribution and actual participation can be kept separate.**
Chadwick documents actual and result batter/pitcher fields and a substitution
extractor. It also warns that numbered assist/putout fields need not be
chronological, and that ordinary count fields can turn unknown counts into
zero. Preserve raw count text and source event text when evaluating this
candidate. These are concrete implementation constraints supporting the
user's existing separation decision, not another question about that decision.
[Chadwick documentation](https://chadwick.readthedocs.io/en/latest/cwevent.html).

**The ordinary Statcast CSV is not a full fielding-act log.** Its documented
`hit_location` identifies the first fielder to touch the ball, and its fielders
and counts describe specific pitch context. Those columns do not document an
exhaustive field/throw/catch/tag sequence.
[CSV documentation](https://baseballsavant.mlb.com/csv-docs).

## Candidate selection inventory

This is research in the existing review package. No source module is created.

| Candidate field/product | Selection | Concrete next evidence check |
| --- | --- | --- |
| Retrosheet game/player/lineup identifiers | Identity/join-only | Exact MLB identity crosswalk and in-game substitution scope |
| Retrosheet raw defensive sequences and relay details | Potentially additional; overlap unresolved | Compare against the same game's owning MLB payload; retain repeated participants and unknowns |
| Retrosheet assist/putout totals, ordinary outcomes and lineups | Already supplied where the authoritative MLB payload has them | Do not duplicate merely because the current mapping omits a field |
| Retrosheet parsed `fseq`/`firstf` | Derived within Retrosheet | Retain raw event text as the evidence; no separate assertion source for parser output |
| Retrosheet actual/result batter and substitution context | Meaning understood; duplicate/derived coverage check required | Reconcile against authoritative MLB attribution and count evidence |
| Statcast throwing/receiving observations | Potentially additional | Working public export, event grain, units, missingness and stable game/play joins |
| Statcast aggregate performance scores | Additional analytical products, unsuitable substitutes | Do not replace custom act depth or breadth with OAA or arm strength |
| FieldVision tracking chunks | Unresolved access and semantics | Requires legitimate access before schema/coverage assessment; present probe denied |
| ABS challenge-opportunity state | Owning MLB coverage audit first | Inventory challenges remaining, adverse call, position-player pitching and technical availability at each event |

## What this closes, and what remains engineering work

- Closed factual uncertainty: richer public historical defensive sequence
  evidence exists. Retrosheet was successfully accessed and a real repeated
  fielder example inspected.
- Closed factual uncertainty: public throwing/receiving products and explicit
  ABS opportunity definitions exist. Export and complete event coverage remain
  separate checks.
- Corrected scope: the current-season problem cannot be declared solved by a
  historical archive; an inaccessible tracking endpoint cannot be called usable.
- Implementation work: compare candidate evidence field by field with the
  authoritative source, prove exact joins and supported world-side acts, and
  carry accepted inputs through the existing source/SHACL/SPARQL/SQL lifecycle.
  New source/model admission still follows the repository's existing gates.

This research does not change the accepted metrics, introduce object
properties, or turn unavailable player scores into zeros. It also does not
require another vote on the already accepted four-act meaning, role kinds,
review denominator or independent-running policy.
