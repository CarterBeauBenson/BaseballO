PRAGMA foreign_keys = ON;

CREATE TABLE serving_build (
    build_id TEXT PRIMARY KEY,
    contract_version INTEGER NOT NULL,
    created_at_utc TEXT NOT NULL,
    corpus_fingerprint TEXT NOT NULL,
    source_query_sha256 TEXT NOT NULL,
    schema_sha256 TEXT NOT NULL,
    materializer_sha256 TEXT NOT NULL,
    mapping_sha256 TEXT NOT NULL,
    validation_sha256 TEXT NOT NULL,
    rating_spec_sha256 TEXT NOT NULL,
    game_count INTEGER NOT NULL,
    plate_appearance_count INTEGER NOT NULL,
    advanced_query_count INTEGER NOT NULL,
    advanced_binding_count INTEGER NOT NULL,
    batting_result_count INTEGER NOT NULL,
    pitch_count INTEGER NOT NULL,
    runner_event_count INTEGER NOT NULL,
    assignment_count INTEGER NOT NULL,
    empty_player_game_count INTEGER NOT NULL,
    damage_opportunity_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'validated'))
) STRICT;

CREATE TABLE game_dimension (
    graph_iri TEXT PRIMARY KEY,
    game_iri TEXT NOT NULL UNIQUE,
    game_pk TEXT NOT NULL UNIQUE,
    official_date TEXT NOT NULL,
    game_start TEXT NOT NULL,
    season INTEGER NOT NULL,
    game_set TEXT NOT NULL,
    venue_iri TEXT,
    venue_label TEXT,
    home_team_iri TEXT,
    home_team_label TEXT,
    away_team_iri TEXT,
    away_team_label TEXT
) STRICT;

CREATE TABLE plate_appearance_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    plate_appearance_iri TEXT NOT NULL,
    game_iri TEXT NOT NULL,
    batter_iri TEXT NOT NULL,
    batter_label TEXT NOT NULL,
    pitcher_iri TEXT,
    pitcher_label TEXT,
    outcome TEXT,
    was_hit INTEGER,
    hit_type TEXT,
    start_time TEXT,
    end_time TEXT,
    duration TEXT,
    duration_minutes REAL,
    pitches INTEGER,
    swings INTEGER,
    bunts INTEGER,
    contacts INTEGER,
    balls INTEGER,
    strikes INTEGER,
    fouls INTEGER,
    foul_tips INTEGER,
    runner_runs INTEGER,
    runner_outs INTEGER,
    safe_resolutions INTEGER,
    positive_outcome INTEGER,
    productive_other_runner INTEGER,
    grind_score INTEGER NOT NULL,
    outcome_rating REAL NOT NULL CHECK (outcome_rating BETWEEN 0.0 AND 1.0),
    grind_rating REAL NOT NULL CHECK (grind_rating BETWEEN 0.0 AND 1.0),
    situational_rating REAL NOT NULL CHECK (situational_rating BETWEEN 0.0 AND 1.0),
    plate_appearance_quality REAL NOT NULL CHECK (plate_appearance_quality BETWEEN 0.0 AND 1.0),
    plate_appearance_quality_band TEXT NOT NULL CHECK (plate_appearance_quality_band IN ('Excellent', 'Good', 'Mixed', 'Poor', 'Bad')),
    plate_appearance_quality_version TEXT NOT NULL,
    good_at_bat_evidence_count INTEGER,
    good_at_bat INTEGER,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (graph_iri, plate_appearance_iri)
) STRICT;

CREATE TABLE advanced_query_manifest (
    query_id TEXT PRIMARY KEY,
    query_sha256 TEXT NOT NULL,
    reducer_mode TEXT NOT NULL CHECK (reducer_mode IN ('detail', 'additive')),
    variables_json TEXT NOT NULL,
    binding_count INTEGER NOT NULL
) STRICT;

CREATE TABLE advanced_result_fact (
    query_id TEXT NOT NULL REFERENCES advanced_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    row_ordinal INTEGER NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, row_ordinal)
) STRICT;

