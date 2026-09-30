# Defensive act count replaces strict sequence depth

Accepted by Carter Beau Benson on September 30, 2026, before implementation.

The question contrasted:

- A: count four distinct supported defensive acts even when catching and
  tagging overlap; measure act count rather than the longest ordered chain.
- B: retain the longest strictly ordered chain, in which overlapping acts do
  not necessarily contribute separate sequential steps.

The user's answer was:

> A
>
> fix the other things

For the existing `resolution-depth` metric, count the distinct supported
Fielding Attempt, Throw, Catch Attempt and Tag Attempt individuals in each
complete defensive play. A Catch Attempt also typed Fielding Attempt counts
once. Distinct repeated performances count separately. Temporal overlap does
not reduce the count; strict BFO precedence is not required. Display the
metric as Defensive Acts and preserve its existing identifier for clients.
Selected-range player results remain means with the accepted defensive
participation minimum. PAQ-2.1 uses this accepted act-count dimension wherever
it previously used defensive depth.

This changes the metric, not the ontology or the identities of performances.
Completeness of acts and agents remains required; unsupported acts are not
invented. No object properties, ontology classes, replacement timestamps or
strict precedence assertions are authorized. Existing targeted RML repair and
source reacquisition permissions remain in force. Other authorized engineering
repairs should continue without another approval request.
