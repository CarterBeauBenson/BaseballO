-- Derived, disposable serving products. No ontology/proposal vocabulary.
CREATE TABLE IF NOT EXISTS metric_suite_manifest (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  version TEXT NOT NULL, implementation_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_schedule_coverage (
  official_date TEXT PRIMARY KEY,
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_evidence (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
  binding_sha256 TEXT NOT NULL, binding_json TEXT NOT NULL CHECK(json_valid(binding_json)),
  PRIMARY KEY(graph_iri,binding_sha256)
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_result (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
  metric_id TEXT NOT NULL, entity_key TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('available','unavailable')),
  numerator TEXT, denominator TEXT,
  result_json TEXT NOT NULL CHECK(json_valid(result_json)),
  result_sha256 TEXT NOT NULL,
  CHECK ((numerator IS NULL) = (denominator IS NULL)),
  CHECK (status <> 'unavailable' OR numerator IS NULL),
  PRIMARY KEY(graph_iri,metric_id,entity_key)
) STRICT;
CREATE INDEX IF NOT EXISTS metric_suite_result_by_metric
  ON metric_suite_result(metric_id,graph_iri);
-- Hash-bound validation provenance, separate from RDF-derived metric facts.
CREATE TABLE IF NOT EXISTS metric_suite_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_run_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_runner_resolution_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_count_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_boundary_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_defensive_admission (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),
  proof_sha256 TEXT NOT NULL
) STRICT;

-- Reusable analytical observations. Detail JSON preserves exact existing
-- reducer inputs; identity, applicability and values have indexed SQL columns.
CREATE TABLE IF NOT EXISTS metric_suite_block_manifest (
  graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
  version INTEGER NOT NULL, scope_rows INTEGER NOT NULL CHECK(scope_rows>=0)
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_scope_fact (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
  kind TEXT NOT NULL, entity_iri TEXT NOT NULL, player_iri TEXT, game_iri TEXT NOT NULL,
  fact_key TEXT NOT NULL, record_json TEXT NOT NULL CHECK(json_valid(record_json)), record_sha256 TEXT NOT NULL,
  PRIMARY KEY(graph_iri,fact_key)
) STRICT;
CREATE INDEX IF NOT EXISTS metric_suite_scope_by_player ON metric_suite_scope_fact(player_iri,kind,graph_iri);
CREATE TABLE IF NOT EXISTS metric_suite_input_state (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), family TEXT NOT NULL,
  member_key TEXT NOT NULL, row_count INTEGER NOT NULL CHECK(row_count>=0),
  state_json TEXT NOT NULL CHECK(json_valid(state_json)), state_sha256 TEXT NOT NULL,
  PRIMARY KEY(graph_iri,family)
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_input_row (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), family TEXT NOT NULL,
  entity_iri TEXT NOT NULL, player_iri TEXT, game_iri TEXT,
  eligible INTEGER CHECK(eligible IN (0,1)), numerator TEXT, denominator TEXT,
  record_json TEXT NOT NULL CHECK(json_valid(record_json)), record_sha256 TEXT NOT NULL,
  CHECK((numerator IS NULL)=(denominator IS NULL)),
  PRIMARY KEY(graph_iri,family,entity_iri)
) STRICT;
CREATE INDEX IF NOT EXISTS metric_suite_input_by_player ON metric_suite_input_row(family,player_iri,graph_iri);
CREATE INDEX IF NOT EXISTS metric_suite_input_by_value ON metric_suite_input_row(family,eligible,numerator,denominator,graph_iri);
CREATE TABLE IF NOT EXISTS metric_suite_shell (
  graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri), metric_id TEXT NOT NULL,
  result_json TEXT NOT NULL CHECK(json_valid(result_json)), result_sha256 TEXT NOT NULL,
  PRIMARY KEY(graph_iri,metric_id)
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_reference (
  metric_id TEXT NOT NULL, season INTEGER NOT NULL, graph_set_sha256 TEXT NOT NULL,
  row_count INTEGER NOT NULL CHECK(row_count>=0),
  PRIMARY KEY(metric_id,season,graph_set_sha256)
) STRICT;
CREATE TABLE IF NOT EXISTS metric_suite_reference_rank (
  metric_id TEXT NOT NULL, season INTEGER NOT NULL, graph_set_sha256 TEXT NOT NULL,
  observation_key TEXT NOT NULL, rank_json TEXT NOT NULL CHECK(json_valid(rank_json)), rank_sha256 TEXT NOT NULL,
  PRIMARY KEY(metric_id,season,graph_set_sha256,observation_key),
  FOREIGN KEY(metric_id,season,graph_set_sha256) REFERENCES metric_suite_reference ON DELETE CASCADE
) STRICT;
CREATE TRIGGER IF NOT EXISTS metric_input_insert_invalidates_ranks AFTER INSERT ON metric_suite_input_row
BEGIN
DELETE FROM metric_suite_reference WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri=NEW.graph_iri);
DELETE FROM metric_suite_reference_rank WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri=NEW.graph_iri);
END;
CREATE TRIGGER IF NOT EXISTS metric_input_update_invalidates_ranks AFTER UPDATE ON metric_suite_input_row
BEGIN
DELETE FROM metric_suite_reference WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri IN (OLD.graph_iri,NEW.graph_iri));
DELETE FROM metric_suite_reference_rank WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri IN (OLD.graph_iri,NEW.graph_iri));
END;
CREATE TRIGGER IF NOT EXISTS metric_input_delete_invalidates_ranks AFTER DELETE ON metric_suite_input_row
BEGIN
DELETE FROM metric_suite_reference WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri=OLD.graph_iri);
DELETE FROM metric_suite_reference_rank WHERE season IN (SELECT season FROM game_dimension WHERE graph_iri=OLD.graph_iri);
END;
-- Direct changes cannot leave apparently current derived inputs behind.
-- The owning writer refreshes shells and manifests after each full projection.
CREATE TRIGGER IF NOT EXISTS metric_evidence_insert_invalidates_blocks AFTER INSERT ON metric_suite_evidence
BEGIN DELETE FROM metric_suite_block_manifest WHERE graph_iri=NEW.graph_iri; END;
CREATE TRIGGER IF NOT EXISTS metric_evidence_update_invalidates_blocks AFTER UPDATE ON metric_suite_evidence
BEGIN DELETE FROM metric_suite_block_manifest WHERE graph_iri IN (OLD.graph_iri,NEW.graph_iri); END;
CREATE TRIGGER IF NOT EXISTS metric_evidence_delete_invalidates_blocks AFTER DELETE ON metric_suite_evidence
BEGIN DELETE FROM metric_suite_block_manifest WHERE graph_iri=OLD.graph_iri; END;
CREATE TRIGGER IF NOT EXISTS metric_result_insert_invalidates_shell AFTER INSERT ON metric_suite_result
BEGIN DELETE FROM metric_suite_shell WHERE graph_iri=NEW.graph_iri AND metric_id=NEW.metric_id; END;
CREATE TRIGGER IF NOT EXISTS metric_result_update_invalidates_shell AFTER UPDATE ON metric_suite_result
BEGIN DELETE FROM metric_suite_shell WHERE graph_iri=OLD.graph_iri AND metric_id=OLD.metric_id;
DELETE FROM metric_suite_shell WHERE graph_iri=NEW.graph_iri AND metric_id=NEW.metric_id; END;
CREATE TRIGGER IF NOT EXISTS metric_result_delete_invalidates_shell AFTER DELETE ON metric_suite_result
BEGIN DELETE FROM metric_suite_shell WHERE graph_iri=OLD.graph_iri AND metric_id=OLD.metric_id; END;
