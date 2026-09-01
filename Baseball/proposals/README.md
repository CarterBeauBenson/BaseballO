# Proposal catalog

This is the only active proposal directory in BaseballO. Each unresolved source
or ontology extension receives one self-contained subdirectory containing its
field inventory, de-duplication decisions, source-independent Mermaid, proposed
axioms and annotations when needed, review notes, and a machine-readable
`review.json`. Start that record from
[`../governance/templates/proposal-review.json`](../governance/templates/proposal-review.json).
When a package enters review, each artifact is recorded as an exact
`{path, sha256}` object; bare paths do not satisfy the gate.

The governing lifecycle is documented in
[`../governance/README.md`](../governance/README.md). Active proposals are
design-only: their review status may be `draft` or `under-review`, never
`accepted`. An explicit ontologist decision is recorded before the package is
moved to [`../archive/design-records/`](../archive/design-records/). Executable
implementation begins in a later change from that archived decision.

Proposal vocabulary is review-only. It may not appear in executable RML,
SHACL, SPARQL contracts, serving schemas, or UI code while the proposal is
active. Acceptance is not inferred from successful validation, an instruction
to continue, lack of objection, or implementation speed. Accepted proposals
move to `archive/design-records/`; rejected proposals remain archived with
their rejection rationale so they cannot be accidentally revived.

## Active reviews

The accepted source-independent review surface for the next MLB implementation
pass is archived as
[`FINAL-MLB-RML-REVIEW.md`](../archive/design-records/FINAL-MLB-RML-REVIEW.md).

The packages below are all **under review** with a null ontologist decision.
They are design-only and authorize no ontology, RML, SHACL, acquisition, RDF,
SQL, or UI change. Each link keeps one answerable modeling boundary visible;
the Mermaid shows candidate world-side structure and the competency questions
list the decisions still required.

### Implementation gates

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Season plans without complete phases](mlb-organizations-season-plan-without-phase/README.md) | [shape](mlb-organizations-season-plan-without-phase/source-independent-mermaid.md) | [decisions](mlb-organizations-season-plan-without-phase/competency-questions.md) |
| [Transaction person resource kind](mlb-transactions-person-resource-kind/README.md) | [shape](mlb-transactions-person-resource-kind/source-independent-mermaid.md) | [decisions](mlb-transactions-person-resource-kind/competency-questions.md) |
| [Occurrent evidence in authority products](authority-graph-occurrent-evidence-placement/README.md) | [shape](authority-graph-occurrent-evidence-placement/source-independent-mermaid.md) | [decisions](authority-graph-occurrent-evidence-placement/competency-questions.md) |

### MLB game and shared baseball ontology gaps

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Deferred MLB-game measurements](mlb-game-deferred-measurements/README.md) | [shape](mlb-game-deferred-measurements/source-independent-mermaid.md) | [decisions](mlb-game-deferred-measurements/competency-questions.md) |

### MLB people gaps

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Uniform-number evidence](mlb-people-uniform-number/README.md) | [shape](mlb-people-uniform-number/source-independent-mermaid.md) | [decisions](mlb-people-uniform-number/competency-questions.md) |
| [MLB debut evidence](mlb-people-debut-evidence/README.md) | [shape](mlb-people-debut-evidence/source-independent-mermaid.md) | [decisions](mlb-people-debut-evidence/competency-questions.md) |
| [Draft evidence](mlb-people-draft-evidence/README.md) | [shape](mlb-people-draft-evidence/source-independent-mermaid.md) | [decisions](mlb-people-draft-evidence/competency-questions.md) |

### MLB organization gaps

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Alternate organization names](mlb-organizations-alternate-names/README.md) | [shape](mlb-organizations-alternate-names/source-independent-mermaid.md) | [decisions](mlb-organizations-alternate-names/competency-questions.md) |
| [Provider organization codes](mlb-organizations-provider-codes/README.md) | [shape](mlb-organizations-provider-codes/source-independent-mermaid.md) | [decisions](mlb-organizations-provider-codes/competency-questions.md) |
| [Provider status](mlb-organizations-provider-status/README.md) | [shape](mlb-organizations-provider-status/source-independent-mermaid.md) | [decisions](mlb-organizations-provider-status/competency-questions.md) |
| [First-year evidence](mlb-organizations-first-year-evidence/README.md) | [shape](mlb-organizations-first-year-evidence/source-independent-mermaid.md) | [decisions](mlb-organizations-first-year-evidence/competency-questions.md) |
| [Season format flags](mlb-organizations-season-format-flags/README.md) | [shape](mlb-organizations-season-format-flags/source-independent-mermaid.md) | [decisions](mlb-organizations-season-format-flags/competency-questions.md) |
| [Season counts](mlb-organizations-season-counts/README.md) | [shape](mlb-organizations-season-counts/source-independent-mermaid.md) | [decisions](mlb-organizations-season-counts/competency-questions.md) |
| [Qualification thresholds](mlb-organizations-qualification-thresholds/README.md) | [shape](mlb-organizations-qualification-thresholds/source-independent-mermaid.md) | [decisions](mlb-organizations-qualification-thresholds/competency-questions.md) |

