# BaseballO roadmap

This is the ordered continuation plan. Current metric gaps and the last verified
publication are in [metric readiness](serving/METRIC-READINESS.md). Runtime
queues and build progress belong to NiFi's owner records, not this work queue.
The [previous roadmap](archive/operational-history/2026-09-23/ROADMAP.md) is
retained as history; its completed setup tasks and superseded design questions
are not instructions to repeat that work.

## Fixed architecture and scope

```text
Authorized source ingestion: API -> RML -> source SHACL -> authoritative Fuseki
Metric serving: existing RDF -> SPARQL and calculations in NiFi -> prepared SQL -> UI
```

Authoritative RDF is persistent. Reviewed game query indexes and SQL products
are derived and replaceable. Seven detachable MLB source modules own acquisition,
validation, promotion, retry, quarantine and provenance. Cross-source work begins
at the triple store. The dashboard's SQL owner is independent of source ingestion,
the legacy report builder and authority SQL.

Metric, performance and UI work starts from existing promoted RDF. A missing
input is a precisely recorded gap. An approved source addition preserves unrelated
RDF; a full RDF rebuild requires explicit authorization. The September 17 batch's
permission is not a standing rebuild instruction.

## 1. Populate the nineteen dashboard cards

The active [RML repair plan](sources/mlb-game/review/rml-audit-2026-10-03.md#current-repair-plan-and-scope)
was expanded on October 4 to cover H4, all recorded failure groups, remaining
history work, stale evidence, and a bounded review of all seven source modules.
Both H4 additions are promoted (110 triples total). The observer now distinguishes
current repair scopes and superseded history proofs; two old Transactions
promotion failures also completed without remapping. The new
[F8 foul-selector](archive/design-records/mlb-game-foul-substitution-review-completion/README.md)
and [P1 pitching-participation](archive/design-records/mlb-game-actual-pitcher-participation/README.md)
packages were accepted together on October 4 and implemented after the separate
acceptance commit `9b41838`. P1 has promoted its exact two removals and three
additions in 823420. F8 is active in the existing foul lane; the repair plan
records completed versus queued games. Remaining history comparisons stay with NiFi;
the plan distinguishes actual defects from source/modeling exclusions. Continue
independent metric work over valid RDF.

The October 2 RML repair snapshot is covered by
[F5/D2](archive/design-records/mlb-game-foul-defense-selection-repair/README.md): the
accepted context repair for 14 foul-selector failures and 14 defensive census
failures is active with its exact protected-pin update. Existing NiFi lanes own
their bounded retries. The separate 822861 foul worker source-census fix has
promoted 42 missing triples. Keep NiFi promotion and SQL delivery separate from
offline repair checks.

1. Apply the independent roster/player and PA-boundary admission repairs through the existing
   NiFi evidence worker and affected SQL player projections. Preserve the
   existing database and RDF. The four retained retries for 822848, 822854,
   822936 and 823338 are complete and published; do not repeat them.
2. Inspect published selected-period player rows and exact gaps. September 21-27
   has **11/19 named, qualified leaderboards** in its last verified publication.
   The month has 5/19 populated cards and no roster gaps. The full season has
   all 2,429 expected games and verified rosters, but only **5/19 populated
   cards**. The previously missing game 823087 and prepared player names are
   already published. Use the dated readiness record for deployment evidence;
   recovered admissions are not populated leaderboard counts.
3. Complete supported contribution, progress, Empty Game and scoring-history
   calculations from existing RDF. Keep unknown contribution ownership and
   incomplete populations explicit; do not drop observations to fill a card.
4. W2 was explicitly approved and its first W1/W2 addition was promoted on
   September 29 at 14:23 Eastern. Game 822864 / PA 54 received only the 15 missing
   award facts and eight approved dependencies; its SQL update is pending. Resolve the
   remaining count, PA-boundary, defensive and review gaps in their
   owners. The [readiness table](serving/METRIC-READINESS.md#remaining-work-by-metric)
   identifies their dependencies and concrete known cases. New ontology/RML
   semantics still require the named user decision.
5. Verify named qualified players, selected-period averages, the Empty Games
   count, automatic top five and expanded details for all 19 cards in the
   published dashboard. Source promotion or SQL build success alone is not this
   delivery outcome.

Settled decisions remain settled: exact fractions internally, percentile display
on 0-100 for PAQ, the selected season's eligible regular-season PA reference,
averages over the selected period except Empty Games as a count with no
appearance minimum, automatic batting qualification for rates and averages
of 3.1 PA per team game, role-appropriate other minimums,
separate review mechanisms and backend-only Role Realization Breadth.
The September 28 decision also permits individually complete player records
when other players have gaps. Exclude an affected player's entire selected-range
record and disclose coverage; retain full season-reference requirements and
the existing participation minima. The range must never shrink silently.

Completed prerequisites include the independent dashboard builder, prepared
player names and historical ranks, reusable game products, resumable SQL
partitions, exact proof-compatibility reuse, all four latest-day B1 repairs and
the two Q7 game additions. Do not queue them again as new work. Publication of
the latest results is tracked separately in metric readiness.

## 2. Keep operation incremental and recoverable

The [September 24 skeptical review](serving/ARCHITECTURE-REVIEW.md) records the
repaired request-time RDF fallback, cross-product fallback and missing/corrupt
dashboard publication recovery. Its remaining engineering concerns are shared
report/dashboard imports and calculation fingerprints that invalidate more
game work than the changed metric requires. These are engineering boundaries,
not requests for new source ingestion or semantic review.

- Diagnose recorded source or serving failures from terminal evidence, repair
  their cause and use the owning bounded retry. Do not monitor healthy runs.
- Tune the existing current/repair/historical queue priorities and bounded
  workers from recorded timings and memory limits. Source SHACL already reuses
  one Jena load per game while retaining each profile's report.
- Keep dashboard, full-report, authority SQL, repository evidence and RDF recovery
  independent. Preserve the published product when its replacement fails.
- Complete the remaining recovery acceptance work in
  [production readiness](infra/PRODUCTION-READINESS.md) and
  [RDF recovery](infra/RDF-RECOVERY.md): real backup/export/restore evidence,
  recovery objectives and the remaining host/configuration recovery scope.
- Keep acquisition at 05:00 Eastern and the user-authorized 15-minute batch
  checker. The completed temporary Q7 repair timer is stopped.

The configured NiFi-port migration fix, shared provisioning helpers, authority
lock recovery and report checkpointing are implemented. Their old roadmap
entries are not open implementation tasks. See the
[operational delivery record](infra/OPERATIONS-IMPROVEMENTS.md).

## 3. Extend legacy Explorer SQL only when useful

The legacy Explorer is separate from `/metrics`. Its contract still admits
PAQ-1/Good At Bat and supporting options to SQL; other families retain their
existing SPARQL routes pending family-specific result equivalence.

- Complete a family's row, filter, aggregation and date-scope equivalence before
  admitting that family to SQL. Existing shared grains and all 56 static DSQ
  tables are implemented candidates, not universal route admission.
- Add fact-to-fact bridge modules only for a concrete supported question and
  prove its equivalence through the existing owner.
- Preserve RDF/SQL timing evidence at matching corpus fingerprints.
- Keep official date/game-type provenance explicit. Accepted season-phase RDF
  is already available as a fallback and consistency check; a wholly RDF-only
  historical classification still needs coverage/equivalence evidence.

## 4. Review source and ontology gaps independently

Use the single [proposal catalog](proposals/README.md) for remaining MLB field
coverage, temporal role histories and future-source decisions. Operationally
successful ingestion does not establish complete API mapping. Existing-field
coverage debt stays in its source lane; do not reacquire or remap a season
because a metric exposes one omitted case.

The ontologist owns classes, axioms, identity policies and genuinely new modeling
assumptions. New object properties are prohibited. Existing ontology curation
debt remains recorded in [governance](governance/README.md), including unresolved
structural findings; documentation cleanup does not settle those decisions.

Statcast's rejected implementation remains retired. Fresh field inventories and
review-only geometry/process-profile designs need explicit acceptance before a
new detachable module is implemented. Weather and travel/rest remain later,
separate source families.

## Working and publishing

Use `dev`, fetch before publishing, and commit and push completed in-scope work
under [AGENTS.md](../AGENTS.md). Git was reauthorized on September 8. Never push
directly to `main`, rewrite published history or restore GitHub validation
without explicit authorization.

Use only the smallest useful developer check for changed behavior. Documentation
changes require diff review and `git diff --check`. NiFi's separate Repository
Evidence observer owns aggregate validation. Continue independent authorized
work when a semantic gap blocks one source assertion; do not make the entire
project wait on it.
