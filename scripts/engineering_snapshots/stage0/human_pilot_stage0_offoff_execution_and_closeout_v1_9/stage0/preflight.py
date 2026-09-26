from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile
from typing import Any, Iterable

from .common import (
    Stage0Error,
    domain_sha256,
    load_json_object,
    require_file_sha,
    require_lower_sha256,
    sha256_file,
    strict_json_loads,
    write_or_reuse_exact,
)
from .constants import (
    BASE_MODEL_PATH,
    BASE_MODEL_REVISION,
    CANDIDATE_ADAPTER_PATH,
    CANDIDATE_ADAPTER_SHA256,
    E1_DESIGN_MERGE_COMMIT,
    E1_POLICY_REQUEST_SCHEMA_SHA256,
    E1_POLICY_REQUEST_SOURCE_RELATIVE_PATH,
    E1_READINESS_ROOT,
    EXECUTION_ROOT,
    EXPECTED_SOURCE_HEAD,
    GENERIC_FIXED_HEAD_REVIEW,
    GENERIC_FIXED_HEAD_REVIEW_SHA256,
    GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT,
    GENERIC_WORKTREE,
    PARENT_ADAPTER_PATH,
    PARENT_ADAPTER_SHA256,
    PREFLIGHT_ROOT,
    PYTHON,
    ROUND_ROOT,
    TASK_ACCESS,
    TASK_ACCESS_SHA256,
    TWIN_REVIEW,
    TWIN_REVIEW_SHA256,
)
from .attempt_recovery import (
    audit_stage0_resume_state,
)
from .twin_contract import load_twin_review

EXPECTED_CHANGED_PATHS = {
    "configs/evaluation/schemas/e1_episode_artifact_v1.json",
    "configs/evaluation/schemas/select_policy_runtime_manifest_v1.json",
    "configs/evaluation/schemas/select_server_runtime_manifest_v1.json",
    "src/pchsi/evaluation/action_trace.py",
    "src/pchsi/evaluation/schema_models.py",
    "src/pchsi/evaluation/select_execution_identity.py",
    "src/pchsi/evaluation/select_policy_runtime.py",
    "src/pchsi/evaluation/select_result_audit.py",
    "tests/evaluation/test_generic_select_artifact_identity_v1.py",
    "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py",
}


def _run(command: list[str], *, cwd: Path, log_path: Path) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
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
        "$ " + " ".join(command)
        + "\n\n"
        + result.stdout
        + "\n--- STDERR ---\n"
        + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise Stage0Error(f"PREFLIGHT_TEST_FAILED:{log_path.name}")


def _parse_status_z(raw: str) -> set[str]:
    entries = raw.split("\0")
    if entries and entries[-1] == "":
        entries.pop()
    result: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        if len(entry) < 4 or entry[2] != " ":
            raise Stage0Error(f"GIT_STATUS_ENTRY_INVALID:{entry!r}")
        status = entry[:2]
        result.add(entry[3:])
        if "R" in status or "C" in status:
            index += 1
        index += 1
    return result


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=GENERIC_WORKTREE,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise Stage0Error("GIT_FAILED:" + result.stderr.strip())
    return result.stdout


def _unique_recursive_string(
    values: list[Any],
    *,
    key: str,
) -> str:
    observed: set[str] = set()
    for value in values:
        observed.update(
            _collect_key_strings(
                value,
                key=key,
            )
        )
    if len(observed) != 1:
        raise Stage0Error(
            "READINESS_AUTHORITY_NOT_UNIQUE:"
            + key
            + ":"
            + repr(sorted(observed))
        )
    return next(iter(observed))