### MLB venue gaps

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Azimuth geometry](mlb-venues-azimuth/README.md) | [shape](mlb-venues-azimuth/source-independent-mermaid.md) | [decisions](mlb-venues-azimuth/competency-questions.md) |
| [Elevation, unit, and datum](mlb-venues-elevation/README.md) | [shape](mlb-venues-elevation/source-independent-mermaid.md) | [decisions](mlb-venues-elevation/competency-questions.md) |
| [Time-zone evidence](mlb-venues-time-zone/README.md) | [shape](mlb-venues-time-zone/source-independent-mermaid.md) | [decisions](mlb-venues-time-zone/competency-questions.md) |
| [Address evidence](mlb-venues-address-evidence/README.md) | [shape](mlb-venues-address-evidence/source-independent-mermaid.md) | [decisions](mlb-venues-address-evidence/competency-questions.md) |
| [Contact evidence](mlb-venues-contact-evidence/README.md) | [shape](mlb-venues-contact-evidence/source-independent-mermaid.md) | [decisions](mlb-venues-contact-evidence/competency-questions.md) |
| [Provider active status](mlb-venues-provider-status/README.md) | [shape](mlb-venues-provider-status/source-independent-mermaid.md) | [decisions](mlb-venues-provider-status/competency-questions.md) |

### MLB transaction gaps

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Death code](mlb-transactions-death-code/README.md) | [shape](mlb-transactions-death-code/source-independent-mermaid.md) | [decisions](mlb-transactions-death-code/competency-questions.md) |
| [Uniform-number code](mlb-transactions-uniform-number-code/README.md) | [shape](mlb-transactions-uniform-number-code/source-independent-mermaid.md) | [decisions](mlb-transactions-uniform-number-code/competency-questions.md) |

### Statcast restart

| Review boundary | Mermaid | Questions |
| --- | --- | --- |
| [Pitch Speed Process Profile](statcast-pitch-speed-process-profile/README.md) | [shape](statcast-pitch-speed-process-profile/source-independent-mermaid.md) | [decisions](statcast-pitch-speed-process-profile/competency-questions.md) |
| [Bat-tracking geometry](statcast-bat-tracking-geometry/README.md) | [shape](statcast-bat-tracking-geometry/source-specific-mermaid.md) | [decisions](statcast-bat-tracking-geometry/competency-questions.md) |
| [Arm-angle geometry](statcast-arm-angle-geometry/README.md) | [shape](statcast-arm-angle-geometry/source-specific-mermaid.md) | [decisions](statcast-arm-angle-geometry/competency-questions.md) |
| [Batted-ball expectancy](statcast-batted-ball-expectancy/README.md) | [shape](statcast-batted-ball-expectancy/source-specific-mermaid.md) | [decisions](statcast-batted-ball-expectancy/competency-questions.md) |
| [Run and win expectancy](statcast-run-win-expectancy/README.md) | [shape](statcast-run-win-expectancy/source-specific-mermaid.md) | [decisions](statcast-run-win-expectancy/competency-questions.md) |
| [Defensive alignment](statcast-defensive-alignment/README.md) | [shape](statcast-defensive-alignment/source-specific-mermaid.md) | [decisions](statcast-defensive-alignment/competency-questions.md) |

The already accepted MLB organizations, people, venues, and transactions
source contracts are preserved in
[`../archive/design-records/`](../archive/design-records/).

The required progression is:

1. competency questions and source evidence;
2. field-level de-duplication inventory;
3. source-independent Mermaid shapes;
4. ontologist review;
5. accepted `review.json` archived in a separate change;
6. accepted ontology and identity changes;
7. source-specific Mermaid review and explicit ontologist acceptance;
8. source-specific RML and SHACL implementation;
9. one-record and one-game semantic proof; and
10. bounded corpus promotion.

Generated Mermaid from finished RML is a regression artifact, not a substitute
for pre-implementation review. The current semantic baseline is frozen and
unratified; an existing executable artifact is not itself evidence that its
pattern was accepted.
