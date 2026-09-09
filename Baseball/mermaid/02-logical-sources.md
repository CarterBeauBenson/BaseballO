# Logical-source partitions

```mermaid
flowchart TD
    RAW["untouched MLB feed/live JSON"] --> ROOT["root, teams, players, venue, officials"]
    RAW --> PLAY["allPlays records and result filters"]
    RAW --> CTX["disposable ancestor context"]
    CTX --> PITCH["pitch records + play/batter/pitcher identity"]
    PITCH --> CALL["ball, strike, foul, foul tip, in-play filters"]
    PITCH --> PHYSICAL["contact and coordinate filters"]
    PLAY --> REVIEW["review actors, decisions, transitions, results, and final links"]
    PLAY --> BUNT["sac_bunt terminal pitch filter"]
    PLAY --> RESULT["hit, out, walk, sacrifice, error, interference, balk filters"]
    PLAY --> RUNNER["runner movement filters"]
    RUNNER --> OUT["out"]
    RUNNER --> SAFE["reach and advance"]
    RUNNER --> RUN["score from origin or base"]
    RUNNER --> STEAL["stolen base and caught stealing"]
    RUNNER --> CONTROL["passed ball, wild pitch, and pitch-control failure"]
    PLAY --> UTS["uncaught third strike"]
    RAW --> FIELDING["fielding credits: role trigger only"]
```

The active RML contains 103 logical sources. Repeated filters are deliberate:
one source record may support distinct acts, physical processes, judgments,
decisions, calls, counted processes, records, sites, roles, and artifacts. The
temporary context adds ancestor identity but never changes or replaces the raw
source. Source partitions never collapse those individuals.
