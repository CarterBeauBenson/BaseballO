#!/usr/bin/env python3
"""Validate BaseballO structure and active source contracts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote

import yaml
from pyshacl import validate as validate_shacl
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.plugins.sparql import prepareQuery


ROOT = Path(__file__).resolve().parents[1]
GIT_ROOT = ROOT.parent
ACTIVE_MAPPING = ROOT / "sources" / "mlb-game" / "mapping" / "mlb-game.rml.ttl"
MAPPING_VALIDATOR = (
    ROOT / "sources" / "mlb-game" / "mapping" / "validate_mlb_game_mapping.py"
)
SOURCE_MODULE_CATALOG = ROOT / "sources" / "source-modules.json"
ONTOLOGY_CURATION_VALIDATOR = ROOT / "scripts" / "validate_ontology_curation.py"
SEMANTIC_CHANGE_CONTROL_VALIDATOR = (
    ROOT / "scripts" / "validate_semantic_change_control.py"
)
ONTOLOGY_CURATION_TEST = ROOT / "tests" / "test_ontology_curation.py"
SEMANTIC_CHANGE_CONTROL_TEST = ROOT / "tests" / "test_semantic_change_control.py"
QUERY_SCOPE_CATALOG = ROOT / "sparql" / "source-scope-catalog.json"
AUTHORITATIVE_SHACL = ROOT / "sources" / "mlb-game" / "shacl" / "authoritative.ttl"
CONTEXT_BUILDER = ROOT / "scripts" / "pipeline" / "prepare-rml-context.py"
ONTOLOGY_OVERLAY_VALIDATOR = ROOT / "scripts" / "validate_ontology_overlay.py"
RML_MERMAID_GENERATOR = ROOT / "scripts" / "generate_rml_mermaid.py"
SELECTIVE_REASONING_TEST = ROOT / "scripts" / "reasoning" / "test-selective-reasoning.py"
REASONING_BASELINE_GENERATOR = (
    ROOT / "scripts" / "reasoning" / "generate-fixture-proof-baseline.py"
)
SERVING_LAYER_TEST = ROOT / "tests" / "test_serving_layer.py"
SERVING_MATERIALIZER_TEST = ROOT / "tests" / "test_serving_materializer.py"
DSQ_QUERY_MODULE_TEST = ROOT / "tests" / "test_dsq_query_modules.py"
DSQ_SQL_MATERIALIZATION_TEST = ROOT / "tests" / "test_dsq_sql_materializations.py"
PROMOTED_GRAPH_EVENT_TEST = ROOT / "tests" / "test_promoted_graph_events.py"
AUTHORITY_SERVING_TEST = ROOT / "tests" / "test_authority_serving_materializer.py"
REPOSITORY_VALIDATION_OBSERVER_TEST = (
    ROOT / "tests" / "test_repository_validation_observer.py"
)
SERVING_EQUIVALENCE_TEST = ROOT / "tests" / "test_serving_equivalence.py"
SPARQL_SOURCE_SCOPE_TEST = ROOT / "tests" / "test_sparql_source_scopes.py"
SELECTIVE_REASONER = ROOT / "scripts" / "reasoning" / "selective_reasoner.py"
SELECTIVE_PROVER = ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py"
REASONING_EVIDENCE = ROOT / "reasoning" / "evidence" / "fixture-566279-pa-0.json"
REASONING_REVIEW_SAMPLES = ROOT / "reasoning" / "reviewed-samples.json"
REASONING_REVIEW_EVIDENCE = (
    ROOT / "reasoning" / "evidence" / "fixture-566279-reviewed-samples.json"
)
REASONING_REVIEW_EVALUATOR = ROOT / "scripts" / "reasoning" / "evaluate-reviewed-samples.py"
REASONING_PROFILE_ADMISSION = ROOT / "reasoning" / "profile-admission-tests.json"
SAMPLE = ROOT / "data" / "raw" / "game-566279.json"
RAW_SAMPLE_ROOT = ROOT / "data" / "raw" / "samples"
REVIEW_SAMPLE = RAW_SAMPLE_ROOT / "2026-07-16" / "823440.json"
IN_PLAY_INTERFERENCE_SAMPLE = RAW_SAMPLE_ROOT / "2026-07-20" / "824898.json"
TRIPLE_PLAY_SAMPLE = RAW_SAMPLE_ROOT / "2026-07-21" / "824165.json"
WILD_PITCH_UNCAUGHT_THIRD_STRIKE_SAMPLE = (
    RAW_SAMPLE_ROOT / "2026-07-26" / "824810.json"
)
PASSED_BALL_UNCAUGHT_THIRD_STRIKE_SAMPLE = (
    RAW_SAMPLE_ROOT / "2026-07-24" / "822952.json"
)
MULTI_CONTROL_FAILURE_SAMPLE = RAW_SAMPLE_ROOT / "2026-08-03" / "823757.json"
ROSTER_TEAM_CONTEXT_SAMPLE = RAW_SAMPLE_ROOT / "2026-08-02" / "823919.json"
EXTRA_INNING_CONTEXT_SAMPLE = RAW_SAMPLE_ROOT / "2026-07-17" / "823766.json"
MAPPING_SAMPLES = (
    SAMPLE,
    REVIEW_SAMPLE,
    IN_PLAY_INTERFERENCE_SAMPLE,
    TRIPLE_PLAY_SAMPLE,
    WILD_PITCH_UNCAUGHT_THIRD_STRIKE_SAMPLE,
    PASSED_BALL_UNCAUGHT_THIRD_STRIKE_SAMPLE,
    ROSTER_TEAM_CONTEXT_SAMPLE,
    *sorted((ROOT / "data" / "raw" / "samples" / "2026-08-03").glob("[0-9]*.json")),
)
SPARQL_ROOT = ROOT / "sparql"
QUERY_BUILDERS = (
    ROOT / "web" / "query-builder" / "analytics-query-builder.js",
    ROOT / "web" / "query-builder" / "empty-games-query-builder.js",
    ROOT / "web" / "query-builder" / "hit-query-builder.js",
)
WEB_ROOT = ROOT / "web"
CANNED_AUDIT_ROOT = ROOT / "benchmarks" / "canned-query-audit"
CANNED_AUDIT_BASELINE = CANNED_AUDIT_ROOT / "corpus-2026-08-03-baseline.json"
ADVANCED_QUERY_ROOT = SPARQL_ROOT / "advanced"
ADVANCED_QUERY_CATALOG = ADVANCED_QUERY_ROOT / "advanced-query-catalog.json"
ADVANCED_AUDIT_ROOT = ROOT / "benchmarks" / "advanced-query-audit"
ADVANCED_AUDIT_BASELINE = ADVANCED_AUDIT_ROOT / "corpus-2026-08-03-baseline.json"
QUERY_AUDIT_EVIDENCE_REGISTER = ROOT / "benchmarks" / "query-audit-evidence-register.json"
QUERY_INDEX_BENCHMARK_ROOT = ROOT / "benchmarks" / "query-index"
QUERY_INDEX_CORPUS_BASELINE = QUERY_INDEX_BENCHMARK_ROOT / "corpus-2026-08-03-baseline.json"
QUERY_INDEX_EVIDENCE_REGISTER = QUERY_INDEX_BENCHMARK_ROOT / "evidence-register.json"
TDB2_EXECUTION_ROOT = QUERY_INDEX_BENCHMARK_ROOT / "tdb2-execution"
TDB2_EXECUTION_SUMMARY = TDB2_EXECUTION_ROOT / "tdb2-execution-summary.json"
REVIEWED_QUERY_ROUTING = SPARQL_ROOT / "query-index" / "operational-query-routing.json"
QUERY_INDEX_SEMANTIC_CONTRACT = SPARQL_ROOT / "query-index" / "semantic-contract.json"
SHACL_ROOT = ROOT / "shacl"
PAQ_CONTRACT = ROOT / "serving" / "plate-appearance-quality-v1.json"
SH = Namespace("http://www.w3.org/ns/shacl#")
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
CCO = Namespace("https://www.commoncoreontologies.org/")
IDX = Namespace("https://w3id.org/baseball/query-index/")

REQUIRED_PATHS = (
    GIT_ROOT / ".editorconfig",
    GIT_ROOT / ".gitattributes",
    GIT_ROOT / ".github" / "workflows" / "validate.yml",
    GIT_ROOT / ".github" / "CODEOWNERS",
    GIT_ROOT / ".githooks" / "pre-push",
    GIT_ROOT / "AGENTS.md",
    GIT_ROOT / "README.md",
    ROOT / "README.md",
    ROOT / "REPOSITORY-LAYOUT.md",
    ROOT / "ROADMAP.md",
    ROOT / "governance" / "README.md",
    ROOT / "governance" / "RECENT-WORK-AUDIT-2026-08-28.md",
    ROOT / "governance" / "ontology-curation-debt.json",
    ROOT / "governance" / "semantic-freeze.json",
    ROOT / "governance" / "proposal-review.schema.json",
    ROOT / "governance" / "templates" / "proposal-review.json",
    ROOT / "benchmarks" / "README.md",
    QUERY_AUDIT_EVIDENCE_REGISTER,
    ROOT / "ontology" / "BaseballO.ttl",
    ROOT / "ontology" / "BaseballO-axioms-overlay.ttl",
    ROOT / "ontology" / "CommonCoreOntologiesMerged.ttl",
    ACTIVE_MAPPING,
    ROOT / "mappings" / "policies" / "modeling-choices.yaml",
    ROOT / "sources" / "mlb-game" / "mapping" / "iri-policy.yaml",
    ROOT / "mermaid" / "README.md",
    ROOT / "sources" / "mlb-game" / "review" / "rml-mermaid-manifest.json",
    ROOT / "mermaid" / "patterns" / "README.md",
    ROOT / "sources" / "README.md",
    SOURCE_MODULE_CATALOG,
    ROOT / "sources" / "mlb-game" / "README.md",
    ROOT / "sources" / "mlb-game" / "SEMANTIC-AUDIT.md",
    ROOT / "sources" / "mlb-game" / "review" / "README.md",
    ROOT / "sources" / "mlb-game" / "review" / "semantic-status.json",
    ROOT / "proposals" / "README.md",
    SHACL_ROOT / "README.md",
    AUTHORITATIVE_SHACL,
    SHACL_ROOT / "query-index.ttl",
    SHACL_ROOT / "reasoning-output.ttl",
    ROOT / "reasoning" / "README.md",
    ROOT / "reasoning" / "bfo-clif-manifest.json",
    ROOT / "reasoning" / "profiles" / "event-order.json",
    ROOT / "reasoning" / "profiles" / "event-structure.json",
    ROOT / "reasoning" / "profiles" / "participation.json",
    REASONING_EVIDENCE,
    REASONING_REVIEW_SAMPLES,
    REASONING_REVIEW_EVIDENCE,
    REASONING_REVIEW_EVALUATOR,
    REASONING_PROFILE_ADMISSION,
    WEB_ROOT / "package.json",
    WEB_ROOT / "index.html",
    WEB_ROOT / "styles.css",
    WEB_ROOT / "app.js",
    WEB_ROOT / "server.mjs",
    WEB_ROOT / "query-builder" / "empty-games-query-builder.js",
    WEB_ROOT / "tests" / "analytics-query-builder.test.mjs",
    ROOT / "infra" / "README.md",
    ROOT / "infra" / "fuseki" / "configuration" / "baseball-dev.ttl",
    ROOT / "infra" / "versions.psd1",
    ROOT / "scripts" / "infra" / "launch-explorer.ps1",
    ROOT / "scripts" / "infra" / "install-explorer-shortcut.ps1",
    ROOT / "scripts" / "pipeline" / "import-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "graph-pair-transaction.py",
    ROOT / "scripts" / "pipeline" / "test-graph-pair-transaction.py",
    ROOT / "scripts" / "pipeline" / "materialize-serving-layer.py",
    ROOT / "scripts" / "pipeline" / "query-serving-layer.py",
    ROOT / "scripts" / "pipeline" / "verify-serving-fingerprint.py",
    ROOT / "scripts" / "pipeline" / "verify-explorer-serving.py",
    ROOT / "scripts" / "pipeline" / "test-manual-vertical-slice.ps1",
    ROOT / "scripts" / "pipeline" / "run-rml.ps1",
    ROOT / "scripts" / "pipeline" / "prepare-rml-context.py",
    ROOT / "scripts" / "pipeline" / "load-game-graph.ps1",
    ROOT / "scripts" / "pipeline" / "validate-generated-rdf.py",
    ROOT / "scripts" / "pipeline" / "validate-shacl.py",
    ROOT / "scripts" / "pipeline" / "validate-mapping-shacl-contracts.py",
    ROOT / "scripts" / "pipeline" / "build-query-index.ps1",
    ROOT / "scripts" / "pipeline" / "compile-query-index.py",
    ROOT / "scripts" / "pipeline" / "compile-dsq-query.py",
    ROOT / "scripts" / "pipeline" / "emit-promoted-graph-event.py",
    ROOT / "scripts" / "pipeline" / "materialize-authority-serving.py",
    ROOT / "scripts" / "pipeline" / "record-repository-validation.py",
    ROOT / "scripts" / "pipeline" / "query-serving-candidate.py",
    ROOT / "scripts" / "pipeline" / "prove-serving-equivalence.py",
    ROOT / "scripts" / "pipeline" / "query-index-common.ps1",
    ROOT / "scripts" / "infra" / "canonical-text.ps1",
    ROOT / "scripts" / "pipeline" / "test-query-index.ps1",
    ROOT / "scripts" / "pipeline" / "benchmark-query-index.ps1",
    ROOT / "scripts" / "pipeline" / "benchmark-query-index-corpus.ps1",
    ROOT / "scripts" / "pipeline" / "capture-tdb2-query-execution.ps1",
    ROOT / "scripts" / "pipeline" / "run-reviewed-query.ps1",
    ROOT / "scripts" / "pipeline" / "test-reviewed-query-routing.ps1",
    ROOT / "scripts" / "pipeline" / "capture-query-algebra.ps1",
    ROOT / "scripts" / "pipeline" / "export-dehydration-package.ps1",
    ROOT / "scripts" / "pipeline" / "restore-dehydration-package.ps1",
    ROOT / "scripts" / "pipeline" / "validate-dehydration-package.py",
    ROOT / "scripts" / "pipeline" / "test-dehydration-package.ps1",
    ROOT / "scripts" / "pipeline" / "test-query-index-failure.ps1",
    ROOT / "scripts" / "pipeline" / "audit-canned-queries.ps1",
    ROOT / "scripts" / "pipeline" / "audit-advanced-queries.ps1",
    ROOT / "scripts" / "reasoning" / "sync-bfo-clif.py",
    ROOT / "scripts" / "reasoning" / "selective_reasoner.py",
    ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py",
    ROOT / "scripts" / "reasoning" / "run-selective-reasoning.ps1",
    ONTOLOGY_CURATION_VALIDATOR,
    SEMANTIC_CHANGE_CONTROL_VALIDATOR,
    ONTOLOGY_CURATION_TEST,
    SEMANTIC_CHANGE_CONTROL_TEST,
    REASONING_BASELINE_GENERATOR,
    SELECTIVE_REASONING_TEST,
    SERVING_LAYER_TEST,
    SERVING_MATERIALIZER_TEST,
    RML_MERMAID_GENERATOR,
    ROOT / "sparql" / "empty-games-prototype.rq",
    ROOT / "sparql" / "serving" / "game-dimension.rq",
    ROOT / "serving" / "README.md",
    ROOT / "serving" / "contract.json",
    PAQ_CONTRACT,
    ROOT / "serving" / "schema.sql",
    ROOT / "serving" / "authority-contract.json",
    ROOT / "serving" / "authority-schema.sql",
    ROOT / "serving" / "nifi" / "flow-contract.json",
    ROOT / "serving" / "nifi" / "provision.ps1",
    ROOT / "serving" / "equivalence" / "flow-contract.json",
    ROOT / "serving" / "equivalence" / "provision.ps1",
    ROOT / "infra" / "nifi" / "repository-evidence" / "flow-contract.json",
    ROOT / "infra" / "nifi" / "repository-evidence" / "provision.ps1",
    ADVANCED_QUERY_ROOT / "README.md",
    ADVANCED_QUERY_CATALOG,
    ROOT / "sparql" / "query-inventory.md",
    QUERY_SCOPE_CATALOG,
    ROOT / "sparql" / "multi-source" / "README.md",
    ROOT / "sparql" / "derived" / "README.md",
    ROOT / "sparql" / "graph-condensation-requirements.md",
    ROOT / "sparql" / "query-index" / "README.md",
    ROOT / "sparql" / "query-index" / "query-decision-matrix.md",
    REVIEWED_QUERY_ROUTING,
    QUERY_INDEX_EVIDENCE_REGISTER,
    ROOT / "sparql" / "query-index" / "dehydration-package.md",
    ROOT / "sparql" / "query-index" / "benchmarks" / "benchmark-pairs.json",
    ROOT / "sparql" / "query-modules" / "README.md",
    ROOT / "sparql" / "query-modules" / "catalog.json",
    ROOT / "sparql" / "query-modules" / "authority" / "README.md",
    ROOT / "sparql" / "query-modules" / "authority" / "catalog.json",
    DSQ_QUERY_MODULE_TEST,
    DSQ_SQL_MATERIALIZATION_TEST,
    PROMOTED_GRAPH_EVENT_TEST,
    AUTHORITY_SERVING_TEST,
    REPOSITORY_VALIDATION_OBSERVER_TEST,
    SERVING_EQUIVALENCE_TEST,
    SPARQL_SOURCE_SCOPE_TEST,
    ROOT / "benchmarks" / "query-index" / "README.md",
    ROOT / "benchmarks" / "query-index" / "fixture-566279-baseline.md",
    ROOT / "benchmarks" / "query-index" / "fixture-566279-baseline.json",
    ROOT / "benchmarks" / "query-index" / "corpus-2026-08-03-baseline.md",
    QUERY_INDEX_CORPUS_BASELINE,
    ROOT / "benchmarks" / "query-index" / "algebra" / "optimized-algebra-summary.md",
    ROOT / "benchmarks" / "query-index" / "algebra" / "optimized-algebra-summary.json",
    TDB2_EXECUTION_ROOT / "README.md",
    TDB2_EXECUTION_SUMMARY,
    CANNED_AUDIT_ROOT / "README.md",
    CANNED_AUDIT_ROOT / "corpus-2026-08-03-baseline.md",
    CANNED_AUDIT_BASELINE,
    ADVANCED_AUDIT_ROOT / "README.md",
    ADVANCED_AUDIT_ROOT / "corpus-2026-08-03-baseline.md",
    ADVANCED_AUDIT_BASELINE,
    ROOT / "benchmarks" / "serving-layer" / "README.md",
    ROOT / "benchmarks" / "serving-layer" / "current.json",
    SAMPLE,
)

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REMOTE_PREFIXES = ("http://", "https://", "mailto:", "#")
MERMAID_DIAGRAM_TYPES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "gitGraph",
)


def require_layout() -> None:
    missing = [path.relative_to(GIT_ROOT) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        raise ValueError("Missing required paths: " + ", ".join(map(str, missing)))


def validate_layout_boundaries() -> int:
    retired = (
        ROOT / ".editorconfig",
        ROOT / ".gitattributes",
        ROOT / ".github",
        ROOT / "generated",
        ROOT / "source-schema",
        ROOT / "mappings" / "direct",
        ROOT / "mermaid" / "proposals",
        ROOT / "ontology" / "proposals",
    )
    populated = [
        path.relative_to(GIT_ROOT)
        for path in retired
        if path.exists() and any(child.is_file() for child in path.rglob("*"))
    ]
    if populated:
        raise ValueError(f"Retired repository locations contain files: {populated}")

    stale_names = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file()
        and "archive" not in path.parts
        and "mlb-direct" in path.name.lower()
    ]
    if stale_names:
        raise ValueError(f"Active paths retain the retired mlb-direct name: {stale_names}")

    workflow = (GIT_ROOT / ".github" / "workflows" / "validate.yml").read_text(
        encoding="utf-8"
    )
    required_workflow_fragments = (
        "Baseball/requirements-dev.txt",
        "cache-dependency-path: Baseball/requirements-dev.txt",
        "python Baseball/scripts/validate_repository.py",
        "runs-on: ubuntu-latest",
        "runs-on: windows-latest",
    )
    missing = [value for value in required_workflow_fragments if value not in workflow]
    if missing:
        raise ValueError(f"Git-root validation workflow has stale project paths: {missing}")

    attributes = (GIT_ROOT / ".gitattributes").read_text(encoding="utf-8")
    required_attribute_fragments = (
        "*.rq text eol=lf",
        "Baseball/data/raw/** -text -eol",
        "Baseball/data/raw/samples/2026-07-14/823443.json text eol=lf",
        "Baseball/data/raw/samples/2026-07-15/schedule.json text eol=lf",
        "Baseball/data/raw/samples/2026-07-16/823440.json text eol=lf",
        "Baseball/data/raw/samples/2026-07-17/822789.json text eol=lf",
    )
    missing = [value for value in required_attribute_fragments if value not in attributes]
    if missing:
        raise ValueError(f"Git attributes omit portability boundaries: {missing}")
    editorconfig = (GIT_ROOT / ".editorconfig").read_text(encoding="utf-8")
    raw_editor_boundary = (
        "[Baseball/data/raw/**]",
        "charset = unset",
        "end_of_line = unset",
        "insert_final_newline = unset",
        "trim_trailing_whitespace = unset",
    )
    missing = [value for value in raw_editor_boundary if value not in editorconfig]
    if missing:
        raise ValueError(f"EditorConfig can rewrite raw evidence bytes: {missing}")
    return len(retired)


def validate_json() -> int:
    files = list(ROOT.rglob("*.json"))
    for path in files:
        with path.open(encoding="utf-8") as stream:
            json.load(stream)
    return len(files)


def validate_yaml() -> int:
    files = [
        path
        for pattern in ("*.yaml", "*.yml")
        for path in ROOT.rglob(pattern)
        if "archive" not in path.parts
    ]
    for path in files:
        with path.open(encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
        if not isinstance(value, dict) or not value:
            raise ValueError(f"Active YAML contract is empty or not a mapping: {path}")
    return len(files)


def validate_raw_corpus() -> tuple[int, int, int]:
    start = date.fromisoformat("2026-07-14")
    end = date.fromisoformat("2026-08-25")
    expected_dates: list[str] = []
    current = start
    while current <= end:
        expected_dates.append(current.isoformat())
        current += timedelta(days=1)

    schedule_files = sorted(RAW_SAMPLE_ROOT.glob("????-??-??/schedule.json"))
    game_files = sorted(
        path
        for path in RAW_SAMPLE_ROOT.glob("????-??-??/*.json")
        if path.stem.isdigit()
    )
    if len(schedule_files) != 43 or len(game_files) != 546:
        raise ValueError(
            "Expected 43 dated schedules and 546 canonical raw game files; "
            f"found {len(schedule_files)} and {len(game_files)}"
        )
    actual_dates = [path.parent.name for path in schedule_files]
    if actual_dates != expected_dates:
        raise ValueError("Raw schedule dates do not cover 2026-07-14 through 2026-08-25")

    game_pks: set[str] = set()
    for path in game_files:
        document = json.loads(path.read_text(encoding="utf-8"))
        game_pk = str(document.get("gamePk", ""))
        official_date = str(
            document.get("gameData", {}).get("datetime", {}).get("officialDate", "")
        )
        state = str(
            document.get("gameData", {}).get("status", {}).get("abstractGameState", "")
        )
        if game_pk != path.stem:
            raise ValueError(f"Raw game filename disagrees with gamePk: {path}")
        if game_pk in game_pks:
            raise ValueError(f"Duplicate raw gamePk in dated corpus: {game_pk}")
        if official_date != path.parent.name:
            raise ValueError(f"Raw game is not stored under its official date: {path}")
        if state != "Final":
            raise ValueError(f"Raw corpus contains a non-final game: {path}")
        game_pks.add(game_pk)

    scheduled_final_pks: set[str] = set()
    game_types: dict[str, str] = {}
    final_schedule_entries = 0
    for path in schedule_files:
        schedule = json.loads(path.read_text(encoding="utf-8"))
        for schedule_date in schedule.get("dates", []):
            for game in schedule_date.get("games", []):
                if game.get("status", {}).get("abstractGameState") == "Final":
                    game_pk = str(game.get("gamePk", ""))
                    if not game_pk.isdigit():
                        raise ValueError(f"Schedule contains an unsafe final gamePk: {path}")
                    game_type = str(game.get("gameType", ""))
                    previous_type = game_types.get(game_pk)
                    if previous_type is not None and previous_type != game_type:
                        raise ValueError(f"Schedule gameType changed for game {game_pk}")
                    game_types[game_pk] = game_type
                    final_schedule_entries += 1
                    scheduled_final_pks.add(game_pk)
    if final_schedule_entries != 552:
        raise ValueError(
            f"Expected 552 final schedule entries; found {final_schedule_entries}"
        )
    if scheduled_final_pks != game_pks:
        missing = sorted(scheduled_final_pks - game_pks)
        extra = sorted(game_pks - scheduled_final_pks)
        raise ValueError(
            f"Raw game and final schedule identities differ; missing={missing}, extra={extra}"
        )
    all_star_pks = {game_pk for game_pk, game_type in game_types.items() if game_type == "A"}
    regular_season_pks = {game_pk for game_pk, game_type in game_types.items() if game_type == "R"}
    unsupported_game_types = sorted(set(game_types.values()) - {"A", "R"})
    if all_star_pks != {"823443"} or len(regular_season_pks) != 545 or unsupported_game_types:
        raise ValueError(
            "Raw corpus must contain 545 regular-season games and only the separately "
            "scoped 2026 All-Star Game 823443; "
            f"regular={len(regular_season_pks)}, all_star={sorted(all_star_pks)}, "
            f"unsupported_types={unsupported_game_types}"
        )
    return len(schedule_files), len(game_files), final_schedule_entries


def validate_review_context() -> None:
    source = REVIEW_SAMPLE
    with tempfile.TemporaryDirectory(prefix="baseballo-review-context-") as directory:
        output = Path(directory) / "context.json"
        subprocess.run(
            [sys.executable, str(CONTEXT_BUILDER), str(source), str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        document = json.loads(output.read_text(encoding="utf-8"))

    plays = {
        int(play["about"]["atBatIndex"]): play
        for play in document["liveData"]["plays"]["allPlays"]
    }
    challenge = plays[37]["_baseballO"]
    umpire_review = plays[44]["_baseballO"]
    if (
        challenge.get("reviewInitiation") != "challenge"
        or challenge.get("reviewType") != "pitch_result"
        or challenge.get("reviewOriginalDecision") != "strike"
        or challenge.get("reviewFinalDecision") != "strike"
        or challenge.get("reviewChallengerId") != "687282"
    ):
        raise ValueError("Player challenge review context regression in game 823440")
    if (
        umpire_review.get("reviewInitiation") != "umpire_review"
        or umpire_review.get("reviewType") != "home_run"
        or "reviewChallengerId" in umpire_review
        or "reviewOriginalDecision" in umpire_review
        or "reviewFinalDecision" in umpire_review
        or "reviewPattern" in umpire_review
    ):
        raise ValueError("Umpire-initiated review context regression in game 823440")
    source_document = json.loads(source.read_text(encoding="utf-8"))
    if "_baseballO" in source_document:
        raise ValueError("Raw game 823440 was modified with execution-only context")

    with tempfile.TemporaryDirectory(prefix="baseballo-in-play-context-") as directory:
        output = Path(directory) / "context.json"
        subprocess.run(
            [sys.executable, str(CONTEXT_BUILDER), str(IN_PLAY_INTERFERENCE_SAMPLE), str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        document = json.loads(output.read_text(encoding="utf-8"))
    interference_play = next(
        play
        for play in document["liveData"]["plays"]["allPlays"]
        if int(play["about"]["atBatIndex"]) == 32
    )
    if interference_play["_baseballO"].get("terminalPitchIsInPlay") is not True:
        raise ValueError("Terminal in-play catcher-interference regression in game 824898")
    source_document = json.loads(IN_PLAY_INTERFERENCE_SAMPLE.read_text(encoding="utf-8"))
    if "_baseballO" in source_document:
        raise ValueError("Raw game 824898 was modified with execution-only context")

    uncaught_cases = (
        (WILD_PITCH_UNCAUGHT_THIRD_STRIKE_SAMPLE, 32, "wild_pitch"),
        (PASSED_BALL_UNCAUGHT_THIRD_STRIKE_SAMPLE, 53, "passed_ball"),
    )
    for source, at_bat_index, expected_classification in uncaught_cases:
        with tempfile.TemporaryDirectory(
            prefix="baseballo-uncaught-third-strike-context-"
        ) as directory:
            output = Path(directory) / "context.json"
            subprocess.run(
                [sys.executable, str(CONTEXT_BUILDER), str(source), str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            document = json.loads(output.read_text(encoding="utf-8"))
        play = next(
            candidate
            for candidate in document["liveData"]["plays"]["allPlays"]
            if int(candidate["about"]["atBatIndex"]) == at_bat_index
        )
        context = play["_baseballO"]
        placeholders = [
            runner
            for runner in play["runners"]
            if runner["_baseballO"].get("isUncaughtThirdStrikePlaceholder") is True
        ]
        if (
            context.get("isUncaughtThirdStrike") is not True
            or context.get("uncaughtThirdStrikeEventType") != expected_classification
            or len(placeholders) != 1
            or placeholders[0]["_baseballO"].get("hasRunnerResolution") is not False
            or not placeholders[0]["_baseballO"].get("eventPlayId")
        ):
            raise ValueError(
                f"Uncaught-third-strike context regression in game {source.stem}"
            )
        source_document = json.loads(source.read_text(encoding="utf-8"))
        if "_baseballO" in source_document:
            raise ValueError(
                f"Raw game {source.stem} was modified with execution-only context"
            )

    with tempfile.TemporaryDirectory(
        prefix="baseballo-multi-control-failure-context-"
    ) as directory:
        output = Path(directory) / "context.json"
        subprocess.run(
            [
                sys.executable,
                str(CONTEXT_BUILDER),
                str(MULTI_CONTROL_FAILURE_SAMPLE),
                str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        document = json.loads(output.read_text(encoding="utf-8"))
    classification_event_ids = {
        runner["_baseballO"].get("eventPlayId")
        for play in document["liveData"]["plays"]["allPlays"]
        for runner in play.get("runners", [])
        if runner.get("details", {}).get("eventType")
        in {"passed_ball", "wild_pitch"}
    }
    if None in classification_event_ids or len(classification_event_ids) != 3:
        raise ValueError(
            "Multiple pitch-control failures within one plate appearance were collapsed "
            "in game 823757"
        )

    with tempfile.TemporaryDirectory(
        prefix="baseballo-roster-team-context-"
    ) as directory:
        output = Path(directory) / "context.json"
        subprocess.run(
            [
                sys.executable,
                str(CONTEXT_BUILDER),
                str(ROSTER_TEAM_CONTEXT_SAMPLE),
                str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        document = json.loads(output.read_text(encoding="utf-8"))
    source_document = json.loads(
        ROSTER_TEAM_CONTEXT_SAMPLE.read_text(encoding="utf-8")
    )
    raw_players = source_document["liveData"]["boxscore"]["teams"]
    if not any(
        "parentTeamId" not in player
        for side in ("away", "home")
        for player in raw_players[side]["players"].values()
    ):
        raise ValueError(
            "Roster-team regression sample no longer exercises a missing parentTeamId"
        )
    for side in ("away", "home"):
        team_boxscore = document["liveData"]["boxscore"]["teams"][side]
        expected_team_id = str(team_boxscore["team"]["id"])
        for player in team_boxscore["players"].values():
            if player.get("_baseballO", {}).get("teamId") != expected_team_id:
                raise ValueError(
                    f"Roster player team context regression in game 823919 ({side})"
                )
    if "_baseballO" in source_document:
        raise ValueError("Raw game 823919 was modified with execution-only context")

    with tempfile.TemporaryDirectory(
        prefix="baseballo-extra-inning-context-"
    ) as directory:
        output = Path(directory) / "context.json"
        subprocess.run(
            [
                sys.executable,
                str(CONTEXT_BUILDER),
                str(EXTRA_INNING_CONTEXT_SAMPLE),
                str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        document = json.loads(output.read_text(encoding="utf-8"))
    extra_inning_starts = {}
    for play in document["liveData"]["plays"]["allPlays"]:
        if play["about"]["inning"] == 10:
            key = (play["about"]["inning"], play["about"]["halfInning"])
            extra_inning_starts.setdefault(key, play["_baseballO"])
    for half, runner_id in (("top", "681715"), ("bottom", "694192")):
        occupancies = extra_inning_starts[(10, half)]["startBaseOccupancies"]
        if not any(
            occupancy.get("baseCode") == "2B"
            and occupancy.get("runnerId") == runner_id
            for occupancy in occupancies
        ):
            raise ValueError(
                f"Automatic runner start-state regression in game 823766 ({half})"
            )


def validate_turtle() -> int:
    files = list(ROOT.rglob("*.ttl"))
    for path in files:
        Graph().parse(path, format="turtle")
    return len(files)


def validate_shacl_profiles() -> int:
    profiles = {
        "authoritative": AUTHORITATIVE_SHACL,
        "query-index": SHACL_ROOT / "query-index.ttl",
        "reasoning-output": SHACL_ROOT / "reasoning-output.ttl",
    }
    shape_count = 0
    for name, path in profiles.items():
        shapes = Graph().parse(path, format="turtle")
        shape_count += len(set(shapes.subjects(RDF.type, SH.NodeShape)))
        conforms, _, report_text = validate_shacl(
            data_graph=Graph(),
            shacl_graph=shapes,
            inference="none",
            advanced=True,
            meta_shacl=True,
            allow_infos=True,
            allow_warnings=True,
        )
        if not conforms:
            raise ValueError(f"SHACL profile {name} is not meta-valid:\n{report_text}")

    invalid_authoritative = Graph()
    invalid_authoritative.add(
        (URIRef("urn:baseball:shacl-smoke:pitch"), RDF.type, BASE.PitchAct)
    )
    conforms, _, _ = validate_shacl(
        data_graph=invalid_authoritative,
        shacl_graph=Graph().parse(profiles["authoritative"], format="turtle"),
        inference="none",
        advanced=True,
    )
    if conforms:
        raise ValueError("Authoritative SHACL profile accepted an incomplete PitchAct")

    authoritative_shapes = Graph().parse(profiles["authoritative"], format="turtle")
    invalid_stasis = Graph()
    stasis = URIRef("urn:baseball:shacl-smoke:stasis")
    invalid_stasis.add((stasis, RDF.type, CCO.ont00000824))
    invalid_stasis.add((stasis, BFO.BFO_0000055, URIRef("urn:baseball:shacl-smoke:role")))
    conforms, report_graph, _ = validate_shacl(
        data_graph=invalid_stasis,
        shacl_graph=authoritative_shapes,
        inference="none",
        advanced=True,
    )
    stasis_messages = {str(value) for value in report_graph.objects(None, SH.resultMessage)}
    if conforms or not any("Stasis must not realize" in value for value in stasis_messages):
        raise ValueError("Authoritative SHACL does not enforce the Stasis realization prohibition")

    invalid_plate_appearance = Graph()
    plate_appearance = URIRef("urn:baseball:shacl-smoke:plate-appearance")
    invalid_plate_appearance.add((plate_appearance, RDF.type, BASE.PlateAppearance))
    invalid_plate_appearance.add(
        (plate_appearance, BFO.BFO_0000055, URIRef("urn:baseball:shacl-smoke:batter-role"))
    )
    conforms, report_graph, _ = validate_shacl(
        data_graph=invalid_plate_appearance,
        shacl_graph=authoritative_shapes,
        inference="none",
        advanced=True,
    )
    plate_appearance_messages = {
        str(value) for value in report_graph.objects(None, SH.resultMessage)
    }
    if conforms or not any(
        "must not duplicate the BatterAct realization edge" in value
        for value in plate_appearance_messages
    ):
        raise ValueError(
            "Authoritative SHACL does not keep BatterRole realization on BatterAct"
        )

    invalid_index = Graph()
    invalid_index.add(
        (URIRef("urn:baseball:shacl-smoke:hit"), RDF.type, IDX.HitFact)
    )
    conforms, _, _ = validate_shacl(
        data_graph=invalid_index,
        shacl_graph=Graph().parse(profiles["query-index"], format="turtle"),
        inference="none",
        advanced=True,
    )
    if conforms:
        raise ValueError("Query-index SHACL profile accepted an incomplete HitFact")

    invalid_reasoning = Graph()
    invalid_reasoning.add(
        (
            URIRef("urn:baseball:shacl-smoke:reasoning"),
            URIRef("http://www.w3.org/ns/prov#wasDerivedFrom"),
            URIRef("https://w3id.org/baseball/graph/game/566279"),
        )
    )
    conforms, _, _ = validate_shacl(
        data_graph=invalid_reasoning,
        shacl_graph=Graph().parse(profiles["reasoning-output"], format="turtle"),
        inference="none",
        advanced=True,
    )
    if conforms:
        raise ValueError("Reasoning-output SHACL profile accepted incomplete provenance")

    return shape_count


def validate_sparql() -> int:
    files = list(SPARQL_ROOT.rglob("*.rq"))
    component_files = list((SPARQL_ROOT / "query-index" / "components").glob("*.rq"))
    benchmark_files = list((SPARQL_ROOT / "query-index" / "benchmarks" / "indexed").glob("*.rq"))
    advanced_files = list(ADVANCED_QUERY_ROOT.glob("*.rq"))
    serving_files = list((SPARQL_ROOT / "serving").glob("*.rq"))
    canned_files = [
        path for path in files
        if path not in component_files
        and path not in benchmark_files
        and path not in advanced_files
        and path not in serving_files
    ]
    if (
        len(canned_files) != 51
        or len(component_files) != 13
        or len(benchmark_files) != 19
        or len(advanced_files) != 17
        or len(serving_files) != 6
    ):
        raise ValueError(
            "Expected 51 canned SPARQL queries, 13 query-index components, "
            "19 indexed benchmark companions, 17 advanced semantic queries, "
            "and six serving materialization queries; "
            f"found {len(canned_files)}, {len(component_files)}, "
            f"{len(benchmark_files)}, {len(advanced_files)}, and {len(serving_files)}"
        )
    for path in files:
        try:
            prepareQuery(path.read_text(encoding="utf-8"))
        except Exception as error:
            raise ValueError(
                f"SPARQL parse failed in {path.relative_to(ROOT)}: {error}"
            ) from error
    return len(files)


def validate_query_contract() -> None:
    query_files = list(SPARQL_ROOT.rglob("*.rq")) + list(QUERY_BUILDERS)
    prohibited = (
        ("removed participant predicate", "cco:ont00001833"),
        ("outcome-specific runner identity path", "runner-act/advance"),
        ("outcome-specific runner identity path", "runner-act/score"),
        ("outcome-specific runner identity path", "runner-act/out"),
    )
    for path in query_files:
        text = path.read_text(encoding="utf-8")
        for description, fragment in prohibited:
            if fragment in text:
                raise ValueError(
                    f"Query contract contains {description} in "
                    f"{path.relative_to(ROOT)}: {fragment}"
                )


def validate_source_module_contract() -> tuple[int, set[str]]:
    catalog = json.loads(SOURCE_MODULE_CATALOG.read_text(encoding="utf-8"))
    if (
        catalog.get("artifactType") != "baseballo-source-module-catalog"
        or catalog.get("contractVersion") != 2
    ):
        raise ValueError("Source-module catalog envelope is invalid")

    modules = catalog.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("Source-module catalog must declare at least one module")
    ids: set[str] = set()
    registered_rml: set[Path] = set()
    registered_shacl: set[Path] = set()
    registered_policies: set[Path] = set()
    graph_prefixes: list[tuple[str, str]] = []
    nifi_process_groups: dict[str, str] = {}
    for module in modules:
        module_id = str(module.get("id", ""))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", module_id):
            raise ValueError(f"Invalid source-module id: {module_id!r}")
        if module_id in ids:
            raise ValueError(f"Duplicate source-module id: {module_id}")
        ids.add(module_id)
        expected_root = f"sources/{module_id}"
        if module.get("moduleRoot") != expected_root:
            raise ValueError(f"Source module has a noncanonical root: {module_id}")
        required_fields = (
            "schemaRoot", "mappingRoot", "reviewRoot", "rml", "shacl", "policies",
            "authoritativeGraphPrefixes", "nifiProcessGroups",
            "integrationBoundary", "disconnectPolicy", "operationalStatus",
            "semanticStatus", "extensionPolicy", "semanticStatusRecord",
        )
        missing = [field for field in required_fields if not module.get(field)]
        if missing:
            raise ValueError(
                f"Source module {module_id} is missing: {', '.join(missing)}"
            )
        if module["operationalStatus"] not in {"active", "paused", "retired"}:
            raise ValueError(
                f"Source module {module_id} has invalid operationalStatus"
            )
        if module["semanticStatus"] not in {
            "proposed", "awaiting-ontologist-review", "frozen-known-debt", "approved"
        }:
            raise ValueError(f"Source module {module_id} has invalid semanticStatus")
        if module["extensionPolicy"] not in {
            "blocked-pending-ontologist-review", "approved-designs-only"
        }:
            raise ValueError(f"Source module {module_id} has invalid extensionPolicy")
        module_root = (ROOT / expected_root).resolve()
        for field in ("schemaRoot", "mappingRoot", "reviewRoot"):
            path = (ROOT / str(module[field])).resolve()
            if not path.is_dir() or not path.is_relative_to(module_root):
                raise ValueError(f"Source module {module_id} has invalid {field}")
        semantic_status_path = (ROOT / str(module["semanticStatusRecord"])).resolve()
        if (
            not semantic_status_path.is_file()
            or not semantic_status_path.is_relative_to((module_root / "review").resolve())
        ):
            raise ValueError(
                f"Source module {module_id} has invalid semanticStatusRecord"
            )
        semantic_record = json.loads(semantic_status_path.read_text(encoding="utf-8"))
        if (
            semantic_record.get("artifactType")
            != "baseballo-source-semantic-status"
            or semantic_record.get("contractVersion") != 1
            or semantic_record.get("moduleId") != module_id
            or semantic_record.get("operationalStatus") != module["operationalStatus"]
            or semantic_record.get("semanticStatus") != module["semanticStatus"]
        ):
            raise ValueError(
                f"Source module {module_id} semantic status record disagrees with catalog"
            )
        blockers = semantic_record.get("openBlockers")
        if not isinstance(blockers, list):
            raise ValueError(
                f"Source module {module_id} semantic status lacks openBlockers"
            )
        blocker_ids = [str(blocker.get("id", "")) for blocker in blockers]
        blocker_summaries = [str(blocker.get("summary", "")).strip() for blocker in blockers]
        if (
            any(not value for value in blocker_ids)
            or any(not value for value in blocker_summaries)
            or len(blocker_ids) != len(set(blocker_ids))
        ):
            raise ValueError(f"Source module {module_id} has invalid blocker IDs")
        if module["semanticStatus"] == "approved" and blockers:
            raise ValueError(
                f"Source module {module_id} cannot be approved with open blockers"
            )
        if module["semanticStatus"] == "approved" and (
            module["extensionPolicy"] != "approved-designs-only"
            or semantic_record.get("semanticAcceptance") != "granted-by-ontologist"
        ):
            raise ValueError(
                f"Approved source module {module_id} lacks an explicit ontologist gate"
            )
        if module["semanticStatus"] == "frozen-known-debt":
            if (
                not blockers
                or semantic_record.get("extensionAllowed") is not False
                or semantic_record.get("semanticAcceptance") != "not-granted"
            ):
                raise ValueError(
                    f"Frozen source module {module_id} must expose blockers, deny "
                    "extension, and disclaim semantic acceptance"
                )
            if module["extensionPolicy"] != "blocked-pending-ontologist-review":
                raise ValueError(
                    f"Frozen source module {module_id} must block semantic extension"
                )
        semantic_audit_path = (ROOT / str(semantic_record.get("audit", ""))).resolve()
        if (
            not semantic_audit_path.is_file()
            or not semantic_audit_path.is_relative_to(module_root)
        ):
            raise ValueError(
                f"Source module {module_id} semantic status references an invalid audit"
            )
        for value in module["rml"]:
            path = (ROOT / value).resolve()
            if not path.is_file() or not path.is_relative_to(
                (module_root / "mapping").resolve()
            ):
                raise ValueError(f"Source module {module_id} has invalid RML: {value}")
            if path in registered_rml:
                raise ValueError(f"RML is owned by multiple source modules: {value}")
            registered_rml.add(path)
        for value in module["shacl"]:
            path = (ROOT / value).resolve()
            if not path.is_file() or not path.is_relative_to(
                (module_root / "shacl").resolve()
            ):
                raise ValueError(f"Source module {module_id} has invalid SHACL: {value}")
            if path in registered_shacl:
                raise ValueError(f"SHACL is owned by multiple source modules: {value}")
            registered_shacl.add(path)
        for value in module["policies"]:
            path = (ROOT / value).resolve()
            if not path.is_file() or not path.is_relative_to(
                (module_root / "mapping").resolve()
            ):
                raise ValueError(f"Source module {module_id} has invalid policy: {value}")
            if path in registered_policies:
                raise ValueError(f"Policy is owned by multiple source modules: {value}")
            registered_policies.add(path)
        policy = module["disconnectPolicy"]
        if any(
            policy.get(field) is not True
            for field in (
                "stopsOnlyThisModule",
                "retainsPromotedAuthoritativeRdf",
                "unrelatedModulesRemainRunnable",
            )
        ):
            raise ValueError(f"Source module {module_id} is not detachable")
        for prefix in module["authoritativeGraphPrefixes"]:
            if not isinstance(prefix, str) or not prefix.startswith("https://"):
                raise ValueError(f"Source module {module_id} has invalid graph prefix")
            graph_prefixes.append((module_id, prefix))
        process_groups = module["nifiProcessGroups"]
        if (
            not isinstance(process_groups, list)
            or not process_groups
            or any(not isinstance(name, str) or not name.strip() for name in process_groups)
            or len(process_groups) != len(set(process_groups))
        ):
            raise ValueError(f"Source module {module_id} has invalid NiFi groups")
        for name in process_groups:
            owner = nifi_process_groups.get(name)
            if owner is not None:
                raise ValueError(
                    f"NiFi process group is owned by multiple modules: "
                    f"{name} ({owner}, {module_id})"
                )
            nifi_process_groups[name] = module_id
        nifi_contract = module.get("nifiContract")
        nifi_provisioner = module.get("nifiProvisioner")
        if (nifi_contract is None) != (nifi_provisioner is None):
            raise ValueError(
                f"Source module {module_id} must declare both its NiFi contract and provisioner"
            )
        for field, value in (
            ("nifiContract", nifi_contract),
            ("nifiProvisioner", nifi_provisioner),
        ):
            if value is None:
                continue
            path = (ROOT / str(value)).resolve()
            if not path.is_file() or not path.is_relative_to(module_root):
                raise ValueError(f"Source module {module_id} has invalid {field}")

    for index, (left_id, left) in enumerate(graph_prefixes):
        for right_id, right in graph_prefixes[index + 1 :]:
            if left.startswith(right) or right.startswith(left):
                raise ValueError(
                    f"Source graph prefixes overlap: {left_id}/{right_id}"
                )

    actual_rml = {
        path.resolve() for path in (ROOT / "sources").glob("*/mapping/*.rml.ttl")
    }
    actual_shacl = {
        path.resolve() for path in (ROOT / "sources").glob("*/shacl/*.ttl")
    }
    actual_policies = {
        path.resolve() for path in (ROOT / "sources").glob("*/mapping/*-policy.yaml")
    }
    if actual_rml != registered_rml:
        raise ValueError("Every active source RML must be owned exactly once in the catalog")
    if actual_shacl != registered_shacl:
        raise ValueError("Every active source SHACL must be owned exactly once in the catalog")
    if actual_policies != registered_policies:
        raise ValueError("Every source-field mapping policy must be owned in the catalog")
    stray_rml = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*.rml.ttl")
        if "archive" not in path.parts and path.resolve() not in actual_rml
    ]
    if stray_rml:
        raise ValueError(f"Executable RML exists outside a source module: {stray_rml}")
    proposal_dirs = sorted(
        path.relative_to(ROOT)
        for path in ROOT.rglob("proposals")
        if path.is_dir()
        and "archive" not in path.parts
        and any(child.is_file() for child in path.rglob("*"))
    )
    if proposal_dirs != [Path("proposals")]:
        raise ValueError(f"Exactly one active proposal directory is allowed: {proposal_dirs}")
    return len(modules), ids


def validate_query_source_scopes(source_ids: set[str]) -> int:
    catalog = json.loads(QUERY_SCOPE_CATALOG.read_text(encoding="utf-8"))
    source_catalog = json.loads(SOURCE_MODULE_CATALOG.read_text(encoding="utf-8"))
    source_graph_prefixes = {
        str(module["id"]): tuple(str(prefix) for prefix in module["authoritativeGraphPrefixes"])
        for module in source_catalog["modules"]
    }
    runtime_bound_queries: dict[Path, dict[str, str]] = {}
    binder_ids: set[str] = set()
    for binder in catalog.get("runtimeBinders", []):
        required = {
            "id",
            "source",
            "graphLayer",
            "graphPrefix",
            "graphVariable",
            "queryRegistry",
            "queryRegistryField",
            "runner",
            "regressionTests",
        }
        if not isinstance(binder, dict) or set(binder) != required:
            raise ValueError("SPARQL runtime binder contract is incomplete")
        binder_id = str(binder["id"])
        source_id = str(binder["source"])
        graph_prefix = str(binder["graphPrefix"])
        graph_variable = str(binder["graphVariable"])
        if not binder_id or binder_id in binder_ids:
            raise ValueError(f"SPARQL runtime binder ID is missing or duplicated: {binder_id}")
        binder_ids.add(binder_id)
        if (
            source_id not in source_ids
            or binder["graphLayer"] != "authoritative-rdf"
            or graph_prefix not in source_graph_prefixes.get(source_id, ())
            or graph_variable != "?graph"
            or binder["queryRegistryField"] != "routes[].authoritative"
        ):
            raise ValueError(f"SPARQL runtime binder scope is invalid: {binder_id}")
        registry_path = (ROOT / str(binder["queryRegistry"])).resolve()
        runner_path = (ROOT / str(binder["runner"])).resolve()
        tests = [(ROOT / str(path)).resolve() for path in binder["regressionTests"]]
        if not registry_path.is_file() or not runner_path.is_file() or any(
            not path.is_file() for path in tests
        ):
            raise ValueError(f"SPARQL runtime binder artifact is missing: {binder_id}")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if registry.get("artifactType") != "baseball-reviewed-query-routing":
            raise ValueError(f"SPARQL runtime binder registry is unsupported: {binder_id}")
        runner = runner_path.read_text(encoding="utf-8")
        if (
            f"$sourceGraphPrefix = '{graph_prefix}'" not in runner
            or 'VALUES ?graph { $values }' not in runner
            or "Get-ScopedQuery" not in runner
        ):
            raise ValueError(f"SPARQL runtime binder implementation has drifted: {binder_id}")
        for route in registry.get("routes", []):
            relative = str(route.get("authoritative", ""))
            query_path = (ROOT / relative).resolve()
            if not relative or not query_path.is_file() or query_path in runtime_bound_queries:
                raise ValueError(f"SPARQL runtime binder query registration is invalid: {binder_id}")
            runtime_bound_queries[query_path] = {
                "id": binder_id,
                "source": source_id,
                "graphVariable": graph_variable,
            }
    if (
        catalog.get("artifactType") != "baseballo-sparql-source-scope-catalog"
        or catalog.get("contractVersion") != 2
    ):
        raise ValueError("SPARQL source-scope catalog envelope is invalid")
    coverage: dict[Path, list[str]] = {}
    entries = catalog.get("entries", [])
    entry_ids: set[str] = set()
    allowed_layers = {"authoritative-rdf", "indexed-rdf", "analytical-sql"}
    for entry in entries:
        entry_id = str(entry.get("id", ""))
        if not entry_id or entry_id in entry_ids:
            raise ValueError(f"SPARQL source-scope entry id is missing or duplicated: {entry_id}")
        entry_ids.add(entry_id)
        category = entry.get("category")
        sources = entry.get("sources", [])
        if category not in {"single-source", "multi-source", "derived"}:
            raise ValueError(f"Invalid SPARQL source category: {entry_id}")
        if category == "single-source" and len(sources) != 1:
            raise ValueError(f"Single-source query entry must name one source: {entry_id}")
        if category == "multi-source" and len(sources) < 2:
            raise ValueError(f"Multi-source query entry must name two sources: {entry_id}")
        unknown = sorted(set(sources) - source_ids)
        if unknown:
            raise ValueError(f"SPARQL entry {entry_id} names unknown sources: {unknown}")
        reads = entry.get("readsGraphLayers")
        writes = entry.get("writesGraphLayers")
        patterns = entry.get("patterns")
        if not isinstance(reads, list) or not isinstance(writes, list) or not patterns:
            raise ValueError(f"SPARQL entry {entry_id} lacks read/write layers or patterns")
        if len(reads) != len(set(reads)) or len(writes) != len(set(writes)):
            raise ValueError(f"SPARQL entry {entry_id} repeats a graph layer")
        unknown_layers = sorted((set(reads) | set(writes)) - allowed_layers)
        if unknown_layers:
            raise ValueError(f"SPARQL entry {entry_id} has unknown graph layers: {unknown_layers}")
        if not reads and not writes:
            raise ValueError(f"SPARQL entry {entry_id} declares no graph interaction")
        for pattern in entry["patterns"]:
            matches = list(SPARQL_ROOT.glob(pattern))
            if not matches:
                raise ValueError(f"SPARQL scope pattern matches nothing: {pattern}")
            for path in matches:
                if path.is_file() and path.suffix == ".rq":
                    coverage.setdefault(path.resolve(), []).append(entry_id)
    query_files = {path.resolve() for path in SPARQL_ROOT.rglob("*.rq")}
    missing = sorted(path.relative_to(ROOT) for path in query_files - coverage.keys())
    duplicates = sorted(
        path.relative_to(ROOT) for path, owners in coverage.items() if len(owners) != 1
    )
    extra = sorted(path.relative_to(ROOT) for path in coverage.keys() - query_files)
    if missing or duplicates or extra:
        raise ValueError(
            "SPARQL source-scope coverage is not exact; "
            f"missing={missing}, duplicates={duplicates}, extra={extra}"
        )

    for path, binder in runtime_bound_queries.items():
        owners = coverage.get(path)
        if not owners or len(owners) != 1:
            raise ValueError(f"Runtime-bound SPARQL query lacks one scope owner: {path}")
        owner = next(entry for entry in entries if entry["id"] == owners[0])
        if owner["category"] != "single-source" or owner["sources"] != [binder["source"]]:
            raise ValueError(
                f"Runtime-bound SPARQL query differs from its source-scope owner: {path}"
            )

    entries_by_id = {str(entry["id"]): entry for entry in entries}
    for path, owners in coverage.items():
        entry = entries_by_id[owners[0]]
        query = path.read_text(encoding="utf-8")
        relative = path.relative_to(SPARQL_ROOT).as_posix()
        if entry["category"] == "single-source":
            source_id = str(entry["sources"][0])
            allowed_prefixes = source_graph_prefixes.get(source_id, ())
            if not allowed_prefixes:
                raise ValueError(
                    f"Single-source query owner has no authoritative graph prefix: {source_id}"
                )
            graph_variables = set(
                re.findall(r"\bGRAPH\s+(\?[A-Za-z_][A-Za-z0-9_]*)\s*\{", query, re.IGNORECASE)
            )
            fixed_graphs = re.findall(r"\bGRAPH\s+<([^>]+)>\s*\{", query, re.IGNORECASE)
            if not graph_variables and not fixed_graphs:
                raise ValueError(
                    f"Static single-source query does not select an explicit named graph: {relative}"
                )
            for graph_iri in fixed_graphs:
                if not any(graph_iri.startswith(prefix) for prefix in allowed_prefixes):
                    raise ValueError(
                        f"Single-source query reads a graph outside {source_id}: "
                        f"{relative}; graph={graph_iri}"
                    )
            for variable in graph_variables:
                guarded = any(
                    re.search(
                        rf"FILTER\s*\(\s*STRSTARTS\s*\(\s*STR\s*\(\s*{re.escape(variable)}\s*\)\s*,\s*"
                        rf"['\"]{re.escape(prefix)}['\"]\s*\)\s*\)",
                        query,
                        re.IGNORECASE,
                    )
                    for prefix in allowed_prefixes
                )
                runtime_binder = runtime_bound_queries.get(path.resolve())
                bound_at_runtime = (
                    runtime_binder is not None
                    and runtime_binder["source"] == source_id
                    and runtime_binder["graphVariable"] == variable
                )
                if not guarded and not bound_at_runtime:
                    raise ValueError(
                        f"Static single-source query has an unguarded named-graph variable: "
                        f"{relative}; variable={variable}; source={source_id}"
                    )
        detected_reads: set[str] = set()
        if re.search(r"\bGRAPH\s+\?indexGraph\b", query, re.IGNORECASE):
            detected_reads.add("indexed-rdf")
        if re.search(r"\bGRAPH\s+\?sourceGraph\b", query, re.IGNORECASE):
            detected_reads.add("authoritative-rdf")
        if re.search(r"\bGRAPH\s+\?graph\b", query, re.IGNORECASE):
            if relative.startswith("query-index/benchmarks/indexed/"):
                detected_reads.add("indexed-rdf")
            else:
                detected_reads.add("authoritative-rdf")
        detected_writes = (
            {"indexed-rdf"}
            if relative.startswith("query-index/components/")
            and re.search(r"\bCONSTRUCT\b", query, re.IGNORECASE)
            else set()
        )
        if relative.startswith("serving/"):
            detected_writes.add("analytical-sql")
        if set(entry["readsGraphLayers"]) != detected_reads:
            raise ValueError(
                f"SPARQL read-layer declaration differs from query text: {relative}; "
                f"declared={entry['readsGraphLayers']}, detected={sorted(detected_reads)}"
            )
        if set(entry["writesGraphLayers"]) != detected_writes:
            raise ValueError(
                f"SPARQL write-layer declaration differs from query role: {relative}; "
                f"declared={entry['writesGraphLayers']}, detected={sorted(detected_writes)}"
            )
    return len(query_files)


def validate_rml_information_boundary() -> int:
    graph = Graph().parse(ACTIVE_MAPPING, format="turtle")
    rr = Namespace("http://www.w3.org/ns/r2rml#")
    rml = Namespace("http://semweb.mmlab.be/ns/rml#")
    cco = Namespace("https://www.commoncoreontologies.org/")
    value_predicate = cco.ont00001765
    semantic_links = {
        cco.ont00001808,  # is about
        cco.ont00001916,  # designates
        cco.ont00001966,  # is a measurement of
    }
    checked = 0
    failures: list[str] = []
    for triples_map in graph.subjects(RDF.type, rr.TriplesMap):
        predicates: set[URIRef] = set()
        typed_value = False
        for predicate_object_map in graph.objects(triples_map, rr.predicateObjectMap):
            current_predicates = set(graph.objects(predicate_object_map, rr.predicate))
            predicates.update(current_predicates)
            if value_predicate not in current_predicates:
                continue
            for object_map in graph.objects(predicate_object_map, rr.objectMap):
                if any(graph.objects(object_map, rr.datatype)) and any(
                    graph.objects(object_map, rml.reference)
                ):
                    typed_value = True
        if typed_value:
            checked += 1
            if predicates.isdisjoint(semantic_links):
                failures.append(str(triples_map))
    if failures:
        raise ValueError(
            "Typed CCO value ICE maps require explicit aboutness, designation, or measurement: "
            + ", ".join(failures)
        )
    return checked


def validate_markdown() -> tuple[int, int]:
    markdown_files = list(ROOT.rglob("*.md")) + [
        GIT_ROOT / "README.md",
        GIT_ROOT / "AGENTS.md",
    ]
    mermaid_blocks = 0

    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if r"\`\`\`mermaid" in text:
            raise ValueError(
                f"Escaped Mermaid fence cannot render in a browser: {path.relative_to(ROOT)}"
            )
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip("<>")
            if target.startswith(REMOTE_PREFIXES):
                continue
            relative_target = unquote(target.split("#", 1)[0])
            if relative_target and not (path.parent / relative_target).resolve().exists():
                raise ValueError(
                    f"Broken Markdown link in {path.relative_to(ROOT)}: {target}"
                )

        fence_language: str | None = None
        fence_body: list[str] = []
        for line in text.splitlines():
            if line.startswith("```"):
                if fence_language is None:
                    fence_language = line[3:].strip()
                    fence_body = []
                else:
                    if fence_language == "mermaid":
                        mermaid_blocks += 1
                        first = next((item.strip() for item in fence_body if item.strip()), "")
                        if not first.startswith(MERMAID_DIAGRAM_TYPES):
                            raise ValueError(
                                f"Unknown Mermaid diagram start in {path.relative_to(ROOT)}: "
                                f"{first!r}"
                            )
                    fence_language = None
                    fence_body = []
            elif fence_language is not None:
                fence_body.append(line)
        if fence_language is not None:
            raise ValueError(f"Unclosed code fence in {path.relative_to(ROOT)}")

    return len(markdown_files), mermaid_blocks


def validate_active_mapping() -> None:
    for sample in MAPPING_SAMPLES:
        subprocess.run(
            [sys.executable, str(MAPPING_VALIDATOR), str(sample)],
            cwd=MAPPING_VALIDATOR.parent,
            check=True,
        )


def validate_ontology_overlay() -> None:
    subprocess.run(
        [sys.executable, str(ONTOLOGY_OVERLAY_VALIDATOR)],
        cwd=ROOT,
        check=True,
    )


def validate_rml_mermaid() -> None:
    subprocess.run(
        [sys.executable, str(RML_MERMAID_GENERATOR), "--check"],
        cwd=ROOT,
        check=True,
    )


def validate_selective_reasoning() -> None:
    subprocess.run(
        [sys.executable, str(SELECTIVE_REASONING_TEST)],
        cwd=ROOT,
        check=True,
    )


def validate_reasoning_evidence() -> int:
    evidence = json.loads(REASONING_EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("artifactType") != "baseball-selective-reasoning-proof-baseline":
        raise ValueError("Unknown selective reasoning proof baseline")
    if evidence.get("backend") != "z3-solver" or evidence.get("backendVersion") != "5.0.0":
        raise ValueError("Selective reasoning proof backend is stale")
    if evidence.get("backendScriptSha256") != sha256_file(SELECTIVE_PROVER):
        raise ValueError("Selective reasoning proof baseline has a stale backend hash")
    ontology_hashes = {
        "ontology/BaseballO.ttl": sha256_file(ROOT / "ontology" / "BaseballO.ttl"),
        "ontology/CommonCoreOntologiesMerged.ttl": sha256_file(
            ROOT / "ontology" / "CommonCoreOntologiesMerged.ttl"
        ),
    }
    bfo_hash = sha256_file(ROOT / "reasoning" / "bfo-clif-manifest.json")
    reasoner_hash = sha256_file(SELECTIVE_REASONER)
    profiles = evidence.get("profiles", [])
    if len(profiles) != 3:
        raise ValueError("Selective reasoning baseline must cover three profiles")
    total_obligations = total_proved = 0
    for result in profiles:
        profile_id = str(result["profile"])
        profile_path = ROOT / "reasoning" / "profiles" / f"{profile_id}.json"
        profile_hash = sha256_file(profile_path)
        if result.get("profileSha256") != profile_hash:
            raise ValueError(f"Selective reasoning profile baseline is stale: {profile_id}")
        ruleset = {
            "profileSha256": profile_hash,
            "bfoClifManifestSha256": bfo_hash,
            "ontologySha256": ontology_hashes,
            "reasonerSha256": reasoner_hash,
        }
        ruleset_hash = hashlib.sha256(
            json.dumps(ruleset, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if result.get("rulesetSha256") != ruleset_hash:
            raise ValueError(f"Selective reasoning ruleset baseline is stale: {profile_id}")
        if not str(result.get("reasoningGraph", "")).endswith(f"/rules/{ruleset_hash[:16]}"):
            raise ValueError(f"Selective reasoning graph fingerprint is invalid: {profile_id}")
        obligations = int(result.get("obligationCount", -1))
        proved = int(result.get("provedCount", -1))
        if obligations <= 0 or proved != obligations or result.get("consistency") != "sat":
            raise ValueError(f"Selective reasoning proof is incomplete: {profile_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("proofReportSha256", ""))):
            raise ValueError(f"Selective reasoning proof hash is invalid: {profile_id}")
        total_obligations += obligations
        total_proved += proved
    if int(evidence.get("totalObligations", -1)) != total_obligations:
        raise ValueError("Selective reasoning obligation total is inconsistent")
    if int(evidence.get("totalProved", -1)) != total_proved:
        raise ValueError("Selective reasoning proof total is inconsistent")
    if not evidence.get("allProfilesConsistent"):
        raise ValueError("Selective reasoning baseline reports an inconsistent profile")
    return total_proved


def validate_reasoning_review_evidence() -> tuple[int, int]:
    contract = json.loads(REASONING_REVIEW_SAMPLES.read_text(encoding="utf-8"))
    evidence = json.loads(REASONING_REVIEW_EVIDENCE.read_text(encoding="utf-8"))
    if contract.get("artifactType") != "baseball-selective-reasoning-reviewed-samples":
        raise ValueError("Unknown reviewed reasoning sample contract")
    samples = contract.get("samples", [])
    if len(samples) != 2 or {sample.get("complexity") for sample in samples} != {"simple", "complicated"}:
        raise ValueError("Reviewed reasoning evidence must compare simple and complicated samples")
    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    plays = {int(play["about"]["atBatIndex"]): play for play in raw["liveData"]["plays"]["allPlays"]}
    for sample in samples:
        play = plays[int(sample["plateAppearanceIndex"])]
        observed = {
            "eventType": str(play["result"]["eventType"]),
            "playEventCount": len(play.get("playEvents", [])),
            "pitchCount": sum(1 for event in play.get("playEvents", []) if event.get("isPitch") is True),
            "runnerRecordCount": len(play.get("runners", [])),
            "description": str(play["result"]["description"]),
        }
        if any(sample.get(key) != value for key, value in observed.items()):
            raise ValueError(f"Reviewed reasoning sample is stale: {sample.get('id')}")
    if evidence.get("artifactType") != "baseball-selective-reasoning-reviewed-sample-evidence":
        raise ValueError("Unknown reviewed reasoning comparison evidence")
    if evidence.get("sourceJsonSha256") != sha256_file(SAMPLE):
        raise ValueError("Reviewed reasoning comparison has a stale source JSON hash")
    if evidence.get("samplesContractSha256") != sha256_file(REASONING_REVIEW_SAMPLES):
        raise ValueError("Reviewed reasoning comparison has a stale sample-contract hash")
    fixture_baseline = json.loads(REASONING_EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("sourceRdfSha256") != fixture_baseline.get("sourceRdfSha256"):
        raise ValueError("Reviewed reasoning comparison does not use the accepted fixture RDF")
    results = evidence.get("results", [])
    expected = {(sample["id"], profile) for sample in samples for profile in ("event-order", "event-structure", "participation")}
    observed_keys = {(result.get("sample"), result.get("profile")) for result in results}
    if len(results) != 6 or observed_keys != expected:
        raise ValueError("Reviewed reasoning comparison must cover both samples with all three profiles")
    baseline_profiles = {item["profile"]: item for item in fixture_baseline["profiles"]}
    total_proved = 0
    for result in results:
        profile_id = str(result["profile"])
        profile_path = ROOT / "reasoning" / "profiles" / f"{profile_id}.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if result.get("profileSha256") != sha256_file(profile_path):
            raise ValueError(f"Reviewed reasoning profile hash is stale: {profile_id}")
        if result.get("rulesetSha256") != baseline_profiles[profile_id]["rulesetSha256"]:
            raise ValueError(f"Reviewed reasoning ruleset hash is stale: {profile_id}")
        counts = result.get("counts", {})
        budgets = profile["budgets"]
        if int(counts.get("selectedNodes", -1)) > int(budgets["maxNodes"]):
            raise ValueError(f"Reviewed reasoning node budget exceeded: {profile_id}")
        if int(counts.get("assertedSliceTriples", -1)) > int(budgets["maxSourceTriples"]):
            raise ValueError(f"Reviewed reasoning source budget exceeded: {profile_id}")
        if int(counts.get("inferredTriples", -1)) > int(budgets["maxInferredTriples"]):
            raise ValueError(f"Reviewed reasoning inference budget exceeded: {profile_id}")
        comparison = result.get("queryComparison", {})
        asserted_rows = int(comparison.get("asserted", {}).get("rowCount", -1))
        closure_rows = int(comparison.get("closure", {}).get("rowCount", -1))
        if int(comparison.get("newRows", -1)) != closure_rows - asserted_rows:
            raise ValueError(f"Reviewed reasoning query comparison is inconsistent: {profile_id}")
        for layer in ("asserted", "closure"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(comparison.get(layer, {}).get("rowSetSha256", ""))):
                raise ValueError(f"Reviewed reasoning query hash is invalid: {profile_id}/{layer}")
        proof = result.get("proof", {})
        obligations = int(proof.get("obligationCount", -1))
        proved = int(proof.get("provedCount", -1))
        if obligations < 0 or proved != obligations or proof.get("consistency") != "sat" or proof.get("allObligationsProved") is not True:
            raise ValueError(f"Reviewed reasoning proof is incomplete: {profile_id}")
        shacl = result.get("shaclValidation", {})
        expected_shapes = {
            "explicitGraphBeforeReasoning": ("authoritative", AUTHORITATIVE_SHACL),
            "inferredGraphBeforeLoad": ("reasoning-output", SHACL_ROOT / "reasoning-output.ttl"),
        }
        for boundary, (expected_profile, shape_path) in expected_shapes.items():
            validation = shacl.get(boundary, {})
            if (
                validation.get("profile") != expected_profile
                or validation.get("conforms") is not True
                or validation.get("shapeSha256") != sha256_file(shape_path)
            ):
                raise ValueError(f"Reviewed reasoning SHACL boundary is stale: {profile_id}/{boundary}")
        total_proved += proved
    if evidence.get("runCount") != 6 or evidence.get("allProfilesConsistent") is not True or evidence.get("allObligationsProved") is not True:
        raise ValueError("Reviewed reasoning comparison summary is inconsistent")
    return len(results), total_proved


def validate_query_index_algebra_artifacts() -> int:
    pair_path = SPARQL_ROOT / "query-index" / "benchmarks" / "benchmark-pairs.json"
    summary_path = ROOT / "benchmarks" / "query-index" / "algebra" / "optimized-algebra-summary.json"
    algebra_root = summary_path.parent
    pairs = json.loads(pair_path.read_text(encoding="utf-8"))["pairs"]
    expected_names = {str(pair["name"]) for pair in pairs}
    expected_plans = {
        f"{name}-{layer}-opt.txt"
        for name in expected_names
        for layer in ("authoritative", "indexed")
    }
    actual_plans = {path.name for path in algebra_root.glob("*-opt.txt")}
    if actual_plans != expected_plans:
        raise ValueError(
            "Optimized algebra plan set differs from the benchmark pairs: "
            f"expected {len(expected_plans)}, found {len(actual_plans)}"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_names = {str(result["name"]) for result in summary.get("results", [])}
    if summary_names != expected_names:
        raise ValueError("Optimized algebra summary does not cover every benchmark pair")
    return len(actual_plans)


def validate_web_app() -> None:
    mojibake_markers = ("\ufffd", "\u00e2\u20ac", "\u00c2\u00b7", "\u00ef\u00bb\u00bf")
    for path in WEB_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".js", ".mjs", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in mojibake_markers):
            raise ValueError(
                f"Web asset contains replacement or mojibake text: {path.relative_to(ROOT)}"
            )
    subprocess.run(
        ["node", "--check", "server.mjs"],
        cwd=WEB_ROOT,
        check=True,
    )
    subprocess.run(
        ["node", "--check", "app.js"],
        cwd=WEB_ROOT,
        check=True,
    )
    subprocess.run(
        ["node", "--test", "tests/analytics-query-builder.test.mjs"],
        cwd=WEB_ROOT,
        check=True,
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text_file(path: Path) -> str:
    """Hash repository text independently of checkout newline conventions."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def canonical_query_set_sha256(paths: list[Path]) -> str:
    lines = [
        f"{path.relative_to(ROOT).as_posix()}={sha256_text_file(path)}"
        for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def validate_query_audit_evidence_register() -> dict[str, dict[str, object]]:
    register = json.loads(QUERY_AUDIT_EVIDENCE_REGISTER.read_text(encoding="utf-8"))
    if (
        register.get("artifactType") != "baseball-query-audit-evidence-register"
        or register.get("contractVersion") != 1
    ):
        raise ValueError("Query-audit evidence register envelope is invalid")
    captures = register.get("captures", [])
    by_id = {str(capture.get("id", "")): capture for capture in captures}
    expected = {
        "canned-2026-08-03": CANNED_AUDIT_BASELINE,
        "advanced-2026-08-03": ADVANCED_AUDIT_BASELINE,
    }
    if len(captures) != len(by_id) or set(by_id) != set(expected):
        raise ValueError("Query-audit evidence register does not cover the exact captures")
    for capture_id, artifact in expected.items():
        capture = by_id[capture_id]
        summary = ROOT / str(capture.get("summary", ""))
        if (ROOT / str(capture.get("artifact", ""))).resolve() != artifact.resolve():
            raise ValueError(f"Query-audit register artifact differs for {capture_id}")
        if capture.get("status") != "historical":
            raise ValueError(f"Query-audit capture is not historical: {capture_id}")
        if not summary.is_file():
            raise ValueError(f"Query-audit summary is missing: {capture_id}")
        if sha256_text_file(artifact) != capture.get("artifactTextSha256"):
            raise ValueError(f"Historical query-audit capture changed: {capture_id}")
        if sha256_text_file(summary) != capture.get("summaryTextSha256"):
            raise ValueError(f"Historical query-audit summary changed: {capture_id}")
        report = json.loads(artifact.read_text(encoding="utf-8"))
        if report.get("generatedAtUtc") != capture.get("capturedAtUtc"):
            raise ValueError(f"Query-audit capture timestamp differs: {capture_id}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(capture.get("capturedAtCommit", ""))):
            raise ValueError(f"Query-audit capture commit is invalid: {capture_id}")
        if (
            capture.get("capturedQueryHashAlgorithm") != "raw-bytes-v1"
            or capture.get("compatibleQueryHashAlgorithm") != "canonical-text-v1"
        ):
            raise ValueError(f"Query-audit hash algorithms are invalid: {capture_id}")
    return by_id


def query_index_contract_sha256() -> str:
    """Return the deprecated exact implementation/build fingerprint.

    Historical benchmark artifacts and not-yet-migrated runtime consumers still
    carry this value. It is provenance, not semantic compatibility.
    """
    contract_files = list(
        (SPARQL_ROOT / "query-index" / "components").glob("*.rq")
    ) + [
        ROOT / "scripts" / "infra" / "canonical-text.ps1",
        ROOT / "scripts" / "pipeline" / "compile-query-index.py",
        ROOT / "scripts" / "pipeline" / "build-query-index.ps1",
        ROOT / "scripts" / "pipeline" / "query-index-common.ps1",
        ROOT / "scripts" / "pipeline" / "test-query-index.ps1",
    ]
    lines = [
        f"{path.relative_to(ROOT).as_posix()}={sha256_text_file(path)}"
        for path in sorted(contract_files, key=lambda item: str(item.resolve()).lower())
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def validate_query_index_semantic_contract() -> tuple[dict[str, object], str]:
    contract = json.loads(QUERY_INDEX_SEMANTIC_CONTRACT.read_text(encoding="utf-8"))
    if (
        contract.get("artifactType") != "baseball-query-index-semantic-contract"
        or contract.get("contractVersion") != 1
        or contract.get("semanticContractId") != "baseball-query-index-v2"
        or contract.get("indexMetadataContractVersion") != "1"
        or contract.get("hashAlgorithm") != "canonical-text-v1"
    ):
        raise ValueError("Query-index semantic contract envelope is invalid")

    expected_graph_contract = {
        "authoritativeGraphPrefix": "https://w3id.org/baseball/graph/game/",
        "indexGraphPrefix": "https://w3id.org/baseball/graph/query-index/game/",
        "gameIriPrefix": "https://baseballontology.org/data/game/",
        "indexResourcePrefix": "https://w3id.org/baseball/query-index-build/game/",
        "metadataClassIri": "https://w3id.org/baseball/query-index/QueryIndex",
    }
    if contract.get("graphContract") != expected_graph_contract:
        raise ValueError("Query-index semantic graph contract is invalid")

    semantic_inputs = contract.get("semanticInputs")
    if not isinstance(semantic_inputs, dict):
        raise ValueError("Query-index semantic inputs are missing")
    components = semantic_inputs.get("constructComponents")
    if not isinstance(components, list) or not components:
        raise ValueError("Query-index semantic component inventory is empty")
    declared: dict[str, str] = {}
    for component in components:
        if not isinstance(component, dict) or set(component) != {"path", "textSha256"}:
            raise ValueError("Query-index semantic component entry is invalid")
        relative = str(component["path"])
        digest = str(component["textSha256"])
        if relative in declared or not re.fullmatch(r"sparql/query-index/components/[^/]+[.]rq", relative):
            raise ValueError(f"Query-index semantic component path is invalid: {relative}")
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f"Query-index semantic component is missing: {relative}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or sha256_text_file(path) != digest:
            raise ValueError(f"Query-index semantic component changed: {relative}")
        declared[relative] = digest
    expected_component_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (SPARQL_ROOT / "query-index" / "components").glob("*.rq")
    }
    if set(declared) != expected_component_paths:
        raise ValueError("Query-index semantic contract does not cover the exact component set")

    shape = semantic_inputs.get("shaclProfile")
    expected_shape_path = "shacl/query-index.ttl"
    if (
        not isinstance(shape, dict)
        or set(shape) != {"profile", "path", "textSha256"}
        or shape.get("profile") != "query-index"
        or shape.get("path") != expected_shape_path
        or not re.fullmatch(r"[0-9a-f]{64}", str(shape.get("textSha256", "")))
        or sha256_text_file(ROOT / expected_shape_path) != shape.get("textSha256")
    ):
        raise ValueError("Query-index semantic SHACL profile is invalid or stale")

    idx = "https://w3id.org/baseball/query-index/"
    expected_grains = {
        "GameFact": ("10-game-dimensions.rq", {"venue", "gameStart", "derivedFrom"}),
        "PlateAppearanceFact": ("15-plate-appearances.rq", {"game", "agent", "derivedFrom"}),
        "PlateAppearanceResultFact": (
            "20-plate-appearance-results.rq",
            {"plateAppearance", "game", "agent", "outcomeClass", "sourceEventType", "derivedFrom"},
        ),
        "HitFact": ("30-hits.rq", {"agent", "game", "venue", "hitType", "plateAppearance", "derivedFrom"}),
        "PitchFact": ("40-pitches.rq", {"agent", "game", "venue", "plateAppearance", "derivedFrom"}),
        "PitchCallFact": ("50-pitch-calls.rq", {"pitch", "agent", "game", "callType", "derivedFrom"}),
        "BattingActFact": (
            "60-batting-acts.rq",
            {"agent", "game", "plateAppearance", "battingActType", "derivedFrom"},
        ),
        "ContactFact": (
            "61-contacts.rq",
            {"agent", "game", "venue", "plateAppearance", "battedBall", "derivedFrom"},
        ),
        "RunnerResolutionFact": (
            "70-runner-resolutions.rq",
            {"agent", "game", "resolutionClass", "sourceEventType", "derivedFrom"},
        ),
        "StolenBaseFact": ("71-stolen-bases.rq", {"agent", "game", "derivedFrom"}),
        "AssignmentFact": ("80-game-assignments.rq", {"game", "assignee", "assignmentType", "derivedFrom"}),
    }
    grains = contract.get("factGrains")
    if not isinstance(grains, list) or len(grains) != len(expected_grains):
        raise ValueError("Query-index semantic fact-grain inventory is incomplete")
    grain_by_name = {
        str(grain.get("name", "")): grain
        for grain in grains
        if isinstance(grain, dict)
    }
    if set(grain_by_name) != set(expected_grains) or len(grain_by_name) != len(grains):
        raise ValueError("Query-index semantic fact-grain names are missing or duplicated")
    for name, (component_name, properties) in expected_grains.items():
        grain = grain_by_name[name]
        if set(grain) != {"name", "classIri", "component", "requiredProperties"}:
            raise ValueError(f"Query-index semantic fact grain has an invalid envelope: {name}")
        if grain.get("classIri") != f"{idx}{name}":
            raise ValueError(f"Query-index semantic fact class is invalid: {name}")
        if grain.get("component") != f"sparql/query-index/components/{component_name}":
            raise ValueError(f"Query-index semantic fact component is invalid: {name}")
        values = grain.get("requiredProperties")
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise ValueError(f"Query-index semantic fact properties are duplicated: {name}")
        if set(values) != {f"{idx}{value}" for value in properties}:
            raise ValueError(f"Query-index semantic fact properties are invalid: {name}")

    consumer_grains = contract.get("consumerGrains")
    expected_consumer = {
        "id": "game-team-season-v1",
        "factGrains": ["GameFact", "AssignmentFact"],
        "assignmentTypes": [f"{idx}HomeTeam", f"{idx}AwayTeam"],
        "scope": "per-indexed-game",
        "exactAssignmentCountPerType": 1,
        "distinctAssignees": True,
        "assigneeIriPattern": r"^https://baseballontology[.]org/data/team/[0-9]+$",
        "sourceAssigneeClassIri": "https://baseballontology.org/BaseballTeam",
    }
    if not isinstance(consumer_grains, list) or len(consumer_grains) != 1:
        raise ValueError("Query-index Teams consumer grain is missing")
    consumer = consumer_grains[0]
    if (
        not isinstance(consumer, dict)
        or set(consumer) != set(expected_consumer) | {"description"}
        or any(consumer.get(key) != value for key, value in expected_consumer.items())
    ):
        raise ValueError("Query-index Teams consumer grain is invalid")
    if not str(consumer.get("description", "")).strip():
        raise ValueError("Query-index Teams consumer grain lacks a description")

    serialized_inputs = json.dumps(semantic_inputs, sort_keys=True)
    if any(suffix in serialized_inputs for suffix in (".py", ".ps1")):
        raise ValueError("Query-index semantic admission includes implementation scripts")
    return contract, sha256_text_file(QUERY_INDEX_SEMANTIC_CONTRACT)


def query_index_pairs() -> list[dict[str, object]]:
    path = SPARQL_ROOT / "query-index" / "benchmarks" / "benchmark-pairs.json"
    return json.loads(path.read_text(encoding="utf-8"))["pairs"]


def validate_query_index_evidence_register() -> dict[str, dict[str, object]]:
    register = json.loads(QUERY_INDEX_EVIDENCE_REGISTER.read_text(encoding="utf-8"))
    if (
        register.get("artifactType") != "baseball-query-index-evidence-register"
        or register.get("contractVersion") != 1
    ):
        raise ValueError("Query-index evidence register envelope is invalid")
    captures = register.get("captures", [])
    expected_artifacts = {
        "benchmarks/query-index/fixture-566279-baseline.json",
        "benchmarks/query-index/corpus-2026-08-03-baseline.json",
        "benchmarks/query-index/tdb2-execution/tdb2-execution-summary.json",
    }
    by_artifact = {str(item.get("artifact")): item for item in captures}
    if len(captures) != len(by_artifact) or set(by_artifact) != expected_artifacts:
        raise ValueError("Query-index evidence register does not cover the exact captures")
    ids = [str(item.get("id", "")) for item in captures]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("Query-index evidence capture ids are missing or duplicated")
    current_contract = query_index_contract_sha256()
    for relative, capture in by_artifact.items():
        artifact = ROOT / relative
        summary = ROOT / str(capture.get("summary", ""))
        if not artifact.is_file() or not summary.is_file():
            raise ValueError(f"Registered query-index capture is incomplete: {relative}")
        if capture.get("status") not in {"historical", "current"}:
            raise ValueError(f"Query-index capture has an invalid status: {relative}")
        if not re.fullmatch(r"[0-9a-f]{40}", str(capture.get("capturedAtCommit", ""))):
            raise ValueError(f"Query-index capture commit is invalid: {relative}")
        if sha256_text_file(artifact) != capture.get("artifactTextSha256"):
            raise ValueError(f"Registered query-index capture bytes changed: {relative}")
        report = json.loads(artifact.read_text(encoding="utf-8"))
        contract_hash = str(capture.get("queryIndexContractSha256", ""))
        if report.get("generatedAtUtc") != capture.get("capturedAtUtc"):
            raise ValueError(f"Query-index capture timestamp differs from its register: {relative}")
        if report.get("queryIndexContractSha256") != contract_hash:
            raise ValueError(f"Query-index capture contract differs from its register: {relative}")
        if contract_hash not in summary.read_text(encoding="utf-8"):
            raise ValueError(f"Query-index capture summary has a different contract: {relative}")
        if capture.get("status") == "current" and contract_hash != current_contract:
            raise ValueError(f"Current query-index capture is stale: {relative}")
    return by_artifact


def validate_query_index_benchmarks() -> int:
    captures = validate_query_index_evidence_register()
    fixture = json.loads(
        (QUERY_INDEX_BENCHMARK_ROOT / "fixture-566279-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    if fixture.get("artifactType") != "baseball-query-index-exploratory-benchmark":
        raise ValueError("Single-fixture query-index benchmark has an unknown artifact type")

    report = json.loads(QUERY_INDEX_CORPUS_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-query-index-corpus-benchmark":
        raise ValueError("Corpus query-index benchmark has an unknown artifact type")
    registered = captures["benchmarks/query-index/corpus-2026-08-03-baseline.json"]
    if report.get("queryIndexContractSha256") != registered.get("queryIndexContractSha256"):
        raise ValueError("Corpus query-index benchmark differs from its capture register")
    if int(report.get("queryIndexTripleCount", -1)) != 52992:
        raise ValueError("Corpus benchmark query-index triple count is unexpected")

    results = report.get("results", [])
    names = [str(item.get("name", "")) for item in results]
    if len(results) != 19 or any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("Corpus benchmark query names are missing or duplicated")
    iterations = int(report.get("iterationsPerQueryAndLayer", -1))
    if iterations != 20:
        raise ValueError("Corpus benchmark must retain 20 samples per query and layer")
    for result in results:
        for layer, pair_key, report_key in (
            ("authoritative", "authoritative", "authoritativeQuery"),
            ("indexed", "indexed", "indexedQuery"),
        ):
            relative_path = str(result.get(report_key, ""))
            if not relative_path or not re.fullmatch(
                r"[0-9a-f]{64}", str(result.get(f"{layer}QuerySha256", ""))
            ):
                raise ValueError(f"Corpus benchmark query identity is invalid for {result['name']}")
            samples = result.get(layer, {}).get("samplesMilliseconds", [])
            if len(samples) != iterations or any(float(value) < 0 for value in samples):
                raise ValueError(f"Invalid corpus timing samples for {result['name']} {layer}")
        if int(result.get("resultRows", -1)) < 0:
            raise ValueError(f"Invalid corpus result count for {result['name']}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("rowSetSha256", ""))):
            raise ValueError(f"Invalid corpus row-set hash for {result['name']}")
    return len(results)


def validate_reviewed_query_routing() -> int:
    routing = json.loads(REVIEWED_QUERY_ROUTING.read_text(encoding="utf-8"))
    if (
        routing.get("artifactType") != "baseball-reviewed-query-routing"
        or routing.get("routingVersion") != 2
    ):
        raise ValueError("Reviewed query routing has an unknown artifact type")
    evidence_path = ROOT / str(routing.get("evidence", ""))
    if evidence_path.resolve() != QUERY_INDEX_CORPUS_BASELINE.resolve():
        raise ValueError("Reviewed query routing must cite the corpus benchmark")
    if routing.get("evidenceTextSha256") != sha256_text_file(evidence_path):
        raise ValueError("Reviewed query routing cites changed benchmark evidence")

    pairs = query_index_pairs()
    pair_by_name = {str(pair["name"]): pair for pair in pairs}
    benchmark = json.loads(QUERY_INDEX_CORPUS_BASELINE.read_text(encoding="utf-8"))
    benchmark_by_name = {
        str(result["name"]): result for result in benchmark.get("results", [])
    }
    semantic_contract, semantic_contract_sha256 = (
        validate_query_index_semantic_contract()
    )
    semantic_admission = routing.get("semanticAdmission")
    if (
        not isinstance(semantic_admission, dict)
        or set(semantic_admission)
        != {"contractId", "contract", "contractTextSha256", "basis"}
        or semantic_admission.get("contractId")
        != semantic_contract.get("semanticContractId")
        or semantic_admission.get("contract")
        != QUERY_INDEX_SEMANTIC_CONTRACT.relative_to(ROOT).as_posix()
        or semantic_admission.get("contractTextSha256")
        != semantic_contract_sha256
        or not str(semantic_admission.get("basis", "")).strip()
    ):
        raise ValueError("Reviewed query routing does not admit the exact semantic contract")

    forbidden_legacy_admission_fields = {
        "legacyFingerprintFieldSemantics",
        "measuredContractSha256",
        "admittedContractSha256",
        "historicallyCompatibleContractSha256",
        "compatibilityReview",
    }
    leaked_fields = forbidden_legacy_admission_fields.intersection(routing)
    if leaked_fields:
        raise ValueError(
            "Reviewed query routing retains implementation fingerprints as semantic admission: "
            + ", ".join(sorted(leaked_fields))
        )
    compatibility_bridge = routing.get("compatibleSemanticContractBridge")
    expected_compatible_contracts = [
        {
            "contractId": "baseball-query-index-v1",
            "contractTextSha256": "6955ed9a27854f8e25dded72d13ab845b82d532d78578c6dc7ea8ac77a5abab4",
        }
    ]
    expected_compatibility_keys = {
        "bridgeVersion",
        "status",
        "compatibleContracts",
        "compatibilityReview",
        "requiredOutputValidation",
    }
    if (
        not isinstance(compatibility_bridge, dict)
        or set(compatibility_bridge) != expected_compatibility_keys
        or compatibility_bridge.get("bridgeVersion") != 1
        or compatibility_bridge.get("status") != "reviewed-backward-compatible"
        or compatibility_bridge.get("compatibleContracts")
        != expected_compatible_contracts
        or not str(compatibility_bridge.get("compatibilityReview", "")).strip()
        or not str(compatibility_bridge.get("requiredOutputValidation", "")).strip()
    ):
        raise ValueError(
            "Reviewed query routing has no exact backward-compatible semantic-contract bridge"
        )
    legacy_bridge = routing.get("legacyManifestBridge")
    expected_legacy_hashes = [
        "a573269199d575f513a6481609dd101fd26da113ea8c3daef0b7daae35543629",
        "b966f574263bf0be0e7925e99d4b49175a7056d469b664b7fc5044bda86a16ea",
        "c6b89ed3afd2518c2b8bd71e7f191421a51e7bd33eb901646a8b921bedf00b5c",
        "8498a513f7468faa65b3f9c68bf196ca8fd1ecf62785b90d7e05decaf7ee497c",
        "70457857e549b78c5dfb8fb92ceb7b2670fd6fa635bc1da5db4111fbd423fcc5",
    ]
    expected_bridge_keys = {
        "bridgeVersion",
        "status",
        "appliesOnlyWhenSemanticFieldsAbsent",
        "legacyImplementationField",
        "semanticContractId",
        "semanticContractSha256",
        "fixedImplementationSha256",
        "compatibilityReview",
        "requiredOutputValidation",
    }
    if (
        not isinstance(legacy_bridge, dict)
        or set(legacy_bridge) != expected_bridge_keys
        or legacy_bridge.get("bridgeVersion") != 1
        or legacy_bridge.get("status") != "reviewed-fixed"
        or legacy_bridge.get("appliesOnlyWhenSemanticFieldsAbsent") is not True
        or legacy_bridge.get("legacyImplementationField") != "contractSha256"
        or legacy_bridge.get("semanticContractId")
        != semantic_contract.get("semanticContractId")
        or legacy_bridge.get("semanticContractSha256") != semantic_contract_sha256
        or legacy_bridge.get("fixedImplementationSha256") != expected_legacy_hashes
        or not str(legacy_bridge.get("compatibilityReview", "")).strip()
        or not str(legacy_bridge.get("requiredOutputValidation", "")).strip()
    ):
        raise ValueError("Reviewed query routing has no exact fixed legacy-manifest bridge")
    routes = routing.get("routes", [])
    route_names = {str(route.get("name")) for route in routes}
    if len(routes) != len(pairs) or route_names != set(pair_by_name):
        raise ValueError("Reviewed query routing must cover the exact benchmark pair set")

    expected_indexed = {
        "hits-by-season",
        "hits-by-player-and-venue",
        "outcomes-by-player",
        "outcomes-by-season",
        "plate-appearances-by-player-and-season",
        "three-true-outcomes-by-player",
        "extra-base-hits-by-player",
        "home-runs-by-player-and-venue",
        "multi-hit-games",
        "total-bases-by-player-and-season",
        "hitless-games-by-player",
        "pitches-by-pitcher-and-venue",
        "pitch-summary-by-pitcher",
        "batted-balls-by-batter-and-venue",
        "events-by-player",
        "runs-by-season-and-venue",
    }
    stale_routes: set[str] = set()
    rebenchmark_fields = {
        "evidenceStatus",
        "historicalAuthoritativeQuerySha256",
        "historicalIndexedQuerySha256",
        "currentAuthoritativeQuerySha256",
        "currentIndexedQuerySha256",
    }
    for route in routes:
        name = str(route["name"])
        pair = pair_by_name[name]
        result = benchmark_by_name[name]
        if route.get("authoritative") != pair.get("authoritative"):
            raise ValueError(f"Reviewed authoritative route differs for {name}")
        if route.get("indexed") != pair.get("indexed"):
            raise ValueError(f"Reviewed indexed route differs for {name}")
        current_hashes: dict[str, str] = {}
        measured_hashes: dict[str, object] = {}
        for layer in ("authoritative", "indexed"):
            current_path = ROOT / str(pair[layer])
            current_hash = sha256_text_file(current_path)
            measured_hash = result.get(f"{layer}QuerySha256")
            current_hashes[layer] = current_hash
            measured_hashes[layer] = measured_hash
        stale_layers = {
            layer
            for layer in ("authoritative", "indexed")
            if current_hashes[layer] != measured_hashes[layer]
        }
        if stale_layers:
            stale_routes.add(name)
            if (
                route.get("autoLayer") != "authoritative"
                or route.get("evidenceStatus")
                != "rebenchmark-and-equivalence-required"
                or route.get("historicalAuthoritativeQuerySha256")
                != measured_hashes["authoritative"]
                or route.get("historicalIndexedQuerySha256")
                != measured_hashes["indexed"]
                or route.get("currentAuthoritativeQuerySha256")
                != current_hashes["authoritative"]
                or route.get("currentIndexedQuerySha256")
                != current_hashes["indexed"]
            ):
                raise ValueError(
                    f"Stale measured route is not fail-closed for rebenchmark/equivalence: {name}"
                )
        elif rebenchmark_fields.intersection(route):
            raise ValueError(f"Reviewed route has an unexpected rebenchmark marker: {name}")
        if route.get("autoLayer") not in ("authoritative", "indexed"):
            raise ValueError(f"Reviewed route has an invalid automatic layer: {name}")
        if float(route.get("medianSpeedup", -1)) != float(result.get("medianSpeedup", -2)):
            raise ValueError(f"Reviewed route benchmark evidence is stale for {name}")
    actual_indexed = {
        str(route["name"])
        for route in routes
        if str(route.get("autoLayer")) == "indexed"
    }
    if actual_indexed != expected_indexed - stale_routes:
        raise ValueError("Reviewed indexed routes differ from measured and current candidates")
    return len(routes)


def validate_tdb2_execution_capture() -> int:
    report = json.loads(TDB2_EXECUTION_SUMMARY.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-query-index-tdb2-execution-capture":
        raise ValueError("TDB2 execution capture has an unknown artifact type")
    captures = validate_query_index_evidence_register()
    registered = captures[
        "benchmarks/query-index/tdb2-execution/tdb2-execution-summary.json"
    ]
    if report.get("queryIndexContractSha256") != registered.get(
        "queryIndexContractSha256"
    ):
        raise ValueError("TDB2 execution capture differs from its capture register")
    benchmark = json.loads(QUERY_INDEX_CORPUS_BASELINE.read_text(encoding="utf-8"))
    if report.get("corpusSha256") != benchmark.get("corpusSha256"):
        raise ValueError("TDB2 execution capture and corpus benchmark use different corpora")

    benchmark_results = benchmark.get("results", [])
    expected = {
        (str(result["name"]), layer): str(result[f"{layer}Query"])
        for result in benchmark_results
        for layer in ("authoritative", "indexed")
    }
    expected_hashes = {
        (str(result["name"]), layer): str(result[f"{layer}QuerySha256"])
        for result in benchmark_results
        for layer in ("authoritative", "indexed")
    }
    results = report.get("results", [])
    actual = {(str(item.get("name")), str(item.get("layer"))) for item in results}
    if len(results) != len(expected) or actual != set(expected):
        raise ValueError("TDB2 execution capture does not cover the exact query layers")

    expected_logs: set[str] = set()
    for result in results:
        key = (str(result["name"]), str(result["layer"]))
        relative_query = expected[key]
        if result.get("query") != relative_query:
            raise ValueError(f"TDB2 capture query path differs for {key[0]} {key[1]}")
        if result.get("querySha256") != expected_hashes[key]:
            raise ValueError(f"TDB2 capture query differs from benchmark: {key[0]} {key[1]}")
        log_name = str(result["log"])
        expected_logs.add(log_name)
        log_path = TDB2_EXECUTION_ROOT / log_name
        if not log_path.is_file():
            raise ValueError(f"TDB2 execution log is missing or changed: {log_name}")
        log_text = log_path.read_text(encoding="utf-8")
        normalized_log_hash = hashlib.sha256(log_text.encode("utf-8")).hexdigest()
        if result.get("logSha256") != normalized_log_hash:
            raise ValueError(f"TDB2 execution log is missing or changed: {log_name}")
        if ":: TDB2" not in log_text or ":: Execute" not in log_text:
            raise ValueError(f"TDB2 execution log lacks required sections: {log_name}")
        if int(result.get("tdb2QuadPatterns", 0)) <= 0:
            raise ValueError(f"TDB2 execution log has no quad patterns: {log_name}")
        if int(result.get("executionTraceLineCount", 0)) <= 0:
            raise ValueError(f"TDB2 execution log has no execution trace: {log_name}")
    actual_logs = {path.name for path in TDB2_EXECUTION_ROOT.glob("*.log")}
    if actual_logs != expected_logs:
        raise ValueError("TDB2 execution log directory differs from its summary")
    return len(results)


def validate_canned_query_audit() -> int:
    capture = validate_query_audit_evidence_register()["canned-2026-08-03"]
    report = json.loads(CANNED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-authoritative-canned-query-corpus-audit":
        raise ValueError("Canned-query audit has an unknown artifact type")

    results = report.get("results", [])
    actual_paths = {str(result.get("query")) for result in results}
    if (
        len(results) != len(actual_paths)
        or int(report.get("queryCount", -1)) != len(results)
        or int(capture.get("compatibleQueryCount", -1)) != len(results)
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(capture.get("compatibleQuerySetSha256", ""))
        )
    ):
        raise ValueError("Canned-query historical audit inventory is inconsistent")

    for result in results:
        query_path = Path(str(result.get("query", "")))
        if (
            query_path.is_absolute()
            or ".." in query_path.parts
            or not query_path.parts
            or query_path.parts[0] != "sparql"
            or query_path.suffix != ".rq"
        ):
            raise ValueError(f"Canned-query captured path is invalid: {result.get('query')}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("querySha256", ""))):
            raise ValueError(f"Canned-query captured hash is invalid: {result['query']}")
        if int(result.get("rowCount", 0)) <= 0:
            raise ValueError(f"Canned-query baseline contains an empty result: {result['query']}")
        if int(result.get("duplicateRowCount", -1)) != 0:
            raise ValueError(f"Canned-query baseline contains duplicate rows: {result['query']}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("rowSetSha256", ""))):
            raise ValueError(f"Invalid row-set hash for {result['query']}")

    mapping_hash = str(report.get("mappingSha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", mapping_hash):
        raise ValueError("Canned-query historical mapping hash is invalid")

    snapshots = report.get("graphSnapshots", [])
    if len(snapshots) != 8:
        raise ValueError("Canned-query audit must cover exactly eight authoritative graphs")
    signature_lines = [f"mapping={mapping_hash}"]
    total_triples = 0
    for snapshot in snapshots:
        game_pk = str(snapshot["gamePk"])
        source_path = ROOT / str(snapshot["sourcePath"])
        expected_source = ROOT / "data" / "raw" / "samples" / "2026-08-03" / f"{game_pk}.json"
        if source_path.resolve() != expected_source.resolve():
            raise ValueError(f"Unexpected canned-query audit source path for game {game_pk}")
        source_hash = sha256_file(source_path)
        if str(snapshot.get("sourceSha256")) != source_hash:
            raise ValueError(f"Canned-query audit source hash is stale for game {game_pk}")
        graph_iri = f"https://w3id.org/baseball/graph/game/{game_pk}"
        if str(snapshot.get("graphIri")) != graph_iri:
            raise ValueError(f"Unexpected canned-query audit graph IRI for game {game_pk}")
        triple_count = int(snapshot["authoritativeTripleCount"])
        total_triples += triple_count
        signature_lines.append(f"{graph_iri}|{source_hash}|{triple_count}")

    corpus_hash = hashlib.sha256("\n".join(signature_lines).encode("utf-8")).hexdigest()
    if str(report.get("corpusSha256")) != corpus_hash:
        raise ValueError("Canned-query audit corpus signature is invalid")
    if int(report.get("authoritativeTripleCount", -1)) != total_triples:
        raise ValueError("Canned-query audit authoritative triple total is inconsistent")
    if int(report.get("nonEmptyQueryCount", -1)) != len(results):
        raise ValueError("Canned-query audit non-empty count is inconsistent")
    if int(report.get("zeroRowQueryCount", -1)) != 0:
        raise ValueError("Canned-query audit reports zero-row queries")
    if int(report.get("queriesWithDuplicateRows", -1)) != 0:
        raise ValueError("Canned-query audit reports duplicate rows")
    return len(results)


def validate_advanced_query_audit() -> int:
    capture = validate_query_audit_evidence_register()["advanced-2026-08-03"]
    catalog = json.loads(ADVANCED_QUERY_CATALOG.read_text(encoding="utf-8"))
    if catalog.get("artifactType") != "baseball-advanced-semantic-query-catalog":
        raise ValueError("Advanced-query catalog has an unknown artifact type")
    entries = catalog.get("queries", [])
    advanced_files = sorted(ADVANCED_QUERY_ROOT.glob("*.rq"))
    catalog_paths = {str(entry.get("path")) for entry in entries}
    expected_paths = {
        path.relative_to(ROOT).as_posix() for path in advanced_files
    }
    if len(entries) != 17 or len(advanced_files) != 17 or catalog_paths != expected_paths:
        raise ValueError("Advanced-query catalog does not cover the exact 17-query suite")
    allowed_modes = {
        "positive-evidence", "completeness-gated", "integrity-audit", "decision-support"
    }
    ids = [str(entry.get("id")) for entry in entries]
    if len(set(ids)) != 17:
        raise ValueError("Advanced-query catalog IDs must be unique")
    for entry in entries:
        if entry.get("semanticMode") not in allowed_modes:
            raise ValueError(f"Unknown advanced-query semantic mode: {entry.get('id')}")
        if not isinstance(entry.get("allowZeroRows"), bool):
            raise ValueError(f"Advanced-query zero-row policy is missing: {entry.get('id')}")
        if not str(entry.get("claim", "")).strip():
            raise ValueError(f"Advanced-query claim is missing: {entry.get('id')}")
        if not str(entry.get("label", "")).strip():
            raise ValueError(f"Advanced-query baseball label is missing: {entry.get('id')}")
        result_filters = entry.get("resultFilters", [])
        if not isinstance(result_filters, list):
            raise ValueError(f"Advanced-query result filters must be a list: {entry.get('id')}")
        filter_ids = [str(item.get("id", "")) for item in result_filters]
        if len(filter_ids) != len(set(filter_ids)):
            raise ValueError(f"Advanced-query result filters must be unique: {entry.get('id')}")
        query_text = (ROOT / str(entry["path"])).read_text(encoding="utf-8")
        for item in result_filters:
            filter_id = str(item.get("id", ""))
            variable = str(item.get("variable", ""))
            if filter_id not in {"player", "pitcher", "umpire", "official_scorer"}:
                raise ValueError(f"Advanced-query result filter is not allowlisted: {entry.get('id')} {filter_id}")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", variable):
                raise ValueError(f"Advanced-query result-filter variable is invalid: {entry.get('id')} {filter_id}")
            if f"?{variable}" not in query_text:
                raise ValueError(f"Advanced-query result-filter variable is absent: {entry.get('id')} {filter_id}")
            if not str(item.get("label", "")).strip() or not str(item.get("optionFamily", "")).strip() or not str(item.get("optionDimension", "")).strip():
                raise ValueError(f"Advanced-query result-filter UI contract is incomplete: {entry.get('id')} {filter_id}")
    if len(catalog.get("blockedAnalytics", [])) != 4:
        raise ValueError("Advanced-query catalog must preserve the four blocked claims")

    report = json.loads(ADVANCED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-advanced-semantic-query-corpus-audit":
        raise ValueError("Advanced-query audit has an unknown artifact type")
    results = report.get("results", [])
    by_id = {str(result.get("id")): result for result in results}
    if (
        len(results) != len(by_id)
        or int(report.get("queryCount", -1)) != len(results)
        or int(capture.get("compatibleQueryCount", -1)) != len(results)
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(capture.get("compatibleQuerySetSha256", ""))
        )
    ):
        raise ValueError("Advanced-query historical audit inventory is inconsistent")
    if not re.fullmatch(r"[0-9a-f]{64}", str(report.get("catalogSha256", ""))):
        raise ValueError("Advanced-query historical catalog hash is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(report.get("mappingSha256", ""))):
        raise ValueError("Advanced-query historical mapping hash is invalid")

    for query_id, result in by_id.items():
        query_path = Path(str(result.get("query", "")))
        if (
            not query_id
            or query_path.is_absolute()
            or ".." in query_path.parts
            or not query_path.parts
            or query_path.parts[:2] != ("sparql", "advanced")
            or query_path.suffix != ".rq"
        ):
            raise ValueError(f"Advanced-query audit path is invalid: {query_id}")
        if result.get("semanticMode") not in allowed_modes:
            raise ValueError(f"Advanced-query historical semantic mode is invalid: {query_id}")
        if not isinstance(result.get("allowZeroRows"), bool):
            raise ValueError(f"Advanced-query historical zero-row policy is invalid: {query_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("querySha256", ""))):
            raise ValueError(f"Advanced-query captured hash is invalid: {query_id}")
        row_count = int(result.get("rowCount", -1))
        if row_count < 0 or (row_count == 0 and not result["allowZeroRows"]):
            raise ValueError(f"Advanced-query baseline has an invalid row count: {query_id}")
        if int(result.get("duplicateRowCount", -1)) != 0:
            raise ValueError(f"Advanced-query baseline contains duplicate rows: {query_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("rowSetSha256", ""))):
            raise ValueError(f"Advanced-query baseline row-set hash is invalid: {query_id}")

    snapshots = report.get("graphSnapshots", [])
    if len(snapshots) != 8 or int(report.get("authoritativeGraphCount", -1)) != 8:
        raise ValueError("Advanced-query audit must cover exactly eight authoritative graphs")
    mapping_hash = str(report["mappingSha256"])
    signature_lines = [f"mapping={mapping_hash}"]
    total_triples = 0
    for snapshot in snapshots:
        game_pk = str(snapshot["gamePk"])
        source_path = ROOT / str(snapshot["sourcePath"])
        expected_source = ROOT / "data" / "raw" / "samples" / "2026-08-03" / f"{game_pk}.json"
        if source_path.resolve() != expected_source.resolve():
            raise ValueError(f"Unexpected advanced-query source path for game {game_pk}")
        source_hash = sha256_file(source_path)
        if str(snapshot.get("sourceSha256")) != source_hash:
            raise ValueError(f"Advanced-query source hash is stale for game {game_pk}")
        graph_iri = f"https://w3id.org/baseball/graph/game/{game_pk}"
        triple_count = int(snapshot["authoritativeTripleCount"])
        total_triples += triple_count
        signature_lines.append(f"{graph_iri}|{source_hash}|{triple_count}")
    corpus_hash = hashlib.sha256("\n".join(signature_lines).encode("utf-8")).hexdigest()
    if str(report.get("corpusSha256")) != corpus_hash:
        raise ValueError("Advanced-query audit corpus signature is invalid")
    if int(report.get("authoritativeTripleCount", -1)) != total_triples:
        raise ValueError("Advanced-query audit triple total is inconsistent")
    non_empty = sum(int(result.get("rowCount", -1)) > 0 for result in results)
    if int(report.get("nonEmptyQueryCount", -1)) != non_empty:
        raise ValueError("Advanced-query audit non-empty count is inconsistent")
    if int(report.get("zeroRowQueryCount", -1)) != len(results) - non_empty:
        raise ValueError("Advanced-query audit zero-row count is inconsistent")
    if int(report.get("queriesWithDuplicateRows", -1)) != 0:
        raise ValueError("Advanced-query audit reports duplicate rows")
    integrity_rows = sum(
        int(result["rowCount"])
        for result in results
        if result.get("semanticMode") == "integrity-audit"
    )
    if int(report.get("integrityFindingCount", -1)) != integrity_rows:
        raise ValueError("Advanced-query integrity finding count is inconsistent")
    return len(results)


def validate_paq_contract() -> int:
    contract = json.loads(PAQ_CONTRACT.read_text(encoding="utf-8"))
    if (
        contract.get("artifactType") != "baseball-plate-appearance-quality-contract"
        or contract.get("version") != "PAQ-1.0"
        or contract.get("range") != {"minimum": 0.0, "maximum": 1.0, "displayDecimals": 3}
    ):
        raise ValueError("PAQ-1.0 has an invalid contract envelope")
    weights = contract.get("weights", {})
    for path in ("default",):
        values = weights.get(path, {})
        if not values or abs(sum(float(value) for value in values.values()) - 1.0) > 1e-9:
            raise ValueError(f"PAQ-1.0 weights do not sum to one: {path}")
    expected_bands = [
        (0.850, "Excellent"), (0.650, "Good"), (0.450, "Mixed"),
        (0.250, "Poor"), (0.000, "Bad"),
    ]
    actual_bands = [
        (float(item.get("minimum", -1)), str(item.get("label", "")))
        for item in contract.get("bands", [])
    ]
    if actual_bands != expected_bands or len(contract.get("anchors", [])) < 8:
        raise ValueError("PAQ-1.0 bands or anchor cases are incomplete")
    if contract.get("damageCaps") != {
        "grounded_into_double_play": 0.249,
        "triple_play": 0.249,
    }:
        raise ValueError("PAQ-1.0 damaging multi-out caps are incomplete")
    query = (ADVANCED_QUERY_ROOT / "plate-appearance-fingerprint.rq").read_text(encoding="utf-8")
    required_query_markers = (
        'BIND("PAQ-1.0" AS ?plateAppearanceQualityVersion)',
        "AS ?plateAppearanceQuality)",
        "AS ?outcomeRating)",
        "AS ?grindRating)",
        "AS ?situationalRating)",
    )
    missing = [marker for marker in required_query_markers if marker not in query]
    if missing:
        raise ValueError(f"PAQ-1.0 query contract is incomplete: {', '.join(missing)}")
    return len(contract["anchors"])


def main() -> None:
    require_layout()
    subprocess.run(
        [sys.executable, str(SEMANTIC_CHANGE_CONTROL_VALIDATOR)],
        cwd=GIT_ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ONTOLOGY_CURATION_VALIDATOR)],
        cwd=GIT_ROOT,
        check=True,
    )
    subprocess.run([sys.executable, str(SEMANTIC_CHANGE_CONTROL_TEST)], cwd=GIT_ROOT, check=True)
    subprocess.run([sys.executable, str(ONTOLOGY_CURATION_TEST)], cwd=GIT_ROOT, check=True)
    retired_layout_count = validate_layout_boundaries()
    source_module_count, source_ids = validate_source_module_contract()
    scoped_query_count = validate_query_source_scopes(source_ids)
    json_count = validate_json()
    yaml_count = validate_yaml()
    raw_schedule_count, raw_game_count, final_schedule_entries = validate_raw_corpus()
    validate_review_context()
    turtle_count = validate_turtle()
    shacl_shape_count = validate_shacl_profiles()
    sparql_count = validate_sparql()
    validate_query_contract()
    markdown_count, mermaid_count = validate_markdown()
    validate_ontology_overlay()
    validate_active_mapping()
    rml_information_map_count = validate_rml_information_boundary()
    validate_rml_mermaid()
    validate_selective_reasoning()
    paq_anchor_count = validate_paq_contract()
    subprocess.run([sys.executable, str(SERVING_LAYER_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(SERVING_MATERIALIZER_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(DSQ_QUERY_MODULE_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(DSQ_SQL_MATERIALIZATION_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(PROMOTED_GRAPH_EVENT_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(AUTHORITY_SERVING_TEST)], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(REPOSITORY_VALIDATION_OBSERVER_TEST)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([sys.executable, str(SERVING_EQUIVALENCE_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(SPARQL_SOURCE_SCOPE_TEST)], cwd=ROOT, check=True)
    reasoning_proof_count = validate_reasoning_evidence()
    reasoning_review_runs, reasoning_review_proofs = validate_reasoning_review_evidence()
    validate_web_app()
    canned_audit_count = validate_canned_query_audit()
    advanced_audit_count = validate_advanced_query_audit()
    query_index_benchmark_count = validate_query_index_benchmarks()
    reviewed_route_count = validate_reviewed_query_routing()
    tdb2_capture_count = validate_tdb2_execution_capture()
    algebra_plan_count = validate_query_index_algebra_artifacts()
    print(f"JSON files parsed: {json_count}")
    print(f"YAML files parsed: {yaml_count}")
    print(
        f"Raw corpus checked: {raw_schedule_count} schedules, {raw_game_count} "
        f"distinct games, {final_schedule_entries} final schedule entries"
    )
    print("Challenge and umpire-initiated review context regression passed.")
    print(f"Turtle files parsed: {turtle_count}")
    print(f"SHACL node shapes validated: {shacl_shape_count}")
    print(f"SPARQL queries parsed: {sparql_count}")
    print(f"Repository layout checked: {retired_layout_count} retired locations")
    print(
        f"Source boundaries checked: {source_module_count} modules, "
        f"{scoped_query_count} dependency-scoped queries"
    )
    print(
        f"RML information boundary checked: {rml_information_map_count} typed ICE value maps"
    )
    print(f"Markdown files checked: {markdown_count}")
    print(f"Mermaid blocks checked: {mermaid_count}")
    print(f"Optimized ARQ algebra plans checked: {algebra_plan_count}")
    print("Local web explorer checks passed.")
    print("Reusable DSQ query-module contracts passed.")
    print("Complete DSQ SQL materialization coverage passed.")
    print(f"PAQ-1.0 contract checked: {paq_anchor_count} anchor cases")
    print("Selective reasoning contracts and offline smoke tests passed.")
    print(f"Selective first-order proof obligations checked: {reasoning_proof_count}")
    print(
        f"Reviewed reasoning comparison checked: {reasoning_review_runs} runs, "
        f"{reasoning_review_proofs} proved obligations"
    )
    print(f"Canned-query corpus baselines checked: {canned_audit_count}")
    print(f"Advanced semantic query baselines checked: {advanced_audit_count}")
    print(f"Corpus query-index benchmark pairs checked: {query_index_benchmark_count}")
    print(f"Reviewed operational query routes checked: {reviewed_route_count}")
    print(f"TDB2 query execution captures checked: {tdb2_capture_count}")
    print("Repository validation passed.")


if __name__ == "__main__":
    main()
