# Runner records and review subjects, September 16

Focused implementation of accepted E1/C1, M2 CQ7 and Q4. No ontology term,
object property, RML template, lifetime identity policy or archived approval
was changed. The context pin remains frozen/unratified under the existing
published C1 decision. The checked-in raw fixtures are unchanged.

- [Source coverage](coverage.json): complete histories rise from 8 to 9 of the
  15 August 25 games; personal histories rise from 360 to 363. All six remaining
  games retain their exact withheld-half reasons and separate timing issues.
- [RML/source SHACL proof](rml-proof.json): game 822773 has 35 histories, 83
  episode links and eight scoring histories; 36,153 triples conform. Its one
  ambiguous PA-start boundary is still withheld.
- [Review graph-to-SQL proof](review-sql.json): two supported pitch subjects
  identify Isaac Collins (686555) and Alejandro Kirk (672386). The latter is a
  pinch hitter who supplied the PA's only actual batting stint. Querying actual
  participation avoids assigning an earlier pitch to a later replacement.
- [Scoring History Length through SQL](scoring-depth-sql.json): all eight
  counted runs resolve, and isolated player means retain the exact values.
- The C1 and runner-resolution census now share the exact empty-strikeout
  bookkeeping rule. Null fields alone do not establish an out or advance;
  the safe WP/PB companion remains the one real movement.
- A completed affirmed ordinary foul with no movement/out effect can retain
  a runner history without expanding counted-foul/review RDF. M3/M4 remains
  pending its named decision.

The review query retains its full supporting pitch, motion, PA and Batter Act
paths. Conflicting subjects, missing links or several batting stints withhold
assignment. It does not infer a review mechanism, legal eligibility, a complete
population or a qualified player leaderboard. The existing disposition
calculation and exact SQL result remain equal.

Focused tests: 28 source/history tests and 18 review/serving tests pass. The
real-game proof uses Jena and an isolated SQLite database. NiFi owns promotion,
selected-range validation and serving publication; these developer artifacts
do not assert a completed live refresh.

The combined run-metric proof exposed one [remaining contribution gap](run-contributor-gap.json):
game 822773, PA 83, runner row 0 is Brett Bateman's first-to-second advance on
defensive indifference, before Nathan Lukes's contact. The personal history is
complete, but the graph does not yet establish the independent contribution
channel needed by Run Contributors. Seven contributor results resolve; that
eighth result stays withheld. Scoring History Length is independently checked
for all eight runs. No steal is invented and the advance is not credited to
Lukes. The proof tool's default still checks both metrics; its explicit
`--metrics` selector records exactly the independently tested metric.

The recorded NiFi proof failure for run
`78ba6e06299f4fe7945c49851da34136` was `implementation-changed` during serving
materialization, after source promotion. The existing asynchronous recovery
handler recognizes that specific failure. No schedule was disabled, no failed
evidence was erased, and no healthy run was repeatedly polled.
