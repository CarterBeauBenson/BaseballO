# Competency questions

1. Does an MLB game-feed `passed_ball` or `wild_pitch` scoring classification independently establish a physical `PitchBallControlFailureProcess`?
   - No. It establishes the scorer-classified institutional process, its judgment, decision, rule, and source record.
2. Does an uncaught-third-strike classification independently establish that physical failure process?
   - No. The supported graph contains the institutional uncaught-third-strike process, strikeout, adjudication, rule, and unresolved source placeholder without fabricating a physical failure.
3. What must the MLB-game conformance gate do?
   - Require the supported institutional graph and reject every `PitchBallControlFailureProcess` instance in the MLB-game authoritative graph.
