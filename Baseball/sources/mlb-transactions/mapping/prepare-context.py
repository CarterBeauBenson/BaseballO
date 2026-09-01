#!/usr/bin/env python3
"""Validate MLB transaction inputs and build an isolated RML execution context.

The authoritative API bytes are read-only. This program validates every source
fact needed by the accepted mapping before RML, then emits a deterministic
context whose helper fields contain only structural IRIs and identity hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DATA = "https://baseballontology.org/data/"
SOURCE = f"{DATA}source/mlb-transactions/"
REFERENCE_SYSTEMS = {
    "transactionIdentifier": f"{SOURCE}reference-system/transaction-identifier",
    "transactionType": f"{SOURCE}reference-system/transaction-type",
    "fieldKey": f"{SOURCE}reference-system/field-key",
}
SELECTED_MEMBERS = (
    "id",
    "personId",
    "fromTeamId",
    "toTeamId",
    "date",
    "effectiveDate",
    "resolutionDate",
    "typeCode",
    "typeDesc",
    "description",
)
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FIELD_KEYS = ("date", "effectiveDate", "resolutionDate")
TRADE_CODE = "TR"
SIGNING_CODES = {"SGN", "SFA"}


class InputContractError(ValueError):
    """A transient source input failed the accepted pre-mapping contract."""


@dataclass(frozen=True)
class LoadedJson:
    path: Path
    document: Any
    raw_sha256: str


@dataclass(frozen=True)
class DeathRule:
    code: str
    description: str
    pin_sha256: str
    decision_artifact: str
    decision_sha256: str


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputContractError(f"JSON object repeats key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise InputContractError(f"JSON contains non-finite number token {value!r}")


def load_json(path: Path, label: str) -> LoadedJson:
    resolved = path.resolve()
    if not resolved.is_file():
        raise InputContractError(f"{label} does not exist: {resolved}")
    raw = resolved.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InputContractError(f"{label} is not UTF-8: {resolved}") from error
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (json.JSONDecodeError, InputContractError) as error:
        raise InputContractError(f"{label} is invalid JSON: {error}") from error
    return LoadedJson(resolved, document, digest)


def _validate_unicode(value: str, path: str) -> str:
    if "\ufffd" in value:
        raise InputContractError(
            f"{path} contains the Unicode replacement character; quarantine the bytes"
        )
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise InputContractError(f"{path} contains an unpaired Unicode surrogate")
    return value


def _required_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise InputContractError(f"{path} must be a non-empty string")
    return _validate_unicode(value, path)


def _optional_text(container: dict[str, Any], key: str, path: str) -> str | None:
    if key not in container or container[key] is None:
        return None
    return _required_text(container[key], f"{path}.{key}")


def _positive_integer(value: Any, path: str) -> int:
    if type(value) is not int or value <= 0:  # bool is deliberately excluded
        raise InputContractError(f"{path} must be a positive JSON integer")
    return value


def _source_date(value: Any, path: str) -> str:
    text = _required_text(value, path)
    if not DATE_PATTERN.fullmatch(text):
        raise InputContractError(f"{path} must use YYYY-MM-DD lexical form")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise InputContractError(f"{path} is not a real calendar date: {text}") from error
    if parsed.isoformat() != text:
        raise InputContractError(f"{path} is not in canonical YYYY-MM-DD form")
    return text


def _optional_reference(
    row: dict[str, Any], key: str, row_path: str, diagnostic_name: str
) -> int | None:
    if key not in row or row[key] is None:
        return None
    reference = row[key]
    if not isinstance(reference, dict):
        raise InputContractError(f"{row_path}.{key} must be an object or null")
    identifier = _positive_integer(reference.get("id"), f"{row_path}.{key}.id")
    if diagnostic_name in reference and reference[diagnostic_name] is not None:
        _required_text(
            reference[diagnostic_name], f"{row_path}.{key}.{diagnostic_name}"
        )
    return identifier


def extract_code_list(document: Any) -> dict[str, str]:
    if isinstance(document, list):
        entries = document
    elif isinstance(document, dict) and isinstance(
        document.get("transactionTypes"), list
    ):
        entries = document["transactionTypes"]
    else:
        raise InputContractError(
            "transactionTypes input must be a bare array or an object with a "
            "transactionTypes array"
        )

    code_map: dict[str, str] = {}
    for index, entry in enumerate(entries):
        path = f"transactionTypes[{index}]"
        if not isinstance(entry, dict):
            raise InputContractError(f"{path} must be an object")
        code = _required_text(entry.get("code"), f"{path}.code")
        description = _required_text(
            entry.get("description"), f"{path}.description"
        )
        if code in code_map:
            raise InputContractError(f"transactionTypes repeats code {code!r}")
        code_map[code] = description
    if not code_map:
        raise InputContractError("transactionTypes contains no code entries")
    return code_map


def _canonical_semantic_sha256(path: Path) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InputContractError(f"review artifact is not UTF-8: {path}") from error
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_death_rule(
    pin_path: Path | None,
    code_list: LoadedJson,
    code_map: dict[str, str],
) -> DeathRule | None:
    if pin_path is None:
        return None

    pin = load_json(pin_path, "Death-code pin")
    module_root = Path(__file__).resolve().parents[1]
    repository_root = Path(__file__).resolve().parents[4]
    if not pin.path.is_relative_to(module_root):
        raise InputContractError("Death-code pin must reside inside mlb-transactions")
    value = pin.document
    required = {
        "artifactType",
        "contractVersion",
        "codeListSha256",
        "deathCode",
        "deathDescription",
        "decisionArtifact",
        "decisionSha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise InputContractError(
            "Death-code pin must contain exactly the reviewed pin fields"
        )
    if value["artifactType"] != "baseballo-mlb-transactions-death-code-pin":
        raise InputContractError("Death-code pin has the wrong artifactType")
    if value["contractVersion"] != 1:
        raise InputContractError("Death-code pin has an unsupported contractVersion")
    if value["codeListSha256"] != code_list.raw_sha256:
        raise InputContractError(
            "Death-code pin does not match the acquired transactionTypes bytes"
        )
    code = _required_text(value["deathCode"], "deathCodePin.deathCode")
    description = _required_text(
        value["deathDescription"], "deathCodePin.deathDescription"
    )
    if description != "Death" or code_map.get(code) != description:
        raise InputContractError(
            "Death-code pin must match an exact code/Death pair in transactionTypes"
        )

    decision_artifact = _required_text(
        value["decisionArtifact"], "deathCodePin.decisionArtifact"
    )
    decision_sha256 = _required_text(
        value["decisionSha256"], "deathCodePin.decisionSha256"
    )
    if not SHA256_PATTERN.fullmatch(decision_sha256):
        raise InputContractError("Death-code decisionSha256 is not lowercase SHA-256")
    decision_relative = Path(decision_artifact)
    if decision_relative.is_absolute() or ".." in decision_relative.parts:
        raise InputContractError(
            "Death-code decisionArtifact must be a repository-relative path"
        )
    decision_path = (repository_root / decision_relative).resolve()
    archive_root = (repository_root / "Baseball" / "archive" / "design-records").resolve()
    if not decision_path.is_file() or not decision_path.is_relative_to(archive_root):
        raise InputContractError(
            "Death-code decisionArtifact must be an archived review.json"
        )
    if decision_path.name != "review.json":
        raise InputContractError("Death-code decisionArtifact must name review.json")
    if _canonical_semantic_sha256(decision_path) != decision_sha256:
        raise InputContractError("Death-code decision artifact hash does not match")
    decision = load_json(decision_path, "Death-code decision").document
    if (
        not isinstance(decision, dict)
        or decision.get("artifactType") != "baseballo-semantic-proposal-review"
        or decision.get("status") != "accepted"
        or not isinstance(decision.get("ontologistDecision"), dict)
        or decision["ontologistDecision"].get("disposition") != "accepted"
        or decision["ontologistDecision"].get("decidedBy") != "Carter Beau Benson"
    ):
        raise InputContractError("Death-code decision is not an accepted ontologist review")
    pin_git_path = pin.path.relative_to(repository_root).as_posix()
    authorized = decision["ontologistDecision"].get("authorizedArtifacts", [])
    if pin_git_path not in authorized:
        raise InputContractError(
            "Accepted Death-code decision does not authorize this pin artifact"
        )
    return DeathRule(
        code=code,
        description=description,
        pin_sha256=pin.raw_sha256,
        decision_artifact=decision_artifact,
        decision_sha256=decision_sha256,
    )


def canonical_selected_content(value: dict[str, Any]) -> str:
    if tuple(value.keys()) != SELECTED_MEMBERS:
        raise InputContractError("internal selected-content member order changed")
    # All keys are ASCII and all values are integers, strings, or null. In this
    # restricted domain, this is the RFC 8785 serialization without floats.
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(value: str) -> str:
    try:
        payload = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InputContractError("selected content is not valid Unicode") from error
    return hashlib.sha256(payload).hexdigest()


def _date_record(row_iri: str, field_key: str, value: str) -> dict[str, str]:
    if field_key not in FIELD_KEYS:
        raise InputContractError(f"internal unsupported date field {field_key}")
    date_iri = f"{row_iri}/date/{field_key}"
    return {
        "rowIri": row_iri,
        "dateIdentifierIri": date_iri,
        "dateValue": value,
        "dayIri": f"{DATA}day/{value}",
        "fieldKeyIdentifierIri": f"{date_iri}/field-key",
        "fieldKeyText": field_key,
    }


def build_context(
    transactions_document: Any,
    transactions_sha256: str,
    code_map: dict[str, str],
    code_list_sha256: str,
    death_rule: DeathRule | None,
) -> dict[str, Any]:
    if not isinstance(transactions_document, dict) or not isinstance(
        transactions_document.get("transactions"), list
    ):
        raise InputContractError(
            "transactions input must be an object with a transactions array"
        )

    groups: dict[str, dict[str, str]] = {}
    rows: dict[str, dict[str, str]] = {}
    canonical_by_hash: dict[str, str] = {}
    aboutness: set[tuple[str, str]] = set()
    descriptions: dict[str, dict[str, str]] = {}
    dates: dict[str, dict[str, str]] = {}
    deaths: dict[str, dict[str, str]] = {}
    world_rows: list[dict[str, Any]] = []

    source_rows = transactions_document["transactions"]
    for index, source_row in enumerate(source_rows):
        row_path = f"transactions[{index}]"
        if not isinstance(source_row, dict):
            raise InputContractError(f"{row_path} must be an object")
        transaction_id = _positive_integer(source_row.get("id"), f"{row_path}.id")
        person_id = _optional_reference(source_row, "person", row_path, "fullName")
        from_team_id = _optional_reference(source_row, "fromTeam", row_path, "name")
        to_team_id = _optional_reference(source_row, "toTeam", row_path, "name")
        transaction_date = _source_date(source_row.get("date"), f"{row_path}.date")
        effective_date = _source_date(
            source_row.get("effectiveDate"), f"{row_path}.effectiveDate"
        )
        resolution_date = None
        if "resolutionDate" in source_row and source_row["resolutionDate"] is not None:
            resolution_date = _source_date(
                source_row["resolutionDate"], f"{row_path}.resolutionDate"
            )
        type_code = _required_text(source_row.get("typeCode"), f"{row_path}.typeCode")
        type_description = _required_text(
            source_row.get("typeDesc"), f"{row_path}.typeDesc"
        )
        if type_code not in code_map:
            raise InputContractError(
                f"{row_path}.typeCode {type_code!r} is absent from transactionTypes"
            )
        if code_map[type_code] != type_description:
            raise InputContractError(
                f"{row_path}.typeDesc does not match transactionTypes[{type_code!r}]"
            )
        description = _optional_text(source_row, "description", row_path)

        selected = {
            "id": transaction_id,
            "personId": person_id,
            "fromTeamId": from_team_id,
            "toTeamId": to_team_id,
            "date": transaction_date,
            "effectiveDate": effective_date,
            "resolutionDate": resolution_date,
            "typeCode": type_code,
            "typeDesc": type_description,
            "description": description,
        }
        canonical = canonical_selected_content(selected)
        row_hash = _sha256_text(canonical)
        previous = canonical_by_hash.get(row_hash)
        if previous is not None and previous != canonical:
            raise InputContractError("SHA-256 collision across transaction row content")
        canonical_by_hash[row_hash] = canonical

        group_iri = f"{SOURCE}group/{transaction_id}"
        row_iri = f"{SOURCE}row/{row_hash}"
        groups[group_iri] = {
            "groupIri": group_iri,
            "transactionIdentifierIri": f"{group_iri}/identifier/mlb-transaction-id",
            "transactionIdText": str(transaction_id),
        }
        rows[row_iri] = {
            "groupIri": group_iri,
            "rowIri": row_iri,
            "rowSha256": row_hash,
            "typeIri": f"{row_iri}/type",
            "typeCode": type_code,
        }
        world_rows.append(
            {
                "transactionId": transaction_id,
                "groupIri": group_iri,
                "rowIri": row_iri,
                "rowSha256": row_hash,
                "personId": person_id,
                "fromTeamId": from_team_id,
                "toTeamId": to_team_id,
                "effectiveDate": effective_date,
                "typeCode": type_code,
            }
        )

        for entity_iri in (
            None if person_id is None else f"{DATA}player/{person_id}",
            None if from_team_id is None else f"{DATA}team/{from_team_id}",
            None if to_team_id is None else f"{DATA}team/{to_team_id}",
        ):
            if entity_iri is not None:
                aboutness.add((row_iri, entity_iri))

        if description is not None:
            description_iri = f"{row_iri}/description"
            descriptions[description_iri] = {
                "rowIri": row_iri,
                "descriptionIri": description_iri,
                "descriptionText": description,
            }

        for field_key, date_value in (
            ("date", transaction_date),
            ("effectiveDate", effective_date),
            ("resolutionDate", resolution_date),
        ):
            if date_value is not None:
                record = _date_record(row_iri, field_key, date_value)
                dates[record["dateIdentifierIri"]] = record

        if (
            death_rule is not None
            and type_code == death_rule.code
            and type_description == death_rule.description
            and person_id is not None
        ):
            death_iri = f"{row_iri}/process/death"
            deaths[death_iri] = {
                "rowIri": row_iri,
                "deathIri": death_iri,
                "personIri": f"{DATA}player/{person_id}",
            }

    trades: dict[str, dict[str, str]] = {}
    trade_agents: dict[tuple[str, str], dict[str, str]] = {}
    trade_legs: dict[str, dict[str, str]] = {}
    rows_by_group: dict[str, list[dict[str, Any]]] = {}
    for item in world_rows:
        rows_by_group.setdefault(item["groupIri"], []).append(item)
    for group_iri, members in rows_by_group.items():
        if not members or any(member["typeCode"] != TRADE_CODE for member in members):
            continue
        if any(
            member["personId"] is None
            or member["fromTeamId"] is None
            or member["toTeamId"] is None
            or member["fromTeamId"] == member["toTeamId"]
            for member in members
        ):
            continue
        effective_dates = {member["effectiveDate"] for member in members}
        if len(effective_dates) != 1:
            continue
        effective_date = next(iter(effective_dates))
        trade_iri = f"{group_iri}/act/trade"
        trades[trade_iri] = {"groupIri": group_iri, "tradeIri": trade_iri}
        for member in members:
            assert member["personId"] is not None
            assert member["fromTeamId"] is not None
            assert member["toTeamId"] is not None
            person_iri = f"{DATA}player/{member['personId']}"
            from_team_iri = f"{DATA}team/{member['fromTeamId']}"
            to_team_iri = f"{DATA}team/{member['toTeamId']}"
            for team_iri in (from_team_iri, to_team_iri):
                trade_agents[(trade_iri, team_iri)] = {
                    "tradeIri": trade_iri,
                    "teamIri": team_iri,
                }
            leg_token = member["rowSha256"]
            loss_iri = f"{trade_iri}/leg/{leg_token}/loss-of-player-role"
            gain_iri = f"{trade_iri}/leg/{leg_token}/gain-of-player-role"
            old_role_iri = (
                f"{person_iri}/team/{member['fromTeamId']}/role/player/stint/"
                f"loss/{effective_date}/transaction/{member['transactionId']}"
            )
            new_role_iri = (
                f"{person_iri}/team/{member['toTeamId']}/role/player/stint/"
                f"gain/{effective_date}/transaction/{member['transactionId']}"
            )
            trade_legs[member["rowIri"]] = {
                "rowIri": member["rowIri"],
                "tradeIri": trade_iri,
                "personIri": person_iri,
                "fromTeamIri": from_team_iri,
                "toTeamIri": to_team_iri,
                "oldRoleIri": old_role_iri,
                "newRoleIri": new_role_iri,
                "lossIri": loss_iri,
                "gainIri": gain_iri,
                "lossRegionIri": f"{loss_iri}/temporal-region",
                "gainRegionIri": f"{gain_iri}/temporal-region",
                "dayIri": f"{DATA}day/{effective_date}",
                "effectiveDate": effective_date,
            }

    signings: dict[str, dict[str, str]] = {}
    for member in world_rows:
        if (
            member["typeCode"] not in SIGNING_CODES
            or member["personId"] is None
            or member["toTeamId"] is None
        ):
            continue
        person_iri = f"{DATA}player/{member['personId']}"
        team_iri = f"{DATA}team/{member['toTeamId']}"
        effective_date = member["effectiveDate"]
        contract_iri = f"{member['rowIri']}/act/contract-formation"
        gain_iri = f"{contract_iri}/gain-of-player-role"
        role_iri = (
            f"{person_iri}/team/{member['toTeamId']}/role/player/stint/"
            f"gain/{effective_date}/transaction/{member['transactionId']}"
        )
        signings[member["rowIri"]] = {
            "rowIri": member["rowIri"],
            "contractIri": contract_iri,
            "personIri": person_iri,
            "teamIri": team_iri,
            "playerRoleIri": role_iri,
            "gainIri": gain_iri,
            "contractRegionIri": f"{contract_iri}/temporal-region",
            "gainRegionIri": f"{gain_iri}/temporal-region",
            "dayIri": f"{DATA}day/{effective_date}",
            "effectiveDate": effective_date,
            "typeCode": member["typeCode"],
        }

    def ordered(values: dict[str, dict[str, str]]) -> list[dict[str, str]]:
        return [values[key] for key in sorted(values)]

    return {
        "artifactType": "baseballo-mlb-transactions-rml-context",
        "contractVersion": 1,
        "moduleId": "mlb-transactions",
        "source": {
            "transactionsSha256": transactions_sha256,
            "transactionTypesSha256": code_list_sha256,
            "sourceRowCount": len(source_rows),
            "uniqueRowCount": len(rows),
            "deathMappingEnabled": death_rule is not None,
            "deathCodePinSha256": None if death_rule is None else death_rule.pin_sha256,
            "deathDecisionArtifact": (
                None if death_rule is None else death_rule.decision_artifact
            ),
            "deathDecisionSha256": (
                None if death_rule is None else death_rule.decision_sha256
            ),
        },
        "referenceSystems": [
            {"iri": REFERENCE_SYSTEMS["transactionIdentifier"]},
            {"iri": REFERENCE_SYSTEMS["transactionType"]},
            {"iri": REFERENCE_SYSTEMS["fieldKey"]},
        ],
        "groups": ordered(groups),
        "rows": ordered(rows),
        "aboutness": [
            {"rowIri": row_iri, "entityIri": entity_iri}
            for row_iri, entity_iri in sorted(aboutness)
        ],
        "descriptions": ordered(descriptions),
        "dates": ordered(dates),
        "deaths": ordered(deaths),
        "trades": ordered(trades),
        "tradeAgents": [trade_agents[key] for key in sorted(trade_agents)],
        "tradeLegs": ordered(trade_legs),
        "signings": ordered(signings),
    }


def _write_json(path: Path, value: Any) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    # RMLMapper 8.1.0 uses the Windows process charset while reading JSON.
    # Lossless JSON Unicode escapes prevent UTF-8 source text from becoming
    # mojibake in emitted literals. json.loads reconstructs the same code
    # points; raw API bytes and the Unicode-based row digest are unchanged.
    payload = json.dumps(value, ensure_ascii=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    os.replace(temporary, resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MLB transactions and create an RML context"
    )
    parser.add_argument("transactions", type=Path)
    parser.add_argument("transaction_types", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--death-code-pin", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    transactions = load_json(args.transactions, "transactions input")
    transaction_types = load_json(args.transaction_types, "transactionTypes input")
    output_path = args.output.resolve()
    protected_inputs = {transactions.path, transaction_types.path}
    if output_path in protected_inputs:
        raise InputContractError("execution context must not overwrite API input bytes")
    if args.manifest is not None and args.manifest.resolve() in protected_inputs:
        raise InputContractError("manifest must not overwrite API input bytes")

    code_map = extract_code_list(transaction_types.document)
    death_rule = load_death_rule(args.death_code_pin, transaction_types, code_map)
    context = build_context(
        transactions.document,
        transactions.raw_sha256,
        code_map,
        transaction_types.raw_sha256,
        death_rule,
    )
    _write_json(output_path, context)
    context_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()

    if args.manifest is not None:
        manifest = {
            "artifactType": "baseballo-mlb-transactions-context-preparation",
            "contractVersion": 1,
            "moduleId": "mlb-transactions",
            "transactionsPath": str(transactions.path),
            "transactionsSha256": transactions.raw_sha256,
            "transactionTypesPath": str(transaction_types.path),
            "transactionTypesSha256": transaction_types.raw_sha256,
            "deathCodePinPath": (
                None if args.death_code_pin is None else str(args.death_code_pin.resolve())
            ),
            "deathCodePinSha256": context["source"]["deathCodePinSha256"],
            "contextPath": str(output_path),
            "contextSha256": context_sha256,
            "sourceRowCount": context["source"]["sourceRowCount"],
            "uniqueRowCount": context["source"]["uniqueRowCount"],
            "deathRowCount": len(context["deaths"]),
            "completedAtUtc": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(args.manifest, manifest)

    print(
        "MLB transactions context: "
        f"source rows={context['source']['sourceRowCount']}; "
        f"unique rows={context['source']['uniqueRowCount']}; "
        f"death rows={len(context['deaths'])}; "
        f"sha256={context_sha256}"
    )


if __name__ == "__main__":
    try:
        main()
    except InputContractError as error:
        print(f"MLB transactions input validation failed: {error}")
        raise SystemExit(1)
