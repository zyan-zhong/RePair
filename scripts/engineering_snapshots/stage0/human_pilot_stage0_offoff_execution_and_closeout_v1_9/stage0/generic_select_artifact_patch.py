from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .common import (
    Stage0Error,
    canonical_json_bytes,
    sha256_file,
    write_or_reuse_exact,
)
from .constants import (
    EXPECTED_SOURCE_HEAD,
    GENERIC_SELECT_ARTIFACT_PATCH_ROOT,
    GENERIC_WORKTREE,
)

BASE_CHANGED_PATHS = {
    "configs/evaluation/schemas/select_policy_runtime_manifest_v1.json",
    "configs/evaluation/schemas/select_server_runtime_manifest_v1.json",
    "src/pchsi/evaluation/select_execution_identity.py",
    "src/pchsi/evaluation/select_policy_runtime.py",
    "src/pchsi/evaluation/select_result_audit.py",
    "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py",
}

ARTIFACT_PATCH_PATHS = {
    "configs/evaluation/schemas/e1_episode_artifact_v1.json",
    "src/pchsi/evaluation/action_trace.py",
    "src/pchsi/evaluation/schema_models.py",
    "tests/evaluation/test_generic_select_artifact_identity_v1.py",
}

TARGET_CHANGED_PATHS = BASE_CHANGED_PATHS | ARTIFACT_PATCH_PATHS

REGRESSION_TEST_RELATIVE_PATH = (
    "tests/evaluation/test_generic_select_artifact_identity_v1.py"
)


def patch_action_trace_source(source: str) -> str:
    old = '''            elif (
                self.logical_condition_id
                == "P4-R1-Q2-BAD"
            ):
                if self.training_seed is None:
                    raise ValueError(
                        "SELECT pi1 trace requires training_seed"
                    )

                if (
                    self.model_name
                    != self.checkpoint_instance_id
                ):
                    raise ValueError(
                        "SELECT pi1 model/checkpoint mismatch"
                    )

            else:
                raise ValueError(
                    "unknown SELECT logical condition"
                )
'''
    new = '''            else:
                if self.training_seed is None:
                    raise ValueError(
                        "SELECT trained trace requires training_seed"
                    )

                if (
                    self.model_name
                    != self.checkpoint_instance_id
                ):
                    raise ValueError(
                        "SELECT trained model/checkpoint mismatch"
                    )
'''
    count = source.count(old)
    if count != 1:
        raise Stage0Error(
            "ACTION_TRACE_PATCH_ANCHOR_CHANGED:"
            + str(count)
        )
    return source.replace(old, new, 1)


def patch_schema_models_source(source: str) -> str:
    old = '''            elif (
                self.logical_condition_id
                == "P4-R1-Q2-BAD"
            ):
                if (
                    type(self.training_seed)
                    is not int
                    or self.training_seed < 0
                ):
                    raise ValueError(
                        "SELECT pi1 episode requires "
                        "non-negative training_seed"
                    )

            else:
                raise ValueError(
                    "unknown SELECT logical condition"
                )
'''
    new = '''            else:
                if (
                    type(self.training_seed)
                    is not int
                    or self.training_seed < 0
                ):
                    raise ValueError(
                        "SELECT trained episode requires "
                        "non-negative training_seed"
                    )
'''
    count = source.count(old)
    if count != 1:
        raise Stage0Error(
            "SCHEMA_MODELS_PATCH_ANCHOR_CHANGED:"
            + str(count)
        )
    return source.replace(old, new, 1)


