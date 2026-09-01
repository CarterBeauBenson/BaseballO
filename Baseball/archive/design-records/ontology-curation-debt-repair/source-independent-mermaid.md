# Source-independent review shapes

These diagrams show candidate ontology structure only. They are not generated
from RML and do not claim that any provider record establishes an instance.
Solid arrows are candidate reviewed relations or taxonomy. Dashed arrows are
explicitly withheld until the named evidence gap is resolved.

## Teams, roles, venue, and time

```mermaid
classDiagram
    class Organization
    class BaseballTeam
    class Role
    class BaseballGameTeamRole
    class HomeTeamRole
    class AwayTeamRole
    class HomeBaseballTeam
    class AwayBaseballTeam
    class Facility
    class BaseballVenue
    class ArtifactFunction
    class BaseballGameHostingFunction
    class TemporalInterval
    class BaseballGameTemporalInterval
    class TemporalInstant
    class BaseballEventTemporalInstant
    class BaseballGame

    Organization <|-- BaseballTeam
    Role <|-- BaseballGameTeamRole
    BaseballGameTeamRole <|-- HomeTeamRole
    BaseballGameTeamRole <|-- AwayTeamRole
    BaseballTeam <|-- HomeBaseballTeam
    BaseballTeam <|-- AwayBaseballTeam
    Facility <|-- BaseballVenue
    ArtifactFunction <|-- BaseballGameHostingFunction
    TemporalInterval <|-- BaseballGameTemporalInterval
    TemporalInstant <|-- BaseballEventTemporalInstant

    BaseballGameTeamRole --> BaseballTeam : inheres in
    BaseballGameTeamRole --> BaseballGame : realized in
    HomeBaseballTeam --> HomeTeamRole : bearer of some
    AwayBaseballTeam --> AwayTeamRole : bearer of some
    BaseballGameTemporalInterval --> BaseballGame : is temporal region of
    BaseballVenue --> BaseballGameHostingFunction : bearer of some
    BaseballGameHostingFunction --> BaseballGame : realized in only
```

Home and away classify a team relative to a role instance in a particular
game. They are candidate defined query views over the Role pattern, not
primitive or permanent kinds of Organization. A query must still traverse the
Role's realization to identify the particular Baseball Game.

## Timestamp and coordinate information

```mermaid
flowchart LR
    subgraph World[World-side entities]
        GAME[Baseball Game]
        PROCESS[Process that is an occurrent part of the Game]
        REGION[Temporal Region occupied by the Process]
        INSTANT[Baseball Event Temporal Instant]
        SITE[Batted-Ball Location Site]
        BALL[Baseball]
        MOTION[Batted-Ball Motion Process]
        MOTIONPART[Process occurrent part of\nBatted-Ball Motion]
    end

    subgraph Content[Generically dependent information content]
        TIMESTAMP[Baseball Timestamp ICE]
        COORD[Baseball Field Coordinate ICE]
        REFSYS[Baseball Field Coordinate Reference System ICE]
    end

    CARRIER[Optional material Information Bearing Entity]

    CARRIER -.->|may be carrier of| TIMESTAMP
    TIMESTAMP -->|has datetime value| DATETIME[xsd:dateTime literal]
    TIMESTAMP -->|designates| INSTANT
    PROCESS -->|occurrent part of| GAME
    PROCESS -->|occupies temporal region| REGION
    INSTANT -->|first instant of or last instant of| REGION

    COORD -->|uses reference system| REFSYS
    COORD -.->|coordinate literal properties unresolved| VALUES[withheld values]
    COORD -->|designates| SITE
    BALL -->|participates in| MOTION
    MOTIONPART -->|occurrent part of| MOTION
    SITE -->|is site of| MOTIONPART
```

The datetime literal and `uses reference system` assertions originate at the
ICE under the separately reviewed direct-value foundation. A material IBE may
carry that content but is not a value-bearing detour. The dashed coordinate
claims are not proposed axioms and must not appear in executable RML before a
separate value-representation, geometry, unit, and source-semantics decision.
One coordinate does not make the Site the location of the entire motion; it
must be tied to the relevant temporal Process part.

