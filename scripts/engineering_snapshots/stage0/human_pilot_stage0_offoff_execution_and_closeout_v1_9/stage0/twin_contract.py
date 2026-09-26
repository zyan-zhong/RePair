from __future__ import annotations

from pathlib import Path
from typing import Any
import zipfile

from .common import Stage0Error, strict_json_loads
from .constants import (
    CANDIDATE_ADAPTER_PATH,
    CANDIDATE_ADAPTER_SHA256,
    CANDIDATE_CHECKPOINT_ID,
    OFFOFF_HANDOFF_SHA256,
    PAIRED_CELL_COUNT,
    PARENT_ADAPTER_PATH,
    PARENT_ADAPTER_SHA256,
    PARENT_CHECKPOINT_ID,
    PROTOCOL_EQUALITY_SHA256,
    REPLICATE_SEEDS,
    SELECT_TASK_COUNT,
    TOTAL_CONDITION_CELL_COUNT,
)


REQUIRED_MEMBERS = {
    "REVIEW_MANIFEST_V1.json",
    "TWIN_OFFOFF_PROTOCOL_EQUALITY_V1.json",
    "OFFOFF_EXECUTION_HANDOFF_V1.json",
    "FIXED_HEAD_AUDIT_V1.json",
    "IDENTITY_SHA256_V1.json",
    "bindings/SELECT_SERVER_RUNTIME_MANIFEST_V1.json",
    "bindings/PARENT_SELECT_POLICY_RUNTIME_MANIFEST_V1.json",
    "bindings/CANDIDATE_SELECT_POLICY_RUNTIME_MANIFEST_V1.json",
    "bindings/PARENT_POLICY_CONDITION_MANIFEST_V1.json",
    "bindings/CANDIDATE_POLICY_CONDITION_MANIFEST_V1.json",
    "bindings/PARENT_CONDITION_RUN_SCHEDULE_V1.json",
    "bindings/CANDIDATE_CONDITION_RUN_SCHEDULE_V1.json",
}


def _object(value: bytes, name: str) -> dict[str, Any]:
    parsed = strict_json_loads(value)
    if not isinstance(parsed, dict):
        raise Stage0Error(f"TWIN_MEMBER_NOT_OBJECT:{name}")
    return parsed


