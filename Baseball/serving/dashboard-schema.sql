PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS game_dimension (
  graph_iri TEXT PRIMARY KEY, game_iri TEXT NOT NULL UNIQUE, game_pk TEXT NOT NULL UNIQUE,
  official_date TEXT NOT NULL, game_start TEXT NOT NULL, season INTEGER NOT NULL,
  game_set TEXT NOT NULL, venue_iri TEXT, venue_label TEXT, home_team_iri TEXT,
  home_team_label TEXT, away_team_iri TEXT, away_team_label TEXT
) STRICT;
CREATE TABLE IF NOT EXISTS dashboard_checkpoint (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  input_sha256 TEXT NOT NULL, proof_json TEXT NOT NULL CHECK(json_valid(proof_json))
) STRICT;
CREATE TABLE IF NOT EXISTS dashboard_build (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1), build_id TEXT NOT NULL,
  corpus_fingerprint TEXT NOT NULL, input_set_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('candidate','validated'))
) STRICT;
CREATE TABLE IF NOT EXISTS dashboard_state (
  name TEXT PRIMARY KEY, value TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS dashboard_games_by_date ON game_dimension(game_set,official_date);
