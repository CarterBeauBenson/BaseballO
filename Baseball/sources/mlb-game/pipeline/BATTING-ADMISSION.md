# B1 operational contract

[B1 was accepted](../../../archive/design-records/batting-leaderboard-admission/README.md)
and published in commit `543d951` before this implementation.

The existing source SHACL stage runs `batting-admission.py` against the exact
retained final payload and mapped Turtle. It first reconciles unfiltered
source membership, official player/team PA totals and roster context. Empty
batting-stat blocks imply zero only when nonnegative PA totals and an exact
zero team-total residual independently establish that result. Unresolved
credit, substitutions or source inconsistencies withhold qualification.

The script binds source expectations into
`../shacl/batting-admission.ttl`. Graph membership and cardinality decisions
execute in SHACL: exact PA/Batter Act/Role/bearer and adjudication paths,
recognized result types, every player's official count including zero, and
the full roster with the game's home/away context. The source expectations
remain proof inputs. They never become authoritative RDF or metric SQL facts.

Artifacts under `pipeline/evidence/mlb-game/<game>/<run>/`:

- `batting-admission.json`: status and hashes of source, RDF, implementation
  and validation artifacts.
- `batting-admission.source.json`: compact independent source expectations.
- `batting-admission.shapes.ttl` and `.report.ttl`: executable parameterized
  source profile and its validation report, when source reconciliation passes.

The graph-pair promotion marker binds the proof by path and hash. The serving
materializer verifies that marker, the exact promoted source/RDF identity,
the current proof implementation and retained artifacts. It stores proof
provenance in `metric_suite_admission`, separately from canonical RDF query
bindings in `metric_suite_evidence`. Queries derive PA counts and distinct
game/team exposure from those RDF bindings. A caller cannot submit proof flags.

Schedule preparation also retains `qualificationCoverage` in each compact
batch manifest, including nonfinal observations. Whole-response totals must
reconcile before it certifies a date, including a date with no games. Serving
compares every selected date and expected final game to promoted graphs;
missing days, unresolved games and missing/extra graphs withhold qualification.
Old manifests without the new completeness evidence do not certify a range.

A missing or failed batting proof does not stop unrelated accepted graph
ingestion. A validation execution error follows normal source retry/quarantine.
All full metric score populations remain independently required. B1 alone
cannot turn partial contact or award consequences into player leaders.

No source schedule, broad lifecycle topology, ontology term, RML mapping or
global semantic admission changes. The existing NiFi lane loads these
components on its normal invocations; no second scheduler is introduced.
