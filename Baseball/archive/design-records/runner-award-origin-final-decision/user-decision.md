## FINAL DECISION FOR THE TWO REMAINING METRIC GAPS

### A. REMOVE THE BASE AWARD DIRECTIVE PATTERN

Do not require or mint an event-specific `Base Award Directive ICE`.

A Walk/HBP plus completed advance does not establish that a new directive ICE was produced. It does not need to.

The normative entity already exists: the applicable **Baseball Rule**, which is a CCO `Process Regulation`.

Use the following existing CCO relations:

```text
requires
https://www.commoncoreontologies.org/ont00001974

is required by
https://www.commoncoreontologies.org/ont00001807

is cause of
https://www.commoncoreontologies.org/ont00001803

prescribed by
https://www.commoncoreontologies.org/ont00001920
```

Authoritative pattern:

```text
Applicable Baseball Rule
        │
        │ requires
        ▼
Baserunning Act
        ▲
        │ is cause of
Walk Process / Hit-by-Pitch Process
```

Where appropriate, the institutional result may additionally be:

```text
Walk/HBP Process
    prescribed by → Applicable Baseball Rule
```

The two assertions answer different questions:

```text
Walk/HBP Process is cause of Baserunning Act
    = this particular institutional result produced this particular advance

Baseball Rule requires Baserunning Act
    = the advance is normatively required under the applicable rule
```

#### Batter on Walk/HBP

For the batter's own advance, admit:

```text
Walk/HBP Process
    is cause of → batter's Baserunning Act

Applicable Award Rule
    requires → batter's Baserunning Act
```

only when the source establishes:

```text
operative PA result = Walk / Intentional Walk / HBP
runner = batter
destination judgment = first base
same PA
no contradictory operative replay result
```

The rule supplies the entitlement to first base. The source supplies the particular Walk/HBP and the particular resolved runner.

#### Existing forced runners

For an existing runner, do not infer the advance merely because a Walk/HBP happened.

Require positive force evidence from the source.

For example:

```text
Walk/HBP occurs
runner movement is identified as forced
runner identity is established
movement is exactly the required next-base advance
same PA/event chain
operative destination agrees
```

Then:

```text
Walk/HBP Process
    is cause of → forced runner Baserunning Act

Applicable Force-Advance Rule
    requires → forced runner Baserunning Act
```

The applicable rule for a forced existing runner may therefore differ from the rule governing the batter's award.

Do not admit:

```text
extra-base advance
wild-pitch advance
passed-ball advance
steal
balk advance
mixed-cause movement
ambiguous movement reason
contradictory review
```

as an award-caused advance.

#### Consequence for the metric binding

The authoritative award-source path becomes:

```text
Walk/HBP Process
    → is cause of
Baserunning Act
    ← occurrent part of
Runner Resolution Episode
    → has occurrent part
Safe / Run Resolution
```

The index may derive:

```text
?resolution idx:awardSource ?walkOrHBP
```

No `Base Award Directive ICE` is required.

---

### B. DO NOT REQUIRE A PRECEDING STASIS TO ESTABLISH MOVEMENT ORIGIN

Keep the generalized `Baserunner-at-Base Stasis` and the PA-start subclass for situations in which a stasis is actually supported.

However:

```text
movement.start = "2B"
```

does not warrant:

```text
Baserunner-at-2B Stasis
    precedes → Baserunning Act
```

and especially does not warrant asserting that the stasis's final instant is identical with the act's first instant.

Remove that boundary requirement from the origin metric contract.

Instead represent the source-supported assertion as an ICE.

Add:

```text
Baserunning Segment Origin Designation
```

Definition:

> A Designative Information Content Entity that designates the Base represented by a source record as the origin of a particular Baserunning Act.

Authoritative pattern:

```text
Baserunning Segment Origin Designation
    is about → Baserunning Act

Baserunning Segment Origin Designation
    designates → Base
```

Use existing CCO:

```text
is about
https://www.commoncoreontologies.org/ont00001808

designates
https://www.commoncoreontologies.org/ont00001916
```

The designation may be represented as a continuant part of the relevant Baseball Event Record if that follows the existing record pattern.

#### Source mapping rule

For each mapped Baserunning Act belonging to a runner movement segment:

```text
if movement.start = 1B
    mint Origin Designation → designates First Base

if movement.start = 2B
    mint Origin Designation → designates Second Base

if movement.start = 3B
    mint Origin Designation → designates Third Base
```

