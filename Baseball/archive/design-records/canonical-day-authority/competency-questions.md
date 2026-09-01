# Competency questions

| ID | Question | Candidate answer |
| --- | --- | --- |
| DAY-01 | Is a Day source-specific? | No. A Day is a source-neutral Temporal Interval; source-specific Calendar Date Identifiers may designate it. |
| DAY-02 | How are consecutive Days ordered? | The earlier Day precedes the later Day, including Days for which no event source emitted a Process. |
| DAY-03 | How is a dated Process located? | The Process occupies its own Temporal Region; that region is a temporal part of the supported Day. The Process is not asserted to last the whole Day. |
| DAY-04 | Which Day contains an MLB Game? | Preserve the UTC timestamp and venue IANA zone. The Game region is a temporal part of the venue-local official baseball Day; the UTC identifier may separately locate the instant and UTC Day. |
| DAY-05 | How are transaction dates interpreted? | As MLB institutional Day evidence with unspecified timezone unless the source supplies a zone. Do not invent Eastern boundaries. |
| DAY-06 | How are corrections handled? | Reprocessing atomically replaces the affected source-owned daily graph and recomputes dependent role history while preserving prior manifests and hashes. |

## Negative tests

- A source-specific date string is not the Day.
- Two differently scoped calendar intervals are not identified merely because
  their lexical date is equal.
- A Process is not asserted to occupy the entire Day without exact evidence.
- A named graph is not typed as a Day or another world entity.
- An empty Day is not omitted from the canonical consecutive-Day sequence.

