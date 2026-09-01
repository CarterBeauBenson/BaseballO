#!/usr/bin/env python3
"""Validate an MLB venues response and build a transient RML execution context."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


CONTEXT_KEY = "_baseballO"
DIMENSION_SELECTORS = (
    "leftLine",
    "leftCenter",
    "center",
    "rightCenter",
    "rightLine",
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEASON = re.compile(r"^[0-9]{4}$")
SURFACE_TYPES = {"Grass", "Artificial Turf"}
ROOF_TYPES = {"Open", "Dome", "Retractable"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one official MLB venues response without changing its bytes, "
            "then add an execution-only _baseballO context for RMLMapper."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--requested-season", required=True)
    parser.add_argument(
        "--expected-sha256",
        help="Optional exact-byte SHA-256 from the NiFi acquisition manifest.",
    )
    return parser.parse_args()


def reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON numeric constant is not allowed: {value}")


def normalized_season(value: object, label: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a four-digit season, got {value!r}")
    rendered = str(value)
    if not SEASON.fullmatch(rendered):
        raise ValueError(f"{label} must be a four-digit season, got {value!r}")
    return rendered


def normalized_venue_id(value: object, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive JSON integer, got {value!r}")
    return str(value)


def normalized_positive_decimal(value: object, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive JSON number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be finite, got {value!r}")
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{label} is not a decimal number: {value!r}") from error
    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"{label} must be greater than zero, got {value!r}")
    rendered = format(decimal_value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def normalized_decimal_in_range(
    value: object, label: str, minimum: Decimal, maximum: Decimal
) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a JSON number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be finite, got {value!r}")
    decimal_value = Decimal(str(value))
    if not decimal_value.is_finite() or not minimum <= decimal_value <= maximum:
        raise ValueError(f"{label} must be in [{minimum},{maximum}], got {value!r}")
    rendered = format(decimal_value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def normalized_positive_integer(value: object, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive JSON integer, got {value!r}")
    return str(value)


def exact_code(value: object, label: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} must be one of {sorted(allowed)!r}, got {value!r}")
    return value


def exact_lexical_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def response_records(
    document: dict[str, Any], requested_season: str, response_sha256: str
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    venues = document.get("venues")
    if not isinstance(venues, list) or not venues:
        raise ValueError("Official venue response must contain a nonempty venues array")

    venue_records: list[dict[str, str]] = []
    name_records: list[dict[str, str]] = []
    dimension_records: list[dict[str, str]] = []
    coordinate_records: list[dict[str, str]] = []
    capacity_records: list[dict[str, str]] = []
    surface_records: list[dict[str, str]] = []
    roof_records: list[dict[str, str]] = []
    open_roof_records: list[dict[str, str]] = []
    seen_venue_ids: set[str] = set()

    for position, venue in enumerate(venues):
        if not isinstance(venue, dict):
            raise ValueError(f"venues[{position}] must be a JSON object")
        if CONTEXT_KEY in venue:
            raise ValueError(
                f"venues[{position}] already contains reserved key {CONTEXT_KEY!r}"
            )
        venue_id = normalized_venue_id(venue.get("id"), f"venues[{position}].id")
        if venue_id in seen_venue_ids:
            raise ValueError(f"Venue response repeats MLB venue id {venue_id}")
        seen_venue_ids.add(venue_id)

        response_season = venue.get("season")
        if response_season is not None:
            normalized_response_season = normalized_season(
                response_season, f"venues[{position}].season"
            )
            if normalized_response_season != requested_season:
                raise ValueError(
                    f"venues[{position}].season {normalized_response_season} does not "
                    f"match requested season {requested_season}"
                )

        common = {
            "venueId": venue_id,
            "requestedSeason": requested_season,
            "responseSha256": response_sha256,
        }
        venue_records.append(dict(common))

        name = venue.get("name")
        if name is not None:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    f"venues[{position}].name must be a nonempty string or null"
                )
            name_records.append(
                {
                    **common,
                    "name": name,
                    "nameLexicalSha256": exact_lexical_sha256(name),
                }
            )

        location = venue.get("location")
        if location is not None:
            if not isinstance(location, dict):
                raise ValueError(f"venues[{position}].location must be an object or null")
            coordinates = location.get("defaultCoordinates")
            if coordinates is not None:
                if not isinstance(coordinates, dict):
                    raise ValueError(
                        f"venues[{position}].location.defaultCoordinates must be an object or null"
                    )
                latitude_present = coordinates.get("latitude") is not None
                longitude_present = coordinates.get("longitude") is not None
                if latitude_present != longitude_present:
                    raise ValueError(
                        f"venues[{position}].location.defaultCoordinates must contain a complete pair"
                    )
                if latitude_present:
                    coordinate_records.append(
                        {
                            **common,
                            "latitude": normalized_decimal_in_range(
                                coordinates["latitude"],
                                f"venues[{position}].location.defaultCoordinates.latitude",
                                Decimal("-90"),
                                Decimal("90"),
                            ),
                            "longitude": normalized_decimal_in_range(
                                coordinates["longitude"],
                                f"venues[{position}].location.defaultCoordinates.longitude",
                                Decimal("-180"),
                                Decimal("180"),
                            ),
                        }
                    )

        field_info = venue.get("fieldInfo")
        if field_info is None:
            continue
        if not isinstance(field_info, dict):
            raise ValueError(f"venues[{position}].fieldInfo must be an object or null")
        if field_info.get("capacity") is not None:
            capacity_records.append(
                {
                    **common,
                    "capacity": normalized_positive_integer(
                        field_info["capacity"], f"venues[{position}].fieldInfo.capacity"
                    ),
                }
            )
        if field_info.get("turfType") is not None:
            surface_type = exact_code(
                field_info["turfType"],
                f"venues[{position}].fieldInfo.turfType",
                SURFACE_TYPES,
            )
            surface_records.append(
                {
                    **common,
                    "surfaceType": surface_type,
                    "surfaceTypeToken": surface_type.lower().replace(" ", "-"),
                }
            )
        if field_info.get("roofType") is not None:
            roof_type = exact_code(
                field_info["roofType"],
                f"venues[{position}].fieldInfo.roofType",
                ROOF_TYPES,
            )
            destination = open_roof_records if roof_type == "Open" else roof_records
            destination.append(
                {
                    **common,
                    "roofType": roof_type,
                    "roofTypeToken": roof_type.lower(),
                }
            )
        for selector in DIMENSION_SELECTORS:
            if selector not in field_info or field_info[selector] is None:
                continue
            decimal_value = normalized_positive_decimal(
                field_info[selector],
                f"venues[{position}].fieldInfo.{selector}",
            )
            dimension_records.append(
                {
                    **common,
                    "selector": selector,
                    "decimalValue": decimal_value,
                }
            )

    return (
        venue_records,
        name_records,
        dimension_records,
        coordinate_records,
        capacity_records,
        surface_records,
        roof_records,
        open_roof_records,
    )


def write_context(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise ValueError(f"Venue response does not exist: {source}")
    if source == output:
        raise ValueError("Execution context output must not overwrite source bytes")

    requested_season = normalized_season(args.requested_season, "requested season")
    source_bytes = source.read_bytes()
    response_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if args.expected_sha256 is not None:
        expected = args.expected_sha256.lower()
        if not SHA256.fullmatch(expected):
            raise ValueError("--expected-sha256 must contain 64 lowercase hex digits")
        if response_sha256 != expected:
            raise ValueError(
                "Venue response SHA-256 differs from the acquisition manifest"
            )

    try:
        document = json.loads(
            source_bytes.decode("utf-8"), parse_constant=reject_nonstandard_json_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Venue response is not strict UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("Official venue response root must be a JSON object")
    if CONTEXT_KEY in document:
        raise ValueError(f"Source root already contains reserved key {CONTEXT_KEY!r}")

    (
        venue_records,
        name_records,
        dimension_records,
        coordinate_records,
        capacity_records,
        surface_records,
        roof_records,
        open_roof_records,
    ) = response_records(document, requested_season, response_sha256)
    context = dict(document)
    context[CONTEXT_KEY] = {
        "contractVersion": 1,
        "requestedSeason": requested_season,
        "responseSha256": response_sha256,
        "venueRecords": venue_records,
        "nameRecords": name_records,
        "dimensionRecords": dimension_records,
        "coordinateRecords": coordinate_records,
        "capacityRecords": capacity_records,
        "surfaceRecords": surface_records,
        "roofRecords": roof_records,
        "openRoofRecords": open_roof_records,
    }
    write_context(output, context)

    print(
        json.dumps(
            {
                "artifactType": "baseballo-mlb-venues-rml-context-summary",
                "contractVersion": 1,
                "responseSha256": response_sha256,
                "venueCount": len(venue_records),
                "nameCount": len(name_records),
                "dimensionCount": len(dimension_records),
                "coordinateCount": len(coordinate_records),
                "capacityCount": len(capacity_records),
                "surfaceCount": len(surface_records),
                "roofCount": len(roof_records),
                "openRoofCount": len(open_roof_records),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
