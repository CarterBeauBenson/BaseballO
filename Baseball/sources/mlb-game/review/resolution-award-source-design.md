# Award causes and rule requirements

Implements the [final user decision](../../../archive/design-records/runner-award-origin-final-decision/README.md).

The final user decision replaces event-specific award directives with
Walk/HBP **is cause of** the particular Baserunning Act and the applicable
Baseball Rule **requires** that act. Existing runners require positive source
force evidence (`r_adv_force`), exact next-base completion and same-event
identity. Reviewed/ambiguous PAs and unverified rule editions are withheld by
the current conservative source selection.

`BaserunningSegmentOriginDesignation` is about the act, designates the Base
from `movement.start`, and is part of its source record. `originBase` is not
substituted for start. No stasis, physical location, shared boundary or runner
continuity is inferred. The metric supplies HOME=0 for the PA batter. Existing
runners use their act's designation first; PA-start fallback requires positive
act-start and no-intervening-movement evidence, otherwise origin is unavailable.
The current source does not manufacture that fallback completeness evidence.

The generalized stasis and PA-start subclass remain for positively supported states. No new object properties or RDF index predicates are introduced.
