# Triples-map families

```mermaid
flowchart LR
    SOURCE["reviewed logical sources"] --> CONTEXT["game, team, venue, person, role, time, containment"]
    SOURCE --> ACT["PitchAct, BatterAct, SwingAct, BuntAct, BaserunningAct, StealAttemptAct"]
    SOURCE --> PHYSICAL["pitch motion, contact, batted motion, catching, batted play"]
    SOURCE --> DEFENSE["source-supported fielding, catching, throwing and tagging acts"]
    SOURCE --> INSTITUTIONAL["ball, strike, fair, foul, foul tip, plate result, runner result, stolen base, passed ball, wild pitch, uncaught third strike"]
    SOURCE --> ADJ["judgment acts, decision ICEs, call acts, rule inputs"]
    SOURCE --> INFO["event records, timestamps, identifiers and designations"]
    SOURCE --> ARTIFACT["baseball, bat, base, home plate"]
    CONTEXT --> RDF["generated game graph"]
    ACT --> RDF
    PHYSICAL --> RDF
    DEFENSE --> RDF
    INSTITUTIONAL --> RDF
    ADJ --> RDF
    INFO --> RDF
    ARTIFACT --> RDF
```

The Triples Maps are separated because each identity-bearing ontological
category receives its own individual. Multiple maps may add types or relations
to the same stable individual, such as a plate result receiving its most
specific outcome type or one foul-tip process receiving both FoulTipProcess and
StrikeProcess types.

Use the [generated catalog](patterns/README.md) for the exact current maps and
relations. These overview categories do not imply that all source fields or
all physical acts are evidenced by every play.
