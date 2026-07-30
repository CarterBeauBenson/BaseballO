# Logical Source Shape

The mapping defines 37 logical sources over one untouched JSON document. The source count is larger than the number of canonical record structures because pitch calls, runner outcomes, and result types are selected with separate JSONPath filters.

```mermaid
flowchart TB
    RAW["game.json"] --> ROOT["RootSource<br/>$"]

    ROOT --> GD["gameData"]
    GD --> TEAMS["AwayTeamSource<br/>HomeTeamSource"]
    GD --> PLAYERS["PlayerSource"]
    GD --> VENUE["VenueSource"]
    VENUE -.->|"geographic coordinate ICE deferred"| GEO["location.defaultCoordinates"]

    ROOT --> LD["liveData"]
    LD --> PLAYS["plays.allPlays[*]<br/>canonical detailed plays"]
    LD --> OFFICIALS["boxscore.officials[*]<br/>OfficialSource"]

    PLAYS --> PLAY["PlaySource"]
    PLAYS --> LAST["LastPlaySource<br/>allPlays[-1:]"]
    PLAYS --> PITCH["PitchSource"]
    PLAYS --> BATTED["BattedPitchSource"]
    PLAYS --> CALLS["9 pitch-call filters<br/>B, *B, C, S, F, T, X, D, E"]
    PLAYS --> RESULTS["11 result.eventType filters"]
    PLAYS --> RUNNER["RunnerSource"]
    PLAYS --> RUNNER_FILTERS["5 runner-outcome filters"]
    PLAYS --> CREDIT["FieldingCreditSource"]

    PLAYS -.->|"duplicate view: not mapped"| CURRENT["currentPlay"]
    PLAYS -.->|"index view: not mapped"| PBI["playsByInning"]
    PLAYS -.->|"aggregate view: not mapped"| LINE["linescore"]

    classDef canonical fill:#d7f5df,stroke:#24733b,color:#102a18;
    classDef filtered fill:#fff2cc,stroke:#997a00,color:#3d3100;
    classDef excluded fill:#eeeeee,stroke:#777,color:#333,stroke-dasharray:5 5;
    class RAW,ROOT,GD,LD,PLAYS,PLAY canonical;
    class TEAMS,PLAYERS,VENUE,OFFICIALS,LAST,PITCH,BATTED,CALLS,RESULTS,RUNNER,RUNNER_FILTERS,CREDIT filtered;
    class CURRENT,PBI,LINE,GEO excluded;
```

## Shape observation

The mapping correctly anchors detailed events on `allPlays`, but the filtered logical sources repeat traversal of the same nested arrays. This is simple and declarative, though processor performance should be measured at season scale.
