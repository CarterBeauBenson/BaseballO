# Source evidence

## Provider and observation

Provider: MLB Stats API. Observed transiently on 2026-08-28 with date-bounded
official requests of the form:

<https://statsapi.mlb.com/api/v1/transactions?startDate=07/01/2026&endDate=08/28/2026>

No response JSON was written to the repository.

Observed top-level fields were `id`, `person`, optional `fromTeam`, optional
`toTeam`, `date`, `effectiveDate`, optional `resolutionDate`, `typeCode`,
`typeDesc`, and `description`.

In the observed bounded response:

- 4,746 rows had both `fromTeam` and `toTeam`;
- 9,589 rows had `toTeam` but no `fromTeam`;
- 57 rows had neither team.

This optionality prohibits shapes that require both teams for every record.

## Observed type heterogeneity

Observed type descriptions included Acquired, Assigned, Claimed Off Waivers,
Recalled, Designated for Assignment, Declared Free Agency, Number Change,
Obtained, Optioned, Outrighted, Released, Retired, Status Change, Selected,
Signed as Free Agent, Signed, Suspension, and Trade.

Provider descriptions outside that bounded list also include event kinds such
as death. The endpoint's product category therefore does not establish a
single world-side universal.

## Identity evidence

At least one trade transaction ID recurred across separate participant rows.
The repeated ID is evidence for an overall source transaction grouping, while
the Person-specific row remains a distinct record grain. Before RML, a
one-transaction fixture must prove whether the row identity is uniquely
determined by `(transaction id, person id)` or also needs another stable source
component. Array position is not an accepted identity component.

## Positive and nearby negative examples

Positive: a `Trade` grouping with from/to teams and several Person rows can
support one Baseball Personnel Trade Act with multiple Team agents that
has supported Gain of Role and Loss of Role parts involving the Persons and
their team-scoped Occupation Roles identified by separate descriptive records.

Nearby negative: an `Acquired` row with only `toTeam` does not state whether
the acquisition resulted from trade, waiver, contract formation, cash
consideration, or another act. The description cannot be promoted through a
guess.

Positive: a `Signed as Free Agent` record can support an Act of Contract
Formation and associated Act of Employment when the description and parties
provide the required evidence.

Nearby negative: a generic `Signed` code alone may describe a draft signing,
extension, minor-league contract, or other agreement. It remains unresolved
without the needed contract context.

Positive: a death record can be about CCO Death and a Person.

Nearby negative: placing that row under the provider's `transactions`
collection does not make Death a Baseball Personnel Transaction Act.

## Existing relation coverage

Existing BFO/CCO relations cover `is about`, `has participant`, `has agent`,
`affects`, `has input`, `has output`, `inheres in`, `has realization`, `designates`,
`occupies temporal region`, `is affiliated with`, and `has organizational
context`. Existing Stasis of Role and Temporal Interval structure expresses
the persistence of a team-scoped Occupation Role. No new object property or
roster-membership role is proposed.
