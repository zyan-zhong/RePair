"""Historical source-collection lineage bridge without mutating source evidence."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any

from .bundle_reader import validate_attempt_bundle
from .canonical import (
    domain_hash,
    ensure_directory_no_symlink,
    ensure_regular_no_symlink,
    require_object,
    sha256_file,
    strict_json_loads,
    write_new_json,
)
from .task_access import revalidate_task_access


TRAIN17 = "P4-R1-Q2-BAD-TRAIN17"
LOGICAL_PI1 = "P4-R1-Q2-BAD"


def _read_json(path: Path) -> dict[str, object]:
    source = ensure_regular_no_symlink(path, name=path.name)
    return require_object(path.name, strict_json_loads(source.read_bytes()))


def _strings(value: object) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            out.extend(_strings(child))
    elif isinstance(value, list):
        for child in value:
            out.extend(_strings(child))
    elif isinstance(value, str):
        out.append(value)
    return out



def _validate_replay_qualification_context(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, object]:
    source = ensure_regular_no_symlink(
        path,
        name="replay qualification authority",
    )
    observed_sha = sha256_file(source)
    if observed_sha != expected_sha256:
        raise ValueError(
            "replay qualification authority SHA mismatch: "
            f"expected={expected_sha256}, observed={observed_sha}"
        )
    payload = _read_json(source)
    return {
        "path": str(source),
        "sha256": observed_sha,
        "schema_id": payload.get("schema_id"),
        "schema_version": payload.get("schema_version"),
        "role": (
            "DOWNSTREAM_REPLAY_QUALIFICATION_CONTEXT_"
            "NOT_DIRECT_SOURCE_LINEAGE"
        ),
    }



_PUBLISHED_ATTEMPT_ID = re.compile(
    r"^e1-t[0-9]{4}-s[0-9]{10}-a[0-9]{3}$"
)


def _published_attempt_directories(
    attempts_root: Path,
) -> tuple[list[Path], list[str]]:
    root = ensure_directory_no_symlink(
        attempts_root,
        name="source collection attempts root",
    )
    published: list[Path] = []
    infrastructure: list[str] = []

    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.is_symlink():
            raise ValueError(
                "source collection attempts root contains symlink: "
                + child.name
            )
        if not child.is_dir():
            continue
        if _PUBLISHED_ATTEMPT_ID.fullmatch(child.name):
            published.append(child)
            continue
        if child.name == ".staging":
            infrastructure.append(child.name)
            continue
        raise ValueError(
            "source collection attempts root contains unknown directory: "
            + child.name
        )

    return published, infrastructure


def _find_access_by_gamefile(
    task_access: dict[str, object],
    *,
    gamefile_sha256: str,
) -> dict[str, object]:
    rows = task_access.get("rows")
    if not isinstance(rows, list):
        raise TypeError("TASK_ACCESS_REVALIDATION_V1 rows must be array")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("gamefile_sha256") == gamefile_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            "source bundle must resolve to exactly one task-access row by "
            f"gamefile_sha256; observed={len(matches)}"
        )
    row = matches[0]
    if row.get("revalidation_disposition") not in {
        "CONFIRMED_UNCHANGED",
        "DOWNGRADED_DUE_TO_HISTORICAL_EXPOSURE",
    }:
        raise ValueError(
            "source bundle task access is blocked: "
            + str(row.get("revalidation_disposition"))
        )
    if row.get("existing_access_class") != "TRAIN_MEMORY_SOURCE":
        raise ValueError(
            "source collection Analyzer bridge requires TRAIN_MEMORY_SOURCE"
        )
    if row.get("strong_model_allowed") is not True:
        raise ValueError("source access does not permit Analyzer use")
    if row.get("allowed_artifact_granularity") != (
        "FULL_TRAJECTORY_DEV_VISIBLE"
    ):
        raise ValueError("source access is not full-trajectory dev-visible")
    return row


def _approval_index(
    approval: dict[str, object],
) -> dict[str, dict[str, object]]:
    if (
        approval.get("schema_id")
        != "FAILURE_MEMORY_HUMAN_REGISTRATION_APPROVAL_V1"
        or approval.get("schema_version") != 1
        or approval.get("approval_token")
        != "HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1"
        or approval.get("reviewer_decision") != "APPROVED"
    ):
        raise ValueError("human registration approval authority is invalid")
    decisions = approval.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 3:
        raise ValueError("human approval must contain exactly three decisions")
    result: dict[str, dict[str, object]] = {}
    for row in decisions:
        if not isinstance(row, dict):
            raise TypeError("human approval decision must be object")
        attempt_id = row.get("source_attempt_id")
        bundle_sha = row.get("attempt_bundle_sha256")
        if (
            not isinstance(attempt_id, str)
            or not isinstance(bundle_sha, str)
            or row.get("source_condition") != TRAIN17
        ):
            raise ValueError("human approval decision lineage is incomplete")
        if attempt_id in result:
            raise ValueError("duplicate source attempt in human approval")
        result[attempt_id] = row
    return result


def build_source_collection_lineage_bridge(
    *,
    source_execution_root: Path,
    human_approval_path: Path,
    runtime_binding_path: Path,
    replay_qualification_path: Path,
    expected_replay_qualification_sha256: str,
    protected_task_access_path: Path,
    expected_protected_task_access_sha256: str,
) -> dict[str, object]:
    execution_root = ensure_directory_no_symlink(
        source_execution_root,
        name="source collection execution root",
    )
    approval_path = ensure_regular_no_symlink(
        human_approval_path,
        name="human registration approval",
    )
    runtime_path = ensure_regular_no_symlink(
        runtime_binding_path,
        name="source collection runtime binding",
    )
    replay_path = ensure_regular_no_symlink(
        replay_qualification_path,
        name="replay qualification authority",
    )
    access_path = ensure_regular_no_symlink(
        protected_task_access_path,
        name="protected task-access authority",
    )

    observed_access_sha = sha256_file(access_path)
    if observed_access_sha != expected_protected_task_access_sha256:
        raise ValueError(
            "protected task-access authority SHA mismatch: "
            f"{observed_access_sha}"
        )

    approval = _read_json(approval_path)
    approval_by_attempt = _approval_index(approval)
    runtime = _read_json(runtime_path)
    runtime_strings = _strings(runtime)
    train_models = sorted(
        {
            value
            for value in runtime_strings
            if value.startswith("P4-R1-Q2-BAD-TRAIN")
        }
    )
    if train_models != [TRAIN17]:
        raise ValueError(
            "source runtime must bind exactly Train17 and no alternate "
            f"checkpoint; observed={train_models}"
        )

    replay_context = _validate_replay_qualification_context(
        replay_path,
        expected_sha256=expected_replay_qualification_sha256,
    )

    source_ledger = (
        execution_root
        / "source_collection"
        / "source_collection_ledger.jsonl"
    )
    source_ledger = ensure_regular_no_symlink(
        source_ledger,
        name="source collection ledger",
    )
    expected_ledger_sha = approval.get("source_collection_ledger_sha256")
    if (
        not isinstance(expected_ledger_sha, str)
        or sha256_file(source_ledger) != expected_ledger_sha
    ):
        raise ValueError("source collection ledger SHA differs from approval")

    task_access = revalidate_task_access(
        source_manifest_path=access_path
    )

    attempts_root = (
        execution_root
        / "source_collection"
        / "evaluator_run"
        / "attempts"
    )
    attempt_dirs, infrastructure_directories = (
        _published_attempt_directories(attempts_root)
    )
    if len(attempt_dirs) != 12:
        raise ValueError(
            "source collection must contain exactly 12 published attempts; "
            f"observed={len(attempt_dirs)}"
        )

    rows: list[dict[str, object]] = []
    approved_count = 0
    for path in attempt_dirs:
        bundle = validate_attempt_bundle(path)
        if bundle.episode.get("seed") != 17:
            raise ValueError("source collection bundle seed is not 17")
        attempt_id = str(bundle.episode["execution_attempt_id"])
        approval_row = approval_by_attempt.get(attempt_id)
        case_authority = None
        if approval_row is not None:
            if (
                approval_row.get("attempt_bundle_sha256")
                != bundle.attempt_bundle_sha256
            ):
                raise ValueError(
                    "human approval bundle SHA differs from source bytes: "
                    + attempt_id
                )
            approved_count += 1
            case_authority = {
                "case_id": approval_row["case_id"],
                "source_condition": approval_row["source_condition"],
                "attempt_bundle_sha256": approval_row[
                    "attempt_bundle_sha256"
                ],
            }

        access_row = _find_access_by_gamefile(
            task_access,
            gamefile_sha256=bundle.gamefile_sha256,
        )
        row = {
            "source_attempt_id": attempt_id,
            "source_bundle_path": str(path.resolve()),
            "attempt_bundle_sha256": bundle.attempt_bundle_sha256,
            "episode_semantic_sha256": bundle.episode_semantic_sha256,
            "task_id": bundle.task_id,
            "gamefile_sha256": bundle.gamefile_sha256,
            "seed": bundle.episode.get("seed"),
            "logical_policy_id": LOGICAL_PI1,
            "checkpoint_instance_id": TRAIN17,
            "policy_lineage_resolution": (
                "RUN_LEVEL_PREEXECUTION_RUNTIME_BINDING"
            ),
            "human_registered_case_authority": case_authority,
            "task_access_resolution": "UNIQUE_GAMEFILE_SHA256",
            "task_access_row_sha256": access_row["row_sha256"],
            "task_access_class": access_row["existing_access_class"],
            "alignment_census": bundle.alignment_census,
        }
        row["row_sha256"] = domain_hash(
            "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_ROW_V1",
            row,
        )
        rows.append(row)

    if approved_count != 3:
        raise ValueError(
            f"expected 3 human-approved cases; observed={approved_count}"
        )

    bridge = {
        "schema_id": "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1",
        "schema_version": 1,
        "source_execution_root": str(execution_root),
        "source_collection_ledger_path": str(source_ledger),
        "source_collection_ledger_sha256": sha256_file(source_ledger),
        "human_approval_path": str(approval_path),
        "human_approval_sha256": sha256_file(approval_path),
        "runtime_binding_path": str(runtime_path),
        "runtime_binding_sha256": sha256_file(runtime_path),
        "replay_qualification_path": replay_context["path"],
        "replay_qualification_sha256": replay_context["sha256"],
        "replay_qualification_role": replay_context["role"],
        "protected_task_access_path": str(access_path),
        "protected_task_access_sha256": observed_access_sha,
        "task_access_revalidation_sha256": task_access[
            "revalidation_sha256"
        ],
        "logical_policy_id": LOGICAL_PI1,
        "checkpoint_instance_id": TRAIN17,
        "source_bundle_count": len(rows),
        "published_attempt_directory_rule": (
            "E1_ATTEMPT_ID_V1_EXCLUDING_DOT_STAGING"
        ),
        "nonmember_infrastructure_directories": (
            infrastructure_directories
        ),
        "human_registered_case_count": approved_count,
        "access_class_counts": dict(
            Counter(str(row["task_access_class"]) for row in rows)
        ),
        "rows": rows,
        "bridge_status": (
            "POLICY_LINEAGE_AND_ACCESS_CONFIRMED_"
            "REFERENCE_IDENTITY_ARTIFACT_PENDING"
        ),
        "source_evidence_bytes_modified": False,
        "scientific_outcome_created": False,
        "bridge_sha256": "0" * 64,
    }
    bridge["bridge_sha256"] = domain_hash(
        "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1",
        bridge,
        excluded_field="bridge_sha256",
    )
    return bridge


def build_source_collection_lineage_bridge_file(
    *,
    source_execution_root: Path,
    human_approval_path: Path,
    runtime_binding_path: Path,
    replay_qualification_path: Path,
    expected_replay_qualification_sha256: str,
    protected_task_access_path: Path,
    expected_protected_task_access_sha256: str,
    output_path: Path,
) -> dict[str, object]:
    bridge = build_source_collection_lineage_bridge(
        source_execution_root=source_execution_root,
        human_approval_path=human_approval_path,
        runtime_binding_path=runtime_binding_path,
        replay_qualification_path=replay_qualification_path,
        expected_replay_qualification_sha256=(
            expected_replay_qualification_sha256
        ),
        protected_task_access_path=protected_task_access_path,
        expected_protected_task_access_sha256=(
            expected_protected_task_access_sha256
        ),
    )
    write_new_json(output_path, bridge)
    return bridge