def audit_materialized_readiness_authority(
    readiness_root: Path,
) -> dict[str, Any]:
    summary_path = readiness_root / "readiness_summary.json"
    summary = load_json_object(summary_path)
    if summary.get("real_environment_executed") is not False:
        raise Stage0Error(
            "READINESS_SUMMARY_REPORTS_ENVIRONMENT_EXECUTION"
        )
    if summary.get("model_called") is not False:
        raise Stage0Error(
            "READINESS_SUMMARY_REPORTS_MODEL_EXECUTION"
        )

    artifact_map = {
        "gamefile_identity_manifest_sha256":
            readiness_root / "e1_gamefile_sha256_preflight_v1.json",
        "environment_runtime_manifest_sha256":
            readiness_root / "alfworld_environment_runtime_manifest_v1.json",
        "policy_runtime_manifest_sha256":
            readiness_root / "e1_policy_runtime_manifest_v1.json",
        "tokenizer_identity_manifest_sha256":
            readiness_root / "tokenizer_identity_manifest.json",
        "candidate_config_sha256":
            readiness_root / "e1_evaluator_candidate_config_v1.json",
    }
    objects: list[Any] = [summary]
    result: dict[str, Any] = {
        "readiness_summary_path": str(summary_path),
        "readiness_summary_sha256": sha256_file(summary_path),
    }
    for key, artifact_path in artifact_map.items():
        expected = summary.get(key)
        require_lower_sha256(key, expected)
        require_file_sha(
            artifact_path,
            expected,
            "READINESS_" + key.upper(),
        )
        value = load_json_object(artifact_path)
        objects.append(value)
        result[key] = expected
        result[key.replace("_sha256", "_path")] = str(
            artifact_path
        )

    environment = objects[2]
    if environment.get("schema_id") != (
        "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1"
    ):
        raise Stage0Error(
            "MATERIALIZED_ENVIRONMENT_RUNTIME_SCHEMA_CHANGED"
        )

    return result


def _collect_key_strings(
    value: Any,
    *,
    key: str,
) -> set[str]:
    results: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key == key and isinstance(child, str):
                results.add(child)
            results.update(
                _collect_key_strings(
                    child,
                    key=key,
                )
            )
    elif isinstance(value, list):
        for child in value:
            results.update(
                _collect_key_strings(
                    child,
                    key=key,
                )
            )
    return results


def audit_policy_request_source_authority(
    *,
    worktree: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    require_lower_sha256(
        "policy_request_schema_sha256",
        expected_sha256,
    )
    source_path = (
        worktree
        / E1_POLICY_REQUEST_SOURCE_RELATIVE_PATH
    )
    require_file_sha(
        source_path,
        expected_sha256,
        "POLICY_REQUEST_SOURCE",
    )
    return {
        "policy_request_source_path":
            str(source_path),
        "policy_request_schema_sha256":
            expected_sha256,
    }


def discover_policy_request_schema_authority(
    *,
    roots: Iterable[Path],
) -> dict[str, Any]:
    observed: dict[str, list[str]] = {}
    inspected = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size > 8 * 1024 * 1024
            ):
                continue
            lowered = path.name.lower()
            if (
                "episode" not in lowered
                and "attempt" not in lowered
                and "readiness" not in lowered
                and "manifest" not in lowered
            ):
                continue
            inspected += 1
            try:
                value = strict_json_loads(path.read_bytes())
            except Exception:
                continue
            for digest in _collect_key_strings(
                value,
                key="policy_request_schema_sha256",
            ):
                try:
                    require_lower_sha256(
                        "policy_request_schema_sha256",
                        digest,
                    )
                except Stage0Error:
                    continue
                observed.setdefault(digest, []).append(str(path))

    if len(observed) != 1:
        raise Stage0Error(
            "POLICY_REQUEST_SCHEMA_AUTHORITY_NOT_UNIQUE:"
            + json.dumps(
                {
                    digest: paths[:20]
                    for digest, paths in sorted(observed.items())
                },
                sort_keys=True,
            )
        )
    digest, paths = next(iter(sorted(observed.items())))
    return {
        "policy_request_schema_sha256": digest,
        "supporting_artifact_count": len(paths),
        "supporting_artifact_paths": sorted(paths)[:20],
        "inspected_json_file_count": inspected,
    }


