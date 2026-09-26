from __future__ import annotations

from pathlib import Path
import hashlib
import os
import shutil
import subprocess

from stage1_pkg.common import Stage1PackageError, canonical_json_bytes, write_new_json
from stage1_pkg.constants import (
    GENERIC_WORKTREE,
    OUTPUT_ROOT,
    PREEXISTING_CHANGED_PATHS,
    STAGE1_NEW_PATHS,
)
from stage1_pkg.worktree import file_manifest, status_paths, verify_head_and_detached


def run_pytest(args: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *args,
        ],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "PYTHONPATH": str(GENERIC_WORKTREE / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        result.stdout + "\n--- STDERR ---\n" + result.stderr,
        encoding="utf-8",
    )
    return result


def copy_tree_files(source_root: Path, destination_root: Path) -> None:
    for source in sorted(source_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        destination = destination_root / relative
        if destination.exists() or destination.is_symlink():
            raise Stage1PackageError(f"refusing overwrite: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> int:
    package_root = Path(__file__).resolve().parent
    verify_head_and_detached()
    if status_paths() != set(PREEXISTING_CHANGED_PATHS):
        raise Stage1PackageError("Stage1 prestate changed before apply")

    test_source = package_root / "payload/tests/round_control"
    target_tests = GENERIC_WORKTREE / "tests/round_control"
    if target_tests.exists():
        raise Stage1PackageError("round_control tests already exist")

    copy_tree_files(test_source, target_tests)

    red = run_pytest(
        ["tests/round_control"],
        OUTPUT_ROOT / "10_STAGE1_TDD_RED.log",
    )
    combined = red.stdout + "\n" + red.stderr
    if red.returncode == 0:
        raise Stage1PackageError("Stage1 RED unexpectedly passed")
    if (
        "pchsi.round_control" not in combined
        and "ModuleNotFoundError" not in combined
    ):
        raise Stage1PackageError("Stage1 RED failed for unexpected reason")

    source_payload = package_root / "payload/src/pchsi/round_control"
    target_source = GENERIC_WORKTREE / "src/pchsi/round_control"
    if target_source.exists():
        raise Stage1PackageError("round_control source already exists")
    copy_tree_files(source_payload, target_source)

    docs_payload = package_root / "payload/docs/stage1"
    target_docs = GENERIC_WORKTREE / "docs/stage1"
    if target_docs.exists():
        raise Stage1PackageError("Stage1 docs already exist")
    copy_tree_files(docs_payload, target_docs)

    green = run_pytest(
        ["tests/round_control"],
        OUTPUT_ROOT / "20_STAGE1_TDD_GREEN.log",
    )
    if green.returncode != 0:
        raise Stage1PackageError("Stage1 focused GREEN failed")

    research_tests = GENERIC_WORKTREE / "tests/research_intelligence"
    if research_tests.is_dir():
        result = run_pytest(
            ["tests/research_intelligence"],
            OUTPUT_ROOT / "30_RESEARCH_INTELLIGENCE_REGRESSION.log",
        )
        if result.returncode != 0:
            raise Stage1PackageError("research_intelligence regression failed")

    evaluation_tests = GENERIC_WORKTREE / "tests/evaluation"
    if evaluation_tests.is_dir():
        result = run_pytest(
            ["tests/evaluation"],
            OUTPUT_ROOT / "40_EVALUATION_REGRESSION.log",
        )
        if result.returncode != 0:
            raise Stage1PackageError("evaluation regression failed")

    expected = set(PREEXISTING_CHANGED_PATHS) | set(STAGE1_NEW_PATHS)
    observed = status_paths()
    if observed != expected:
        raise Stage1PackageError(
            "Stage1 changed path set mismatch: " + repr(sorted(observed))
        )

    manifest = file_manifest(set(STAGE1_NEW_PATHS))
    freeze_payload = {
        "source_head": "daef26b9cde45182ada534d96335da3ea451f12f",
        "stage1_new_files": manifest,
        "preexisting_stage0_paths": sorted(PREEXISTING_CHANGED_PATHS),
    }
    freeze_sha = hashlib.sha256(
        canonical_json_bytes(freeze_payload)
    ).hexdigest()

    receipt = {
        "schema_id": "STAGE1_CONTROL_PLANE_BUILD_RECEIPT_V1",
        "schema_version": 1,
        "build_status": "PASS",
        "stage1_control_plane_freeze_root_sha256": freeze_sha,
        "stage1_new_file_manifest": manifest,
        "changed_paths_after_build": sorted(observed),
        "repository_commit_created": False,
        "repository_push_executed": False,
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
    }
    write_new_json(
        OUTPUT_ROOT / "STAGE1_CONTROL_PLANE_BUILD_RECEIPT_V1.json",
        receipt,
    )
    print("STAGE1_CONTROL_PLANE_BUILD_PASS")
    print("STAGE1_CONTROL_PLANE_FREEZE_ROOT_SHA256=" + freeze_sha)
    print("REPOSITORY_COMMIT_CREATED=false")
    print("REPOSITORY_PUSH_EXECUTED=false")
    print("MODEL_EXECUTION_COUNT=0")
    print("ENVIRONMENT_EXECUTION_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
