# BaseballO

**A baseball research system that can show why an answer is true.**

Most baseball sites are designed to tell you what happened: a player had two
hits, a pitch was called a strike, or a runner was out. BaseballO is designed
for the next question:

> What people, actions, calls, and recorded evidence make that answer true?

BaseballO keeps the parts of a play connected. A pitch is not just a row with a
result code. It can remain linked to the pitcher, batter, swing, contact, ball
movement, umpire's call, review, runner movement, and final scoring decision.
Researchers can ask new questions across those connections without first
flattening the game into a fixed set of statistics.

This is a working local research project, not a replacement for Baseball
Reference, FanGraphs, Statcast, or a production statistics website.

## The difference in baseball terms

Imagine that you want to study games in which a batter played but made no
meaningful offensive contribution.

A simple database query might count games with zero hits. That is easy, but it
does not answer the whole baseball question. What about a walk, sacrifice fly,
fielder's choice, or stolen base? What if a game's source record contains an
outcome the system does not yet understand?

BaseballO's current **Empty Games** question makes those choices explicit:

1. Start with every game in which the player appeared as a batter.
2. Look for a hit, walk, sacrifice fly, fielder's choice, or explicitly
   adjudicated stolen base.
3. Classify the game as empty only when none of that qualifying evidence is
   present.
4. Exclude a game instead of guessing when its plate-appearance vocabulary is
   outside the reviewed coverage boundary.
5. Divide Empty Games by Offensive Games Played when the user wants an
   empty-game percentage.

The result is still a number, but its definition, evidence boundary, generated
query, selected source-game scope, and denominator remain visible and
reproducible.

| A conventional statistics workflow often starts with | BaseballO starts with |
| --- | --- |
| a prepared statistical row | the people, roles, actions, calls, and outcomes in the game |
| a fixed definition in application code | a reviewed definition assembled from reusable baseball concepts |
| missing evidence treated according to an implicit rule | an explicit completeness rule that can refuse to classify |
| a player's team as a season-level attribute | the team role that player had in that particular game |
| an optimized table as the working source of truth | the complete game evidence as the source of truth, with rebuildable shortcuts |
| a result users are expected to trust | a result whose query and evidence contract can be inspected |

This does not make ordinary baseball databases wrong. They are better for
leaderboards, broad historical coverage, standings, and familiar player pages.
BaseballO is for questions where the definition of a measurement and the path
from game evidence to answer matter as much as the final value.

## Questions BaseballO is being built for

- How often did a player have an Empty Game, under a stated definition of
  offensive contribution?
- Did a reviewed call begin as a player or manager challenge, or as an
  umpire-initiated review?
- What was the original call, what did replay decide, and which call became
  operative?
- Which pitches became swings, contact, balls in play, and eventual runner
  outcomes?
- Which unusual results are absent because they truly did not occur, and which
  cannot be counted safely because the source evidence is incomplete?
- Can a faster summary return exactly the same answer as the complete game
  evidence?
- Can two compatible measurements be combined into a defensible percentage or
  ratio without allowing arbitrary formulas?

The long-term goal is not a larger menu of precomputed statistics. It is a
reusable description of baseball from which researchers can build and inspect
questions that were not anticipated when the data was loaded.

## What you can use now

The local BaseballO Explorer currently provides:

- batting, pitching, baserunning, game, team, venue, and official questions;
- 17 advanced questions about event chains, replay decisions, evidence
  completeness, and structural integrity;
- the reviewed Empty Games analytic and an Empty Games percentage;
- a safe Derived view for combining compatible base measurements;
- official-game-date presets for the latest day, seven days, 30 days, season to
  date, or a custom range;
- filters for season, game, player, team, and venue where they have an
  unambiguous baseball meaning;
- sortable result columns, CSV export, execution time, and the generated query;
  and
- read-only access to the complete game evidence stored in the local graph.

The checked-in research corpus contains 288 completed games with official dates
from July 14 through August 6, 2026, plus a separate development fixture. It is
large enough to test coverage and research workflows, but it is not a complete
season and should not be presented as one.

## What “show your work” means here