def _task_access_counts() -> dict[str, int]:
    require_file_sha(TASK_ACCESS, TASK_ACCESS_SHA256, "TASK_ACCESS")
    payload = strict_json_loads(TASK_ACCESS.read_bytes())
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("records"), list)
    ):
        raise Stage0Error("TASK_ACCESS_WIRE_INVALID")
    counts = Counter(
        row.get("access_class")
        for row in payload["records"]
        if isinstance(row, dict)
    )
    expected = {
        "DEV_VISIBLE": 117,
        "SELECT_SUMMARY_ONLY": 17,
        "CONFIRMATORY_SEALED": 0,
        "HISTORICALLY_EXPOSED": 0,
    }
    observed = {key: counts.get(key, 0) for key in expected}
    if observed != expected or len(payload["records"]) != 134:
        raise Stage0Error(f"TASK_ACCESS_COUNTS_CHANGED:{observed}")
    return observed


def _adapter_audit(root: Path, expected_sha: str, label: str) -> None:
    for name in ("adapter_config.json", "adapter_model.safetensors"):
        path = root / name
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size <= 0
        ):
            raise Stage0Error(f"{label}_{name}_INVALID")
    manifest = root.parent / "adapter_artifact_manifest.json"
    value = load_json_object(manifest)
    if value.get("adapter_bundle_sha256") != expected_sha:
        raise Stage0Error(f"{label}_ADAPTER_BUNDLE_CHANGED")



def _audit_generic_select_artifact_patch_receipt() -> dict[str, Any]:
    value = load_json_object(
        GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT
    )
    if value.get("patch_status") != "PASS":
        raise Stage0Error(
            "GENERIC_SELECT_ARTIFACT_PATCH_NOT_PASS"
        )
    if value.get("source_head") != EXPECTED_SOURCE_HEAD:
        raise Stage0Error(
            "GENERIC_SELECT_ARTIFACT_PATCH_HEAD_CHANGED"
        )
    if value.get("changed_paths") != sorted(
        EXPECTED_CHANGED_PATHS
    ):
        raise Stage0Error(
            "GENERIC_SELECT_ARTIFACT_PATCH_PATHS_CHANGED"
        )
    hashes = value.get("changed_file_sha256")
    if not isinstance(hashes, dict):
        raise Stage0Error(
            "GENERIC_SELECT_ARTIFACT_PATCH_HASH_MAP_INVALID"
        )
    for relative in sorted(
        EXPECTED_CHANGED_PATHS
    ):
        expected = hashes.get(relative)
        if (
            not isinstance(expected, str)
            or len(expected) != 64
        ):
            raise Stage0Error(
                "GENERIC_SELECT_ARTIFACT_PATCH_HASH_INVALID:"
                + relative
            )
        path = GENERIC_WORKTREE / relative
        require_file_sha(
            path,
            expected,
            "GENERIC_SELECT_ARTIFACT_PATCH_FILE",
        )
    freeze = value.get(
        "generic_select_artifact_patch_freeze_root_sha256"
    )
    require_lower_sha256(
        "generic_select_artifact_patch_freeze_root_sha256",
        freeze,
    )
    return value


