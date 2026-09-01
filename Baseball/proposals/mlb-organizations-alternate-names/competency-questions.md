# Decisions needed

| ID | Question | Decision options |
| --- | --- | --- |
| ORG-NAME-01 | Is 'teamName' a Proper Name or display fragment? | Decide from provider meaning and examples. |
| ORG-NAME-02 | Is 'clubName' a Proper Name of the same Baseball Team? | Establish bearer and official/preferred status separately. |
| ORG-NAME-03 | Does 'franchiseName' designate the Team or a distinct franchise-continuity entity? | Do not assume identity; block if the latter entity is not modeled. |
| ORG-NAME-04 | Does 'locationName' designate the Team? | Location text may be only a name component; do not mint a geographic entity or Team name by convenience. |
| ORG-NAME-05 | Are 'shortName'/'nameShort' genuine alternate names? | Decide separately for Team, League Organization, and Division Organization. |
| ORG-NAME-06 | How are changes scoped? | Preserve exact Unicode, content-version Name evidence, and require support before asserting preferred status or validity intervals. |

