# H3: combined repair of existing MLB game selection

**Accepted by the user and activated on October 1.** The
[separate approval record](../../../archive/design-records/metric-source-c1-operation-2026-09-14/h3-approval-2026-10-01.md)
records acceptance of this repair and its scoped pins before implementation.
This supersedes the separate H2 and counted-foul prefix patches. The
[combined patch](rml-selection-repair-2026-10-01.patch) is now applied and remains
as the exact accepted preparation record; do not apply it again.

The user asked for a stage-wide repair, not another isolated fix. The
[September 30 narrow-repair authorization](../../../archive/design-records/metric-repair-scope-2026-09-30/answers.md)
already accepts targeted additions and overlapping temporal regions when
independent evidence reconciles the state. H3 implements those decisions using
existing classes, relations, identity patterns and RML maps. It changes no
ontology file or metric definition and performs no whole-game replacement or
corpus rebuild.

## Scope and evidence

The [audit snapshot](rml-selection-audit-2026-10-01.md) includes every reported
failure family in 2,404 regular-season staging manifests, containing 60,405
selected personal histories. These are diagnostic staging records, not a fresh
assertion of promoted-graph completeness. SQL contains 2,429 regular-season
games. The other 25 games have legacy additive manifest stubs: their original
history/count censuses are unavailable in their promotion receipts, while all
25 retain defensive censuses. Missing manifest detail is not proof of missing
RDF. Existing graph evidence refresh owns that separate issue.

Category diagnosis used 244 immutable retained game samples with recorded
failures, plus the five exact H2 responses. The candidate selects 752 missing
histories in an exact 209-game execution inventory. All 209 pass the worker's
source, history identity, selected-key and half-inning scope checks. Twelve
histories require existing runner-placement dependencies; thirteen require the
existing game-ending interval relation. No new identity policy is introduced.

The 204 sample-backed games use a separately hashed retained source revision.
The five H2 games require their exact original source hashes. Copies of the
immutable samples are owned by the repair worker; checked-in raw evidence is
never deleted or rewritten. Both original promotion and selected response
hashes remain in the receipts. One conflicting revision, game 823433, is
explicitly excluded.

This inventory is a bounded first execution set, **not all season coverage**.
Other manifest games with the same defects require the same owning lane to
identify their exact missing facts from retained or narrowly acquired evidence.
Do not report all RML gaps closed merely because these 209 additions finish.

## Shared causes repaired

| Family | Repair | Evidence still required |
| --- | --- | --- |
| Completed reviews | Reconcile all structured dispositions and the final narrative, including multiple reviews and nonterminal reviews | Explicit completed ruling, known review reason, counters, participants and movements; no reconstruction of an unsupported original call |
| Independent running and administrative records | Account for supported running effects; allow explicitly unchanged administrative counts | Unique movement association and full runner/out/base reconciliation; no administrative Act is invented |
| Overlapping clocks | Use independently reconciled pitch counters, stable identities, substitutions and PA boundaries | Internally valid intervals; preserve observed times; no strict precedence inferred from overlap or array order |
| Counted-foul prefixes | Select existing foul strikes after supported initial substitutions, independent running and completed reviews | Exact unchanged or progressing counts, rostered participants and actual pitch agency; contradictory prefixes stay excluded |
| Defensive descriptions | Preserve supported named catches/groundouts despite a completed final review or a following runner sentence | Narrative plus corroborating credits, participant and out/base evidence; no invented tag, throw order or complete defensive population |
| Repair completion and interruption | Compare the actual selected scope, allow independent cases past exhausted retries, resume post-promotion cleanup | Current promotion validation, unchanged source hashes, existing SHACL, exact base-plus-addition and durable retirement receipts |

