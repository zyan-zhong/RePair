#!/usr/bin/env python3
"""Freeze a pre-outcome, content-addressed Memory live execution manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    strict_json_loads,
)
from pchsi.memory.scientific_decision import (
    FM0, FM1, FM2, FM3, ROUND_ACTIVE,
    REGISTERED_STAGES, STAGE_1B, STAGE_2, STAGE_3,
    validate_decision_rule_v1,
)

_CELL_KEYS = {
    "cell_id", "comparison_group_id", "condition", "round_index", "split",
    "task_id", "task_family", "snapshot_sha256",
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path: Path, *, executable: bool = False) -> None:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=ARTIFACT_NOT_REGULAR:" + str(path))
    if executable and not os.access(path, os.X_OK):
        raise SystemExit("STOP=ARTIFACT_NOT_EXECUTABLE:" + str(path))


def object_value(path: Path) -> dict[str, object] | None:
    try:
        value = strict_json_loads(path.read_bytes())
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def semantic_sha(path: Path, fields: tuple[str, ...]) -> str:
    value = object_value(path)
    if value is not None:
        for field in fields:
            candidate = value.get(field)
            if isinstance(candidate, str):
                try:
                    require_lower_sha256(field, candidate)
                except ValueError:
                    continue
                return candidate
    return sha_file(path)


def binding(path: Path, *, role: str, semantic_fields: tuple[str, ...] = ()) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "semantic_sha256": semantic_sha(path, semantic_fields),
        "size_bytes": len(raw),
        "role": role,
    }


def parse_cells(path: Path, stage: str) -> list[dict[str, object]]:
    rows = []
    for line_number, raw in enumerate(path.read_bytes().splitlines(keepends=True), start=1):
        if not raw:
            continue
        value = strict_json_loads(raw)
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise SystemExit(f"STOP=NONCANONICAL_CELL_ROW:{line_number}")
        if set(value) != _CELL_KEYS:
            raise SystemExit(f"STOP=CELL_ROW_FIELDS:{line_number}")
        for name in ("cell_id", "comparison_group_id", "condition", "task_id", "task_family"):
            if not isinstance(value[name], str) or not value[name]:
                raise SystemExit(f"STOP=CELL_ROW_TEXT:{line_number}:{name}")
        if value["snapshot_sha256"] is not None:
            require_lower_sha256("snapshot_sha256", value["snapshot_sha256"])
        condition = value["condition"]
        if stage in {STAGE_1B, STAGE_3}:
            if condition not in {FM0, FM1, FM2, FM3} or value["round_index"] is not None:
                raise SystemExit(f"STOP=CELL_ARM_OR_ROUND:{line_number}")
        else:
            if condition != ROUND_ACTIVE or type(value["round_index"]) is not int or value["round_index"] < 0:
                raise SystemExit(f"STOP=CELL_STAGE2_ROUND:{line_number}")
        if stage == STAGE_3 and value["split"] not in {"VALID_SEEN", "VALID_UNSEEN"}:
            raise SystemExit(f"STOP=CELL_STAGE3_SPLIT:{line_number}")
        rows.append(dict(value))
    if not rows:
        raise SystemExit("STOP=NO_REGISTERED_CELLS")
    ids = [row["cell_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("STOP=CELL_IDS_REPEAT")
    if stage in {STAGE_1B, STAGE_3}:
        groups: dict[str, set[str]] = {}
        for row in rows:
            groups.setdefault(str(row["comparison_group_id"]), set()).add(str(row["condition"]))
        required = {FM0, FM1, FM2, FM3}
        if any(arms != required for arms in groups.values()):
            raise SystemExit("STOP=INCOMPLETE_FM0_FM3_GROUP")
    else:
        rounds = sorted({int(row["round_index"]) for row in rows})
        if not rounds or rounds[0] != 0 or len(rounds) < 2:
            raise SystemExit("STOP=STAGE2_REQUIRES_ROUND0_AND_LATER_ROUND")
    return rows


def write_new(path: Path, value: dict[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=OUTPUT_EXISTS")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(REGISTERED_STAGES))
    parser.add_argument("--fixed-head", required=True)
    parser.add_argument("--scientific-protocol", required=True)
    parser.add_argument("--scientific-program", required=True)
    parser.add_argument("--runtime-identity", required=True)
    parser.add_argument("--policy-identity", required=True)
    parser.add_argument("--environment-identity", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--cell-manifest", required=True)
    parser.add_argument("--cell-executor", required=True)
    parser.add_argument("--decision-rule", required=True)
    parser.add_argument("--snapshot")
    parser.add_argument("--snapshot-registry")
    parser.add_argument("--executor-code-approval", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if len(args.fixed_head) != 40 or any(ch not in "0123456789abcdef" for ch in args.fixed_head):
        raise SystemExit("STOP=FIXED_HEAD_INVALID")
    if args.executor_code_approval != "CODE_APPROVED_FAILURE_MEMORY_LIVE_CELL_EXECUTOR_V1":
        raise SystemExit("STOP=CELL_EXECUTOR_CODE_APPROVAL_MISMATCH")

    paths = {
        "scientific_protocol": Path(args.scientific_protocol),
        "scientific_program": Path(args.scientific_program),
        "runtime_identity": Path(args.runtime_identity),
        "policy_identity": Path(args.policy_identity),
        "environment_identity": Path(args.environment_identity),
        "panel": Path(args.panel),
        "schedule": Path(args.schedule),
        "cell_manifest": Path(args.cell_manifest),
        "cell_executor": Path(args.cell_executor),
        "decision_rule": Path(args.decision_rule),
    }
    if args.snapshot:
        paths["snapshot"] = Path(args.snapshot)
    if args.snapshot_registry:
        paths["snapshot_registry"] = Path(args.snapshot_registry)
    for name, path in paths.items():
        regular(path, executable=(name == "cell_executor"))
    if args.stage == STAGE_2 and "snapshot_registry" not in paths:
        raise SystemExit("STOP=STAGE2_SNAPSHOT_REGISTRY_REQUIRED")
    if args.stage != STAGE_2 and "snapshot" not in paths:
        raise SystemExit("STOP=STAGE1B_STAGE3_SNAPSHOT_REQUIRED")

    cells = parse_cells(paths["cell_manifest"], args.stage)
    decision = object_value(paths["decision_rule"])
    if decision is None:
        raise SystemExit("STOP=DECISION_RULE_NOT_JSON_OBJECT")
    validated_rule = validate_decision_rule_v1(decision)
    if validated_rule.stage != args.stage:
        raise SystemExit("STOP=DECISION_RULE_STAGE_MISMATCH")

    semantic_fields = {
        "scientific_protocol": ("protocol_sha256", "contract_sha256", "manifest_sha256"),
        "scientific_program": ("program_sha256",),
        "runtime_identity": ("runtime_identity_sha256", "runtime_manifest_sha256", "manifest_sha256"),
        "policy_identity": ("policy_identity_sha256", "policy_runtime_manifest_sha256", "manifest_sha256"),
        "environment_identity": ("environment_identity_sha256", "environment_runtime_manifest_sha256", "manifest_sha256"),
        "panel": ("panel_sha256", "manifest_sha256"),
        "schedule": ("schedule_sha256", "manifest_sha256"),
        "decision_rule": ("rule_sha256",),
        "snapshot": ("snapshot_sha256", "manifest_sha256"),
        "snapshot_registry": ("registry_sha256", "manifest_sha256"),
    }
    bindings = {
        name: binding(path, role=name, semantic_fields=semantic_fields.get(name, ()))
        for name, path in paths.items()
    }
    payload = {
        "schema_id": "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2",
        "schema_version": 2,
        "manifest_sha256": "0" * 64,
        "stage": args.stage,
        "fixed_code_head": args.fixed_head,
        "scientific_execution_authorized": False,
        "preoutcome_frozen": True,
        "registered_cell_count": len(cells),
        "cell_result_schema_id": "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        "bindings": bindings,
        "operational_paths": {name: str(path.resolve()) for name, path in paths.items()},
    }
    payload["manifest_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2\0"
        + canonical_json_bytes({key: value for key, value in payload.items() if key != "manifest_sha256"})
    ).hexdigest()
    write_new(Path(args.output), payload)
    print("MEMORY_LIVE_EXECUTION_MANIFEST_V2_PASS")
    print("STAGE=" + args.stage)
    print("REGISTERED_CELL_COUNT=" + str(len(cells)))
    print("MANIFEST_SHA256=" + payload["manifest_sha256"])
    print("SCIENTIFIC_EXECUTION_AUTHORIZED=false")


if __name__ == "__main__":
    main()
