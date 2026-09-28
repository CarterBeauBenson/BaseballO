# Complete player records within a selected range

On September 28, 2026, the user answered the following pending decision with
"Use your judgment. The season is over, I want to wrap this up":

> May I instead rank players whose entire selected-range record is complete,
> exclude affected players, and show that coverage? Each displayed average
> would still include that player's full selected period.

The selected implementation is to show those complete player records. A gap
affecting another player must not suppress an independently supported result.
The range stays exactly as selected; no fallback to one day or to a player's
subset of known plays is permitted.

- Completeness is assessed for each metric and player over the full range.
  Any applicable unresolved observation excludes that player's metric result.
- Unknown player attribution is handled conservatively: exclude every player
  it could affect, using independently supported participation and game scope.
  An unknown game population cannot be silently omitted.
- Display the incomplete league coverage and exclusion counts alongside the
  rankings. A complete individual record does not establish complete league
  coverage or justify an unqualified league-wide claim.
- Retain the accepted automatic participation minimums, exact pooled averages,
  Empty Games count, metric definitions and separate review mechanisms.
- Season-relative percentiles still need their accepted reference population;
  this decision does not authorize a percentile over an incomplete substitute.
- Existing source admissions remain truthful. This is an analytical and
  presentation change over existing RDF-derived results, not authorization
  for new ontology terms, object properties, RML changes or an RDF rebuild.

This decision is committed and published before its implementation.
