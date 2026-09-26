from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.canonical import canonical_json_bytes
from pchsi.reference_loop.task_access import revalidate_task_access


def _write(path: Path, rows) -> Path:
    path.write_bytes(canonical_json_bytes(rows))
    return path


def test_task_access_never_upgrades_historically_exposed_benchmark(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "access.json",
        [
            {
                "task_id": "ood-1",
                "task_gamefile_group_id": "a" * 64,
                "gamefile_sha256": "b" * 64,
                "split": "valid_unseen",
                "historical_exposure_class": "ROUND1_EXPOSED",
                "historically_exposed": True,
                "access_class": (
                    "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_"
                    "HISTORICALLY_EXPOSED"
                ),
            }
        ],
    )
    result = revalidate_task_access(source_manifest_path=path)
    row = result["rows"][0]

    assert row["revalidation_disposition"] == "CONFIRMED_UNCHANGED"
    assert row["strong_model_allowed"] is False
    assert row["training_allowed"] is False
    assert "UPGRADED" not in row["revalidation_disposition"]


def test_task_access_blocks_one_gamefile_with_conflicting_classes(
    tmp_path: Path,
) -> None:
    common = {
        "gamefile_sha256": "c" * 64,
        "split": "train",
        "historical_exposure_class": "NO_REGISTERED_ROUND1_EXPOSURE",
        "historically_exposed": False,
    }
    path = _write(
        tmp_path / "access.json",
        [
            {
                **common,
                "task_id": "t1",
                "task_gamefile_group_id": "d" * 64,
                "access_class": "TRAIN_MEMORY_SOURCE",
            },
            {
                **common,
                "task_id": "t2",
                "task_gamefile_group_id": "e" * 64,
                "access_class": "TRAIN_RETRIEVAL_DEV",
            },
        ],
    )
    result = revalidate_task_access(source_manifest_path=path)

    assert {
        row["revalidation_disposition"] for row in result["rows"]
    } == {"BLOCKED_INCONSISTENT_SOURCE_AUTHORITY"}