## Double play and foul tip

```mermaid
flowchart LR
    BIP[Baseball Institutional Process] -->|taxonomy| DP[Double Play Process]
    DP -->|has process part exactly two| OUT[Out Process]
    GIDP[Existing Grounded Into Double Play Process] -.->|repair blocked by| GAP[Missing independent institutional\nand ground-ball differentia]
    CODE[Provider grounded_into_double_play code] -.->|does not supply world-side structure| GAP

    STRIKE[Strike Process] -->|taxonomy| FOULTIP[Foul Tip Process]
    STRIKEJ[Strike Judgment Act] -->|taxonomy| FTJ[Foul Tip Judgment Act]
    STRIKED[Strike Decision ICE] -->|taxonomy| FTD[Foul Tip Decision ICE]
    CONTACT[Bat-Ball Contact Process] -->|precedes| FOULTIP
    CATCH[Ball Catching Process] -->|precedes| FOULTIP
    FOULTIP -->|has occurrent part| FTJ
    FTJ -->|has output| FTD
    FTD -->|is about| FOULTIP
```

The dashed GIDP branch is not a proposed axiom. The prior Rule/Judgment/Decision
support cluster merely defined four names through one another and has been
removed. `GroundedIntoDoublePlayProcess` remains frozen in the active ontology
until a source-independent institutional criterion and the relevant physical
ground-ball structure can be stated without circularity.

`FoulTipCallICE` is the retained legacy IRI for the node labeled Foul Tip
Decision ICE. A distinct communicated call act may be modeled when evidence
supports it; the decision ICE is not that act. The Grounded-Into-Double-Play
rule, judgment, and decision are proposed supporting classes for the existing
institutional Process class. They do not replace a future physical ground-ball
motion model.

## Challenges, motion, and replay-review acts

```mermaid
flowchart TB
    CHALLENGE[Challenge Act]
    MANAGER[Manager Act]
    PLAYER[Player Act]
    MC[Manager Challenge Act]
    PC[Player Challenge Act]

    CHALLENGE --> MC
    MANAGER --> MC
    CHALLENGE --> PC
    PLAYER --> PC

    BPP[Baseball Physical Process]
    CMOTION[CCO Motion]
    PITCHM[Pitch Ball Motion Process]
    BATTEDM[Batted-Ball Motion Process]
    THROWNM[Thrown-Ball Motion Process]
    BPP --> PITCHM
    CMOTION --> PITCHM
    BPP --> BATTEDM
    CMOTION --> BATTEDM
    BPP --> THROWNM
    CMOTION --> THROWNM

    BALLJ[Ball Judgment Act]
    STRIKEJ[Strike Judgment Act]
    OUTJ[Out Judgment Act]
    SAFEJ[Safe Judgment Act]
    AFFIRM[Affirming Replay Review Act union]
    OVERTURN[Overturning Replay Review Act union]

    BALLJ --> BALLBALL[Ball-Affirming Review]
    STRIKEJ --> STRIKESTRIKE[Strike-Affirming Review]
    OUTJ --> OUTOUT[Out-Affirming Review]
    SAFEJ --> SAFESAFE[Safe-Affirming Review]
    STRIKEJ --> BALLSTRIKE[Ball-to-Strike Review]
    BALLJ --> STRIKEBALL[Strike-to-Ball Review]
    SAFEJ --> OUTSAFE[Out-to-Safe Review]
    OUTJ --> SAFEOUT[Safe-to-Out Review]

    BALLBALL --> AFFIRM
    STRIKESTRIKE --> AFFIRM
    OUTOUT --> AFFIRM
    SAFESAFE --> AFFIRM
    BALLSTRIKE --> OVERTURN
    STRIKEBALL --> OVERTURN
    OUTSAFE --> OVERTURN
    SAFEOUT --> OVERTURN
```

The solid arrows from two genera into challenge and motion leaves represent
candidate intersection axioms, not multiple direct named `rdfs:subClassOf`
parents. The replay leaf's direct parent is its final judgment kind; union
axioms infer the affirming or overturning group.
