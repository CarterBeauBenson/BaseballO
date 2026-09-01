#!/usr/bin/env python3
"""Fail-closed black-box acceptance check for the Explorer SQL serving route."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REQUIRE_MATERIALIZED_HEADER = "X-BaseballO-Require-Materialized"
FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
EXPLORE_PROBES = {
    "batting": {"dimensions": ["player"], "metrics": ["hits", "plate_appearances"]},
    "pitching": {"dimensions": ["pitcher"], "metrics": ["pitches", "called_strikes"]},
    "baserunning": {"dimensions": ["player"], "metrics": ["runner_events", "runs"]},
    "games": {"dimensions": ["team"], "metrics": ["games"]},
}
POSITIVE_COVERAGE = {
    "advancedQueries",
    "advancedBindings",
    "battingResults",
    "pitches",
    "runnerEvents",
    "assignments",
    "emptyPlayerGames",
    "damageOpportunities",
}


class AcceptanceError(RuntimeError):
    """An Explorer response violated the materialized-serving contract."""


def object_value(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} is not a JSON object")
    return value


class ExplorerClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(self, path: str, body: dict[str, Any] | None = None, *, require_materialized: bool = False) -> tuple[dict[str, Any], float]:
        headers = {"Accept": "application/json", "Connection": "close"}
        data = None
        method = "GET"
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        if require_materialized:
            headers[REQUIRE_MATERIALIZED_HEADER] = "true"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
                status = response.status
        except HTTPError as exc:
            raw = exc.read()
            try:
                detail = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = {"error": raw.decode("utf-8", errors="replace")}
            raise AcceptanceError(f"{method} {path} returned HTTP {exc.code}: {detail.get('error', detail)}") from exc
        except (URLError, TimeoutError) as exc:
            raise AcceptanceError(f"{method} {path} failed: {exc}") from exc
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        if status != 200:
            raise AcceptanceError(f"{method} {path} returned HTTP {status}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcceptanceError(f"{method} {path} did not return UTF-8 JSON") from exc
        return object_value(payload, f"{method} {path} response"), elapsed


def compatible_measures(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in ("unit", "grain", "dimensions", "evidenceUniverse"))


def build_probes(catalogs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    public_families = object_value(catalogs["explore"].get("families"), "Explorer family catalog")
    probes: list[dict[str, Any]] = []
    for family, selection in EXPLORE_PROBES.items():
        definition = object_value(public_families.get(family), f"Explorer family {family}")
        dimensions = object_value(definition.get("dimensions"), f"{family} dimensions")
        metrics = object_value(definition.get("metrics"), f"{family} metrics")
        missing_dimensions = set(selection["dimensions"]) - set(dimensions)
        missing_metrics = set(selection["metrics"]) - set(metrics)
        if missing_dimensions or missing_metrics:
            raise AcceptanceError(f"{family} acceptance selection is absent from the public catalog")
        probes.append({
            "name": f"explore:{family}",
            "path": "/api/query",
            "body": {"family": family, **selection, "dateScope": {"preset": "one_day"}, "gameSet": "regular_season", "limit": 25},
            "kind": "result",
        })
        for dimension, declaration in dimensions.items():
            declaration = object_value(declaration, f"{family}.{dimension}")
            if declaration.get("hasOptions") and declaration.get("input") != "enum":
                query = urlencode({"family": family, "dimension": dimension, "gameSet": "regular_season"})
                probes.append({"name": f"options:{family}:{dimension}", "path": f"/api/options?{query}", "kind": "options"})

    advanced = catalogs["advanced"].get("queries")
    if not isinstance(advanced, list) or not advanced:
        raise AcceptanceError("Reviewed Advanced catalog is empty")
    for entry in advanced:
        entry = object_value(entry, "Advanced catalog entry")
        query_id = entry.get("id")
        if not isinstance(query_id, str) or not query_id:
            raise AcceptanceError("Advanced catalog entry has no ID")
        probes.append({
            "name": f"advanced:{query_id}", "path": "/api/advanced", "kind": "result",
            "body": {"id": query_id, "dateScope": {"preset": "one_day"}, "gameSet": "regular_season"},
        })
        if query_id == "plate-appearance-fingerprint":
            probes.append({
                "name": "advanced:plate-appearance-fingerprint:player-averages",
                "path": "/api/advanced", "kind": "result",
                "body": {"id": query_id, "view": "player_averages", "dateScope": {"preset": "one_day"}, "gameSet": "regular_season"},
            })

    analyses = object_value(catalogs["empty"].get("analyses"), "Empty Games catalog")
    for analysis in analyses:
        probes.append({
            "name": f"empty-games:{analysis}", "path": "/api/canned/empty-games", "kind": "result",
            "body": {"analysis": analysis, "dateScope": {"preset": "one_day"}, "gameSet": "regular_season"},
        })

    measures = object_value(catalogs["derived"].get("measures"), "Derived measure catalog")
    for numerator, numerator_contract in measures.items():
        numerator_contract = object_value(numerator_contract, f"Derived measure {numerator}")
        for denominator, denominator_contract in measures.items():
            denominator_contract = object_value(denominator_contract, f"Derived measure {denominator}")
            if numerator != denominator and compatible_measures(numerator_contract, denominator_contract):
                probes.append({
                    "name": f"derived:{numerator}:{denominator}", "path": "/api/derived", "kind": "result",
                    "body": {"numerator": numerator, "denominator": denominator, "dateScope": {"preset": "one_day"}, "gameSet": "regular_season"},
                })
    if not any(probe["name"].startswith("derived:") for probe in probes):
        raise AcceptanceError("Derived catalog has no compatible numerator/denominator pair")
    return probes


class AcceptanceRun:
    def __init__(self, advanced_query_count: int, allow_empty_grains: bool, expected_build_id: str | None) -> None:
        self.advanced_query_count = advanced_query_count
        self.allow_empty_grains = allow_empty_grains
        self.expected_build_id = expected_build_id
        self.build_id: str | None = None
        self.fingerprint: str | None = None
        self.coverage: dict[str, Any] | None = None
        self.results: list[dict[str, Any]] = []

    def record(self, probe: dict[str, Any], payload: dict[str, Any], elapsed_ms: float) -> None:
        if probe["kind"] == "options":
            layer = payload.get("layer")
            build_id = payload.get("servingBuildId")
            fingerprint = payload.get("corpusFingerprint")
            coverage = payload.get("servingCoverage")
            rows = payload.get("options")
        else:
            meta = object_value(payload.get("meta"), f"{probe['name']} metadata")
            layer = meta.get("layer")
            build_id = meta.get("servingBuildId")
            fingerprint = meta.get("corpusFingerprint")
            coverage = meta.get("servingCoverage")
            rows = object_value(payload.get("results"), f"{probe['name']} results").get("bindings")
        if layer != "materialized":
            raise AcceptanceError(f"{probe['name']} used {layer or 'an unknown layer'} instead of materialized SQL")
        if not isinstance(build_id, str) or not build_id:
            raise AcceptanceError(f"{probe['name']} has no serving build ID")
        if self.expected_build_id and build_id != self.expected_build_id:
            raise AcceptanceError(f"{probe['name']} used build {build_id}, expected {self.expected_build_id}")
        if not isinstance(fingerprint, str) or not FINGERPRINT.fullmatch(fingerprint):
            raise AcceptanceError(f"{probe['name']} has an invalid corpus fingerprint")
        coverage = object_value(coverage, f"{probe['name']} serving coverage")
        if not isinstance(rows, list):
            raise AcceptanceError(f"{probe['name']} has no result list")
        if self.build_id is None:
            self.build_id, self.fingerprint, self.coverage = build_id, fingerprint, coverage
            self.validate_coverage(coverage)
        elif (build_id, fingerprint, coverage) != (self.build_id, self.fingerprint, self.coverage):
            raise AcceptanceError(f"{probe['name']} does not use the same immutable serving build as earlier probes")
        reported = payload.get("meta", {}).get("durationMs") if probe["kind"] == "result" else None
        self.results.append({
            "name": probe["name"], "wallDurationMs": elapsed_ms,
            "servingDurationMs": reported, "rowCount": len(rows),
        })

    def validate_coverage(self, coverage: dict[str, Any]) -> None:
        if coverage.get("advancedQueries") != self.advanced_query_count:
            raise AcceptanceError(
                f"Serving coverage has {coverage.get('advancedQueries')} Advanced queries; catalog has {self.advanced_query_count}"
            )
        missing = POSITIVE_COVERAGE - set(coverage)
        if missing:
            raise AcceptanceError(f"Serving coverage omits: {', '.join(sorted(missing))}")
        for key in POSITIVE_COVERAGE:
            value = coverage[key]
            if not isinstance(value, int) or value < 0:
                raise AcceptanceError(f"Serving coverage {key} is not a non-negative integer")
            if not self.allow_empty_grains and value == 0:
                raise AcceptanceError(f"Serving coverage {key} is empty")


def write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--expected-build-id")
    parser.add_argument("--allow-empty-grains", action="store_true", help="Permit zero-count grains for bounded fixtures")
    parser.add_argument("--evidence", type=Path, help="Optionally write the compact acceptance evidence atomically")
    args = parser.parse_args()
    evidence: dict[str, Any] = {
        "artifactType": "baseball-explorer-serving-acceptance",
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "baseUrl": args.base_url.rstrip("/"),
        "status": "failed",
        "fallbackPolicy": "fail-closed-for-acceptance; fail-open-for-normal-browser-use",
    }
    try:
        client = ExplorerClient(args.base_url, args.timeout_seconds)
        catalogs = {}
        for name, path in (
            ("explore", "/api/catalog"),
            ("advanced", "/api/advanced/catalog"),
            ("empty", "/api/empty-games/catalog"),
            ("derived", "/api/derived/catalog"),
        ):
            catalogs[name], _ = client.request(path)
        advanced_queries = catalogs["advanced"].get("queries")
        if not isinstance(advanced_queries, list):
            raise AcceptanceError("Advanced catalog query list is invalid")
        probes = build_probes(catalogs)
        run = AcceptanceRun(len(advanced_queries), args.allow_empty_grains, args.expected_build_id)
        for probe in probes:
            payload, elapsed = client.request(
                probe["path"], probe.get("body"), require_materialized=True,
            )
            run.record(probe, payload, elapsed)
        evidence.update({
            "status": "succeeded",
            "buildId": run.build_id,
            "corpusFingerprint": run.fingerprint,
            "coverage": run.coverage,
            "probeCount": len(run.results),
            "probes": run.results,
        })
    except (AcceptanceError, OSError, ValueError) as exc:
        evidence["error"] = str(exc)
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    evidence["evidenceSha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if args.evidence:
        write_evidence(args.evidence, evidence)
    print(json.dumps(evidence, separators=(",", ":"), ensure_ascii=True))
    return 0 if evidence["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