The review reason names were checked against MLB's
[review reason enumeration](https://statsapi.mlb.com/api/v1/reviewReasons) and
[replay review rules](https://www.mlb.com/glossary/rules/replay-review).
Provider codes select existing accepted patterns; they do not create ontology
types or grant new semantics to review acts.

## Cases that must remain explicit

- A normal foul with two strikes does not increment the strike count. Its
  `NO_SECOND_STRIKE_INCREMENT` exclusion appears in 2,401 staging games and is
  expected. It is not a failed game.
- M2's affirming-review mapping intentionally does not assert an affirmation
  for an overturned ruling. H3 can reconcile the final runner state without
  falsely mapping that ruling as an affirmation.
- Q7 isolates a pinch-runner appearance with no movement episode. It does not
  invent a movement Process; complete neighboring histories remain usable.
- Stable terminal pickoff identities are absent in sample games 824071,
  824159, 824411, 824412, 824641, 824654 and 824808. Game 823840 also has a batter
  out associated with an unidentified final pickoff record. These require
  corrected source evidence or an explicitly reviewed identity decision.
- Game 824327 has duplicate batter-reach rows. Game 823433's retained revision
  lacks the movement to second required by its next PA state and conflicts
  with existing history alignment. Neither is silently deduplicated or
  repaired by fabricating an episode.
- Remaining source-reconciliation and unusable-clock reports, including
  824295, 824807 and 823631, remain recorded. An overlap allowance is not
  permission to invent missing or reversed time values.
- Defensive contact records frequently do not identify every performance or
  its order. Selecting more described acts does not make that population
  complete. This repair does not alter its metric denominator.

## Runtime behavior

NiFi owns the existing history, foul and defensive additive workers. The
history worker slices three existing personal-history maps, seven existing
placement maps only when needed, and the existing game-end map only when
needed. Existing source SHACL checks the union. The authoritative write is an
additive Graph Store POST; only the affected derived query index is replaced.
The ordinary promoted-graph event feeds SQL materialization.

A newer valid promotion is preserved and used as the base. Its current history
census must still reconcile to the exact approved missing-history keys. The
worker records both inventoried and actual base identities and checks that the
promotion did not change while preparing the delta. Unrelated completed
additions therefore do not automatically invalidate this repair.

The separately sourced history/resolution proofs keep both source identities.
Existing graph admission refresh runs after a successful H3 promotion, before
its owned input is retired. A receipt is written before deletion; a retry after
interruption finishes cleanup and event publication without adding RDF again.
No positive result is granted to an old withheld proof through compatibility.

The independently deployable queue changes are active code in the same change:
the foul and defense workers no longer stop all work behind an exhausted first
fixture; their success and retry checkpoints are bound to the current repair
scope/source and implementation;
the shared additive transaction compares a deterministic selection hash before
returning `already-complete`. Their six focused regressions pass.

## Focused developer evidence and approval

### Second operational pass

The October 1 follow-up found that the foul and defensive workers were
silently deferring below 1.5 GiB of available memory while the history worker
continued independently. Small additions now use a 256 MiB mapper and a
384 MiB retained-graph SHACL session; these stages run sequentially. The three
repair workers share one exclusive, crash-released memory slot and require
1 GiB free before starting. NiFi logs explicit memory/slot deferrals and owns
the next attempt. No source SHACL or validation requirement was removed.
Existing real RML and Jena report-equivalence checks pass at these heap sizes;
the resource-slot regression verifies exclusion and release after failure.

The foul worker also retains a pending case after promotion until evidence
refresh and cleanup finish. Previously, promotion could remove the missing
class report and hide an interrupted cleanup from the queue. It now records
the completed addition before finalization and persists refresh outcomes
before deleting its owned input. Recovery tests cover an interruption after
deletion, unchanged bounded retries, and rejecting a mismatched receipt.

Recorded live results after the resource repair:

- Game 822678: all four selected foul strikes added, 56 triples; the refreshed
  pitch-count admission is `admitted`. Runner-boundary and defensive admissions
  remain `withheld`; that outcome was not changed by the count repair.
- Game 822693: 32 missing defensive triples added through the existing D1 maps.
- The SQL publication from 21:17 UTC covers all 2,429 regular-season games and
  has complete participation coverage. It captured its inputs at 21:01 UTC,
  before these additions. Its dashboard still has five populated cards out of
  19; later promotion events belong to subsequent incremental SQL builds.

These fixes alter execution and recovery, not the accepted context, mappings,
ontology, scoped semantic pins or qualification criteria. They do not close
the explicitly documented source conflicts or all season coverage debt.

### Follow-through on the remaining queue and SQL publication

The next operational pass found 1,923 regular-season games with
`COMPLETE_RUNNER_BOUNDARIES` in the working SQL contribution inputs. This is a
recorded dependency count, not a claim that all 1,923 need new RDF. The fixed
209-game list alone cannot finish that backlog.

After its fixed cases, the same NiFi history worker now discovers additional
cases from retained promotion manifests that record withheld histories or
boundary issues. Each tick inspects at most 25 new manifests and prepares at
most one source response. It persists a game-specific repair request before
any acquisition, prefers retained responses (including immutable repository
samples), and uses the September 30 authorization only when that named game's
retained input is unavailable. The unchanged H3 context reconciles the current
response against existing history identities and episode membership. The
worker records exact missing keys and half innings before using its existing
additive RML/SHACL transaction. A conflict is retained as failed evidence.

If the unchanged selector finds no missing histories, the worker runs the
existing graph evidence refresh instead of executing RML. Its response remains
retained; a validation outcome does not pretend an RDF addition occurred.
Successful additions retain the existing receipt-before-deletion cleanup.
This is execution of the accepted narrow repair, not a new semantic selection,
ontology change, season acquisition request or database rebuild. The context
and semantic pins remain unchanged.

Evidence refresh previously searched only quarantine inputs and missed
immutable game samples already in the repository. It now considers both and
prefers a response matching the original promotion hash. It preserves the
separate source identity when a different retained response is used.

The foul worker now isolates complete PA repair scopes. In game 822682, PA 49
is selected by the accepted mapping, while PAs 50 and 58 remain excluded with
`SUBSTITUTION_IN_PREFIX` (a zero-episode pinch-runner case and a designated
hitter switch). The two excluded PAs no longer block PA 49. Partial completion
records the remaining pitches and keeps the acquired input; the unchanged
whole-game admission still determines whether pitch-count coverage is complete.

The SQL build at 22:08 UTC stopped with `Captured game changed before its SQL
read: 822682`, after retaining 2,898 game checkpoints. The builder now finishes
independent reads, recaptures only a changed game with its current promotion,
dimensions and admissions, and reads its metric facts and display labels under
the same existing writer lock. It records the recaptured promotion hashes in
the publication fingerprint. Active or uncommitted writes remain fenced out.
This avoids restarting the corpus pass merely because one repair finished
between input capture and the game's read.

NiFi then recorded repeated `Recent promotion or schedule update` deferrals:
the default 60-second global quiet window was continually reset by successful
repairs. The dashboard defaults to no global quiet window; its existing
per-game locks and current-promotion checks still protect every graph read.
An explicitly requested `--quiet-seconds` remains available.

Focused regressions cover discovery and identity conflicts, interrupted
acquisition receipts, partial foul repair without input retirement, retained
sample reuse, and SQL publication through both metric-read and label-read
races. The real 822682 selector yields only PA 49 and preserves both exclusions.
These are implementation checks. The last published dashboard still has five
populated cards out of 19; the recorded SQL run above did not publish a new
snapshot. NiFi owns the remaining additions and the next SQL publication.

Activation: acceptance was published first in `3e55b5e`; the exact patch was
then applied. The installed worker's five scope/dependency/cleanup tests and
four counted-foul-prefix tests pass. The existing NiFi history, foul and
defensive workers are running and valid. Their scheduled ticks own the repair
queue; no synchronous corpus job was started. This activation record is not a
claim that all queued additions or SQL publication have finished.

- 37 history/category tests pass, including source contradictions and the new
  defensive description cases.
- Four recorded foul-prefix regressions and six existing defensive-selection
  regressions pass; the six counted-foul completion checks also pass.
- Five history scope/dependency/cleanup regressions pass.
- Exact six-family proof compatibility and the existing dependency regression
  pass; unknown implementation hashes remain rejected.
- All 209 prepared execution selections match 752 exact expected histories.
- The complete held patch passes `git apply --check`.

These are component results, not live RDF or SQL delivery results. NiFi owns
mapping, SHACL, promotion and repository evidence after activation. SQL and UI
coverage must be checked from their actual outputs before calling this done.

AGENTS.md says: "Never refresh a semantic freeze, curation-debt baseline, or
admitted semantic fingerprint unless the user explicitly accepts the named
review package in the current conversation." The user's explicit H3 acceptance
is recorded separately above and includes these context/compatibility pins.
The global freeze remains unratified. The context changes from
`48f1f0daa2cfde9b899a5dad6bcf68f9eb7bcb9a1189715f2e3a2c7e9e432d5d` to
`7d90c64f64e03c920578bf40100677c1534a791792cf49a08b2426fe7c9141d6`;
unrelated protected hashes remain unchanged. The approval record precedes the
implementation; it does not assert that execution or SQL population succeeded.
