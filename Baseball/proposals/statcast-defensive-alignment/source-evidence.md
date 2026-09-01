# Source evidence

The archived accepted Statcast inventory classifies
`if_fielding_alignment` and `of_fielding_alignment` as genuinely additional
provider nominal classifications. That review also records the blockers:

- official value sets and decision rules are incomplete;
- actual player-Site and relative-location structure is not yet reviewed;
- the interval over which a configuration holds is unclear; and
- a Fielder aggregate, field Site, and interval do not independently
  distinguish a defensive configuration.

This package does not reopen duplicate fielder, game, pitch, position, or
lineup fields. MLB-game already has fielder participation and can derive
position occupants from lineup/substitution history after validation.

Existing vocabulary supplies Fielder Role/Person context, Baseball Field Site,
generic Site, Stasis, Temporal Interval, Nominal Measurement ICE, Reference
System, `has continuant part`, `located in`, `participates in`, `occupies
temporal region`, `is a nominal measurement of`, `uses reference system`, `has
text value`, and `is about`.

The provider's precise geometry, relative Site identity, classification
scheme/version, and pitch-relative timing remain missing evidence. This draft
tests whether a generic Stasis plus explicit player Sites can carry the world
structure without creating a one-off `DefensiveAlignment` class.
