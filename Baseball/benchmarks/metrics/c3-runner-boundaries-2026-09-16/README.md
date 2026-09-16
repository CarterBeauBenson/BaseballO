# C3 implemented: action, replacement and placement boundaries

The user's three explicit approvals were recorded and pushed in **06cc732**
before implementation. The [accepted contract](../../../archive/design-records/mlb-game-runner-boundary-anchors/README.md)
adds no ontology classes or object properties. Existing C1 RML templates emit
the newly supported personal histories from the owning source context.

## Source coverage

The unchanged August 25 fixtures now have **12 of 15 games with complete
personal histories**, up from 9. Supported personal histories increase from
**363 to 404**. Every previously supported whole retains its identifier.
[The comparison](coverage.json) records each source hash, before/after counts,
remaining withheld halves and separate PA-boundary issues.

- Non-pitch terminal actions use the approved composite anchor, without
  equating an `actionPlayId` to a pitch's identity. Action out counts reconcile
  after their distinct runner outcomes; pitch and pickoff records retain their
  evidenced pre-out count scope.
- Pinch-runner replacement ends the outgoing person's history and starts the
  incoming person's distinct history. Earlier episodes never transfer.
- Placed runners begin at the explicit entry boundary. No fictitious advance,
  Safe judgment, physical location stasis or credited contribution is added.
- Full source witnesses and unresolved lifetime candidates remain in the
  manifest. Duplicate anchor tokens, inconsistent counts/times and uncertain
  prior-manifest identity or episode allocation changes fail or withhold the
  appropriate gate. A retry of the real full-game mapping preserves identity.

## Graph, query and SQL proof

Three isolated actual-RML fixtures cover one lifetime for each boundary kind.
Each passes exact source-bound SHACL using the existing mapping templates.

Whole game **823989** passes authoritative Jena SHACL with **42,045 triples**,
**40 personal histories** and **81 episode memberships**. The dedicated
runner-history SHACL admits that exact complete history population. It is
registered as the owning module's eighth operational profile and runs in NiFi
after RML and before promotion, retaining source/RDF/implementation/report hashes.

The canonical Jena query and exact SQL check recover all **14 scoring
histories** for Scoring History Length, with isolated one-game player means.
The public date-range request remains withheld without independent schedule
admission. This proof does not certify Run Contributors, all other metric
inputs, a season reference or a populated live dashboard.

Artifacts: [history admission](history-admission.json),
[source census](source-census.json), [RML proof](rml-proof.json),
[query/SQL proof](scoring-sql.json), [isolated mapping cases](one-history-rml.json).
Forty focused tests passed across the C3 source/SHACL tests, three actual-RML
cases in one test, existing runner-history regressions and profile ownership.
Both edited PowerShell entry points parse successfully.

## Remaining distinct gaps

- **823585:** Hamilton's top-tenth placed-runner history has no recorded
  Runner Resolution Episode. C3 explicitly leaves zero-episode histories
  unresolved rather than inventing one.
- **823826:** the third-out force at PA 61 lacks a supported state for another
  runner; the non-pitch review at PA 68 remains unresolved.
- **825042:** the non-pitch review at PA 70 remains unresolved.
- Replacement/placement base reports do not license physical PA-start stases.
  Their separate boundary proof remains withheld, as do ambiguous PA headers.

NiFi owns the existing asynchronous refresh and full repository gate. This
change does not alter the acquisition or recovery schedules, manually promote
a corpus, or claim that asynchronous live publication has finished.