BaseballO keeps several promises that are easy to lose in an analytics system:

- **The raw game files stay unchanged.** Corrections and new interpretations
  happen downstream rather than rewriting the source.
- **Statistics are derived, not inserted as facts during import.** A researcher
  can inspect or revise the definition and rerun the question.
- **Missing evidence is not automatically zero.** Questions that rely on
  absence must first prove that the relevant source coverage is understood.
- **Game context is preserved.** A person can be a batter, pitcher, runner,
  umpire, or scorer in a particular game without turning that role into a
  permanent property of the person.
- **Faster query structures are disposable.** They must match answers from the
  complete game representation and can be rebuilt at any time.
- **Automated inferences are bounded.** Reasoning runs only over an explicitly
  selected part of a game, under fixed limits, and never changes the original
  game graph.

## How a game moves through the project

```mermaid
flowchart LR
    source[Completed-game JSON] --> preserve[Preserve the raw file]
    preserve --> describe[Connect players, roles, actions, calls, and outcomes]
    describe --> check[Check the game for required evidence and structure]
    check --> graph[Complete game knowledge graph]
    graph --> explorer[BaseballO Explorer]
    graph --> research[Reviewed research questions]
    graph --> shortcut[Rebuildable query shortcuts]
    shortcut --> compare[Exact-answer comparison]
    compare --> explorer
```

Apache NiFi runs the repeatable per-game workflow. RML describes how source
records become connected game evidence. SHACL checks required graph structure,
and Apache Jena Fuseki/TDB2 stores and queries it. These are implementation
choices; a baseball researcher can use the Explorer without needing to write or
understand those technologies.

## Current proof points

- 288 completed games are preserved in the checked-in raw corpus.
- 48 standard research queries and 17 advanced event-chain questions have
  reproducible bounded-corpus results.
- 18 complete-versus-accelerated query pairs have exact result comparisons; the
  separate operational runner selects 15 faster routes while the Explorer
  continues to use the complete game evidence.
- Three selective reasoning profiles are constrained to one chosen plate
  appearance and checked against 107 first-order proof obligations.
- Repository validation covers the game mapping, query contracts, graph
  checks, Explorer boundary, workflow evidence, reasoning limits, and query
  equivalence.

Those numbers demonstrate repeatability, not full historical coverage or a
claim that every baseball concept has already been modeled.

## Current boundaries

- The Explorer runs locally and is read-only; it is not publicly hosted.
- The corpus is a research sample, not a full season or historical database.
- Live MLB acquisition is disabled unless a user gives explicit approval.
- Some rare source outcomes remain deliberately generic rather than being
  assigned a more specific baseball meaning without sufficient evidence.
- Advanced questions that depend on something *not* occurring run only within
  documented completeness boundaries.
- The project does not yet provide row-by-row visual drill-down from every
  aggregate result to its source records, although the underlying evidence and
  generated queries are retained.

## Try the local Explorer

After installing the local prerequisites, start Fuseki and the Explorer from
the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File Baseball/scripts/infra/start-fuseki.ps1
Set-Location Baseball/web
npm start
```

Open <http://127.0.0.1:4173/>.

The [Explorer guide](Baseball/web/README.md) explains the current question
families and local run commands.

## Repository guide

The active implementation is under [`Baseball/`](Baseball/README.md).

- [Explorer and safe query builder](Baseball/web/README.md)
- [baseball research queries](Baseball/sparql/README.md)
- [game-data mapping and modeling policies](Baseball/mappings/README.md)
- [graph validation rules](Baseball/shacl/README.md)
- [workflow and local infrastructure](Baseball/infra/README.md)
- [selective reasoning experiment](Baseball/reasoning/README.md)
- [current continuation plan](Baseball/NEXT-PHASE.md)

## Validate the project

```powershell
python -m pip install -r Baseball/requirements-dev.txt
python Baseball/scripts/validate_repository.py
```

The validator checks that the repository's mappings, game samples, queries,
graph rules, Explorer, NiFi workflow contracts, bounded reasoning, and faster
query routes still agree with their reviewed evidence.
