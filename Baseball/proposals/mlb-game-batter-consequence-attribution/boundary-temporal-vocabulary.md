# Runner location and an enclosing Site

> Correction, 2026-09-09: passages below describing the four local runner
> properties are historical and withdrawn. Use the [structural correction](../../archive/design-records/runner-structural-correction/README.md).
> Episode/agent and decision-destination paths replace the first two shortcuts;
> directive prescription and stasis boundaries remain source-evidence gaps.


Status: **nested-site direction selected; identity, temporal scope and source evidence under review**.

The user rejected the Relational Quality candidate and clarified that the
existing Base Site can be located in the other, larger Site under discussion.
The existing Base Site is retained; it is not enlarged or redefined by this
review. Mermaid diagrams remain unchanged. The [decision](../../archive/design-records/baserunner-location-site-direction/decision.json)
records both the initial direction and this clarification.

## Existing vocabulary

The pinned [BFO/CCO dependency](../../ontology/CommonCoreOntologiesMerged.ttl)
provides `obo:BFO_0000171`, labeled **located in**. It relates appropriate
independent continuants spatially at some time. Existing `base:BaseSite` and
BFO Site (`obo:BFO_0000029`) can be used in this direction without introducing
a Relational Quality. This uses Sites, not Spatial Region classes.

The intended spatial assertions are:

- The existing Base is located in its existing Base Site.
- That Base Site is located in the larger Site under discussion.
- The runner is located in that larger Site.

The second assertion follows the user's specified location relation. Do not
silently substitute continuant parthood for it. Do not identify the larger
Site with the entire Baseball Field Site merely because both are Sites.

This distinguishes location near the base from being inside or continuously
in contact with the material Base. It does not entail a safe adjudication or
a particular touching process. Existing `hasAdjudicatedBase` and act-origin
links retain their accepted meanings.

## Remaining engineering and semantic boundary

The larger Site still needs an independently meaningful extent and identity
relative to the field and Base. No fixed radius, whole basepath, moving
runner-centered boundary or new named Site subclass is selected here. Generic
Site vocabulary may suffice; a new class is not assumed necessary.

The runner-to-Site assertion must also apply at the particular game boundary
needed by the metric. BFO's binary `located in` relation says that location
holds at some time; it does not select that boundary. Applying `exists at` to
the runner and Site would establish their existence then, not the location
relation between them. The former association-entity approach is withdrawn.

The existing `BaserunnerAtBaseStasis` remains specifically at PA start. It is
not generalized to later consequences, and an isolated observation does not
establish an interval of persistence. Source fields must support the intended
location at the selected boundary; missing movement rows still cannot prove
unchanged location or stranding.

No ontology, RML, SHACL, semantic pin or Mermaid diagram is changed by this
review. The superseded Quality candidate is retained in the
[historical record](../../archive/design-records/baserunner-location-site-direction/README.md).

## Temporal machinery assessment

The current selective-reasoning exporter explicitly supplies a process's
unique occupied Temporal Region when exporting participation facts. Its
admitted profiles do not supply a corresponding time-qualified location
contract. That participation rule is not automatically applicable to a
Person-to-Site location relation.

CCO `occurs at` (`ont00001918`) has Process as its domain. Moving it onto a
Process Boundary would impose that Process typing; it is not a generic
instantaneous location shortcut. A justified location process would need its
own positive evidence and reviewed interpretation.

RDF statement reification also does not solve this by itself. It describes a
triple token without entailing the triple's truth; a timestamp on that token
does not automatically become the validity time of the world-side relation.
See [W3C RDF 1.1 Semantics, D.1](https://www.w3.org/TR/2014/REC-rdf11-mt-20140225/#reification).
Any temporal assertion extension would need an explicit reviewed truth and
scope contract, rather than only an information record about runner, Site
and time. No such extension is introduced here.

## Implemented evidence audit

[runner-location-evidence.rq](../../sparql/metrics/runner-location-evidence.rq)
reads the existing PA-start Stasis pattern. It exposes the actual stasis and
PA intervals, their first instants, direct runner-to-Base-Site links and any
explicit Base-Site-to-enclosing-location links. Missing fields remain unbound;
the query neither invents larger Sites nor infers boundary validity.

Four focused regressions verify separate PA anchors for the same runner/Site,
unknown time preservation, authoritative graph scope, and exact read-only
source-catalog ownership. The audit does not change source RML, source SHACL,
reasoning profiles, promotion or Mermaid. Site identity remains an open
ontologist question; no response is inferred from elapsed time.