Require:

```text
movement.start is present
value is a recognized base
runner identity is unambiguous
Baserunning Act identity is unambiguous
source row and act correspond
```

Do not require a preceding stasis.

Do not infer:

```text
physical location at the Base
a stasis interval
occurs-at Base
last-instant/first-instant equality
continuity from a previous resolution
```

The assertion means only:

> The source designates this Base as the origin of this particular baserunning movement segment.

#### `originBase` versus `start`

Do not collapse MLB `originBase` and `start`.

For the metric's immediate movement origin, use `movement.start`.

Example:

```text
row 1:
originBase = 2B
start      = 2B
end        = 3B

row 2:
originBase = 2B
start      = 3B
end        = score
```

For row 2, the movement segment begins at 3B.

Therefore its Origin Designation must designate 3B.

Preserve `originBase` separately as source evidence if useful.

---

### C. BATTER TRAJECTORY DOES NOT REQUIRE AN ORIGIN STASIS

Do not block TFS for the batter merely because MLB commonly gives a null runner `start` for the batter-runner.

For PAQ/TFS, the batter's offensive trajectory has a metric-defined initial state:

```text
HOME = trajectory position 0
```

This follows from the player being the batter in the plate appearance and is part of the metric's formal trajectory model.

It is not an assertion that:

```text
Baserunning Act has origin Base Home
```

and does not require minting a Home-Plate Stasis.

Thus:

```text
batter double:
metric trajectory = HOME → 2B
Progress = 2/4 = .500
```

The authoritative RDF still supplies:

```text
batter identity
Baserunning Act
Runner Resolution Episode
Safe Judgment
Safe Decision
Second Base destination
```

The metric supplies `HOME` as the defined initial node of a batter trajectory.

---

### D. EXISTING-RUNNER TFS ORIGIN

For an existing runner, determine the immediate origin in this priority order:

```text
1. Baserunning Segment Origin Designation for the attributed act
   → use designated Base

2. If the attributed act itself begins from the PA-start state and no
   intervening same-runner movement exists:
   use the positively supported PA-start Baserunner-at-Base Stasis

3. Otherwise:
   origin unavailable
```

Do not fall back to:

```text
previous Safe Process
most recent known Base
array ordering
assumed runner continuity
```

unless a later approved continuity pattern explicitly establishes those claims.

This handles the important case:

```text
PA starts: runner on 1B

runner independently steals:
1B → 2B

batter later singles:
runner 2B → 3B
```

The batter-attributed advancement uses:

```text
Origin Designation = 2B
Destination Decision = 3B
```

Therefore:

```text
batter receives credit for 2B → 3B only
```

The earlier steal may establish player state for other analytics but is not credited to the batter.

---

### E. INDEX DERIVATIONS

After these authoritative patterns are proven, the index may derive:

```text
?resolution idx:awardSource ?awardProcess
?act        idx:originBase  ?base
```

Award source derives from:

```text
awardProcess
    is cause of
baserunningAct
    part of
resolutionEpisode
    contains
resolution
```

Origin base derives from:

```text
originDesignation
    is about
baserunningAct

originDesignation
    designates
base
```

These remain deletable serving shortcuts.

---

### F. REQUIRED TESTS

Add positive fixtures for:

```text
walk: batter HOME → 1B
HBP: batter HOME → 1B
bases-loaded walk forced 1B→2B
bases-loaded walk forced 2B→3B
bases-loaded walk forced 3B→score
movement.start = 2B → Origin Designation(2B)
steal 1B→2B followed by batter-attributed 2B→3B
```

Add negative fixtures for:

```text
walk plus wild-pitch extra advance
HBP plus unrelated runner movement
runner advances beyond forced destination
movement.start absent
movement.start unsupported
ambiguous runner identity
ambiguous act identity
originBase disagrees with movement.start
attempt to infer stasis from movement.start
attempt to infer origin from previous Safe Process
```

The metric must remain unavailable for ambiguous cases.

---

## FINAL MODELING DECISION

The two remaining gaps are resolved as follows:

```text
AWARD
    institutional result → causal consequence
    +
    applicable Baseball Rule → normative requirement

ORIGIN
    source start-base value → Designative ICE about the Baserunning Act
    and designating the Base
```

Do not create an event-specific award directive.

Do not create a preceding stasis from a movement-start field.

The generalized Stasis remains available where a temporal state is genuinely evidenced; it is not the required carrier of every baserunning origin.
