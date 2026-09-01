# Source-independent Mermaid

```mermaid
flowchart LR
    RECORD[Source transaction record ICE]
    TRADE[Baseball Personnel Trade Act]
    FROM[Origin Baseball Team]
    TO[Destination Baseball Team]
    PERSON[Person]
    OLDROLE[Old team Player Role]
    NEWROLE[New team Player Role]
    LOSS[Loss of Role]
    GAIN[Gain of Role]
    LREGION[Loss Temporal Region]
    GREGION[Gain Temporal Region]
    DATE[Calendar Date Identifier]
    DAY[Canonical Day]

    RECORD -->|is about| TRADE
    TRADE -->|has agent| FROM
    TRADE -->|has agent| TO
    TRADE -->|has occurrent part| LOSS
    TRADE -->|has occurrent part| GAIN
    OLDROLE -->|inheres in| PERSON
    OLDROLE -->|has organizational context| FROM
    NEWROLE -->|inheres in| PERSON
    NEWROLE -->|has organizational context| TO
    LOSS -->|has participant| PERSON
    LOSS -->|affects| OLDROLE
    LOSS -->|occupies temporal region| LREGION
    GAIN -->|has participant| PERSON
    GAIN -->|affects| NEWROLE
    GAIN -->|occupies temporal region| GREGION
    LOSS -->|precedes| GAIN
    DATE -->|designates| DAY
    LREGION -->|temporal part of| DAY
    GREGION -->|temporal part of| DAY
```

Identical accepted transaction-group identity groups legs into one Trade Act.
Both Teams are agents only when structured direction evidence establishes their
causal participation. The old-role Loss precedes the new-role Gain even when
both are localized only to the same canonical Day.

