# MLB organization reference APIs

Status: **accepted by the ontologist on 2026-08-29; implementation pending**

This package reviews MLB teams, leagues, divisions, and season-plan data. The
team/league/division identity, name, and affiliation fields already occur in
the authoritative MLB game payload. They are therefore not admitted as new
assertions in a parallel source lane. A missing game RML binding is mapping
coverage debt, not source novelty.

The nonduplicative candidate surface is limited to explicit season-plan
evidence such as named planned phase boundaries. A future organization lane
must either own only that surface or receive an explicit ownership migration;
this draft creates no RML, SHACL, NiFi process group, source directory, or
graph namespace.

The proposal reuses the existing `BaseballTeam` class and proposes the smallest
coherent season vocabulary supported by accepted relations:

- `BaseballSeason`;
- `BaseballSeasonPhase`; and
- `BaseballSeasonPlan`.

The three proposed classes are source-independent vocabulary also needed to
complete the existing game semantics. `BaseballLeague` and
`BaseballDivision` remain ontology gaps: the source records establish provider
identities and nesting, but the accepted relations do not yet supply an
independent Organization differentia. In particular, a Baseball Rule ICE is
not a continuant part of the Organization whose competition it governs.
Names, codes, links, active flags, and provider counts are not converted into
domain classes. Season-configuration fields remain blocked where a boolean or
count does not establish a precise world- or plan-side referent.

This draft intentionally does not assert timeless team-to-league or
team-to-division affiliation, League participation in a Baseball Season, or a
League as the Season's Agent. Nor does the mere existence of a Plan license
synthesis of an Act of Planning. Those distinctions are review gates, not
implementation details.

The source evidence was inspected through transient official API responses.
No response JSON was written to the repository.
