# Triples-map families

```mermaid
flowchart LR
    SOURCE["103 logical sources"] --> CONTEXT["game, team, venue, person, role, time, containment"]
    SOURCE --> ACT["PitchAct, BatterAct, SwingAct, BuntAct, BaserunningAct, StealAttemptAct"]
    SOURCE --> PHYSICAL["pitch motion, pitch-control failure, contact, batted motion, catching, base touching, batted play"]
    SOURCE --> INSTITUTIONAL["ball, strike, fair, foul, foul tip, plate result, runner result, stolen base, passed ball, wild pitch, uncaught third strike"]
    SOURCE --> ADJ["judgment acts, decision ICEs, call acts, rule inputs"]
    SOURCE --> INFO["event records, timestamps, coordinate ICEs, location sites"]
    SOURCE --> ARTIFACT["baseball, bat, base, home plate"]
    CONTEXT --> RDF["generated game graph"]
    ACT --> RDF
    PHYSICAL --> RDF
    INSTITUTIONAL --> RDF
    ADJ --> RDF
    INFO --> RDF
    ARTIFACT --> RDF
```

The 354 Triples Maps are separated because each identity-bearing ontological
category receives its own individual. Multiple maps may add types or relations
to the same stable individual, such as a plate result receiving its most
specific outcome type or one foul-tip process receiving both FoulTipProcess and
StrikeProcess types.
