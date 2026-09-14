# Worked metric presentation check — 2026-09-14

The Explorer now presents 25 hypothetical scenarios across all 20 metrics.
The [worked guide](../../../web/metric-worked-examples.md) and browser JSON are
generated from the existing calculation functions with separately specified
expected answers. No example is a source fact or a selected-game result.

Focused verification:

- 18 tests passed in `web/tests/metric-suite.test.mjs`, including every worked
  calculation, generated-artifact drift, exact display formatting and the
  independent static example route.
- `web/tests/metrics-browser-smoke.ps1` visited all 20 metric choices in isolated
  headless Chrome. Each showed its explanation and answer while the live-result
  download remained disabled until an actual game query completed.
- The August 25 live result still showed Dylan Beavers, limited award scope and
  exact TFS 25/12. Selecting the hypothetical passed-ball or third-out scenario
  did not alter that result or disable its matching download.
- Late success and failure responses remained unable to overwrite changed
  selections. Desktop and 390-pixel mobile checks passed; opening the worked
  explanation introduced no horizontal overflow.

The [mobile capture](mobile.png) was visually inspected. Its SHA-256 is
`f98e0c984b2abeaee9bf9507934ef39c490d60d2f983fca4b3aad35c10d0e913`.
It shows the hypothetical third-out example alongside the actual date-selection
controls. This is a presentation capture, not evidence of expanded live metric
coverage. Complete runner histories and other documented source requirements
remain unresolved.
