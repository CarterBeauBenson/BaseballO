#!/usr/bin/env python3
"""Validate repository structure and the active direct RML mapping."""

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

from pyshacl import validate as validate_shacl
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.plugins.sparql import prepareQuery


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_MAPPING = ROOT / "mappings" / "direct" / "mlb-direct.rml.ttl"
MAPPING_VALIDATOR = ROOT / "mappings" / "direct" / "validate_direct_mapping.py"
CONTEXT_BUILDER = ROOT / "scripts" / "pipeline" / "prepare-rml-context.py"
ONTOLOGY_OVERLAY_VALIDATOR = ROOT / "scripts" / "validate_ontology_overlay.py"
RML_MERMAID_GENERATOR = ROOT / "scripts" / "generate_rml_mermaid.py"
SELECTIVE_REASONING_TEST = ROOT / "scripts" / "reasoning" / "test-selective-reasoning.py"
NIFI_EVIDENCE_TEST = ROOT / "tests" / "test_nifi_evidence_stage.py"
NIFI_GAME_FLOW_TEST = ROOT / "tests" / "test_nifi_game_flow.py"
NIFI_CORPUS_FLOW_TEST = ROOT / "tests" / "test_nifi_corpus_flow.py"
NIFI_EVIDENCE_CONTRACT = ROOT / "infra" / "nifi" / "repeatable-stages.json"
SELECTIVE_REASONER = ROOT / "scripts" / "reasoning" / "selective_reasoner.py"
SELECTIVE_PROVER = ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py"
REASONING_EVIDENCE = ROOT / "reasoning" / "evidence" / "fixture-566279-pa-0.json"
REASONING_REVIEW_SAMPLES = ROOT / "reasoning" / "reviewed-samples.json"
REASONING_REVIEW_EVIDENCE = (
    ROOT / "reasoning" / "evidence" / "fixture-566279-reviewed-samples.json"
)
REASONING_REVIEW_EVALUATOR = ROOT / "scripts" / "reasoning" / "evaluate-reviewed-samples.py"
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
MAPPING_SAMPLES = (
    SAMPLE,
    REVIEW_SAMPLE,
    IN_PLAY_INTERFERENCE_SAMPLE,
    TRIPLE_PLAY_SAMPLE,
    WILD_PITCH_UNCAUGHT_THIRD_STRIKE_SAMPLE,
    PASSED_BALL_UNCAUGHT_THIRD_STRIKE_SAMPLE,
    *sorted((ROOT / "data" / "raw" / "samples" / "2026-08-03").glob("[0-9]*.json")),
)
SPARQL_ROOT = ROOT / "sparql"
QUERY_BUILDERS = (
    ROOT / "web" / "query-builder" / "analytics-query-builder.js",
    ROOT / "web" / "query-builder" / "hit-query-builder.js",
)
WEB_ROOT = ROOT / "web"
CANNED_AUDIT_ROOT = ROOT / "benchmarks" / "canned-query-audit"
CANNED_AUDIT_BASELINE = CANNED_AUDIT_ROOT / "corpus-2026-08-03-baseline.json"
ADVANCED_QUERY_ROOT = SPARQL_ROOT / "advanced"
ADVANCED_QUERY_CATALOG = ADVANCED_QUERY_ROOT / "advanced-query-catalog.json"
ADVANCED_AUDIT_ROOT = ROOT / "benchmarks" / "advanced-query-audit"
ADVANCED_AUDIT_BASELINE = ADVANCED_AUDIT_ROOT / "corpus-2026-08-03-baseline.json"
QUERY_INDEX_BENCHMARK_ROOT = ROOT / "benchmarks" / "query-index"
QUERY_INDEX_CORPUS_BASELINE = QUERY_INDEX_BENCHMARK_ROOT / "corpus-2026-08-03-baseline.json"
TDB2_EXECUTION_ROOT = QUERY_INDEX_BENCHMARK_ROOT / "tdb2-execution"
TDB2_EXECUTION_SUMMARY = TDB2_EXECUTION_ROOT / "tdb2-execution-summary.json"
REVIEWED_QUERY_ROUTING = SPARQL_ROOT / "query-index" / "operational-query-routing.json"
SHACL_ROOT = ROOT / "shacl"
SH = Namespace("http://www.w3.org/ns/shacl#")
BASE = Namespace("https://baseballontology.org/")
IDX = Namespace("https://w3id.org/baseball/query-index/")

