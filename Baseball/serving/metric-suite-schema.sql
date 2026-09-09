-- Derived, disposable serving products. No ontology/proposal vocabulary.
CREATE TABLE IF NOT EXISTS metric_suite_manifest (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  version TEXT NOT NULL, implementation_sha256 TEXT NOT NULL
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
