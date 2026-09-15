# MLB metric mapping completion review

Status: **under review; no implementation or ontologist acceptance recorded**.

Two concrete extensions are ready for review. They reuse existing BaseballO,
BFO and CCO vocabulary. They introduce **no classes, properties, or metric
formula changes**. M2 does introduce an explicitly described identity decision
for an existing judgment when it is the operative review judgment.

## Decisions requested together

**M1 — Counted fouls.** Extend the existing foul/strike mapping to ordinary
fouls that demonstrably change the operative count from one strike to two.
Use the preceding event's reconciled count, including intervening non-pitch
events. A foul with two strikes before and after remains a Foul Ball Process
without an additional Strike Process. No count-state ICE or new predicate is
introduced. The [contract](mapping-contract.md#m1-counted-fouls) specifies the
source gate and unchanged instance identities.

**M2 — Affirmed pitch reviews.** Map an explicit, completed, non-overturned
review of a called ball or called strike on its particular pitch, even when
the enclosing PA has no review narrative. Keep the original judgment and
decision distinct from the operative review judgment and decision. The
existing operative pitch judgment becomes the review act; its existing output
remains the operative decision. This avoids a second counted ball/strike.
The pitch's stable ID distinguishes reviews in the same PA. The affected
batter is reached through the pitch and actual batting participation; a
named challenger is not substituted for that batter. See the
[exact identity and assertion contract](mapping-contract.md#m2-affirmed-pitch-reviews).

Acceptance would authorize these two named semantic extensions and their
source-specific designs, source SHACL, focused proofs, and the necessary
MLB-game runtime-admission pin update. It would not ratify the global semantic
baseline, authorize new vocabulary, or accept the unresolved entries in the
[field inventory](field-selection-inventory.md).

## Evidence and implementation boundary

The unchanged game 824315 has **27 candidate second-strike fouls**, alongside
46 ordinary fouls that leave the count at two strikes. These are diagnostic
source counts, not claims that every candidate passes all admission gates.
It also has two explicit completed pitch reviews absent from the current
PA-narrative review entry point. The [evidence](source-evidence.md) gives exact
paths, IDs and counterexamples. The checked-in [capture](source-capture.json)
records the source hash and observations without altering the raw file.

The [source-independent shapes](source-independent-mermaid.md) and
[source-specific shapes](source-specific-mermaid.md) precede executable work.
No executable RML, context, SHACL, ontology, or admission pin has been changed
by this review. The required next sequence after a named acceptance is:

1. Archive and push the decision in its own commit.
2. Implement M1/M2 in the existing MLB-game lane and encode their graph
   constraints in that lane's SHACL. Keep source coverage reconciliation
   separate from graph conformance.
3. Prove a single source case, then one game with SHACL and semantic inspection.
4. Let NiFi own bounded ingestion and subsequent materialization asynchronously.

This package closes two mapping designs. It does **not** claim completion of
all metric mappings or player leaderboards. Official statistical attribution,
complete within-PA runner boundaries, non-pitch count awards, full defensive
act coverage, and all eligible unreviewed decisions have distinct remaining
contracts listed in the inventory. Their source fields must not be described
as absent merely because their mappings remain unfinished.

## Why acceptance is still needed

The repository's [AGENTS.md](../../../AGENTS.md) states: "General instructions
such as 'continue,' 'execute,' 'finish,' or 'take in this source' are not
approval for a new semantic assertion or a new pipeline topology. Approval
must identify the proposal or named modeling decision being accepted."
The current MLB source status also explicitly excludes new fields and
interpretations from its pinned acceptance. This is a review of M1/M2's
assertions and identity policy, not a request for file-by-file engineering
permission. Existing metric and C1/C2 decisions remain accepted.