CREATE TABLE batting_result_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    result_iri TEXT NOT NULL,
    plate_appearance_iri TEXT NOT NULL,
    player_iri TEXT NOT NULL,
    player_label TEXT NOT NULL,
    team_iri TEXT NOT NULL,
    team_label TEXT NOT NULL,
    event_type TEXT NOT NULL,
    PRIMARY KEY (graph_iri, result_iri)
) STRICT;

CREATE TABLE pitch_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    pitch_iri TEXT NOT NULL,
    plate_appearance_iri TEXT NOT NULL,
    pitcher_iri TEXT NOT NULL,
    pitcher_label TEXT NOT NULL,
    team_iri TEXT NOT NULL,
    team_label TEXT NOT NULL,
    pitch_call_code TEXT NOT NULL,
    PRIMARY KEY (graph_iri, pitch_iri)
) STRICT;

CREATE TABLE runner_event_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    resolution_iri TEXT NOT NULL,
    player_iri TEXT NOT NULL,
    player_label TEXT NOT NULL,
    team_iri TEXT NOT NULL,
    team_label TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resolution_class TEXT NOT NULL,
    stolen_base_iri TEXT,
    PRIMARY KEY (graph_iri, resolution_iri)
) STRICT;

CREATE TABLE assignment_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    assignment_iri TEXT NOT NULL,
    assignment_type TEXT NOT NULL CHECK (assignment_type IN ('home', 'away', 'umpire', 'official_scorer')),
    assignee_iri TEXT NOT NULL,
    assignee_label TEXT NOT NULL,
    PRIMARY KEY (graph_iri, assignment_iri)
) STRICT;

CREATE TABLE empty_player_game_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    player_iri TEXT NOT NULL,
    player_label TEXT NOT NULL,
    team_iri TEXT NOT NULL,
    team_label TEXT NOT NULL,
    pitcher_iri TEXT NOT NULL DEFAULT '',
    pitcher_label TEXT NOT NULL DEFAULT '',
    empty_flag INTEGER NOT NULL CHECK (empty_flag IN (0, 1)),
    PRIMARY KEY (graph_iri, player_iri, pitcher_iri)
) STRICT;

CREATE TABLE empty_damage_fact (
    graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
    player_iri TEXT NOT NULL,
    team_iri TEXT NOT NULL,
    pitcher_iri TEXT NOT NULL,
    plate_appearance_iri TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (graph_iri, player_iri, pitcher_iri, plate_appearance_iri)
) STRICT;

CREATE INDEX plate_appearance_game_idx ON plate_appearance_fact(game_iri);
CREATE INDEX plate_appearance_batter_idx ON plate_appearance_fact(batter_iri);
CREATE INDEX plate_appearance_pitcher_idx ON plate_appearance_fact(pitcher_iri);
CREATE INDEX game_dimension_date_idx ON game_dimension(game_set, official_date);
CREATE INDEX game_dimension_scope_idx ON game_dimension(season, venue_iri, home_team_iri, away_team_iri);
CREATE INDEX advanced_result_scope_idx ON advanced_result_fact(query_id, graph_iri);
CREATE INDEX batting_result_scope_idx ON batting_result_fact(graph_iri, player_iri, team_iri, event_type);
CREATE INDEX pitch_scope_idx ON pitch_fact(graph_iri, pitcher_iri, team_iri, pitch_call_code);
CREATE INDEX runner_event_scope_idx ON runner_event_fact(graph_iri, player_iri, team_iri, event_type);
CREATE INDEX assignment_scope_idx ON assignment_fact(graph_iri, assignment_type, assignee_iri);
CREATE INDEX empty_player_game_scope_idx ON empty_player_game_fact(graph_iri, player_iri, team_iri, pitcher_iri, empty_flag);
CREATE INDEX empty_damage_scope_idx ON empty_damage_fact(graph_iri, player_iri, team_iri, pitcher_iri);
