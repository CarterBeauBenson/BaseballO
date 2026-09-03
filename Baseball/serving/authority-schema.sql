PRAGMA foreign_keys = ON;

CREATE TABLE authority_build (
    build_id TEXT PRIMARY KEY,
    contract_version INTEGER NOT NULL,
    created_at_utc TEXT NOT NULL,
    build_mode TEXT NOT NULL CHECK (build_mode IN ('incremental-events', 'full-rdf-rebuild')),
    contract_sha256 TEXT NOT NULL,
    schema_sha256 TEXT NOT NULL,
    materializer_sha256 TEXT NOT NULL,
    compiler_sha256 TEXT NOT NULL,
    module_catalog_sha256 TEXT NOT NULL,
    query_spec_set_sha256 TEXT NOT NULL,
    source_graph_count INTEGER NOT NULL,
    result_row_count INTEGER NOT NULL,
    processed_event_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'validated'))
) STRICT;

CREATE TABLE authority_source_graph (
    graph_iri TEXT PRIMARY KEY,
    source_module TEXT NOT NULL,
    event_id TEXT NOT NULL,
    promoted_at_utc TEXT NOT NULL,
    authoritative_triple_count INTEGER NOT NULL CHECK (authoritative_triple_count > 0),
    promotion_evidence_sha256 TEXT,
    event_sha256 TEXT
) STRICT;

CREATE TABLE authority_query_manifest (
    query_id TEXT PRIMARY KEY,
    spec_path TEXT NOT NULL,
    spec_sha256 TEXT NOT NULL,
    table_name TEXT NOT NULL,
    variables_json TEXT NOT NULL,
    row_count INTEGER NOT NULL
) STRICT;

CREATE TABLE entity_name_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    entity_kind TEXT NOT NULL CHECK (entity_kind IN ('person', 'organization', 'venue')),
    entity_iri TEXT NOT NULL,
    name_ice_iri TEXT NOT NULL,
    name_text TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, name_ice_iri)
) STRICT;

CREATE TABLE person_nickname_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    person_iri TEXT NOT NULL,
    nickname_ice_iri TEXT NOT NULL,
    nickname_text TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, nickname_ice_iri)
) STRICT;

CREATE TABLE entity_identifier_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    entity_kind TEXT NOT NULL CHECK (entity_kind IN ('person', 'organization', 'venue')),
    entity_iri TEXT NOT NULL,
    identifier_ice_iri TEXT NOT NULL,
    reference_system_iri TEXT NOT NULL,
    identifier_text TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, identifier_ice_iri)
) STRICT;

CREATE TABLE person_measurement_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    measurement_kind TEXT NOT NULL CHECK (measurement_kind IN ('height', 'mass')),
    person_iri TEXT NOT NULL,
    quality_iri TEXT NOT NULL,
    measurement_ice_iri TEXT NOT NULL,
    value_lexical TEXT NOT NULL,
    value_decimal REAL NOT NULL,
    unit_iri TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, measurement_ice_iri)
) STRICT;

CREATE TABLE person_side_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    side_kind TEXT NOT NULL CHECK (side_kind IN ('batting', 'throwing')),
    person_iri TEXT NOT NULL,
    disposition_iri TEXT NOT NULL,
    nominal_measurement_ice_iri TEXT NOT NULL,
    reference_system_iri TEXT NOT NULL,
    nominal_code TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, nominal_measurement_ice_iri)
) STRICT;

CREATE TABLE person_position_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    person_iri TEXT NOT NULL,
    description_ice_iri TEXT NOT NULL,
    reference_system_iri TEXT NOT NULL,
    position_code TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, description_ice_iri)
) STRICT;

CREATE TABLE venue_coordinate_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    venue_iri TEXT NOT NULL,
    reference_point_iri TEXT NOT NULL,
    coordinate_ice_iri TEXT NOT NULL,
    reference_system_iri TEXT NOT NULL,
    latitude_lexical TEXT NOT NULL,
    latitude_decimal REAL NOT NULL,
    longitude_lexical TEXT NOT NULL,
    longitude_decimal REAL NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, coordinate_ice_iri)
) STRICT;

CREATE TABLE venue_capacity_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    venue_iri TEXT NOT NULL,
    quality_iri TEXT NOT NULL,
    measurement_ice_iri TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, measurement_ice_iri)
) STRICT;

CREATE TABLE venue_surface_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    venue_iri TEXT NOT NULL,
    playing_surface_iri TEXT NOT NULL,
    nominal_measurement_ice_iri TEXT NOT NULL,
    reference_system_iri TEXT NOT NULL,
    nominal_code TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, nominal_measurement_ice_iri)
) STRICT;

CREATE TABLE calendar_day_fact (
    query_id TEXT NOT NULL REFERENCES authority_query_manifest(query_id),
    graph_iri TEXT NOT NULL REFERENCES authority_source_graph(graph_iri) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    date_identifier_iri TEXT NOT NULL,
    date_value TEXT NOT NULL,
    day_iri TEXT NOT NULL,
    binding_json TEXT NOT NULL,
    binding_sha256 TEXT NOT NULL,
    PRIMARY KEY (query_id, graph_iri, date_identifier_iri)
) STRICT;

CREATE INDEX entity_name_lookup_idx ON entity_name_fact(entity_kind, name_text, entity_iri);
CREATE INDEX entity_identifier_lookup_idx ON entity_identifier_fact(entity_kind, identifier_text, entity_iri);
CREATE INDEX person_measurement_lookup_idx ON person_measurement_fact(measurement_kind, value_decimal, person_iri);
CREATE INDEX person_side_lookup_idx ON person_side_fact(side_kind, nominal_code, person_iri);
CREATE INDEX person_position_lookup_idx ON person_position_fact(position_code, person_iri);
CREATE INDEX venue_coordinate_lookup_idx ON venue_coordinate_fact(latitude_decimal, longitude_decimal, venue_iri);
CREATE INDEX venue_capacity_lookup_idx ON venue_capacity_fact(capacity, venue_iri);
CREATE INDEX venue_surface_lookup_idx ON venue_surface_fact(nominal_code, venue_iri);
CREATE INDEX calendar_day_lookup_idx ON calendar_day_fact(date_value, day_iri);
