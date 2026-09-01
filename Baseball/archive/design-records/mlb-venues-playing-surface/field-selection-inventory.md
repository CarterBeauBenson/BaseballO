# Field inventory and proposed term

| Field or entity | Disposition | Consequence |
| --- | --- | --- |
| `fieldInfo.turfType` | authoritative duplicate; admitted after ownership cutover | Classify a response-supported Baseball Playing Surface under a pinned Reference System. |
| Baseball Field Site | accepted distinct entity | Remains the Site at which baseball occurs; never becomes material turf. |
| venue `id` | identity/join-only | Reuse the canonical Venue of which the surface is a continuant part. |
| request season | provenance | Does not prove an effective interval. |
| null/absent code | resolved absence | Emit no surface witness or classification. |
| unknown present code | invalid input | Fail the pinned code-list gate before RML. |

## Proposed class account

- **IRI:** `https://baseballontology.org/BaseballPlayingSurface`
- **Named parent:** Material Artifact (`cco:ont00000995`).
- **Aristotelian definition:** A Baseball Playing Surface is a Material
  Artifact that is a continuant part of a Baseball Venue and bears a Structural
  Support Artifact Function realized in supporting participants in baseball
  Processes occurring at that Venue's Baseball Field Site.
- **Necessary axioms proposed for the later overlay:** continuant part of some
  Baseball Venue; bearer of some Structural Support Artifact Function.
- **Identity:** the installed material surface particular. Replacement creates
  a new particular; the endpoint response alone does not establish boundaries.
- **Example:** the installed natural-grass and soil surface at a ballpark.

No new function or object property is proposed; CCO Structural Support Artifact
Function supplies the accepted function universal.