REQUIRED_PATHS = (
    ROOT / "README.md",
    ROOT / "NEXT-PHASE.md",
    ROOT / "ontology" / "BaseballO.ttl",
    ROOT / "ontology" / "BaseballO-axioms-overlay.ttl",
    ACTIVE_MAPPING,
    ROOT / "mappings" / "policies" / "modeling-choices.yaml",
    ROOT / "mappings" / "policies" / "iri-policy.yaml",
    ROOT / "mermaid" / "README.md",
    ROOT / "mermaid" / "rml-mermaid-manifest.yaml",
    ROOT / "mermaid" / "patterns" / "README.md",
    SHACL_ROOT / "README.md",
    SHACL_ROOT / "authoritative.ttl",
    SHACL_ROOT / "query-index.ttl",
    ROOT / "reasoning" / "README.md",
    ROOT / "reasoning" / "bfo-clif-manifest.json",
    ROOT / "reasoning" / "profiles" / "event-order.json",
    ROOT / "reasoning" / "profiles" / "event-structure.json",
    ROOT / "reasoning" / "profiles" / "participation.json",
    REASONING_EVIDENCE,
    REASONING_REVIEW_SAMPLES,
    REASONING_REVIEW_EVIDENCE,
    REASONING_REVIEW_EVALUATOR,
    WEB_ROOT / "package.json",
    WEB_ROOT / "index.html",
    WEB_ROOT / "styles.css",
    WEB_ROOT / "app.js",
    WEB_ROOT / "server.mjs",
    WEB_ROOT / "tests" / "analytics-query-builder.test.mjs",
    ROOT / "infra" / "README.md",
    ROOT / "infra" / "fuseki" / "configuration" / "baseball-dev.ttl",
    ROOT / "infra" / "versions.psd1",
    ROOT / "scripts" / "infra" / "configure-nifi-foundation.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-rdf-skeleton.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-games-manual.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-games-daily.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-evidence.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-rdf-flow.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-corpus-audits.ps1",
    ROOT / "infra" / "nifi" / "repeatable-stages.json",
    ROOT / "scripts" / "pipeline" / "import-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "process-staged-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "archive-and-queue-game-json.py",
    ROOT / "scripts" / "pipeline" / "process-nifi-rdf-stage.ps1",
    ROOT / "scripts" / "pipeline" / "queue-ready-corpus-audits.py",
    ROOT / "scripts" / "pipeline" / "process-nifi-corpus-stage.py",
    ROOT / "scripts" / "pipeline" / "test-manual-vertical-slice.ps1",
    ROOT / "scripts" / "pipeline" / "test-nifi-rdf-flow.ps1",
    ROOT / "scripts" / "pipeline" / "run-rml.ps1",
    ROOT / "scripts" / "pipeline" / "prepare-rml-context.py",
    ROOT / "scripts" / "pipeline" / "acquire-daily-games.ps1",
    ROOT / "scripts" / "pipeline" / "load-game-graph.ps1",
    ROOT / "scripts" / "pipeline" / "validate-generated-rdf.py",
    ROOT / "scripts" / "pipeline" / "validate-shacl.py",
    ROOT / "scripts" / "pipeline" / "validate-mapping-shacl-contracts.py",
    ROOT / "scripts" / "pipeline" / "build-query-index.ps1",
    ROOT / "scripts" / "pipeline" / "compile-query-index.py",
    ROOT / "scripts" / "pipeline" / "query-index-common.ps1",
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
    ROOT / "scripts" / "pipeline" / "run-nifi-evidence-stage.py",
    ROOT / "scripts" / "reasoning" / "sync-bfo-clif.py",
    ROOT / "scripts" / "reasoning" / "selective_reasoner.py",
    ROOT / "scripts" / "reasoning" / "prove-selective-reasoning.py",
    ROOT / "scripts" / "reasoning" / "run-selective-reasoning.ps1",
    SELECTIVE_REASONING_TEST,
    NIFI_EVIDENCE_TEST,
    NIFI_GAME_FLOW_TEST,
    NIFI_CORPUS_FLOW_TEST,
    RML_MERMAID_GENERATOR,
    ROOT / "sparql" / "empty-games-prototype.rq",
    ADVANCED_QUERY_ROOT / "README.md",
    ADVANCED_QUERY_CATALOG,
    ROOT / "sparql" / "query-inventory.md",
    ROOT / "sparql" / "graph-condensation-requirements.md",
    ROOT / "sparql" / "query-index" / "README.md",
    ROOT / "sparql" / "query-index" / "query-decision-matrix.md",
    REVIEWED_QUERY_ROUTING,
    ROOT / "sparql" / "query-index" / "dehydration-package.md",
    ROOT / "sparql" / "query-index" / "benchmarks" / "benchmark-pairs.json",
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
    SAMPLE,
)