def patch_episode_artifact_schema(
    value: dict[str, Any],
) -> dict[str, Any]:
    logical = (
        value
        .get("properties", {})
        .get("logical_condition_id")
    )
    if not isinstance(logical, dict):
        raise Stage0Error(
            "EPISODE_ARTIFACT_SCHEMA_LOGICAL_FIELD_MISSING"
        )
    expected = [
        "P4-R0-PI0",
        "P4-R1-Q2-BAD",
    ]
    if logical.get("enum") != expected:
        raise Stage0Error(
            "EPISODE_ARTIFACT_SCHEMA_LOGICAL_ENUM_CHANGED:"
            + repr(logical.get("enum"))
        )
    logical = dict(logical)
    logical.pop("enum")
    logical["minLength"] = 1
    logical["pattern"] = (
        "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    )
    result = dict(value)
    properties = dict(result["properties"])
    properties["logical_condition_id"] = logical
    result["properties"] = properties
    return result


def _run(
    args: list[str],
    *,
    cwd: Path,
    log_path: Path,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "PYTHONPATH": str(cwd / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    log_path.write_text(
        "$ "
        + " ".join(args)
        + "\n\n"
        + result.stdout
        + "\n--- STDERR ---\n"
        + result.stderr,
        encoding="utf-8",
    )
    return result


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_GIT_STATUS_FAILED:"
            + result.stderr.strip()
        )
    entries = result.stdout.split("\0")
    if entries and entries[-1] == "":
        entries.pop()
    paths: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        if len(entry) < 4 or entry[2] != " ":
            raise Stage0Error(
                "ARTIFACT_PATCH_STATUS_ENTRY_INVALID:"
                + repr(entry)
            )
        status = entry[:2]
        paths.add(entry[3:])
        if "R" in status or "C" in status:
            index += 1
        index += 1
    return paths


def _git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_GIT_FAILED:"
            + " ".join(args)
            + ":"
            + result.stderr.strip()
        )
    return result.stdout


def _file_hashes(paths: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in sorted(paths):
        path = GENERIC_WORKTREE / relative
        if not path.is_file() or path.is_symlink():
            raise Stage0Error(
                "ARTIFACT_PATCH_CHANGED_FILE_INVALID:"
                + str(path)
            )
        result[relative] = sha256_file(path)
    return result


def _build_receipt(
    *,
    focused_log: Path,
    legacy_log: Path,
    evaluation_log: Path,
) -> dict[str, Any]:
    diff = _git_text(
        "diff",
        "--binary",
        "--",
        *sorted(TARGET_CHANGED_PATHS),
    )
    hashes = _file_hashes(
        TARGET_CHANGED_PATHS
    )
    freeze_payload = {
        "source_head": EXPECTED_SOURCE_HEAD,
        "changed_files": hashes,
        "diff_sha256": hashlib.sha256(
            diff.encode("utf-8")
        ).hexdigest(),
    }
    freeze_sha = hashlib.sha256(
        canonical_json_bytes(
            freeze_payload
        )
    ).hexdigest()
    return {
        "schema_id":
            "GENERIC_SELECT_ARTIFACT_IDENTITY_PATCH_RECEIPT_V1",
        "schema_version": 1,
        "patch_status": "PASS",
        "source_head": EXPECTED_SOURCE_HEAD,
        "changed_paths":
            sorted(TARGET_CHANGED_PATHS),
        "changed_file_sha256": hashes,
        "git_diff_sha256":
            freeze_payload["diff_sha256"],
        "generic_select_artifact_patch_freeze_root_sha256":
            freeze_sha,
        "focused_regression_log_sha256":
            sha256_file(focused_log),
        "legacy_select_log_sha256":
            sha256_file(legacy_log),
        "evaluation_suite_log_sha256":
            sha256_file(evaluation_log),
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
        "repository_commit_created": False,
        "repository_push_executed": False,
    }


def _verify_existing_patch_receipt(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise Stage0Error(
            "ARTIFACT_PATCH_RECEIPT_MISSING"
        )
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )
    if value.get("patch_status") != "PASS":
        raise Stage0Error(
            "ARTIFACT_PATCH_RECEIPT_NOT_PASS"
        )
    if value.get("source_head") != EXPECTED_SOURCE_HEAD:
        raise Stage0Error(
            "ARTIFACT_PATCH_RECEIPT_HEAD_CHANGED"
        )
    if value.get("changed_paths") != sorted(
        TARGET_CHANGED_PATHS
    ):
        raise Stage0Error(
            "ARTIFACT_PATCH_RECEIPT_PATHS_CHANGED"
        )
    current = _file_hashes(
        TARGET_CHANGED_PATHS
    )
    if value.get("changed_file_sha256") != current:
        raise Stage0Error(
            "ARTIFACT_PATCH_RECEIPT_FILE_HASH_CHANGED"
        )
    return value


def apply_or_verify_generic_select_artifact_patch(
    *,
    package_root: Path,
) -> dict[str, Any]:
    if not GENERIC_WORKTREE.is_dir():
        raise Stage0Error(
            "GENERIC_WORKTREE_MISSING"
        )
    head = _git_text(
        "rev-parse",
        "HEAD",
    ).strip()
    branch = _git_text(
        "branch",
        "--show-current",
    ).strip()
    if head != EXPECTED_SOURCE_HEAD:
        raise Stage0Error(
            "ARTIFACT_PATCH_SOURCE_HEAD_CHANGED:"
            + head
        )
    if branch:
        raise Stage0Error(
            "ARTIFACT_PATCH_WORKTREE_NOT_DETACHED:"
            + branch
        )

    GENERIC_SELECT_ARTIFACT_PATCH_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )
    receipt_path = (
        GENERIC_SELECT_ARTIFACT_PATCH_ROOT
        / "GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT_V1.json"
    )

    status_paths = _git_status_paths()
    if status_paths == TARGET_CHANGED_PATHS:
        return _verify_existing_patch_receipt(
            receipt_path
        )
    if status_paths != BASE_CHANGED_PATHS:
        raise Stage0Error(
            "ARTIFACT_PATCH_PRESTATE_CHANGED:"
            + repr(sorted(status_paths))
        )

    regression_source = (
        package_root
        / "payload/"
        "test_generic_select_artifact_identity_v1.py"
    )
    regression_target = (
        GENERIC_WORKTREE
        / REGRESSION_TEST_RELATIVE_PATH
    )
    if regression_target.exists():
        raise Stage0Error(
            "ARTIFACT_PATCH_REGRESSION_TEST_ALREADY_EXISTS"
        )
    regression_target.write_bytes(
        regression_source.read_bytes()
    )

    red_log = (
        GENERIC_SELECT_ARTIFACT_PATCH_ROOT
        / "10_RED.log"
    )
    red = _run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            REGRESSION_TEST_RELATIVE_PATH,
        ],
        cwd=GENERIC_WORKTREE,
        log_path=red_log,
    )
    if red.returncode == 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_RED_UNEXPECTEDLY_PASSED"
        )
    combined = (
        red.stdout
        + "\n"
        + red.stderr
    )
    if (
        "unknown SELECT logical condition"
        not in combined
        and "P4-R2-HUMAN-T2-DIAGNOSTIC"
        not in combined
    ):
        raise Stage0Error(
            "ARTIFACT_PATCH_RED_FAILED_FOR_UNEXPECTED_REASON"
        )

    action_trace_path = (
        GENERIC_WORKTREE
        / "src/pchsi/evaluation/action_trace.py"
    )
    schema_models_path = (
        GENERIC_WORKTREE
        / "src/pchsi/evaluation/schema_models.py"
    )
    episode_schema_path = (
        GENERIC_WORKTREE
        / "configs/evaluation/schemas/"
        "e1_episode_artifact_v1.json"
    )

    action_trace_path.write_text(
        patch_action_trace_source(
            action_trace_path.read_text(
                encoding="utf-8"
            )
        ),
        encoding="utf-8",
    )
    schema_models_path.write_text(
        patch_schema_models_source(
            schema_models_path.read_text(
                encoding="utf-8"
            )
        ),
        encoding="utf-8",
    )
    episode_schema = json.loads(
        episode_schema_path.read_text(
            encoding="utf-8"
        )
    )
    episode_schema_path.write_text(
        json.dumps(
            patch_episode_artifact_schema(
                episode_schema
            ),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    observed_paths = _git_status_paths()
    if observed_paths != TARGET_CHANGED_PATHS:
        raise Stage0Error(
            "ARTIFACT_PATCH_TARGET_PATH_SET_CHANGED:"
            + repr(sorted(observed_paths))
        )

    focused_log = (
        GENERIC_SELECT_ARTIFACT_PATCH_ROOT
        / "20_FOCUSED_GREEN.log"
    )
    focused = _run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            REGRESSION_TEST_RELATIVE_PATH,
        ],
        cwd=GENERIC_WORKTREE,
        log_path=focused_log,
    )
    if focused.returncode != 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_FOCUSED_GREEN_FAILED"
        )

    legacy_log = (
        GENERIC_SELECT_ARTIFACT_PATCH_ROOT
        / "30_LEGACY_SELECT.log"
    )
    legacy = _run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/evaluation/"
            "test_p4_select_execution_compat_v1.py",
        ],
        cwd=GENERIC_WORKTREE,
        log_path=legacy_log,
    )
    if legacy.returncode != 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_LEGACY_SELECT_FAILED"
        )

    evaluation_log = (
        GENERIC_SELECT_ARTIFACT_PATCH_ROOT
        / "40_EVALUATION_SUITE.log"
    )
    evaluation = _run(
        [
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/evaluation",
        ],
        cwd=GENERIC_WORKTREE,
        log_path=evaluation_log,
    )
    if evaluation.returncode != 0:
        raise Stage0Error(
            "ARTIFACT_PATCH_EVALUATION_SUITE_FAILED"
        )

    receipt = _build_receipt(
        focused_log=focused_log,
        legacy_log=legacy_log,
        evaluation_log=evaluation_log,
    )
    return write_or_reuse_exact(
        receipt_path,
        receipt,
    )