def audit_twin_documents(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    review = documents["review"]
    protocol = documents["protocol"]
    handoff = documents["handoff"]

    expected_seeds = list(REPLICATE_SEEDS)
    exact_checks = {
        "review_status": review.get("review_status")
        == "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
        "protocol_status": protocol.get("status") == "PASS",
        "handoff_status": handoff.get("status")
        == "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
        "select_task_count": review.get("select_task_count")
        == protocol.get("selected_task_count")
        == handoff.get("select_task_count")
        == SELECT_TASK_COUNT,
        "replicate_seeds": review.get("replicate_seeds")
        == protocol.get("replicate_seeds")
        == handoff.get("replicate_seeds")
        == expected_seeds,
        "paired_cells": review.get("paired_cell_count")
        == protocol.get("paired_cell_count")
        == handoff.get("paired_cell_count")
        == PAIRED_CELL_COUNT,
        "total_cells": review.get("total_condition_cell_count")
        == protocol.get("total_condition_cell_count")
        == handoff.get("total_condition_cell_count")
        == TOTAL_CONDITION_CELL_COUNT,
        "grid_equal": protocol.get("grid_equal") is True,
        "memory_off": protocol.get("memory_state") == "OFF"
        and handoff.get("memory_off") is True,
        "harness_off": protocol.get("harness_state") == "OFF"
        and handoff.get("harness_off") is True,
        "protocol_sha": protocol.get("protocol_equality_sha256")
        == PROTOCOL_EQUALITY_SHA256,
        "handoff_sha": handoff.get("handoff_sha256")
        == OFFOFF_HANDOFF_SHA256,
        "execution_closed": review.get("evaluation_execution_authorized")
        is False
        and handoff.get("evaluation_execution_authorized") is False
        and review.get("evaluation_execution_count") == 0
        and handoff.get("evaluation_execution_count") == 0,
        "promotion_closed": handoff.get("promotion_decision_authorized")
        is False
        and handoff.get("promotion_eligible") is False,
    }
    failed = sorted(key for key, passed in exact_checks.items() if not passed)
    if failed:
        if "promotion_closed" in failed:
            raise ValueError("promotion boundary changed")
        raise ValueError("TWIN_CONTRACT_CHANGED:" + ",".join(failed))

    return {
        "select_task_count": SELECT_TASK_COUNT,
        "replicate_seeds": expected_seeds,
        "paired_cell_count": PAIRED_CELL_COUNT,
        "total_condition_cell_count": TOTAL_CONDITION_CELL_COUNT,
        "protocol_equality_sha256": PROTOCOL_EQUALITY_SHA256,
        "handoff_sha256": OFFOFF_HANDOFF_SHA256,
        "paper_efficacy_evidence": False,
        "promotion_eligible": False,
    }



def audit_runtime_binding_documents(
    *,
    server: dict[str, Any],
    parent_runtime: dict[str, Any],
    candidate_runtime: dict[str, Any],
    parent_condition: dict[str, Any],
    candidate_condition: dict[str, Any],
) -> None:
    registry = server.get("static_lora_registry")
    if not isinstance(registry, list):
        raise Stage0Error(
            "TWIN_STATIC_LORA_REGISTRY_INVALID"
        )
    by_name = {
        row.get("served_model_name"): row
        for row in registry
        if isinstance(row, dict)
    }
    parent_registration = by_name.get(
        PARENT_CHECKPOINT_ID
    )
    candidate_registration = by_name.get(
        CANDIDATE_CHECKPOINT_ID
    )
    if (
        not isinstance(parent_registration, dict)
        or not isinstance(candidate_registration, dict)
    ):
        raise Stage0Error(
            "TWIN_STATIC_LORA_IDENTITY_CHANGED"
        )

    expected_parent_path = str(PARENT_ADAPTER_PATH)
    expected_candidate_path = str(
        CANDIDATE_ADAPTER_PATH
    )
    checks = {
        "PARENT_RUNTIME_ID":
            parent_runtime.get(
                "checkpoint_instance_id"
            )
            == PARENT_CHECKPOINT_ID,
        "CANDIDATE_RUNTIME_ID":
            candidate_runtime.get(
                "checkpoint_instance_id"
            )
            == CANDIDATE_CHECKPOINT_ID,
        "PARENT_RUNTIME_SHA":
            parent_runtime.get(
                "adapter_bundle_sha256"
            )
            == PARENT_ADAPTER_SHA256,
        "CANDIDATE_RUNTIME_SHA":
            candidate_runtime.get(
                "adapter_bundle_sha256"
            )
            == CANDIDATE_ADAPTER_SHA256,
        "PARENT_RUNTIME_PATH":
            parent_runtime.get("adapter_path")
            == expected_parent_path,
        "CANDIDATE_RUNTIME_PATH":
            candidate_runtime.get("adapter_path")
            == expected_candidate_path,
        "PARENT_REGISTRY_SHA":
            parent_registration.get(
                "adapter_bundle_sha256"
            )
            == PARENT_ADAPTER_SHA256,
        "CANDIDATE_REGISTRY_SHA":
            candidate_registration.get(
                "adapter_bundle_sha256"
            )
            == CANDIDATE_ADAPTER_SHA256,
        "PARENT_REGISTRY_PATH":
            parent_registration.get("adapter_path")
            == expected_parent_path,
        "CANDIDATE_REGISTRY_PATH":
            candidate_registration.get(
                "adapter_path"
            )
            == expected_candidate_path,
        "PARENT_CONDITION_SHA":
            parent_condition.get(
                "checkpoint_sha256"
            )
            == PARENT_ADAPTER_SHA256,
        "CANDIDATE_CONDITION_SHA":
            candidate_condition.get(
                "checkpoint_sha256"
            )
            == CANDIDATE_ADAPTER_SHA256,
        "SERVER_TWO_LORAS":
            len(registry) == 2,
        "SERVER_MAX_LORAS":
            server.get("max_loras") == 1,
        "SERVER_MAX_CPU_LORAS":
            server.get("max_cpu_loras") == 2,
    }
    failed = sorted(
        key
        for key, passed in checks.items()
        if not passed
    )
    if failed:
        raise Stage0Error(
            "TWIN_RUNTIME_BINDING_CHANGED:"
            + ",".join(failed)
        )


def load_twin_review(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise Stage0Error(f"TWIN_REVIEW_INVALID:{path}")
    if not zipfile.is_zipfile(path):
        raise Stage0Error("TWIN_REVIEW_NOT_ZIP")
    with zipfile.ZipFile(path, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stage0Error(f"TWIN_REVIEW_BAD_MEMBER:{bad}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise Stage0Error("TWIN_REVIEW_DUPLICATE_MEMBER")
        missing = sorted(REQUIRED_MEMBERS - set(names))
        if missing:
            raise Stage0Error("TWIN_REVIEW_MISSING:" + ",".join(missing))
        values = {
            name: _object(archive.read(name), name)
            for name in REQUIRED_MEMBERS
        }

    documents = {
        "review": values["REVIEW_MANIFEST_V1.json"],
        "protocol": values["TWIN_OFFOFF_PROTOCOL_EQUALITY_V1.json"],
        "handoff": values["OFFOFF_EXECUTION_HANDOFF_V1.json"],
    }
    summary = audit_twin_documents(documents)

    parent_runtime = values[
        "bindings/PARENT_SELECT_POLICY_RUNTIME_MANIFEST_V1.json"
    ]
    candidate_runtime = values[
        "bindings/CANDIDATE_SELECT_POLICY_RUNTIME_MANIFEST_V1.json"
    ]
    parent_condition = values[
        "bindings/PARENT_POLICY_CONDITION_MANIFEST_V1.json"
    ]
    candidate_condition = values[
        "bindings/CANDIDATE_POLICY_CONDITION_MANIFEST_V1.json"
    ]
    server = values[
        "bindings/SELECT_SERVER_RUNTIME_MANIFEST_V1.json"
    ]

    audit_runtime_binding_documents(
        server=server,
        parent_runtime=parent_runtime,
        candidate_runtime=candidate_runtime,
        parent_condition=parent_condition,
        candidate_condition=candidate_condition,
    )


    parent_schedule = values[
        "bindings/PARENT_CONDITION_RUN_SCHEDULE_V1.json"
    ]
    candidate_schedule = values[
        "bindings/CANDIDATE_CONDITION_RUN_SCHEDULE_V1.json"
    ]
    parent_grid = [
        (cell["manifest_index"], cell["task_id"], cell["seed"])
        for cell in parent_schedule["cells"]
    ]
    candidate_grid = [
        (cell["manifest_index"], cell["task_id"], cell["seed"])
        for cell in candidate_schedule["cells"]
    ]
    if parent_grid != candidate_grid or len(parent_grid) != PAIRED_CELL_COUNT:
        raise Stage0Error("TWIN_SCHEDULE_GRID_CHANGED")

    return {
        "summary": summary,
        "values": values,
        "parent_grid": parent_grid,
    }
