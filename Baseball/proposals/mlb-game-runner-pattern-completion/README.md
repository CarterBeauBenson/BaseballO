# R1: finish existing runner patterns in 26 affected games

Under review. No execution or semantic approval is recorded.

## Requested decision

Authorize a targeted, additive completion of the already accepted runner
episode, endpoint and personal-history patterns in the 26 games listed in
`candidate-inventory.json`. All have retained source inputs. Reuse the current
RML mappings and their current selectors unchanged; this is execution scope,
not permission to invent classes, properties, identities or interpretations.

The inventory identifies 2,023 candidate PAs from existing SQL diagnostics.
It is a candidate list, not a claim that every row is repairable. Select only
runner rows whose retained source agrees with the existing graph's game, PA,
runner, act and outcome identity. Existing contradictory facts, unsupported
histories and unmatched referents remain unresolved. No API acquisition is
requested. Preserve the entire existing graph and add only absent triples.

The permitted pattern includes the following existing mapping families and
their already accepted referents:

- Runner Resolution Episode, its Baserunning Act and resolution parts, its
  PA containment, the act's evidenced agent, and the source record's aboutness.
- Explicit segment origins and Safe Decision destinations, with their existing
  base artifacts and designation/identifier records.
- Independently reconciled personal runner histories, temporal regions and
  episode memberships, including the current approved ending and placement
  patterns where the retained source supports them. Unsupported clocks and
  zero-episode histories retain the current T1/Q7 behavior.
- Existing supported contact and Walk/HBP attribution for those same selected
  runner resolutions, with the already accepted rule/record dependencies.

These are full supported patterns, rather than another fixed eight-triple
exception. Engineering may include the existing dependency maps necessary to
express these patterns, without a new approval for every file. This does not
authorize new mapping logic, unrelated pitches, defensive/review populations,
new result types, graph replacement or a database rebuild.

## Concrete observed failure

Game 823200, PA 36, runner row 0 is Ezequiel Tovar's double. The retained response
identifies runner 678662 and destination second base. Existing RDF contains
`runner-act/movement/36/0`, typed Baserunning Act, realizing that player's
Baserunner Role and having that player as participant. The resolution is
`runner-resolution/reach/36/0`. The episode and explicit agent link are absent.
The SQL reader consequently returns the existing act and Safe Process but
cannot bind the complete runner pattern. PAs 16 and 52 similarly describe
Tovar's ordinary outs in the retained source.

The retained witness for this game is pinned in the inventory. This is known
mapping coverage debt. It is not absent MLB evidence, a SQL arithmetic problem,
or authorization to infer the missing links directly inside the metric code.
The independent Help calculation repair in `2bc0772` remains valid and does not
depend on this proposal.

## Competency questions and proposed answers

- May existing runner rows support the same episode/agent/endpoint pattern
  already accepted for W2 outside W1's intentional walks? Yes, when the
  unchanged selectors and scoped SHACL support the exact row and dependencies.
- May an existing complete, independently reconciled personal history contain
  the selected episodes using the accepted C1 pattern? Yes; incomplete or
  unsupported histories remain withheld under the current rules.
- Does completing these runner patterns certify every metric, every PA, all
  defensive actions, or a full percentile reference? No. Their independent
  source admissions and metric prerequisites still apply.
- May the repair delete or replace unrelated RDF, alter source bytes, fabricate
  timestamps, reduce qualification minimums or drop missing observations? No.

## Field selection and de-duplication

| Retained authoritative source field | Classification | Existing use |
| --- | --- | --- |
| gamePk, PA index, runner-row index | Identity/join-only | Match accepted entity identities |
| runner identifier and movement resolution | Already supplied; mapping coverage debt | Actual runner, act, episode and resolution |
| origin, destination, safe/out/scored state | Already supplied; mapping coverage debt | Existing endpoint and designation patterns |
| supported event/contact/award attribution | Already supplied; mapping coverage debt | Existing causal/consequence pattern |
| full ordered runner history and replacements | Deterministically derived by accepted reconciliation | Existing personal history and membership |
| supported temporal boundaries | Already supplied | Preserve current T1 omission rules |
| ambiguous history, strategy or attribution | Unresolved | Do not add a speculative assertion |

## Bounded implementation after acceptance

Use the existing MLB-game additive transaction and SHACL machinery. Pin each
selected source witness and base graph. Run only the selected existing RML
families with their necessary accepted dependencies; subtract already present
triples. Validate the affected patterns against the base plus additions. A
conflict stops that candidate. Record the exact added triples, preserve all base
triples, and refresh only the affected derived query index and SQL partitions.
NiFi owns retries, provenance and execution. No whole-game replacement is
substituted for missing targeted execution support.

The current graph can still have distinct count, timing, strategy, defensive
and review gaps after this addition. R1 does not claim to solve all 19 metrics
by itself. K1's compound strikeout result remains a separate named decision.

## Existing semantic anchors

- `archive/design-records/runner-continuity-boundary-projection/review.json`
- `archive/design-records/mlb-game-w1-award-dependencies/review.json`
- `archive/design-records/mlb-game-zero-episode-history-isolation/review.json`
- `archive/design-records/mlb-game-clock-conflict-isolation/review.json`

No new ontology term or object property is proposed.
