"""Read-only revalidation of existing task/gamefile access authority."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .canonical import (
    domain_hash,
    ensure_regular_no_symlink,
    exact_keyset,
    require_bool,
    require_object,
    require_sha256,
    require_text,
    sha256_file,
    strict_json_loads,
    write_new_json,
)


_ALLOWED_SOURCE_CLASSES = {
    "TRAIN_MEMORY_SOURCE",
    "TRAIN_RETRIEVAL_DEV",
    "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
    "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
}


def _read_rows(path: Path) -> list[dict[str, object]]:
    source = ensure_regular_no_symlink(path, name="task-access source")
    raw = source.read_bytes()
    if path.suffix == ".jsonl":
        rows: list[dict[str, object]] = []
        for line_number, line in enumerate(raw.splitlines(), 1):
            if not line:
                raise ValueError(
                    f"blank JSONL line in task-access source: {line_number}"
                )
            rows.append(
                require_object(
                    f"task-access row {line_number}",
                    strict_json_loads(line),
                )
            )
        return rows

    value = strict_json_loads(raw)
    if isinstance(value, list):
        return [
            require_object(f"task-access row {index}", row)
            for index, row in enumerate(value)
        ]
    payload = require_object("task-access source", value)
    for key in ("records", "rows", "tasks"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [
                require_object(f"task-access row {index}", row)
                for index, row in enumerate(candidate)
            ]
    raise ValueError("task-access JSON must be an array or contain records/rows/tasks")


def _source_record(row: dict[str, object]) -> dict[str, object]:
    required = {
        "task_gamefile_group_id",
        "gamefile_sha256",
        "split",
        "historical_exposure_class",
        "historically_exposed",
        "access_class",
    }
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"task-access source row missing fields: {missing}")
    record = {
        "task_id": str(
            row.get("task_id")
            or row.get("task_gamefile_group_id")
        ),
        "task_gamefile_group_id": row["task_gamefile_group_id"],
        "gamefile_sha256": row["gamefile_sha256"],
        "existing_access_class": row["access_class"],
        "split": row["split"],
        "historical_exposure_class": row["historical_exposure_class"],
        "historically_exposed": row["historically_exposed"],
    }
    require_text("task_id", record["task_id"])
    require_sha256(
        "task_gamefile_group_id", record["task_gamefile_group_id"]
    )
    require_sha256("gamefile_sha256", record["gamefile_sha256"])
    require_text("existing_access_class", record["existing_access_class"])
    require_text("split", record["split"])
    require_text(
        "historical_exposure_class",
        record["historical_exposure_class"],
    )
    require_bool("historically_exposed", record["historically_exposed"])
    if record["existing_access_class"] not in _ALLOWED_SOURCE_CLASSES:
        raise ValueError(
            "unknown existing task access class: "
            + str(record["existing_access_class"])
        )
    return record


def _permissions(record: dict[str, object]) -> dict[str, object]:
    access = record["existing_access_class"]
    exposed = record["historically_exposed"]

    if access == "TRAIN_MEMORY_SOURCE":
        if exposed:
            disposition = "DOWNGRADED_DUE_TO_HISTORICAL_EXPOSURE"
            reason = "train source was historically exposed; training remains allowed but no fresh/clean claim"
        else:
            disposition = "CONFIRMED_UNCHANGED"
            reason = "existing train-memory source authority confirmed"
        return {
            "allowed_consumers": [
                "HIERARCHICAL_ANALYZER",
                "HUMAN_TRAINING_RESEARCHER",
                "SAME_STATE_F0F1_DEVELOPMENT",
                "VERIFIED_TRAINING_DATA_BUILDER",
            ],
            "allowed_artifact_granularity": "FULL_TRAJECTORY_DEV_VISIBLE",
            "strong_model_allowed": True,
            "training_allowed": True,
            "f0f1_development_allowed": True,
            "selection_summary_allowed": False,
            "confirmatory_execution_allowed": False,
            "revalidation_disposition": disposition,
            "revalidation_reason": reason,
        }

    if access == "TRAIN_RETRIEVAL_DEV":
        return {
            "allowed_consumers": [
                "HIERARCHICAL_ANALYZER",
                "RETRIEVAL_DEVELOPMENT",
                "HUMAN_TRAINING_RESEARCHER",
            ],
            "allowed_artifact_granularity": "FULL_TRAJECTORY_DEV_VISIBLE",
            "strong_model_allowed": True,
            "training_allowed": False,
            "f0f1_development_allowed": True,
            "selection_summary_allowed": False,
            "confirmatory_execution_allowed": False,
            "revalidation_disposition": "CONFIRMED_UNCHANGED",
            "revalidation_reason": (
                "retrieval-development authority confirmed; active training "
                "writeback remains forbidden"
            ),
        }

    if access == "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED":
        if exposed:
            return {
                "allowed_consumers": [
                    "INDEPENDENT_CONFIRMATORY_EVALUATOR"
                ],
                "allowed_artifact_granularity": "AGGREGATE_ONLY",
                "strong_model_allowed": False,
                "training_allowed": False,
                "f0f1_development_allowed": False,
                "selection_summary_allowed": False,
                "confirmatory_execution_allowed": True,
                "revalidation_disposition": (
                    "DOWNGRADED_DUE_TO_HISTORICAL_EXPOSURE"
                ),
                "revalidation_reason": (
                    "historical exposure removes clean-confirmation status; "
                    "detailed Analyzer release remains blocked"
                ),
            }
        return {
            "allowed_consumers": [
                "INDEPENDENT_CONFIRMATORY_EVALUATOR"
            ],
            "allowed_artifact_granularity": "AGGREGATE_ONLY",
            "strong_model_allowed": False,
            "training_allowed": False,
            "f0f1_development_allowed": False,
            "selection_summary_allowed": False,
            "confirmatory_execution_allowed": True,
            "revalidation_disposition": "CONFIRMED_UNCHANGED",
            "revalidation_reason": "clean ID confirmation lock confirmed",
        }

    # Historically exposed valid-unseen standard benchmark.
    if not exposed:
        return {
            "allowed_consumers": [],
            "allowed_artifact_granularity": "BLOCKED",
            "strong_model_allowed": False,
            "training_allowed": False,
            "f0f1_development_allowed": False,
            "selection_summary_allowed": False,
            "confirmatory_execution_allowed": False,
            "revalidation_disposition": (
                "BLOCKED_INCONSISTENT_SOURCE_AUTHORITY"
            ),
            "revalidation_reason": (
                "historically exposed benchmark class contradicts "
                "historically_exposed=false"
            ),
        }
    return {
        "allowed_consumers": [
            "STANDARD_OOD_BENCHMARK_EVALUATOR"
        ],
        "allowed_artifact_granularity": "AGGREGATE_ONLY",
        "strong_model_allowed": False,
        "training_allowed": False,
        "f0f1_development_allowed": False,
        "selection_summary_allowed": False,
        "confirmatory_execution_allowed": True,
        "revalidation_disposition": "CONFIRMED_UNCHANGED",
        "revalidation_reason": (
            "historically exposed standard OOD benchmark authority confirmed"
        ),
    }


def revalidate_task_access(
    *,
    source_manifest_path: Path,
) -> dict[str, object]:
    source = ensure_regular_no_symlink(
        source_manifest_path,
        name="task-access source manifest",
    )
    source_sha = sha256_file(source)
    records = [_source_record(row) for row in _read_rows(source)]

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record["gamefile_sha256"])].append(record)

    inconsistent_gamefiles = {
        gamefile
        for gamefile, group in grouped.items()
        if len(
            {
                str(item["existing_access_class"])
                for item in group
            }
        )
        != 1
    }

    output_rows: list[dict[str, object]] = []
    for record in records:
        row = {
            "task_id": record["task_id"],
            "task_gamefile_group_id": record[
                "task_gamefile_group_id"
            ],
            "gamefile_sha256": record["gamefile_sha256"],
            "existing_access_class": record["existing_access_class"],
            "historical_exposure_flags": {
                "historical_exposure_class": record[
                    "historical_exposure_class"
                ],
                "historically_exposed": record[
                    "historically_exposed"
                ],
            },
            "source_manifest_path": str(source),
            "source_manifest_sha256": source_sha,
        }
        if str(record["gamefile_sha256"]) in inconsistent_gamefiles:
            row.update(
                {
                    "allowed_consumers": [],
                    "allowed_artifact_granularity": "BLOCKED",
                    "strong_model_allowed": False,
                    "training_allowed": False,
                    "f0f1_development_allowed": False,
                    "selection_summary_allowed": False,
                    "confirmatory_execution_allowed": False,
                    "revalidation_disposition": (
                        "BLOCKED_INCONSISTENT_SOURCE_AUTHORITY"
                    ),
                    "revalidation_reason": (
                        "same gamefile appears with multiple access classes"
                    ),
                }
            )
        else:
            row.update(_permissions(record))
        row["row_sha256"] = domain_hash(
            "TASK_ACCESS_REVALIDATION_ROW_V1",
            row,
        )
        output_rows.append(row)

    output_rows.sort(
        key=lambda item: (
            str(item["gamefile_sha256"]),
            str(item["task_id"]),
        )
    )
    artifact = {
        "schema_id": "TASK_ACCESS_REVALIDATION_V1",
        "schema_version": 1,
        "source_manifest_path": str(source),
        "source_manifest_sha256": source_sha,
        "row_count": len(output_rows),
        "rows": output_rows,
        "revalidation_sha256": "0" * 64,
    }
    artifact["revalidation_sha256"] = domain_hash(
        "TASK_ACCESS_REVALIDATION_V1",
        artifact,
        excluded_field="revalidation_sha256",
    )
    return artifact


def revalidate_task_access_file(
    *,
    source_manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    artifact = revalidate_task_access(
        source_manifest_path=source_manifest_path
    )
    write_new_json(output_path, artifact)
    return artifact


def load_task_access_revalidation(path: Path) -> dict[str, object]:
    source = ensure_regular_no_symlink(
        path, name="task-access revalidation"
    )
    payload = require_object(
        "task-access revalidation",
        strict_json_loads(source.read_bytes()),
    )
    exact_keyset(
        payload,
        {
            "schema_id",
            "schema_version",
            "source_manifest_path",
            "source_manifest_sha256",
            "row_count",
            "rows",
            "revalidation_sha256",
        },
        name="TASK_ACCESS_REVALIDATION_V1",
    )
    if payload["schema_id"] != "TASK_ACCESS_REVALIDATION_V1":
        raise ValueError("task-access revalidation schema mismatch")
    expected = domain_hash(
        "TASK_ACCESS_REVALIDATION_V1",
        payload,
        excluded_field="revalidation_sha256",
    )
    if payload["revalidation_sha256"] != expected:
        raise ValueError("task-access revalidation self-hash mismatch")
    return payload


def find_access_row(
    artifact: dict[str, object],
    *,
    task_id: str,
    gamefile_sha256: str,
) -> dict[str, object]:
    rows = artifact.get("rows")
    if not isinstance(rows, list):
        raise TypeError("task-access revalidation rows must be array")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("task_id") == task_id
        and row.get("gamefile_sha256") == gamefile_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            "task access row must be unique for task/gamefile, "
            f"observed={len(matches)}"
        )
    return matches[0]