OFFLINE_PIPELINE_PATHS = (
    ROOT / "scripts" / "infra" / "configure-nifi-games-manual.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-rdf-flow.ps1",
    ROOT / "scripts" / "infra" / "configure-nifi-corpus-audits.ps1",
    ROOT / "scripts" / "pipeline" / "import-game-json.ps1",
    ROOT / "scripts" / "pipeline" / "archive-and-queue-game-json.py",
    ROOT / "scripts" / "pipeline" / "process-nifi-rdf-stage.ps1",
    ROOT / "scripts" / "pipeline" / "queue-ready-corpus-audits.py",
    ROOT / "scripts" / "pipeline" / "process-nifi-corpus-stage.py",
    ROOT / "scripts" / "pipeline" / "process-staged-game-json.ps1",
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
    missing = [path.relative_to(ROOT) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        raise ValueError("Missing required paths: " + ", ".join(map(str, missing)))


def validate_json() -> int:
    files = list(ROOT.rglob("*.json"))
    for path in files:
        with path.open(encoding="utf-8") as stream:
            json.load(stream)
    return len(files)


def validate_raw_corpus() -> tuple[int, int, int]:
    start = date.fromisoformat("2026-07-14")
    end = date.fromisoformat("2026-08-06")
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
    if len(schedule_files) != 24 or len(game_files) != 288:
        raise ValueError(
            "Expected 24 dated schedules and 288 canonical raw game files; "
            f"found {len(schedule_files)} and {len(game_files)}"
        )
    actual_dates = [path.parent.name for path in schedule_files]
    if actual_dates != expected_dates:
        raise ValueError("Raw schedule dates do not cover 2026-07-14 through 2026-08-06")

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
    final_schedule_entries = 0
    for path in schedule_files:
        schedule = json.loads(path.read_text(encoding="utf-8"))
        for schedule_date in schedule.get("dates", []):
            for game in schedule_date.get("games", []):
                if game.get("status", {}).get("abstractGameState") == "Final":
                    game_pk = str(game.get("gamePk", ""))
                    if not game_pk.isdigit():
                        raise ValueError(f"Schedule contains an unsafe final gamePk: {path}")
                    final_schedule_entries += 1
                    scheduled_final_pks.add(game_pk)
    if final_schedule_entries != 294:
        raise ValueError(
            f"Expected 294 final schedule entries; found {final_schedule_entries}"
        )
    if scheduled_final_pks != game_pks:
        missing = sorted(scheduled_final_pks - game_pks)
        extra = sorted(game_pks - scheduled_final_pks)
        raise ValueError(
            f"Raw game and final schedule identities differ; missing={missing}, extra={extra}"
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


def validate_turtle() -> int:
    files = list(ROOT.rglob("*.ttl"))
    for path in files:
        Graph().parse(path, format="turtle")
    return len(files)


def validate_shacl_profiles() -> int:
    profiles = {
        "authoritative": SHACL_ROOT / "authoritative.ttl",
        "query-index": SHACL_ROOT / "query-index.ttl",
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
    return shape_count


def validate_sparql() -> int:
    files = list(SPARQL_ROOT.rglob("*.rq"))
    component_files = list((SPARQL_ROOT / "query-index" / "components").glob("*.rq"))
    benchmark_files = list((SPARQL_ROOT / "query-index" / "benchmarks" / "indexed").glob("*.rq"))
    advanced_files = list(ADVANCED_QUERY_ROOT.glob("*.rq"))
    canned_files = [
        path for path in files
        if path not in component_files
        and path not in benchmark_files
        and path not in advanced_files
    ]
    if (
        len(canned_files) != 48
        or len(component_files) != 13
        or len(benchmark_files) != 18
        or len(advanced_files) != 17
    ):
        raise ValueError(
            "Expected 48 canned SPARQL queries, 13 query-index components, "
            "18 indexed benchmark companions, and 17 advanced semantic queries; "
            f"found {len(canned_files)}, {len(component_files)}, "
            f"{len(benchmark_files)}, and {len(advanced_files)}"
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


def validate_markdown() -> tuple[int, int]:
    markdown_files = list(ROOT.rglob("*.md"))
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
        "ontology/CommonCoreOntologiesMerged (1).ttl": sha256_file(
            ROOT / "ontology" / "CommonCoreOntologiesMerged (1).ttl"
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
        total_proved += proved
    if evidence.get("runCount") != 6 or evidence.get("allProfilesConsistent") is not True or evidence.get("allObligationsProved") is not True:
        raise ValueError("Reviewed reasoning comparison summary is inconsistent")
    return len(results), total_proved


def validate_offline_pipeline_boundary() -> None:
    prohibited = ("statsapi.mlb.com", "acquire-daily-games.ps1")
    for path in OFFLINE_PIPELINE_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        matches = [value for value in prohibited if value.lower() in text]
        if matches:
            raise ValueError(
                "Active offline pipeline references external acquisition in "
                f"{path.relative_to(ROOT)}: {', '.join(matches)}"
            )


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


def query_index_contract_sha256() -> str:
    contract_files = list(
        (SPARQL_ROOT / "query-index" / "components").glob("*.rq")
    ) + [
        ROOT / "scripts" / "pipeline" / "compile-query-index.py",
        ROOT / "scripts" / "pipeline" / "build-query-index.ps1",
        ROOT / "scripts" / "pipeline" / "query-index-common.ps1",
        ROOT / "scripts" / "pipeline" / "test-query-index.ps1",
    ]
    lines = [
        f"{path.relative_to(ROOT).as_posix()}={sha256_file(path)}"
        for path in sorted(contract_files, key=lambda item: str(item.resolve()).lower())
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def query_index_pairs() -> list[dict[str, object]]:
    path = SPARQL_ROOT / "query-index" / "benchmarks" / "benchmark-pairs.json"
    return json.loads(path.read_text(encoding="utf-8"))["pairs"]


def validate_query_index_benchmarks() -> int:
    current_contract = query_index_contract_sha256()
    fixture = json.loads(
        (QUERY_INDEX_BENCHMARK_ROOT / "fixture-566279-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    if fixture.get("queryIndexContractSha256") != current_contract:
        raise ValueError("Single-fixture query-index benchmark contract is stale")

    report = json.loads(QUERY_INDEX_CORPUS_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-query-index-corpus-benchmark":
        raise ValueError("Corpus query-index benchmark has an unknown artifact type")
    if report.get("queryIndexContractSha256") != current_contract:
        raise ValueError("Corpus query-index benchmark contract is stale")

    audit = json.loads(CANNED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("corpusSha256") != audit.get("corpusSha256"):
        raise ValueError("Corpus benchmark and canned-query audit use different corpora")
    if int(report.get("authoritativeTripleCount", -1)) != int(
        audit.get("authoritativeTripleCount", -2)
    ):
        raise ValueError("Corpus benchmark authoritative triple count is inconsistent")
    if int(report.get("queryIndexTripleCount", -1)) != 52944:
        raise ValueError("Corpus benchmark query-index triple count is unexpected")

    pairs = query_index_pairs()
    expected_names = {str(pair["name"]) for pair in pairs}
    results = report.get("results", [])
    if len(results) != len(pairs) or {str(item.get("name")) for item in results} != expected_names:
        raise ValueError("Corpus benchmark does not cover the exact query-pair manifest")
    pair_by_name = {str(pair["name"]): pair for pair in pairs}
    iterations = int(report.get("iterationsPerQueryAndLayer", -1))
    if iterations != 20:
        raise ValueError("Corpus benchmark must retain 20 samples per query and layer")
    for result in results:
        pair = pair_by_name[str(result["name"])]
        for layer, pair_key, report_key in (
            ("authoritative", "authoritative", "authoritativeQuery"),
            ("indexed", "indexed", "indexedQuery"),
        ):
            relative_path = str(pair[pair_key])
            if result.get(report_key) != relative_path:
                raise ValueError(f"Corpus benchmark query path differs for {result['name']}")
            if result.get(f"{layer}QuerySha256") != sha256_file(ROOT / relative_path):
                raise ValueError(f"Corpus benchmark query hash is stale for {result['name']}")
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
    if routing.get("artifactType") != "baseball-reviewed-query-routing":
        raise ValueError("Reviewed query routing has an unknown artifact type")
    evidence_path = ROOT / str(routing.get("evidence", ""))
    if evidence_path.resolve() != QUERY_INDEX_CORPUS_BASELINE.resolve():
        raise ValueError("Reviewed query routing must cite the corpus benchmark")

    pairs = query_index_pairs()
    pair_by_name = {str(pair["name"]): pair for pair in pairs}
    benchmark = json.loads(QUERY_INDEX_CORPUS_BASELINE.read_text(encoding="utf-8"))
    benchmark_by_name = {
        str(result["name"]): result for result in benchmark.get("results", [])
    }
    routes = routing.get("routes", [])
    route_names = {str(route.get("name")) for route in routes}
    if len(routes) != len(pairs) or route_names != set(pair_by_name):
        raise ValueError("Reviewed query routing must cover the exact benchmark pair set")

    expected_indexed = {
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
    actual_indexed = {
        str(route["name"])
        for route in routes
        if str(route.get("autoLayer")) == "indexed"
    }
    if actual_indexed != expected_indexed:
        raise ValueError("Reviewed indexed routes differ from the measured candidates")

    for route in routes:
        name = str(route["name"])
        pair = pair_by_name[name]
        result = benchmark_by_name[name]
        if route.get("authoritative") != pair.get("authoritative"):
            raise ValueError(f"Reviewed authoritative route differs for {name}")
        if route.get("indexed") != pair.get("indexed"):
            raise ValueError(f"Reviewed indexed route differs for {name}")
        if route.get("autoLayer") not in ("authoritative", "indexed"):
            raise ValueError(f"Reviewed route has an invalid automatic layer: {name}")
        if float(route.get("medianSpeedup", -1)) != float(result.get("medianSpeedup", -2)):
            raise ValueError(f"Reviewed route benchmark evidence is stale for {name}")
    return len(routes)


def validate_tdb2_execution_capture() -> int:
    report = json.loads(TDB2_EXECUTION_SUMMARY.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-query-index-tdb2-execution-capture":
        raise ValueError("TDB2 execution capture has an unknown artifact type")
    current_contract = query_index_contract_sha256()
    if report.get("queryIndexContractSha256") != current_contract:
        raise ValueError("TDB2 execution capture query-index contract is stale")
    audit = json.loads(CANNED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("corpusSha256") != audit.get("corpusSha256"):
        raise ValueError("TDB2 execution capture and canned-query audit use different corpora")

    pairs = query_index_pairs()
    expected = {
        (str(pair["name"]), layer): str(pair[layer])
        for pair in pairs
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
        if result.get("querySha256") != sha256_file(ROOT / relative_query):
            raise ValueError(f"TDB2 capture query hash is stale for {key[0]} {key[1]}")
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
    report = json.loads(CANNED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-authoritative-canned-query-corpus-audit":
        raise ValueError("Canned-query audit has an unknown artifact type")

    component_files = set((SPARQL_ROOT / "query-index" / "components").glob("*.rq"))
    indexed_files = set((SPARQL_ROOT / "query-index" / "benchmarks" / "indexed").glob("*.rq"))
    advanced_files = set(ADVANCED_QUERY_ROOT.glob("*.rq"))
    canned_files = sorted(
        path for path in SPARQL_ROOT.rglob("*.rq")
        if path not in component_files
        and path not in indexed_files
        and path not in advanced_files
    )
    expected_paths = {path.relative_to(ROOT).as_posix() for path in canned_files}
    results = report.get("results", [])
    actual_paths = {str(result.get("query")) for result in results}
    if len(canned_files) != 48 or len(results) != 48 or actual_paths != expected_paths:
        raise ValueError("Canned-query audit does not cover the exact 48-query library")

    for result in results:
        query_path = ROOT / str(result["query"])
        if str(result.get("querySha256")) != sha256_file(query_path):
            raise ValueError(
                f"Canned-query baseline is stale for {result['query']}; rerun the live audit"
            )
        if int(result.get("rowCount", 0)) <= 0:
            raise ValueError(f"Canned-query baseline contains an empty result: {result['query']}")
        if int(result.get("duplicateRowCount", -1)) != 0:
            raise ValueError(f"Canned-query baseline contains duplicate rows: {result['query']}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("rowSetSha256", ""))):
            raise ValueError(f"Invalid row-set hash for {result['query']}")

    mapping_hash = sha256_file(ACTIVE_MAPPING)
    if str(report.get("mappingSha256")) != mapping_hash:
        raise ValueError("Canned-query audit mapping hash is stale")

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
    if int(report.get("nonEmptyQueryCount", -1)) != 48:
        raise ValueError("Canned-query audit non-empty count is inconsistent")
    if int(report.get("zeroRowQueryCount", -1)) != 0:
        raise ValueError("Canned-query audit reports zero-row queries")
    if int(report.get("queriesWithDuplicateRows", -1)) != 0:
        raise ValueError("Canned-query audit reports duplicate rows")
    return len(results)


def validate_advanced_query_audit() -> int:
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
    allowed_modes = {"positive-evidence", "completeness-gated", "integrity-audit"}
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
    if len(catalog.get("blockedAnalytics", [])) != 4:
        raise ValueError("Advanced-query catalog must preserve the four blocked claims")

    report = json.loads(ADVANCED_AUDIT_BASELINE.read_text(encoding="utf-8"))
    if report.get("artifactType") != "baseball-advanced-semantic-query-corpus-audit":
        raise ValueError("Advanced-query audit has an unknown artifact type")
    results = report.get("results", [])
    by_id = {str(result.get("id")): result for result in results}
    entries_by_id = {str(entry["id"]): entry for entry in entries}
    if len(results) != 17 or set(by_id) != set(entries_by_id):
        raise ValueError("Advanced-query audit does not cover the exact catalog")
    if str(report.get("catalogSha256")) != sha256_file(ADVANCED_QUERY_CATALOG):
        raise ValueError("Advanced-query audit catalog hash is stale")
    if str(report.get("mappingSha256")) != sha256_file(ACTIVE_MAPPING):
        raise ValueError("Advanced-query audit mapping hash is stale")

    for query_id, result in by_id.items():
        entry = entries_by_id[query_id]
        query_path = ROOT / str(entry["path"])
        if str(result.get("query")) != str(entry["path"]):
            raise ValueError(f"Advanced-query audit path is invalid: {query_id}")
        if str(result.get("semanticMode")) != str(entry["semanticMode"]):
            raise ValueError(f"Advanced-query audit semantic mode is stale: {query_id}")
        if bool(result.get("allowZeroRows")) != bool(entry["allowZeroRows"]):
            raise ValueError(f"Advanced-query audit zero-row policy is stale: {query_id}")
        if str(result.get("querySha256")) != sha256_file(query_path):
            raise ValueError(f"Advanced-query baseline is stale for {query_id}")
        row_count = int(result.get("rowCount", -1))
        if row_count < 0 or (row_count == 0 and not bool(entry["allowZeroRows"])):
            raise ValueError(f"Advanced-query baseline has an invalid row count: {query_id}")
        if int(result.get("duplicateRowCount", -1)) != 0:
            raise ValueError(f"Advanced-query baseline contains duplicate rows: {query_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("rowSetSha256", ""))):
            raise ValueError(f"Advanced-query baseline row-set hash is invalid: {query_id}")

    snapshots = report.get("graphSnapshots", [])
    if len(snapshots) != 8 or int(report.get("authoritativeGraphCount", -1)) != 8:
        raise ValueError("Advanced-query audit must cover exactly eight authoritative graphs")
    mapping_hash = sha256_file(ACTIVE_MAPPING)
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
    if int(report.get("queryCount", -1)) != 17:
        raise ValueError("Advanced-query audit query count is inconsistent")
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


def validate_nifi_evidence_contract() -> int:
    contract = json.loads(NIFI_EVIDENCE_CONTRACT.read_text(encoding="utf-8"))
    if contract.get("contractVersion") != 1:
        raise ValueError("NiFi evidence contractVersion must be 1")
    stages = contract.get("stages", {})
    expected = {
        "mapping-shacl-validation",
        "selective-reasoning",
        "canned-query-audit",
        "advanced-query-audit",
        "authoritative-index-equivalence",
        "benchmark-evidence",
        "repository-validation",
    }
    if set(stages) != expected:
        raise ValueError("NiFi evidence stage inventory is incomplete or unexpected")
    for stage_name, stage in stages.items():
        command = stage.get("command")
        dependencies = stage.get("dependencies")
        if not isinstance(command, list) or not command or not all(
            isinstance(value, str) and value for value in command
        ):
            raise ValueError(f"NiFi evidence stage has an invalid command: {stage_name}")
        if not isinstance(dependencies, list) or not dependencies:
            raise ValueError(f"NiFi evidence stage has no dependencies: {stage_name}")
        if int(stage.get("timeoutSeconds", 0)) <= 0 or not stage.get("schedule"):
            raise ValueError(f"NiFi evidence stage has invalid execution limits: {stage_name}")
        ports = stage.get("requiresLoopbackPorts", [])
        if ports and (ports != [3030] or stage.get("cacheable") is not False):
            raise ValueError(
                f"Live NiFi stage must target loopback Fuseki and disable skipping: {stage_name}"
            )
        if any("http://" in value or "https://" in value for value in command):
            raise ValueError(f"NiFi evidence command contains a network endpoint: {stage_name}")
        for value in command:
            if value.startswith(("scripts/", "mappings/", "data/")):
                if not (ROOT / value).is_file():
                    raise ValueError(
                        f"NiFi evidence command references a missing repository file: {value}"
                    )
    benchmark_command = stages["benchmark-evidence"]["command"]
    if "{artifactDirectory}" not in benchmark_command:
        raise ValueError("NiFi benchmark evidence must be written outside the repository")
    if stages["repository-validation"].get("cacheable") is not True:
        raise ValueError("Offline repository validation must use dependency-aware skipping")
    return len(stages)


def validate_nifi_game_flow_contract() -> int:
    manual = (ROOT / "scripts" / "infra" / "configure-nifi-games-manual.ps1").read_text(
        encoding="utf-8"
    )
    shared = (ROOT / "scripts" / "infra" / "configure-nifi-rdf-flow.ps1").read_text(
        encoding="utf-8"
    )
    staged = (ROOT / "scripts" / "pipeline" / "process-staged-game-json.ps1").read_text(
        encoding="utf-8"
    )
    if "import-game-json.ps1" in manual or "import-game-json.ps1" in staged:
        raise ValueError("Active NiFi manual flow still invokes the bundled importer")
    if "archive-and-queue-game-json.py" not in staged:
        raise ValueError("Active NiFi manual flow does not use the immutable archive queue")
    stages = ("assess", "rml", "validate", "load", "index", "promote")
    missing = [stage for stage in stages if f"'{stage}'" not in shared]
    if missing:
        raise ValueError(f"Shared NiFi RDF flow is missing stages: {', '.join(missing)}")
    if "configure-nifi-rdf-flow.ps1" not in manual:
        raise ValueError("Manual NiFi configuration does not configure the shared RDF flow")
    corpus = (ROOT / "scripts" / "infra" / "configure-nifi-corpus-audits.ps1").read_text(
        encoding="utf-8"
    )
    corpus_stages = ("canned", "advanced", "equivalence", "benchmark", "complete")
    missing_corpus = [stage for stage in corpus_stages if f"'{stage}'" not in corpus]
    if missing_corpus:
        raise ValueError(f"NiFi corpus flow is missing stages: {', '.join(missing_corpus)}")
    if "configure-nifi-corpus-audits.ps1" not in manual or "Queue corpus completion check" not in shared:
        raise ValueError("Per-game promotion is not connected to the NiFi corpus audit flow")
    return len(stages)


def main() -> None:
    require_layout()
    json_count = validate_json()
    raw_schedule_count, raw_game_count, final_schedule_entries = validate_raw_corpus()
    validate_review_context()
    turtle_count = validate_turtle()
    shacl_shape_count = validate_shacl_profiles()
    sparql_count = validate_sparql()
    validate_query_contract()
    markdown_count, mermaid_count = validate_markdown()
    validate_ontology_overlay()
    validate_active_mapping()
    validate_rml_mermaid()
    validate_selective_reasoning()
    nifi_evidence_stage_count = validate_nifi_evidence_contract()
    nifi_game_stage_count = validate_nifi_game_flow_contract()
    subprocess.run([sys.executable, str(NIFI_EVIDENCE_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(NIFI_GAME_FLOW_TEST)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(NIFI_CORPUS_FLOW_TEST)], cwd=ROOT, check=True)
    reasoning_proof_count = validate_reasoning_evidence()
    reasoning_review_runs, reasoning_review_proofs = validate_reasoning_review_evidence()
    validate_offline_pipeline_boundary()
    validate_web_app()
    canned_audit_count = validate_canned_query_audit()
    advanced_audit_count = validate_advanced_query_audit()
    query_index_benchmark_count = validate_query_index_benchmarks()
    reviewed_route_count = validate_reviewed_query_routing()
    tdb2_capture_count = validate_tdb2_execution_capture()
    algebra_plan_count = validate_query_index_algebra_artifacts()
    print(f"JSON files parsed: {json_count}")
    print(
        f"Raw corpus checked: {raw_schedule_count} schedules, {raw_game_count} "
        f"distinct games, {final_schedule_entries} final schedule entries"
    )
    print("Challenge and umpire-initiated review context regression passed.")
    print(f"Turtle files parsed: {turtle_count}")
    print(f"SHACL node shapes validated: {shacl_shape_count}")
    print(f"SPARQL queries parsed: {sparql_count}")
    print(f"Markdown files checked: {markdown_count}")
    print(f"Mermaid blocks checked: {mermaid_count}")
    print(f"Optimized ARQ algebra plans checked: {algebra_plan_count}")
    print("Local web explorer checks passed.")
    print("Selective reasoning contracts and offline smoke tests passed.")
    print("NiFi evidence fingerprint and quarantine tests passed.")
    print("NiFi staged per-game archive, assessment, and quarantine tests passed.")
    print("NiFi promotion-driven corpus readiness and completion tests passed.")
    print(f"NiFi repeatable evidence stages checked: {nifi_evidence_stage_count}")
    print(f"NiFi per-game semantic stages checked: {nifi_game_stage_count}")
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
    print("Active manual pipeline contains no MLB acquisition endpoint or command.")
    print("Repository validation passed.")


if __name__ == "__main__":
    main()