def _fixed_head_audit() -> dict[str, Any]:
    require_file_sha(
        GENERIC_FIXED_HEAD_REVIEW,
        GENERIC_FIXED_HEAD_REVIEW_SHA256,
        "GENERIC_FIXED_HEAD_REVIEW",
    )
    if not zipfile.is_zipfile(GENERIC_FIXED_HEAD_REVIEW):
        raise Stage0Error("GENERIC_FIXED_HEAD_REVIEW_NOT_ZIP")
    with zipfile.ZipFile(GENERIC_FIXED_HEAD_REVIEW) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stage0Error(
                f"GENERIC_FIXED_HEAD_REVIEW_BAD_MEMBER:{bad}"
            )
        fixed = strict_json_loads(
            archive.read("FIXED_HEAD_REVIEW_V1.json")
        )
        if not isinstance(fixed, dict):
            raise Stage0Error("GENERIC_FIXED_HEAD_OBJECT_INVALID")

    head = _git("rev-parse", "HEAD").strip()
    branch = _git("branch", "--show-current").strip()
    if head != EXPECTED_SOURCE_HEAD or branch:
        raise Stage0Error(
            f"GENERIC_WORKTREE_IDENTITY_CHANGED:{head}:{branch}"
        )
    status = subprocess.run(
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
    if status.returncode != 0:
        raise Stage0Error("GENERIC_WORKTREE_STATUS_FAILED")
    changed = _parse_status_z(status.stdout)
    if changed != EXPECTED_CHANGED_PATHS:
        raise Stage0Error(
            f"GENERIC_WORKTREE_CHANGED_PATHS:{sorted(changed)}"
        )
    patch = _audit_generic_select_artifact_patch_receipt()
    result = dict(fixed)
    result[
        "generic_select_artifact_patch_freeze_root_sha256"
    ] = patch[
        "generic_select_artifact_patch_freeze_root_sha256"
    ]
    return result



def audit_first_select_cell_binding_contract(
    *,
    twin: dict[str, Any],
    readiness: dict[str, Any],
    policy_request: dict[str, Any],
) -> dict[str, Any]:
    repo_src = str(
        GENERIC_WORKTREE / "src"
    )
    if repo_src not in sys.path:
        sys.path.insert(
            0,
            repo_src,
        )

    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes as repo_canonical_json_bytes,
        sha256_bytes,
    )
    from pchsi.evaluation.condition_run_schedule import (
        ConditionRunScheduleV1,
    )
    from pchsi.evaluation.distillation_access import (
        TaskAccessManifestV1,
    )
    from pchsi.evaluation.distillation_governance import (
        canonical_model_sha256,
    )
    from pchsi.evaluation.episode_evaluator import (
        EpisodeExecutionConfig,
    )
    from pchsi.evaluation.policy_condition import (
        PolicyConditionManifestV1,
    )
    from pchsi.evaluation.run_schedule import (
        execution_attempt_id,
    )
    from pchsi.evaluation.select_execution_identity import (
        bind_select_condition_cell,
        build_select_execution_profile,
        validate_select_execution_profile_binding,
    )
    from pchsi.evaluation.select_policy_runtime import (
        SelectPolicyRuntimeManifestV1,
    )
    from pchsi.evaluation.task_manifest import (
        FrozenTaskRecord,
    )

    from .live_runner import (
        _bound_cell_fields,
        _execution_identity,
        _traj_file,
    )

    task_access = (
        TaskAccessManifestV1.from_json(
            TASK_ACCESS.read_bytes()
        )
    )
    access_by_index = {
        row.manifest_index: row
        for row in task_access.records
    }

    values = twin["values"]
    results = []

    for prefix in (
        "PARENT",
        "CANDIDATE",
    ):
        condition = (
            PolicyConditionManifestV1.from_dict(
                values[
                    "bindings/"
                    + prefix
                    + "_POLICY_CONDITION_MANIFEST_V1.json"
                ]
            )
        )
        runtime = (
            SelectPolicyRuntimeManifestV1.from_dict(
                values[
                    "bindings/"
                    + prefix
                    + "_SELECT_POLICY_RUNTIME_MANIFEST_V1.json"
                ]
            )
        )
        schedule = (
            ConditionRunScheduleV1.from_dict(
                values[
                    "bindings/"
                    + prefix
                    + "_CONDITION_RUN_SCHEDULE_V1.json"
                ]
            )
        )
        if len(schedule.cells) != 85:
            raise Stage0Error(
                "PREFLIGHT_SELECT_SCHEDULE_CELL_COUNT_CHANGED:"
                + prefix
                + ":"
                + str(len(schedule.cells))
            )

        cell = schedule.cells[0]
        access = access_by_index.get(
            cell.manifest_index
        )
        if access is None:
            raise Stage0Error(
                "PREFLIGHT_FIRST_SELECT_ACCESS_MISSING:"
                + prefix
            )

        condition_sha = (
            canonical_model_sha256(
                condition
            )
        )
        runtime_sha = sha256_bytes(
            repo_canonical_json_bytes(
                runtime.to_dict()
            )
        )
        schedule_sha = (
            canonical_model_sha256(
                schedule
            )
        )

        bound = bind_select_condition_cell(
            schedule_cell=cell,
            task_access=access,
            policy_condition=condition,
            policy_runtime=runtime,
            task_access_manifest_sha256=(
                TASK_ACCESS_SHA256
            ),
            policy_condition_manifest_sha256=(
                condition_sha
            ),
            condition_run_schedule_sha256=(
                schedule_sha
            ),
            select_policy_runtime_manifest_sha256=(
                runtime_sha
            ),
        )

        identity = _execution_identity(
            bound
        )
        (
            scheduled_cell_id,
            task_index,
            task_id,
            seed,
        ) = _bound_cell_fields(
            bound
        )

        if (
            scheduled_cell_id
            != cell.condition_cell_id
            or task_index
            != cell.manifest_index
            or task_id
            != cell.task_id
            or seed
            != cell.seed
        ):
            raise Stage0Error(
                "PREFLIGHT_FIRST_SELECT_BOUND_CELL_CHANGED:"
                + prefix
            )

        profile = (
            build_select_execution_profile(
                identity
            )
        )
        validate_select_execution_profile_binding(
            identity=identity,
            profile=profile,
        )

        gamefile = Path(
            access.gamefile
        )
        if (
            not gamefile.is_file()
            or gamefile.is_symlink()
        ):
            raise Stage0Error(
                "PREFLIGHT_FIRST_SELECT_GAMEFILE_INVALID:"
                + prefix
            )
        if (
            sha256_file(gamefile)
            != access.gamefile_sha256
        ):
            raise Stage0Error(
                "PREFLIGHT_FIRST_SELECT_GAMEFILE_SHA_CHANGED:"
                + prefix
            )

        task = FrozenTaskRecord(
            index=task_index,
            task_id=task_id,
            split=access.dataset_split,
            task_type=access.task_type,
            gamefile=str(gamefile),
            gamefile_sha1=(
                access.gamefile_sha1
            ),
            root=str(
                gamefile.parent
            ),
            traj_file=str(
                _traj_file(
                    gamefile
                )
            ),
        )

        attempt_id = execution_attempt_id(
            scheduled_cell_id=(
                scheduled_cell_id
            ),
            attempt_ordinal=0,
        )

        config = EpisodeExecutionConfig(
            run_id=(
                "human-pilot-stage0-preflight-"
                + prefix.lower()
            ),
            cell=bound,
            execution_attempt_id=attempt_id,
            attempt_ordinal=0,
            task=task,
            seed=seed,
            evaluator_commit=(
                condition.evaluator_commit
            ),
            design_merge_commit=(
                E1_DESIGN_MERGE_COMMIT
            ),
            runtime_core_commit=(
                condition.runtime_core_commit
            ),
            raw_protocol_sha256=(
                condition.raw_protocol_sha256
            ),
            split_access_sha256=(
                identity.task_access_manifest_sha256
            ),
            gamefile_identity_manifest_sha256=(
                readiness[
                    "gamefile_identity_manifest_sha256"
                ]
            ),
            environment_runtime_manifest_sha256=(
                readiness[
                    "environment_runtime_manifest_sha256"
                ]
            ),
            policy_runtime_manifest_sha256=(
                runtime_sha
            ),
            policy_request_schema_sha256=(
                policy_request[
                    "policy_request_schema_sha256"
                ]
            ),
            run_schedule_sha256=(
                schedule_sha
            ),
            gamefile_sha256=(
                access.gamefile_sha256
            ),
            task_access_manifest_sha256=(
                identity.task_access_manifest_sha256
            ),
            policy_condition_manifest_sha256=(
                identity.policy_condition_manifest_sha256
            ),
            condition_run_schedule_sha256=(
                identity.condition_run_schedule_sha256
            ),
            access_class=(
                identity.access_class
            ),
            policy_condition_id=(
                identity.policy_condition_id
            ),
            condition_cell_id=(
                identity.condition_cell_id
            ),
            evaluation_context=(
                identity.evaluation_context
            ),
            select_execution_identity=(
                identity
            ),
        )

        if config.cell is not bound:
            raise Stage0Error(
                "PREFLIGHT_FIRST_SELECT_CONFIG_CELL_CHANGED:"
                + prefix
            )

        results.append({
            "condition": prefix,
            "condition_cell_id":
                scheduled_cell_id,
            "manifest_index":
                task_index,
            "task_id":
                task_id,
            "seed":
                seed,
            "served_model_name":
                identity.served_model_name,
            "episode_execution_config":
                "PASS",
        })

    return {
        "status": "PASS",
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "conditions": results,
    }


