# Source evidence

This proposal uses the repository's accepted MLB organizations review as its
evidence base. It does not acquire or retain new API JSON.

## Provider evidence already recorded

The accepted organizations source review observed team responses containing a
canonical Team identity, a season request/context value, and nested Division
identity/name fields. League and Division collection responses can also nest
related Organization identifiers. The accepted contract deliberately maps the
Organizations and names but emits no Team-to-Division relation because a
historically scoped institutional pattern had not yet been approved.

The current field inventory classifies Team `division.id` and `division.name`
as authoritative duplicates during reference-source migration. It treats the
nesting itself as blocked: co-occurrence identifies both Organizations but does
not establish a timeless affiliation. That blocker is the exact question this
package isolates.

The accepted organization mapping keys Teams and Divisions by provider
resource kind and ID, and may key Seasons/Plans by league and season. These
identity facts can be reused. Season and Plan identity do not themselves prove
membership, participation, agency, or a temporal boundary.

## Existing vocabulary

The candidate shape needs only accepted terms:

- Baseball Team (`base:BaseballTeam`);
- generic CCO Organization (`cco:ont00001180`) for the Division;
- Organization Member Role (`cco:ont00000175`);
- Gain of Role (`cco:ont00001194`);
- Loss of Role (`cco:ont00000613`);
- Stasis of Role (`cco:ont00000824`);
- Temporal Region (`obo:BFO_0000008`);
- Temporal Interval (`obo:BFO_0000202`);
- Calendar Date Identifier (`cco:ont00001340`);
- Day (`cco:ont00000800`);
- `inheres in` (`obo:BFO_0000197`);
- `has organizational context` (`cco:ont00001992`);
- `participates in` / `has participant`
  (`obo:BFO_0000056` / `obo:BFO_0000057`);
- `affects` (`cco:ont00001834`);
- `designates` (`cco:ont00001916`); and
- `occupies temporal region` (`obo:BFO_0000199`).

No new class or relation is proposed. A new particular Role individual per
continuous stint is an instance-identity policy, not a new universal. When a
boundary is supported, Gain or Loss has the Team as participant, affects the
exact Member Role, and occupies its own Temporal Region. The Team and Role
participate in the intervening Stasis, which occupies its own Temporal
Interval. The Stasis does not realize the Role. Gain or Loss typing alone does
not license a `realizes` relation to the affected Role.

## Evidence still needed

- Corpus proof that season-scoped Team acquisition returns the Division for
  the requested historical season rather than a present-day value.
- Coverage evidence for years in which a Team had no Division or the provider
  changed historical identifiers.
- A reviewed continuity rule for adjacent seasons and offseasons.
- Evidence identifying start/end Days, plus a reviewed localization rule for
  the Gain/Loss Temporal Regions and their relation to the Stasis interval, or
  an explicit decision to retain only coarser season-scoped or censored
  intervals. Exact adjacency is not assumed.
- A correction/provenance rule when repeated acquisitions disagree.

The authoritative graph may preserve the resulting Role history after source
payload deletion, but only claims actually warranted by that evidence can be
promoted.
