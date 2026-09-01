# Field inventory and proposed term

| Field or entity | Disposition | Consequence |
| --- | --- | --- |
| roof-present `fieldInfo.roofType` code | authoritative duplicate; admitted after ownership cutover | Classify a response-supported Baseball Venue Roof. |
| open-air/no-roof code | configuration information | Preserve information about the Venue; emit no roof particular. |
| venue `id` | identity/join-only | Reuse the canonical Venue of which a supported roof is a continuant part. |
| open/closed observation | absent | Emit no operational state or Stasis. |
| request season | provenance | Does not establish an effective interval. |
| null/absent code | resolved absence | Emit no roof assertion. |

## Proposed class account

- **IRI:** `https://baseballontology.org/BaseballVenueRoof`
- **Named parent:** Material Artifact (`cco:ont00000995`).
- **Aristotelian definition:** A Baseball Venue Roof is a Material Artifact
  that is a continuant part of a Baseball Venue and bears a Covering Artifact
  Function realized in Processes in which some portion of that Venue is
  covered.
- **Necessary axioms proposed for the later overlay:** continuant part of some
  Baseball Venue; bearer of some Covering Artifact Function
  (`cco:ont00001310`).
- **Identity:** the particular installed roof artifact. Provider type and
  retrieval time do not establish installation, removal, or position history.
- **Example:** the retractable roof artifact installed at a covered ballpark.

No new function or object property is proposed.
