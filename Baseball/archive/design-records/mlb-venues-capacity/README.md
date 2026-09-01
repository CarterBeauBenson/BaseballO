# MLB venue spectator-accommodation amount

Status: **accepted 2026-08-30 — source-independent design**

MLB venue `capacity` measures a real Spectator Accommodation Amount inhering in
the Baseball Venue. The amount reflects installed Spectator Seats plus designed
standing-room accommodation. It is not merely a provider record state, a count
of spectators currently present, or an occupancy Directive.

Seats are Material Artifacts that bear a Sitting Artifact Function. A designed
standing-room area is a Site that is a continuant part of the Venue; its
accommodation function is borne by the Venue or the material infrastructure
that establishes that Site, never by the Site itself. Functions may exist while
unrealized. The amount Quality may continue to inhere when the Venue is empty.

The source supplies a response-scoped measurement but not the installation,
reconfiguration, or counting Process. No such Process or historical interval
is invented. This package proposes four classes and no object property.
