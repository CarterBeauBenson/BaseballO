#!/usr/bin/env python3
"""Plan and gate a NiFi-owned replay of retained MLB Game quarantine inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")
GAME_PK = re.compile(r"^\d+$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: object) -> datetime:
    text = re.sub(
        r"(\.\d{6})\d+(?=(?:Z|[+-]\d{2}:\d{2})$)",
        r"\1",
        str(value).replace("Z", "+00:00"),
    )
    timestamp = datetime.fromisoformat(text)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp has no timezone")
    return timestamp.astimezone(timezone.utc)


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def contained_path(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes its owned root: {resolved}") from exc
    return resolved


def validate_input(path: Path, quarantine_root: Path, expected_game_pk: str) -> dict[str, Any]:
    resolved = contained_path(path, quarantine_root, "Quarantine input")
    relative = resolved.relative_to(quarantine_root.resolve())
    if (
        len(relative.parts) != 3
        or relative.parts[0] != expected_game_pk
        or relative.name != "input.json"
        or not GAME_PK.fullmatch(expected_game_pk)
        or not resolved.is_file()
    ):
        raise ValueError(f"Invalid quarantine input identity: {resolved}")
    document = read_object(resolved)
    if str(document.get("gamePk")) != expected_game_pk:
        raise ValueError(f"Quarantine path and payload gamePk disagree: {resolved}")
    state = document.get("gameData", {}).get("status", {}).get("abstractGameState")
    if state != "Final":
        raise ValueError(f"Quarantine payload is not a final game: {resolved}")
    return document


def current_candidates(state_root: Path) -> dict[str, dict[str, str]]:
    quarantine_root = state_root.resolve() / "pipeline" / "quarantine" / "mlb-game"
    candidates: dict[str, tuple[int, dict[str, str]]] = {}
    if not quarantine_root.exists():
        return {}
    for path in quarantine_root.glob("*/*/input.json"):
        relative = path.resolve().relative_to(quarantine_root.resolve())
        game_pk = relative.parts[0]
        if not GAME_PK.fullmatch(game_pk):
            continue
        validate_input(path, quarantine_root, game_pk)
        candidate = {
            "gamePk": game_pk,
            "inputPath": str(path.resolve()),
            "inputSha256": sha256_file(path),
        }
        order = path.stat().st_mtime_ns
        if game_pk not in candidates or order > candidates[game_pk][0]:
            candidates[game_pk] = (order, candidate)
    return {game_pk: item[1] for game_pk, item in candidates.items()}


def promotions_for(state_root: Path, game_pk: str) -> list[tuple[datetime, Path, dict[str, Any]]]:
    root = (
        state_root.resolve()
        / "pipeline"
        / "evidence"
        / "nifi"
        / "game-promotion"
        / game_pk
    )
    if not root.exists():
        return []
    matches: list[tuple[datetime, Path, dict[str, Any]]] = []
    for path in root.glob("*.json"):
        try:
            value = read_object(path)
            timestamp = parse_timestamp(value["promotedAtUtc"])
            if (
                value.get("artifactType") != "baseball-nifi-game-promotion"
                or str(value.get("gamePk")) != game_pk
                or int(value.get("authoritativeTripleCount", 0)) <= 0
                or int(value.get("queryIndexTripleCount", 0)) <= 0
            ):
                continue
            matches.append((timestamp, path.resolve(), value))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return sorted(matches, key=lambda item: item[0])


def promotion_for(
    state_root: Path, game_pk: str, raw_sha256: str, not_before: datetime | None = None
) -> Path | None:
    matches = [
        item
        for item in promotions_for(state_root, game_pk)
        if item[2].get("rawSha256") == raw_sha256
        and (not_before is None or item[0] >= not_before)
    ]
    return matches[-1][1] if matches else None


def quarantine_timestamp(input_path: Path) -> datetime:
    failure_path = input_path.parent / "failure.json"
    if failure_path.is_file():
        failure = read_object(failure_path)
        try:
            return parse_timestamp(failure["quarantinedAtUtc"])
        except (KeyError, TypeError, ValueError):
            pass
    return datetime.fromtimestamp(input_path.stat().st_mtime, timezone.utc)


def replay_config(contract_path: Path) -> dict[str, Any]:
    contract = read_object(contract_path)
    if (
        contract.get("artifactType") != "baseballo-nifi-source-flow-contract"
        or contract.get("sourceModule") != "mlb-game"
    ):
        raise ValueError("Unsupported MLB Game flow contract")
    replay = contract.get("quarantineReplay")
    if not isinstance(replay, dict):
        raise ValueError("MLB Game flow contract has no quarantine replay policy")
    proof = replay.get("proofGames")
    if not isinstance(proof, list) or len(proof) != 5:
        raise ValueError("Quarantine replay must declare exactly five proof games")
    game_pks = [str(item.get("gamePk")) for item in proof if isinstance(item, dict)]
    if len(game_pks) != 5 or len(set(game_pks)) != 5 or any(
        not GAME_PK.fullmatch(game_pk) for game_pk in game_pks
    ):
        raise ValueError("Quarantine replay proof-game identities are invalid")
    return replay


def prior_certified_proof(
    state_root: Path, configured_proof_pks: list[str]
) -> Path | None:
    """Return the latest still-verifiable proof of the configured replay lane."""
    plans_root = (
        state_root.resolve() / "pipeline" / "evidence" / "nifi" / "quarantine-replay"
    )
    proof_paths = sorted(
        plans_root.glob("*/proof.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for proof_path in proof_paths:
        try:
            proof = read_object(proof_path)
            plan_path = contained_path(
                Path(str(proof["planPath"])), plans_root, "Prior replay plan"
            )
            plan = read_object(plan_path)
            if (
                proof.get("artifactType")
                != "baseballo-mlb-game-quarantine-replay-proof"
                or proof.get("contractVersion") != 1
                or plan.get("artifactType")
                != "baseballo-mlb-game-quarantine-replay-plan"
                or plan.get("contractVersion") != 1
                or plan_path.parent.name != plan.get("planId")
                or [str(item["gamePk"]) for item in plan.get("proof", [])]
                != configured_proof_pks
            ):
                continue
            created = parse_timestamp(plan["createdAtUtc"])
            recorded_promotions = {
                str(contained_path(Path(str(path)), state_root / "pipeline" / "evidence" / "nifi" / "game-promotion", "Prior proof promotion"))
                for path in proof.get("promotions", [])
            }
            if len(recorded_promotions) != len(configured_proof_pks):
                continue
            verified = []
            for item in plan["proof"]:
                promotion = promotion_for(
                    state_root,
                    str(item["gamePk"]),
                    str(item["inputSha256"]),
                    created,
                )
                if promotion is None:
                    break
                verified.append(str(promotion.resolve()))
            if len(verified) == len(configured_proof_pks) and set(verified) == recorded_promotions:
                return proof_path.resolve()
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return None


def work_record(candidate: dict[str, str], phase: str, plan_path: Path) -> dict[str, str]:
    return {
        "phase": phase,
        "gamePk": candidate["gamePk"],
        "inputPath": candidate["inputPath"],
        "inputSha256": candidate["inputSha256"],
        "planPath": str(plan_path.resolve()),
        "materializeMode": "deferred",
        "scheduleEvidencePath": "none",
        "pipelineRunId": uuid.uuid4().hex,
        "resolutionMode": "replayed-and-promoted",
        "promotionEvidence": "none",
    }


def resolution_record(
    candidate: dict[str, str],
    plan_path: Path,
    mode: str,
    promotion_evidence: Path,
) -> dict[str, str]:
    record = work_record(candidate, "resolve-existing", plan_path)
    record["resolutionMode"] = mode
    record["promotionEvidence"] = str(promotion_evidence.resolve())
    return record


def create_plan(state_root: Path, contract_path: Path) -> dict[str, Any]:
    replay = replay_config(contract_path)
    candidates = current_candidates(state_root)
    replay_candidates: dict[str, dict[str, str]] = {}
    existing_resolutions: list[tuple[dict[str, str], str, Path]] = []
    for game_pk, candidate in candidates.items():
        exact = promotion_for(state_root, game_pk, candidate["inputSha256"])
        if exact is not None:
            existing_resolutions.append((candidate, "already-promoted-exact", exact))
            continue
        later_promotions = [
            item
            for item in promotions_for(state_root, game_pk)
            if item[0] > quarantine_timestamp(Path(candidate["inputPath"]))
        ]
        if later_promotions:
            existing_resolutions.append(
                (candidate, "superseded-by-later-promotion", later_promotions[-1][1])
            )
            continue
        replay_candidates[game_pk] = candidate
    proof_pks = [str(item["gamePk"]) for item in replay["proofGames"]]
    missing = [game_pk for game_pk in proof_pks if game_pk not in replay_candidates]
    prior_proof: Path | None = None
    proof_selection_mode = "configured-representative-games"
    if missing and replay_candidates:
        prior_proof = prior_certified_proof(state_root, proof_pks)
        if prior_proof is None:
            raise ValueError(
                "Representative quarantine proof inputs are missing and no prior certified "
                "five-game replay proof is available: " + ", ".join(missing)
            )
        # The representative edge-case proof establishes the replay mechanism.
        # Every later replay still proves up to five exact current payload hashes
        # before releasing any remainder, so no stale or substituted input can pass.
        proof_pks = sorted(replay_candidates, key=int)[:5]
        proof_selection_mode = "current-inputs-after-prior-certified-proof"
    plan_id = uuid.uuid4().hex
    plan_path = (
        state_root.resolve()
        / "pipeline"
        / "evidence"
        / "nifi"
        / "quarantine-replay"
        / plan_id
        / "plan.json"
    )
    created = datetime.now(timezone.utc).isoformat()
    proof = [replay_candidates[game_pk] for game_pk in proof_pks]
    remainder = [
        replay_candidates[game_pk]
        for game_pk in sorted(replay_candidates, key=int)
        if game_pk not in set(proof_pks)
    ]
    plan = {
        "artifactType": "baseballo-mlb-game-quarantine-replay-plan",
        "contractVersion": 1,
        "planId": plan_id,
        "createdAtUtc": created,
        "contractPath": str(contract_path.resolve()),
        "proofBasis": {
            "selectionMode": proof_selection_mode,
            "priorProofEvidence": str(prior_proof) if prior_proof is not None else None,
        },
        "proof": proof,
        "remainder": remainder,
        "existingResolutions": [
            {
                **candidate,
                "resolutionMode": mode,
                "promotionEvidence": str(promotion),
            }
            for candidate, mode, promotion in existing_resolutions
        ],
    }
    atomic_json(plan_path, plan)
    records = [work_record(item, "proof", plan_path) for item in proof]
    records.extend(
        resolution_record(candidate, plan_path, mode, promotion)
        for candidate, mode, promotion in existing_resolutions
    )
    records.append({"phase": "gate", "planPath": str(plan_path.resolve())})
    return {
        "artifactType": "baseballo-mlb-game-quarantine-replay-submission",
        "contractVersion": 1,
        "planPath": str(plan_path.resolve()),
        "proofCount": len(proof),
        "remainderCount": len(remainder),
        "existingResolutionCount": len(existing_resolutions),
        "records": records,
    }


def read_plan(state_root: Path, plan_path: Path) -> tuple[dict[str, Any], Path]:
    plans_root = (
        state_root.resolve() / "pipeline" / "evidence" / "nifi" / "quarantine-replay"
    )
    resolved = contained_path(plan_path, plans_root, "Quarantine replay plan")
    plan = read_object(resolved)
    if (
        plan.get("artifactType") != "baseballo-mlb-game-quarantine-replay-plan"
        or plan.get("contractVersion") != 1
        or resolved.parent.name != plan.get("planId")
    ):
        raise ValueError("Invalid quarantine replay plan")
    return plan, resolved


def require_proof(state_root: Path, plan_path: Path) -> dict[str, Any]:
    plan, resolved = read_plan(state_root, plan_path)
    created = datetime.fromisoformat(str(plan["createdAtUtc"]).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    missing: list[str] = []
    promotions: list[str] = []
    for item in plan["proof"]:
        promotion = promotion_for(
            state_root, str(item["gamePk"]), str(item["inputSha256"]), created
        )
        if promotion is None:
            missing.append(str(item["gamePk"]))
        else:
            promotions.append(str(promotion))
    if missing:
        raise RuntimeError("Proof promotions are not complete: " + ", ".join(missing))
    evidence = {
        "artifactType": "baseballo-mlb-game-quarantine-replay-proof",
        "contractVersion": 1,
        "planPath": str(resolved),
        "verifiedAtUtc": datetime.now(timezone.utc).isoformat(),
        "promotions": promotions,
    }
    atomic_json(resolved.parent / "proof.json", evidence)
    return evidence


def emit_remainder(state_root: Path, plan_path: Path) -> dict[str, Any]:
    plan, resolved = read_plan(state_root, plan_path)
    if not (resolved.parent / "proof.json").is_file():
        require_proof(state_root, resolved)
    quarantine_root = state_root.resolve() / "pipeline" / "quarantine" / "mlb-game"
    records: list[dict[str, str]] = []
    for item in plan["remainder"]:
        path = Path(str(item["inputPath"]))
        validate_input(path, quarantine_root, str(item["gamePk"]))
        if sha256_file(path) != item["inputSha256"]:
            raise ValueError(f"Quarantine input changed after planning: {path}")
        records.append(work_record(item, "remainder", resolved))
    return {
        "artifactType": "baseballo-mlb-game-quarantine-replay-remainder",
        "contractVersion": 1,
        "planPath": str(resolved),
        "records": records,
    }


def emit_latest_proof(state_root: Path) -> dict[str, Any]:
    plans_root = (
        state_root.resolve() / "pipeline" / "evidence" / "nifi" / "quarantine-replay"
    )
    open_plans = sorted(
        (
            path
            for path in plans_root.glob("*/plan.json")
            if not (path.parent / "proof.json").is_file()
        ),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if not open_plans:
        raise ValueError("No open quarantine replay proof plan exists")
    plan, resolved = read_plan(state_root, open_plans[0])
    created = datetime.fromisoformat(str(plan["createdAtUtc"]).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    candidates = current_candidates(state_root)
    records: list[dict[str, str]] = []
    completed = 0
    pending = 0
    for expected in plan["proof"]:
        game_pk = str(expected["gamePk"])
        candidate = candidates.get(game_pk)
        expected_hash = str(expected["inputSha256"])
        promotion = promotion_for(state_root, game_pk, expected_hash, created)
        if promotion is not None:
            completed += 1
            if candidate is not None and candidate["inputSha256"] == expected_hash:
                records.append(
                    resolution_record(
                        candidate,
                        resolved,
                        "already-promoted-exact",
                        promotion,
                    )
                )
            continue
        if candidate is None or candidate["inputSha256"] != expected_hash:
            raise ValueError(
                f"Current quarantine input does not match planned proof hash for game {game_pk}"
            )
        records.append(work_record(candidate, "proof", resolved))
        pending += 1
    # The original gate FlowFile may have exhausted its retry budget before a
    # repair made the proof games promotable. Reissue the gate with every proof
    # retry so an open plan can always advance once its exact evidence exists.
    records.append({"phase": "gate", "planPath": str(resolved)})
    return {
        "artifactType": "baseballo-mlb-game-quarantine-proof-retry",
        "contractVersion": 1,
        "planPath": str(resolved),
        "proofCount": len(plan["proof"]),
        "pendingProofCount": pending,
        "completedProofCount": completed,
        "records": records,
    }


def emit_latest_remainder(state_root: Path) -> dict[str, Any]:
    """Reissue only unresolved remainder inputs from the latest matching plan."""
    plans_root = (
        state_root.resolve() / "pipeline" / "evidence" / "nifi" / "quarantine-replay"
    )
    candidates = current_candidates(state_root)
    if not candidates:
        raise ValueError("No unresolved MLB-game quarantine inputs exist")
    plan_paths = sorted(
        plans_root.glob("*/plan.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    selected: tuple[dict[str, Any], Path] | None = None
    for plan_path in plan_paths:
        plan, resolved = read_plan(state_root, plan_path)
        remainder = {str(item["gamePk"]): item for item in plan["remainder"]}
        if any(game_pk in remainder for game_pk in candidates):
            selected = (plan, resolved)
            break
    if selected is None:
        raise ValueError("No quarantine replay plan owns the unresolved inputs")

    plan, resolved = selected
    created = datetime.fromisoformat(str(plan["createdAtUtc"]).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    records: list[dict[str, str]] = []
    replay_count = 0
    resolution_count = 0
    for expected in plan["remainder"]:
        game_pk = str(expected["gamePk"])
        candidate = candidates.get(game_pk)
        if candidate is None:
            continue
        expected_hash = str(expected["inputSha256"])
        if candidate["inputSha256"] != expected_hash:
            raise ValueError(
                f"Current quarantine input does not match planned remainder hash for game {game_pk}"
            )
        promotion = promotion_for(state_root, game_pk, expected_hash, created)
        if promotion is None:
            records.append(work_record(candidate, "remainder", resolved))
            replay_count += 1
        else:
            records.append(
                resolution_record(
                    candidate,
                    resolved,
                    "already-promoted-exact",
                    promotion,
                )
            )
            resolution_count += 1
    if not records:
        raise ValueError("The selected replay plan has no unresolved remainder inputs")
    return {
        "artifactType": "baseballo-mlb-game-quarantine-remainder-retry",
        "contractVersion": 1,
        "planPath": str(resolved),
        "replayCount": replay_count,
        "existingResolutionCount": resolution_count,
        "records": records,
    }


def resolve_input(
    state_root: Path,
    plan_path: Path,
    game_pk: str,
    input_path: Path,
    input_sha256: str,
    resolution_mode: str = "replayed-and-promoted",
    promotion_evidence: Path | None = None,
) -> dict[str, Any]:
    _, resolved_plan = read_plan(state_root, plan_path)
    if not SHA256.fullmatch(input_sha256):
        raise ValueError("Replay input hash is invalid")
    quarantine_root = state_root.resolve() / "pipeline" / "quarantine" / "mlb-game"
    selected = contained_path(input_path, quarantine_root, "Quarantine input")
    validate_input(selected, quarantine_root, game_pk)
    if sha256_file(selected) != input_sha256:
        raise ValueError("Replay input hash changed before resolution")
    if resolution_mode == "replayed-and-promoted":
        promotion = promotion_for(state_root, game_pk, input_sha256)
        if promotion is None:
            raise RuntimeError(f"No successful graph-pair promotion matches replayed game {game_pk}")
    else:
        if resolution_mode not in {
            "already-promoted-exact",
            "superseded-by-later-promotion",
        } or promotion_evidence is None:
            raise ValueError("Unsupported existing-quarantine resolution mode")
        promotion_root = (
            state_root.resolve()
            / "pipeline"
            / "evidence"
            / "nifi"
            / "game-promotion"
            / game_pk
        )
        promotion = contained_path(promotion_evidence, promotion_root, "Promotion evidence")
        available = {path: (timestamp, value) for timestamp, path, value in promotions_for(state_root, game_pk)}
        if promotion not in available:
            raise ValueError("Existing-quarantine resolution cites invalid promotion evidence")
        promotion_timestamp, promotion_value = available[promotion]
        if (
            resolution_mode == "already-promoted-exact"
            and promotion_value.get("rawSha256") != input_sha256
        ):
            raise ValueError("Exact existing promotion does not match the quarantine input hash")
        if (
            resolution_mode == "superseded-by-later-promotion"
            and promotion_timestamp <= quarantine_timestamp(selected)
        ):
            raise ValueError("Superseding promotion is not later than the quarantine record")

    removed: list[dict[str, str]] = []
    game_root = quarantine_root / game_pk
    for candidate in game_root.glob("*/input.json"):
        validate_input(candidate, quarantine_root, game_pk)
        candidate_hash = sha256_file(candidate)
        disposition = resolution_mode if candidate.resolve() == selected else "superseded-by-selected-resolution"
        resolution = {
            "artifactType": "baseballo-mlb-game-quarantine-resolution",
            "contractVersion": 1,
            "gamePk": game_pk,
            "resolvedAtUtc": datetime.now(timezone.utc).isoformat(),
            "disposition": disposition,
            "removedInputSha256": candidate_hash,
            "selectedReplayInputSha256": input_sha256,
            "promotionEvidence": str(promotion),
            "replayPlan": str(resolved_plan),
        }
        atomic_json(candidate.parent / "resolution.json", resolution)
        candidate.unlink()
        removed.append({"path": str(candidate.resolve()), "sha256": candidate_hash})
    if not removed:
        raise RuntimeError(f"No quarantine input remained to resolve for game {game_pk}")
    return {
        "artifactType": "baseballo-mlb-game-quarantine-resolution-result",
        "contractVersion": 1,
        "gamePk": game_pk,
        "promotionEvidence": str(promotion),
        "removedInputs": removed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action",
        required=True,
        choices=(
            "plan",
            "check-proof",
            "emit-remainder",
            "emit-latest-proof",
            "emit-latest-remainder",
            "resolve",
        ),
    )
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--game-pk")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-sha256")
    parser.add_argument("--resolution-mode", default="replayed-and-promoted")
    parser.add_argument("--promotion-evidence", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.action == "plan":
        if args.contract is None:
            raise ValueError("plan requires --contract")
        output = create_plan(args.state_root, args.contract)
    elif args.action == "check-proof":
        if args.plan is None:
            raise ValueError("check-proof requires --plan")
        output = require_proof(args.state_root, args.plan)
    elif args.action == "emit-remainder":
        if args.plan is None:
            raise ValueError("emit-remainder requires --plan")
        output = emit_remainder(args.state_root, args.plan)
    elif args.action == "emit-latest-proof":
        output = emit_latest_proof(args.state_root)
    elif args.action == "emit-latest-remainder":
        output = emit_latest_remainder(args.state_root)
    else:
        if (
            args.plan is None
            or args.input is None
            or args.game_pk is None
            or args.input_sha256 is None
        ):
            raise ValueError("resolve requires --plan, --game-pk, --input, and --input-sha256")
        output = resolve_input(
            args.state_root,
            args.plan,
            args.game_pk,
            args.input,
            args.input_sha256,
            args.resolution_mode or "replayed-and-promoted",
            args.promotion_evidence,
        )
    print(json.dumps(output, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