def run_preflight(*, package_root: Path) -> dict[str, Any]:
    package_inventory = package_root / "PACKAGE_FILES.sha256"
    if not package_inventory.is_file():
        raise Stage0Error("PACKAGE_INVENTORY_MISSING")
    package_inventory_sha = sha256_file(package_inventory)

    require_file_sha(TWIN_REVIEW, TWIN_REVIEW_SHA256, "TWIN_REVIEW")
    twin = load_twin_review(TWIN_REVIEW)
    fixed = _fixed_head_audit()
    counts = _task_access_counts()
    _adapter_audit(
        PARENT_ADAPTER_PATH,
        PARENT_ADAPTER_SHA256,
        "PARENT",
    )
    _adapter_audit(
        CANDIDATE_ADAPTER_PATH,
        CANDIDATE_ADAPTER_SHA256,
        "CANDIDATE",
    )

    if not BASE_MODEL_PATH.is_dir() or BASE_MODEL_PATH.is_symlink():
        raise Stage0Error(
            f"BASE_MODEL_PATH_INVALID:{BASE_MODEL_PATH}"
        )
    if BASE_MODEL_PATH.name != BASE_MODEL_REVISION:
        raise Stage0Error("BASE_MODEL_REVISION_PATH_CHANGED")

    test_root = PREFLIGHT_ROOT / "logs"
    commands = (
        (
            "runtime_imports.log",
            [
                str(PYTHON),
                "-c",
                (
                    "import alfworld, textworld, torch, "
                    "transformers, vllm; "
                    'assert vllm.__version__ == "0.11.0"; '
                    'assert transformers.__version__ == "4.57.3"; '
                    'assert torch.__version__ == "2.8.0+cu128"; '
                    "print('vllm=' + vllm.__version__); "
                    "print('transformers=' + transformers.__version__); "
                    "print('torch=' + torch.__version__); "
                    "print('alfworld_import=PASS'); "
                    "print('textworld_import=PASS')"
                ),
            ],
        ),
        (
            "generic_focused.log",
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/evaluation/"
                "test_generic_select_policy_artifact_binding_v1.py",
            ],
        ),
        (
            "generic_artifact_identity.log",
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/evaluation/"
                "test_generic_select_artifact_identity_v1.py",
            ],
        ),
        (
            "legacy_select.log",
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/evaluation/"
                "test_p4_select_execution_compat_v1.py",
            ],
        ),
        (
            "evaluation_suite.log",
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/evaluation",
            ],
        ),
    )
    for name, command in commands:
        _run(
            command,
            cwd=GENERIC_WORKTREE,
            log_path=test_root / name,
        )

    readiness = audit_materialized_readiness_authority(
        E1_READINESS_ROOT
    )
    policy_request = (
        audit_policy_request_source_authority(
            worktree=GENERIC_WORKTREE,
            expected_sha256=(
                E1_POLICY_REQUEST_SCHEMA_SHA256
            ),
        )
    )

    first_select_cell_binding_audit = (
        audit_first_select_cell_binding_contract(
            twin=twin,
            readiness=readiness,
            policy_request=policy_request,
        )
    )

    resume_state_audit = (
        audit_stage0_resume_state(
            twin_values=twin["values"],
            execution_root=EXECUTION_ROOT,
        )
    )

    parent_condition = twin["values"][
        "bindings/PARENT_POLICY_CONDITION_MANIFEST_V1.json"
    ]
    receipt: dict[str, Any] = {
        "schema_id":
            "HUMAN_PILOT_STAGE0_OFFLINE_PREFLIGHT_RECEIPT_V1",
        "schema_version": 1,
        "preflight_status": "PASS",
        "package_inventory_sha256": package_inventory_sha,
        "source_head": EXPECTED_SOURCE_HEAD,
        "generic_select_binding_freeze_root_sha256": fixed.get(
            "generic_select_binding_freeze_root_sha256"
        ),
        "generic_select_artifact_patch_freeze_root_sha256":
            fixed.get(
                "generic_select_artifact_patch_freeze_root_sha256"
            ),
        "generic_fixed_head_review_sha256":
            GENERIC_FIXED_HEAD_REVIEW_SHA256,
        "twin_review_sha256": TWIN_REVIEW_SHA256,
        "task_access_manifest_sha256": TASK_ACCESS_SHA256,
        "task_access_class_counts": counts,
        "base_model_local_path": str(BASE_MODEL_PATH),
        "base_model_revision": BASE_MODEL_REVISION,
        "chat_template_sha256":
            parent_condition["chat_template_sha256"],
        "raw_protocol_sha256":
            parent_condition["raw_protocol_sha256"],
        "runtime_core_commit":
            parent_condition["runtime_core_commit"],
        "evaluator_commit":
            parent_condition["evaluator_commit"],
        "policy_request_schema_sha256": policy_request[
            "policy_request_schema_sha256"
        ],
        "policy_request_schema_supporting_artifact_count":
            1,
        "policy_request_schema_supporting_artifact_paths":
            [
                policy_request[
                    "policy_request_source_path"
                ]
            ],
        "readiness_summary_path":
            readiness["readiness_summary_path"],
        "readiness_summary_sha256":
            readiness["readiness_summary_sha256"],
        "environment_runtime_manifest_path":
            readiness["environment_runtime_manifest_path"],
        "environment_runtime_manifest_sha256":
            readiness["environment_runtime_manifest_sha256"],
        "gamefile_identity_manifest_path":
            readiness["gamefile_identity_manifest_path"],
        "gamefile_identity_manifest_sha256":
            readiness["gamefile_identity_manifest_sha256"],
        "tokenizer_identity_manifest_path":
            readiness["tokenizer_identity_manifest_path"],
        "tokenizer_identity_manifest_sha256":
            readiness["tokenizer_identity_manifest_sha256"],
        "candidate_config_path":
            readiness["candidate_config_path"],
        "candidate_config_sha256":
            readiness["candidate_config_sha256"],
        "design_merge_commit":
            E1_DESIGN_MERGE_COMMIT,
        "first_select_cell_binding_audit":
            first_select_cell_binding_audit,
        "resume_state_audit":
            resume_state_audit,
        "select_task_count": 17,
        "replicate_seeds": [17, 31, 47, 73, 101],
        "paired_cell_count": 85,
        "total_condition_cell_count": 170,
        "memory_off": True,
        "harness_off": True,
        "paper_efficacy_evidence": False,
        "promotion_eligible": False,
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "preflight_receipt_sha256": "",
    }
    receipt["preflight_receipt_sha256"] = domain_sha256(
        receipt["schema_id"],
        receipt,
        sha_field="preflight_receipt_sha256",
    )
    PREFLIGHT_ROOT.mkdir(parents=True, exist_ok=True)
    return write_or_reuse_exact(
        PREFLIGHT_ROOT / "OFFLINE_PREFLIGHT_RECEIPT_V1.json",
        receipt,
    )
