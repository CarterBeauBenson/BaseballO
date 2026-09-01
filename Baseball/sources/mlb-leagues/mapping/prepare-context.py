#!/usr/bin/env python3
"""Validate one MLB leagues response and build transient RML context.

This script is the pre-RML source-contract gate. It validates present selected
source values and exposes ancestor identifiers plus deterministic hashes needed
by RMLMapper. It does not assign ontology classes or emit RDF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any


CONTEXT_VERSION = 1
POSITIVE_ID = re.compile(r"^[1-9][0-9]*$")
SEASON_CODE = re.compile(r"^[0-9]{4}$")
DATE_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9]*Date$")
ENDPOINT_KINDS = {"leagues": "league"}
PHASE_BOUNDARIES = {
    "regular-season": ("regularSeasonStartDate", "regularSeasonEndDate"),
    "postseason": ("postSeasonStartDate", "postSeasonEndDate"),
}


class ContractError(ValueError):
    """A source value violates the accepted pre-mapping contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON number is not allowed: {value}")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="strict")).hexdigest()


def _identifier(value: Any, path: str, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise ContractError(f"{path} is required")
        return None
    if isinstance(value, bool):
        raise ContractError(f"{path} must be a positive integer identifier")
    lexical = str(value) if isinstance(value, int) else value
    if not isinstance(lexical, str) or not POSITIVE_ID.fullmatch(lexical):
        raise ContractError(f"{path} must be a positive integer identifier")
    return lexical


def _season_code(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ContractError(f"{path} must be a four-digit season code")
    lexical = str(value) if isinstance(value, int) else value
    if (
        not isinstance(lexical, str)
        or not SEASON_CODE.fullmatch(lexical)
        or lexical == "0000"
    ):
        raise ContractError(f"{path} must be a four-digit season code")
    return lexical


def _name(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty Unicode string")
    if "\ufffd" in value:
        raise ContractError(f"{path} contains a Unicode replacement character")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ContractError(f"{path} is not valid Unicode") from error
    return value


def _date_value(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractError(f"{path} must be an ISO calendar date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ContractError(f"{path} must be a valid ISO calendar date") from error
    if parsed.isoformat() != value:
        raise ContractError(f"{path} must use canonical YYYY-MM-DD form")
    return value


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{path} must be a JSON object")
    return value


def _validate_sport(record: dict[str, Any], path: str) -> None:
    if "sport" not in record or record["sport"] is None:
        return
    sport = _object(record["sport"], f"{path}.sport")
    sport_id = _identifier(sport.get("id"), f"{path}.sport.id", required=False)
    if sport_id is not None and sport_id != "1":
        raise ContractError(f"{path}.sport.id must be 1 for this baseball lane")


def _response_fields(
    endpoint_family: str, request_scope: str, response_sha256: str
) -> dict[str, str]:
    return {
        "responseEndpointFamily": endpoint_family,
        "requestScope": request_scope,
        "requestScopeHash": _sha256_text(request_scope),
        "responseSha256": response_sha256,
    }


def build_context(
    payload: dict[str, Any],
    *,
    endpoint_family: str,
    request_scope: str,
    response_sha256: str,
) -> dict[str, Any]:
    if endpoint_family != "leagues":
        raise ContractError("the mlb-leagues connector accepts only the leagues endpoint")
    raw_records = payload.get("leagues")
    if not isinstance(raw_records, list) or not raw_records:
        raise ContractError(
            f"root {endpoint_family!r} must be a non-empty JSON array"
        )

    response = _response_fields(endpoint_family, request_scope, response_sha256)
    organizations: dict[tuple[str, str], dict[str, Any]] = {}
    seasons: dict[tuple[str, str], dict[str, Any]] = {}
    dates: dict[tuple[str, str, str], dict[str, Any]] = {}
    phases: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add_organization(
        kind: str, value: Any, path: str, *, required: bool
    ) -> str | None:
        if value is None:
            if required:
                raise ContractError(f"{path} is required")
            return None
        record = _object(value, path)
        entity_id = _identifier(record.get("id"), f"{path}.id", required=True)
        assert entity_id is not None
        canonical_name = _name(record.get("name"), f"{path}.name")
        key = (kind, entity_id)
        existing = organizations.get(key)
        if existing is not None:
            prior = existing.get("name")
            if prior is not None and canonical_name is not None and prior != canonical_name:
                raise ContractError(
                    f"conflicting canonical names for {kind} {entity_id}"
                )
            if prior is None and canonical_name is not None:
                existing["name"] = canonical_name
                existing["nameHash"] = _sha256_text(canonical_name)
        else:
            item: dict[str, Any] = {
                **response,
                "entityKind": kind,
                "entityId": entity_id,
            }
            if canonical_name is not None:
                item["name"] = canonical_name
                item["nameHash"] = _sha256_text(canonical_name)
            organizations[key] = item
        return entity_id

    def add_season(league_id: str, record: dict[str, Any], path: str) -> None:
        root_season = _season_code(record.get("season"), f"{path}.season")
        date_info_value = record.get("seasonDateInfo")
        if date_info_value is None:
            date_info: dict[str, Any] = {}
        else:
            date_info = _object(date_info_value, f"{path}.seasonDateInfo")
        info_season = _season_code(
            date_info.get("seasonId"), f"{path}.seasonDateInfo.seasonId"
        )
        if root_season and info_season and root_season != info_season:
            raise ContractError(f"{path} has conflicting season and seasonId values")
        season = root_season or info_season

        non_null_date_keys = [
            key
            for key, value in date_info.items()
            if key.endswith("Date") and value is not None
        ]
        if season is None:
            if non_null_date_keys:
                raise ContractError(f"{path} has season dates but no season code")
            return

        season_key = (league_id, season)
        seasons.setdefault(
            season_key,
            {**response, "leagueId": league_id, "seasonCode": season},
        )

        validated_dates: dict[str, str] = {}
        for field_key, raw_value in date_info.items():
            if not field_key.endswith("Date") or raw_value is None:
                continue
            if not DATE_FIELD.fullmatch(field_key):
                raise ContractError(
                    f"{path}.seasonDateInfo contains unsafe date field {field_key!r}"
                )
            lexical = _date_value(
                raw_value, f"{path}.seasonDateInfo.{field_key}"
            )
            assert lexical is not None
            validated_dates[field_key] = lexical
            date_key = (league_id, season, field_key)
            existing = dates.get(date_key)
            if existing is not None and existing["dateValue"] != lexical:
                raise ContractError(
                    f"conflicting {field_key} values for league {league_id} season {season}"
                )
            dates[date_key] = {
                **response,
                "leagueId": league_id,
                "seasonCode": season,
                "fieldKey": field_key,
                "dateValue": lexical,
            }

        for phase_key, (start_key, end_key) in PHASE_BOUNDARIES.items():
            if start_key in validated_dates and end_key in validated_dates:
                phases[(league_id, season, phase_key)] = {
                    **response,
                    "leagueId": league_id,
                    "seasonCode": season,
                    "phaseKey": phase_key,
                }

    for index, raw_record in enumerate(raw_records):
        path = f"$.leagues[{index}]"
        record = _object(raw_record, path)
        root_id = add_organization("league", record, path, required=True)
        assert root_id is not None
        _validate_sport(record, path)
        _season_code(record.get("season"), f"{path}.season")
        divisions = record.get("divisions")
        if divisions is not None:
            if not isinstance(divisions, list):
                raise ContractError(f"{path}.divisions must be an array or null")
            for division_index, division in enumerate(divisions):
                add_organization(
                    "division",
                    division,
                    f"{path}.divisions[{division_index}]",
                    required=True,
                )
        add_season(root_id, record, path)

    organization_rows = sorted(
        organizations.values(),
        key=lambda item: (item["entityKind"], int(item["entityId"])),
    )
    season_rows = sorted(
        seasons.values(), key=lambda item: (int(item["leagueId"]), item["seasonCode"])
    )
    date_rows = sorted(
        dates.values(),
        key=lambda item: (
            int(item["leagueId"]),
            item["seasonCode"],
            item["fieldKey"],
        ),
    )
    phase_rows = sorted(
        phases.values(),
        key=lambda item: (
            int(item["leagueId"]),
            item["seasonCode"],
            item["phaseKey"],
        ),
    )
    return {
        "_baseballO": {
            "contextVersion": CONTEXT_VERSION,
            "sourceModule": "mlb-leagues",
            "inputValidation": "passed",
            "counts": {
                "organizations": len(organization_rows),
                "seasons": len(season_rows),
                "phases": len(phase_rows),
                "dates": len(date_rows),
            },
        },
        "responseRecords": [response],
        "organizationRecords": organization_rows,
        "seasonRecords": season_rows,
        "phaseRecords": phase_rows,
        "dateRecords": date_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate transient MLB leagues JSON and build RML context."
    )
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_context", type=Path)
    parser.add_argument(
        "--endpoint-family", choices=sorted(ENDPOINT_KINDS), required=True
    )
    parser.add_argument(
        "--request-scope",
        required=True,
        help="Exact request URI or persistent acquisition-scope identifier.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.request_scope:
        raise ContractError("--request-scope must not be empty")
    input_path = args.input_json.resolve()
    output_path = args.output_context.resolve()
    if not input_path.is_file():
        raise ContractError(f"input JSON does not exist: {input_path}")
    if input_path == output_path:
        raise ContractError("execution context must not overwrite the raw input")

    raw = input_path.read_bytes()
    response_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ContractError("input JSON is not strict UTF-8") from error
    payload = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    if not isinstance(payload, dict):
        raise ContractError("root JSON value must be an object")

    context = build_context(
        payload,
        endpoint_family=args.endpoint_family,
        request_scope=args.request_scope,
        response_sha256=response_sha256,
    )
    serialized = json.dumps(
        context, indent=2, ensure_ascii=False, sort_keys=True
    ) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(serialized)
        os.replace(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    counts = context["_baseballO"]["counts"]
    print(
        json.dumps(
            {
                "status": "validated",
                "sourceModule": "mlb-leagues",
                "endpointFamily": args.endpoint_family,
                "responseSha256": response_sha256,
                "counts": counts,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, json.JSONDecodeError) as error:
        print(f"mlb-leagues input rejected: {error}", file=sys.stderr)
        raise SystemExit(2)
