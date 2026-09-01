# MLB-game classification and geometry implementation authorization

Status: **accepted**

This administrative record combines the ontologist's explicit acceptance of
three separately reviewed packages:

- baseball pitch and batted-ball classification classes;
- baseball season segments and transaction periods; and
- baseball strike-zone geometry.

It authorizes their bounded implementation in the MLB-game source module and
its rebuildable query-index and SPARQL consumers. It introduces no additional
class, property, identity policy, or source interpretation.

The implementation must retain four negative boundaries from the accepted
review:

1. historical nominal-classification evidence does not drive OWL class
   inference; only the current rebuildable query-index graph receives explicit
   current subtype assertions;
2. transaction periods are Temporal Intervals, not Processes;
3. `BaseballStrikeZoneSite` has necessary restrictions only until its six
   identity-bearing geometric anchors are modeled; and
4. provider coordinates do not designate or mint a world-side batted-ball Site
   until the provider frame is grounded to the field.

Unresolved physical measurements in the active deferred-measurements package
remain blocked. This record does not authorize Statcast work.
