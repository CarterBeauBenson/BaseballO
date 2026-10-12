# M1: error-step credit across offensive metrics

Status: **under review**. This is an analytical policy proposal over existing
promoted RDF. It introduces no ontology terms, object properties, RML changes,
source acquisition, or graph rebuild. No approval or implementation is implied.

## Decision

Extend EG6A's accepted error-step exclusion to the numeric and breadth readers.
An explicitly adjudicated error-classified advancement contributes zero new
positive credit. Preserve independently supported contact/award/running steps,
actual terminal states, existing out attribution, and actual-end-state erosion.
An unspecified or ambiguously associated advance remains unresolved.

For a safely completed attributed consequence, retain TFS's existing denominator
`4 - originalStart` and use only credited forward distance in its progress
numerator. Do not restart the denominator at each row. A terminal out in that
same consequence still eliminates its prior progress under the accepted
terminal-out policy. Separate independent consequences retain their own scope.

| Complete supported consequence | Proposed progress | State used for erosion |
| --- | ---: | --- |
| Batter reaches first on a single, then third on an adjudicated error | `1/4` | Third |
| Runner starts first, reaches second on a hit, then third on an adjudicated error | `1/3` | Third |
| Same first-to-third path ends in an attributed out in that consequence | `0`; existing destruction still applies | Out |
| Runner starts second and reaches third only on an adjudicated error | `0` | Third |

Offensive Reach and Help use the existence of a separately credited positive,
not physical contact membership alone. Contribution Mix continues to count one
supported contribution per channel. Run Contributors counts distinct supported
offensive contributors to the scoring runner, excluding error-only steps.
Scoring History Length retains physical history membership, including error
segments; this proposal does not remove actual events. Empty Games retains EG6A.
Derived PAQ inputs and Empty Game Damage use these corrected components without
changing their existing reference, qualification, or aggregation rules.

## Existing evidence and scope

- [EG6A](../../archive/design-records/mlb-game-empty-game-final-boundaries/README.md)
  accepts the binary exclusion and explicitly supplies no numeric weights.
- [The existing contact policy](../../sparql/metrics/contact-progress-policy.json)
  leaves secondary errors during otherwise credited hits unresolved.
- [The cross-metric audit, A2](../../serving/RML-CROSS-METRIC-AUDIT.md)
  reproduces numerical credit for an error-classified contact step.
- EG6's retained cases 822945/61, 823623/34, 824018/86, 824429/18,
  824576/9, 824744/58 and /65, and 825062/87 contain the existing error
  attribution pattern. No wider source selection is proposed.

The field inventory is unchanged: runner-record identity joins an existing
resolution to its Error Process, Error Judgment Act and Error Decision ICE;
existing origin designations, safe/run/out decisions and complete supported
histories supply the physical path. Existing contact/award/independent-act
evidence supplies contributor identity. No new provider field is needed.

Reuse the accepted source-independent pattern in EG6. No graph shape changes
are proposed: physical parthood and safe destinations remain true even when a
metric assigns no positive credit. After approval, update only the analytical
policy, calculation/readers and their focused arithmetic/attribution checks;
NiFi prepares affected derived products from existing RDF.
