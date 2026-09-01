#!/usr/bin/env python3
"""Validate one transient MLB people response and build RML execution context."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any


DATA = "https://baseballontology.org/data/"
HEIGHT = re.compile(r"^(?P<feet>[0-9]+)' (?P<inches>[0-9]{1,2})\"$")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
POSITIVE_ID = re.compile(r"^[1-9][0-9]*$")
RESOURCE_KINDS = {"player", "person"}
SIDE_CODES = {"L": ("left",), "R": ("right",), "S": ("left", "right")}
POSITION_TUPLES = {
    "1": ("Pitcher", "Pitcher", "P", "pitcher"),
    "2": ("Catcher", "Catcher", "C", "catcher"),
    "3": ("First Base", "Infielder", "1B", "fielder"),
    "4": ("Second Base", "Infielder", "2B", "fielder"),
    "5": ("Third Base", "Infielder", "3B", "fielder"),
    "6": ("Shortstop", "Infielder", "SS", "fielder"),
    "7": ("Outfielder", "Outfielder", "LF", "fielder"),
    "8": ("Outfielder", "Outfielder", "CF", "fielder"),
    "9": ("Outfielder", "Outfielder", "RF", "fielder"),
    "10": ("Designated Hitter", "Hitter", "DH", "designated-hitter"),
    "Y": ("Two-Way Player", "Two-Way Player", "TWP", "two-way"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def require_person_id(value: Any, field: str) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive MLB integer identifier")
    lexical = str(value) if isinstance(value, (int, str)) else ""
    if not POSITIVE_ID.fullmatch(lexical):
        raise ValueError(f"{field} must be a positive MLB integer identifier")
    return str(int(lexical))


def optional_text(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Present {field} must be a non-empty string")
    if "\ufffd" in value:
        raise ValueError(f"Present {field} contains a Unicode replacement character")
    return value


def optional_date(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise ValueError(f"Present {field} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Present {field} is not a valid calendar date") from error
    if parsed.isoformat() != value:
        raise ValueError(f"Present {field} is not canonical YYYY-MM-DD")
    return value


def optional_height(record: dict[str, Any]) -> str | None:
    value = record.get("height")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Present height must be a feet/inches string")
    match = HEIGHT.fullmatch(value)
    if match is None:
        raise ValueError("Present height must match the reviewed feet/inches grammar")
    feet = int(match.group("feet"))
    inches = int(match.group("inches"))
    if inches >= 12:
        raise ValueError("Present height inches component must be less than 12")
    total_inches = (12 * feet) + inches
    if total_inches <= 0:
        raise ValueError("Present height must compute to strictly positive inches")
    return str(total_inches)


def optional_positive_integer(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Present {field} must be a positive JSON integer")
    return str(value)


def optional_side(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Present {field} must be an object")
    code = value.get("code")
    if not isinstance(code, str) or code not in SIDE_CODES:
        raise ValueError(f"Present {field}.code must be exactly L, R, or S")
    return code


def optional_position(record: dict[str, Any]) -> tuple[str, str] | None:
    value = record.get("primaryPosition")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Present primaryPosition must be an object")
    code = value.get("code")
    if not isinstance(code, str) or code not in POSITION_TUPLES:
        raise ValueError("Present primaryPosition.code is not in the reviewed position table")
    expected_name, expected_type, expected_abbreviation, concept = POSITION_TUPLES[code]
    actual = (value.get("name"), value.get("type"), value.get("abbreviation"))
    expected = (expected_name, expected_type, expected_abbreviation)
    if actual != expected:
        raise ValueError(
            f"Present primaryPosition tuple {actual!r} does not match code {code} {expected!r}"
        )
    return code, concept


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--resource-kind", required=True, choices=sorted(RESOURCE_KINDS))
    parser.add_argument("--expected-person-id")
    parser.add_argument("--request-scope")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise ValueError(f"MLB people response is missing: {input_path}")
    if input_path == output_path:
        raise ValueError("Refusing to overwrite the transient MLB people response")
    raw = input_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("MLB people response is not valid UTF-8") from error
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"MLB people response is not valid JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("MLB people response root must be an object")
    people = document.get("people")
    if not isinstance(people, list) or len(people) != 1 or not isinstance(people[0], dict):
        raise ValueError("MLB people proof lane requires exactly one people record")
    record = people[0]
    if "_baseballO" in document or "_baseballO" in record:
        raise ValueError("Source payload uses reserved _baseballO context key")

    person_id = require_person_id(record.get("id"), "people[0].id")
    if args.expected_person_id is not None:
        expected = require_person_id(args.expected_person_id, "expected person id")
        if person_id != expected:
            raise ValueError(f"Response person id {person_id} differs from request seed {expected}")
    resource_kind = args.resource_kind
    person_iri = f"{DATA}{resource_kind}/{person_id}"
    response_sha = sha256_bytes(raw)
    request_scope = args.request_scope or f"mlb-people:{resource_kind}:{person_id}"
    if not request_scope.strip():
        raise ValueError("Request scope must be non-empty")
    request_scope_sha = sha256_text(request_scope)
    response_iri = f"{DATA}source/mlb-people/response/{request_scope_sha}/{response_sha}"

    full_name = optional_text(record, "fullName")
    nickname = optional_text(record, "nickName")
    total_inches = optional_height(record)
    birth_date = optional_date(record, "birthDate")
    weight_pounds = optional_positive_integer(record, "weight")
    batting_code = optional_side(record, "batSide")
    throwing_code = optional_side(record, "pitchHand")
    position = optional_position(record)
    current_team_id = None
    if record.get("currentTeam") is not None:
        if not isinstance(record["currentTeam"], dict):
            raise ValueError("Present currentTeam must be an object")
        current_team_id = require_person_id(record["currentTeam"].get("id"), "currentTeam.id")

    identifier_iri = f"{person_iri}/identifier/mlb-person-id"
    context: dict[str, Any] = {
        "records": [
            {
                "personId": person_id,
                "personIri": person_iri,
                "responseIri": response_iri,
                "responseSha256": response_sha,
                "requestScopeSha256": request_scope_sha,
                "identifierIri": identifier_iri,
            }
        ],
        "fullNames": [],
        "nicknames": [],
        "heightMeasurements": [],
        "massMeasurements": [],
        "battingDispositions": [],
        "throwingDispositions": [],
        "positionRecords": [],
        "pitcherPositionRecords": [],
        "catcherPositionRecords": [],
        "fielderPositionRecords": [],
        "designatedHitterPositionRecords": [],
        "twoWayPositionRecords": [],
        "positionBattingSideRecords": [],
        "positionThrowingSideRecords": [],
        "currentTeamAboutness": [],
        "birthEvidence": [],
    }
    if full_name is not None:
        context["fullNames"].append(
            {
                "personIri": person_iri,
                "responseIri": response_iri,
                "nameIri": f"{person_iri}/name/mlb-full/{sha256_text(full_name)}",
                "text": full_name,
            }
        )
    if nickname is not None:
        context["nicknames"].append(
            {
                "personIri": person_iri,
                "responseIri": response_iri,
                "nameIri": f"{person_iri}/name/mlb-nickname/{sha256_text(nickname)}",
                "text": nickname,
            }
        )
    if total_inches is not None:
        context["heightMeasurements"].append(
            {
                "personIri": person_iri,
                "responseIri": response_iri,
                "heightIri": f"{person_iri}/quality/height",
                "measurementIri": f"{person_iri}/measurement/height/{response_sha}",
                "totalInches": total_inches,
            }
        )
    if weight_pounds is not None:
        context["massMeasurements"].append(
            {
                "personIri": person_iri,
                "responseIri": response_iri,
                "massIri": f"{person_iri}/quality/mass",
                "measurementIri": f"{person_iri}/measurement/mass/{response_sha}",
                "pounds": weight_pounds,
            }
        )

    def add_side(kind: str, code: str | None) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        if code is None:
            return rows
        for side in SIDE_CODES[code]:
            disposition_iri = f"{person_iri}/disposition/{kind}-side/{side}"
            rows.append(
                {
                    "personIri": person_iri,
                    "responseIri": response_iri,
                    "dispositionIri": disposition_iri,
                    "measurementIri": (
                        f"{person_iri}/measurement/{kind}-side/{side}/{response_sha}"
                    ),
                    "sourceCode": code,
                    "side": side,
                }
            )
        return rows

    batting_rows = add_side("batting", batting_code)
    throwing_rows = add_side("throwing", throwing_code)
    context["battingDispositions"].extend(batting_rows)
    context["throwingDispositions"].extend(throwing_rows)

    if position is not None:
        position_code, position_concept = position
        description_iri = (
            f"{person_iri}/description/baseball-position/{position_code}/{response_sha}"
        )
        position_row = {
            "personIri": person_iri,
            "responseIri": response_iri,
            "descriptionIri": description_iri,
            "positionCode": position_code,
            "positionConcept": position_concept,
        }
        context["positionRecords"].append(position_row)
        if position_concept == "pitcher":
            context["pitcherPositionRecords"].append(
                {**position_row, "roleIri": f"{person_iri}/role/pitcher"}
            )
        elif position_concept == "catcher":
            context["catcherPositionRecords"].append(
                {
                    **position_row,
                    "roleIri": f"{person_iri}/role/catcher",
                    "fieldingDispositionIri": (
                        f"{person_iri}/disposition/fielding/{position_code}"
                    ),
                }
            )
        elif position_concept == "fielder":
            context["fielderPositionRecords"].append(
                {
                    **position_row,
                    "roleIri": f"{person_iri}/role/fielder",
                    "fieldingDispositionIri": (
                        f"{person_iri}/disposition/fielding/{position_code}"
                    ),
                }
            )
        elif position_concept == "two-way":
            context["twoWayPositionRecords"].append(
                {
                    **position_row,
                    "pitcherRoleIri": f"{person_iri}/role/pitcher",
                    "fielderRoleIri": f"{person_iri}/role/fielder",
                }
            )
        else:
            context["designatedHitterPositionRecords"].append(
                {**position_row, "roleIri": f"{person_iri}/role/batter"}
            )
        if position_concept in {"catcher", "fielder", "pitcher", "two-way"}:
            context["positionThrowingSideRecords"].extend(
                {**position_row, "dispositionIri": row["dispositionIri"]}
                for row in throwing_rows
            )
        if position_concept == "designated-hitter":
            context["positionBattingSideRecords"].extend(
                {**position_row, "dispositionIri": row["dispositionIri"]}
                for row in batting_rows
            )

    if current_team_id is not None:
        context["currentTeamAboutness"].append(
            {
                "responseIri": response_iri,
                "teamIri": f"{DATA}team/{current_team_id}",
            }
        )
    if birth_date is not None:
        context["birthEvidence"].append(
            {
                "personIri": person_iri,
                "responseIri": response_iri,
                "birthIri": f"{person_iri}/birth",
                "dateIdentifierIri": (
                    f"{person_iri}/identifier/birth-date/{birth_date}/{response_sha}"
                ),
                "dayIri": f"{DATA}day/{birth_date}",
                "date": birth_date,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".partial",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            json.dump(context, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
