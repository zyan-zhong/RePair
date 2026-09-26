from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile


EXPECTED_HEAD = 'daef26b9cde45182ada534d96335da3ea451f12f'
FIXED_HEAD_REVIEW = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "GENERIC_SELECT_POLICY_ARTIFACT_BINDING_HUMAN_OFFOFF_REVIEW_V1.zip"
)
EXPECTED_FIXED_HEAD_REVIEW_SHA = '842d6e6549ab2de8e9b29ab30fddcd6d34f0d4c5d15436d4360f1a43e30fc4fe'
TARGET_WT = Path('/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-generic-select-policy-binding-human-offoff-v1')
TASK_ACCESS = Path('/data/home/scwb204/pchsi_evidence/p1b_materialized_access_v1/task_access_manifest.json')
P1B_POLICY_CONDITION = Path('/data/home/scwb204/pchsi_evidence/p1b_materialized_access_v1/policy_condition_manifest.json')
PARENT_ADAPTER_PATH = Path('/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_checkpoint_set_v1_frozen/seed_17/adapter')
CANDIDATE_ADAPTER_PATH = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_v1/human-t2-train17-continuation-v1-a000/adapter')
PARENT_TRAINING_CONFIG = Path('/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_training_config_v1/training_config.json')
CANDIDATE_TRAINING_CONTRACT = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/round_generic_training_stage_v2_1_hardening_build/profiles/human_reference_t2/ROUND_LOCAL_TRAINING_CONTRACT_V1.json')
OUTPUT_ROOT = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/human_t2_twin_offoff_binding_build_v1_1_output')
OUTPUT_ZIP = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_V1_1.zip')
PYTHON = Path('/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python')

TASK_ACCESS_SHA = (
    "5b8859a50478601cc054423af88fb57f5"
    "c31d95b96aeb67ab528987274eb9718"
)
PARENT_ADAPTER_SHA = (
    "b296f2254b1fa1f2e141dffd3f6b5af"
    "903f839df4790ffcb245fd8dd57773ace"
)
CANDIDATE_ADAPTER_SHA = (
    "908acf081e80008800284653c3340c39"
    "7353eef0de08ee044f06810cab2a251e"
)
PARENT_TRAINING_CONFIG_SHA = (
    "a860a77890e34e4cfcb38dff0acdf35d"
    "b0a3605d0a494c100f2b74b9f5228f9c"
)
CANDIDATE_TRAINING_CONTRACT_SHA = (
    "d23339bc42f665f88bf4156550a030f5"
    "950b75d9d8bf813825a58627830ccf31"
)

PARENT_LOGICAL = "P4-R1-Q2-BAD"
PARENT_CHECKPOINT = "P4-R1-Q2-BAD-TRAIN17"
CANDIDATE_LOGICAL = "P4-R2-HUMAN-T2-DIAGNOSTIC"
CANDIDATE_CHECKPOINT = (
    "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17"
)

EXPECTED_CHANGED_PATHS = {
    "configs/evaluation/schemas/"
    "select_policy_runtime_manifest_v1.json",
    "configs/evaluation/schemas/"
    "select_server_runtime_manifest_v1.json",
    "src/pchsi/evaluation/select_execution_identity.py",
    "src/pchsi/evaluation/select_policy_runtime.py",
    "src/pchsi/evaluation/select_result_audit.py",
    "tests/evaluation/"
    "test_generic_select_policy_artifact_binding_v1.py",
}

EXPECTED_REPLICATE_SEEDS = (17, 31, 47, 73, 101)


class Stop(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def domain_sha256(
    schema_id: str,
    value: dict,
    sha_field: str,
) -> str:
    payload = {
        key: child
        for key, child in value.items()
        if key != sha_field
    }
    return hashlib.sha256(
        schema_id.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    ).hexdigest()


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    log: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "$ " + " ".join(args)
            + "\n\n"
            + result.stdout
            + "\n--- STDERR ---\n"
            + result.stderr,
            encoding="utf-8",
        )
    return result


def git(*args: str) -> str:
    result = run(
        ["git", *args],
        cwd=TARGET_WT,
    )
    if result.returncode != 0:
        raise Stop(
            "GIT_FAILED:"
            + " ".join(args)
            + ":"
            + result.stderr.strip()
        )
    return result.stdout.strip()


def require_regular_file(
    path: Path,
    expected_sha: str | None = None,
    label: str = "FILE",
) -> None:
    if not path.is_file() or path.is_symlink():
        raise Stop(f"{label}_INVALID:{path}")
    if expected_sha is not None:
        observed = sha256_file(path)
        if observed != expected_sha:
            raise Stop(
                f"{label}_SHA_CHANGED:"
                f"{observed}:{expected_sha}"
            )



def parse_git_status_porcelain_v1_z(raw: str) -> set[str]:
    """Return exact changed paths from git status --porcelain=v1 -z."""
    if not isinstance(raw, str):
        raise TypeError("raw status must be str")

    entries = raw.split("\0")
    if entries and entries[-1] == "":
        entries.pop()

    paths: set[str] = set()
    index = 0

    while index < len(entries):
        entry = entries[index]

        if len(entry) < 4 or entry[2] != " ":
            raise Stop(
                "TARGET_PORCELAIN_STATUS_ENTRY_INVALID:"
                + repr(entry)
            )

        status = entry[:2]
        path = entry[3:]

        if not path:
            raise Stop(
                "TARGET_PORCELAIN_STATUS_PATH_EMPTY:"
                + repr(entry)
            )

        if "R" in status or "C" in status:
            if index + 1 >= len(entries):
                raise Stop(
                    "TARGET_PORCELAIN_RENAME_SOURCE_MISSING:"
                    + repr(entry)
                )
            index += 1

        paths.add(path)
        index += 1

    return paths


def audit_fixed_head() -> dict:
    require_regular_file(
        FIXED_HEAD_REVIEW,
        EXPECTED_FIXED_HEAD_REVIEW_SHA,
        "FIXED_HEAD_REVIEW",
    )
    if not zipfile.is_zipfile(FIXED_HEAD_REVIEW):
        raise Stop("FIXED_HEAD_REVIEW_NOT_ZIP")
    with zipfile.ZipFile(FIXED_HEAD_REVIEW) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stop(
                f"FIXED_HEAD_REVIEW_BAD_MEMBER:{bad}"
            )

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    if head != EXPECTED_HEAD:
        raise Stop(
            f"TARGET_HEAD_CHANGED:{head}:{EXPECTED_HEAD}"
        )
    if branch != "":
        raise Stop(
            f"TARGET_WORKTREE_NOT_DETACHED:{branch}"
        )

    status_result = run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        cwd=TARGET_WT,
    )
    if status_result.returncode != 0:
        raise Stop(
            "TARGET_PORCELAIN_STATUS_FAILED:"
            + status_result.stderr.strip()
        )

    changed = parse_git_status_porcelain_v1_z(
        status_result.stdout
    )

    if changed != EXPECTED_CHANGED_PATHS:
        raise Stop(
            "TARGET_CHANGED_PATH_SET_MISMATCH:"
            + repr(sorted(changed))
        )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(TARGET_WT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    tests = (
        (
            "10_generic_focused.log",
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
            "20_legacy_select.log",
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
            "30_evaluation_suite.log",
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

    for log_name, command in tests:
        result = run(
            command,
            cwd=TARGET_WT,
            env=env,
            log=OUTPUT_ROOT / "logs" / log_name,
        )
        if result.returncode != 0:
            raise Stop(
                "FIXED_HEAD_TEST_FAILED:"
                + log_name
            )

    file_hashes = {}
    for path_text in sorted(EXPECTED_CHANGED_PATHS):
        path = TARGET_WT / path_text
        require_regular_file(path, label="CHANGED_FILE")
        file_hashes[path_text] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    freeze_payload = {
        "source_head": EXPECTED_HEAD,
        "changed_files": file_hashes,
    }
    freeze_sha = hashlib.sha256(
        canonical_json_bytes(freeze_payload)
    ).hexdigest()

    return {
        "source_head": head,
        "target_detached": True,
        "changed_paths": sorted(changed),
        "git_status_porcelain_v1_z_sha256": hashlib.sha256(
            status_result.stdout.encode("utf-8")
        ).hexdigest(),
        "changed_files": file_hashes,
        "generic_select_binding_freeze_root_sha256": (
            freeze_sha
        ),
    }


def load_task_access_and_anchor():
    sys.path.insert(0, str(TARGET_WT / "src"))

    from pchsi.evaluation.distillation_access import (
        TaskAccessManifestV1,
    )

    require_regular_file(
        TASK_ACCESS,
        TASK_ACCESS_SHA,
        "TASK_ACCESS",
    )
    value = TaskAccessManifestV1.from_json(
        TASK_ACCESS.read_bytes()
    )

    counts = Counter(
        record.access_class.value
        for record in value.records
    )
    expected = {
        "DEV_VISIBLE": 117,
        "SELECT_SUMMARY_ONLY": 17,
        "CONFIRMATORY_SEALED": 0,
        "HISTORICALLY_EXPOSED": 0,
    }
    observed = {
        key: counts.get(key, 0)
        for key in expected
    }
    if observed != expected:
        raise Stop(
            "TASK_ACCESS_CLASS_COUNTS_CHANGED:"
            + repr(observed)
            + ":"
            + repr(expected)
        )

    require_regular_file(
        P1B_POLICY_CONDITION,
        label="P1B_POLICY_CONDITION",
    )
    anchor = json.loads(
        P1B_POLICY_CONDITION.read_text(
            encoding="utf-8"
        )
    )
    if anchor.get("schema_id") != (
        "POLICY_CONDITION_MANIFEST_V1"
    ):
        raise Stop(
            "P1B_POLICY_CONDITION_SCHEMA_CHANGED"
        )

    return value, observed, anchor


def verify_adapter_and_training_artifacts() -> None:
    require_regular_file(
        PARENT_TRAINING_CONFIG,
        PARENT_TRAINING_CONFIG_SHA,
        "PARENT_TRAINING_CONFIG",
    )
    require_regular_file(
        CANDIDATE_TRAINING_CONTRACT,
        CANDIDATE_TRAINING_CONTRACT_SHA,
        "CANDIDATE_TRAINING_CONTRACT",
    )

    for path, label in (
        (
            PARENT_ADAPTER_PATH / "adapter_config.json",
            "PARENT_ADAPTER_CONFIG",
        ),
        (
            PARENT_ADAPTER_PATH / "adapter_model.safetensors",
            "PARENT_ADAPTER_MODEL",
        ),
        (
            CANDIDATE_ADAPTER_PATH / "adapter_config.json",
            "CANDIDATE_ADAPTER_CONFIG",
        ),
        (
            CANDIDATE_ADAPTER_PATH / "adapter_model.safetensors",
            "CANDIDATE_ADAPTER_MODEL",
        ),
    ):
        require_regular_file(
            path,
            label=label,
        )

    for root, expected, label in (
        (
            PARENT_ADAPTER_PATH,
            PARENT_ADAPTER_SHA,
            "PARENT",
        ),
        (
            CANDIDATE_ADAPTER_PATH,
            CANDIDATE_ADAPTER_SHA,
            "CANDIDATE",
        ),
    ):
        manifest = root.parent / "adapter_artifact_manifest.json"
        require_regular_file(
            manifest,
            label=label + "_ADAPTER_MANIFEST",
        )
        value = json.loads(
            manifest.read_text(encoding="utf-8")
        )
        observed = value.get(
            "adapter_bundle_sha256"
        )
        if observed != expected:
            raise Stop(
                f"{label}_ADAPTER_BUNDLE_SHA_CHANGED:"
                f"{observed}:{expected}"
            )


def build_twin_bindings(
    *,
    task_access,
    anchor: dict,
    fixed_head: dict,
    access_counts: dict,
) -> dict:
    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes as repo_canonical_json_bytes,
        sha256_bytes,
    )
    from pchsi.evaluation.condition_run_schedule import (
        ConditionRunPurpose,
        build_condition_run_schedule,
    )
    from pchsi.evaluation.distillation_access import (
        DistillationAccessClass,
    )
    from pchsi.evaluation.distillation_governance import (
        canonical_model_sha256,
    )
    from pchsi.evaluation.policy_condition import (
        CheckpointKind,
        PolicyConditionManifestV1,
        TrainingMethod,
    )
    from pchsi.evaluation.run_schedule import (
        REPLICATE_SEEDS,
    )
    from pchsi.evaluation.select_policy_runtime import (
        SelectPolicyRuntimeManifestV1,
        SelectServerRuntimeManifestV1,
        SelectStaticLoRARegistrationV1,
    )
    from pchsi.evaluation.select_result_audit import (
        validate_master_schedule_set,
    )

    if tuple(REPLICATE_SEEDS) != EXPECTED_REPLICATE_SEEDS:
        raise Stop(
            "REPLICATE_SEEDS_CHANGED:"
            + repr(REPLICATE_SEEDS)
        )

    base_repository = anchor.get(
        "base_model_repository"
    )
    base_revision = anchor.get(
        "base_model_revision"
    )
    tokenizer_identity_sha = anchor.get(
        "tokenizer_identity_manifest_sha256"
    )
    chat_template_sha = anchor.get(
        "chat_template_sha256"
    )
    raw_protocol_sha = anchor.get(
        "raw_protocol_sha256"
    )
    runtime_core_commit = anchor.get(
        "runtime_core_commit"
    )
    evaluator_commit = anchor.get(
        "evaluator_commit"
    )
    for name, value in (
        ("base_model_repository", base_repository),
        ("base_model_revision", base_revision),
        ("tokenizer_identity_manifest_sha256", tokenizer_identity_sha),
        ("chat_template_sha256", chat_template_sha),
        ("raw_protocol_sha256", raw_protocol_sha),
        ("runtime_core_commit", runtime_core_commit),
        ("evaluator_commit", evaluator_commit),
    ):
        if not isinstance(value, str) or not value:
            raise Stop(
                "PROTOCOL_ANCHOR_FIELD_INVALID:"
                + name
            )

    parent_registration = (
        SelectStaticLoRARegistrationV1(
            logical_condition_id=PARENT_LOGICAL,
            checkpoint_instance_id=PARENT_CHECKPOINT,
            training_seed=17,
            served_model_name=PARENT_CHECKPOINT,
            adapter_path=str(PARENT_ADAPTER_PATH),
            adapter_bundle_sha256=PARENT_ADAPTER_SHA,
            adapter_rank=16,
        )
    )
    candidate_registration = (
        SelectStaticLoRARegistrationV1(
            logical_condition_id=CANDIDATE_LOGICAL,
            checkpoint_instance_id=CANDIDATE_CHECKPOINT,
            training_seed=17,
            served_model_name=CANDIDATE_CHECKPOINT,
            adapter_path=str(CANDIDATE_ADAPTER_PATH),
            adapter_bundle_sha256=CANDIDATE_ADAPTER_SHA,
            adapter_rank=16,
        )
    )

    server = SelectServerRuntimeManifestV1(
        schema_id="SELECT_SERVER_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id=(
            "HUMAN_T2_TWIN_OFFOFF_SELECT_SERVER_RUNTIME_V1"
        ),
        vllm_version="0.11.0",
        base_model_repository=base_repository,
        base_model_revision=base_revision,
        tokenizer_identity_manifest_sha256=(
            tokenizer_identity_sha
        ),
        chat_template_sha256=chat_template_sha,
        dtype="bfloat16",
        tensor_parallel_size=1,
        generation_config_mode="vllm",
        chat_template_content_format="string",
        enable_lora=True,
        max_lora_rank=16,
        max_loras=1,
        max_cpu_loras=2,
        lora_dtype="auto",
        runtime_dynamic_lora_updates=False,
        static_lora_registry=(
            parent_registration,
            candidate_registration,
        ),
    )
    server_sha = sha256_bytes(
        repo_canonical_json_bytes(
            server.to_dict()
        )
    )

    def make_runtime(
        *,
        logical: str,
        checkpoint: str,
        adapter_path: Path,
        adapter_sha: str,
    ):
        runtime = SelectPolicyRuntimeManifestV1(
            schema_id="SELECT_POLICY_RUNTIME_MANIFEST_V1",
            schema_version=1,
            manifest_id=(
                "SELECT_POLICY_RUNTIME_"
                + checkpoint
            ),
            server_runtime_manifest_sha256=(
                server_sha
            ),
            policy_condition_id=checkpoint,
            logical_condition_id=logical,
            checkpoint_instance_id=checkpoint,
            training_seed=17,
            served_model_name=checkpoint,
            adapter_path=str(adapter_path),
            adapter_bundle_sha256=adapter_sha,
            adapter_rank=16,
        )
        runtime_sha = sha256_bytes(
            repo_canonical_json_bytes(
                runtime.to_dict()
            )
        )
        return runtime, runtime_sha

    parent_runtime, parent_runtime_sha = make_runtime(
        logical=PARENT_LOGICAL,
        checkpoint=PARENT_CHECKPOINT,
        adapter_path=PARENT_ADAPTER_PATH,
        adapter_sha=PARENT_ADAPTER_SHA,
    )
    candidate_runtime, candidate_runtime_sha = (
        make_runtime(
            logical=CANDIDATE_LOGICAL,
            checkpoint=CANDIDATE_CHECKPOINT,
            adapter_path=CANDIDATE_ADAPTER_PATH,
            adapter_sha=CANDIDATE_ADAPTER_SHA,
        )
    )

    def make_condition(
        *,
        condition_id: str,
        checkpoint_path: Path,
        checkpoint_sha: str,
        training_run_id: str,
        training_config_sha: str,
        runtime_sha: str,
        served_model_name: str,
        policy_version: str,
    ):
        return PolicyConditionManifestV1(
            schema_id="POLICY_CONDITION_MANIFEST_V1",
            schema_version=1,
            policy_condition_id=condition_id,
            base_model_repository=base_repository,
            base_model_revision=base_revision,
            checkpoint_kind=CheckpointKind.LORA_ADAPTER,
            checkpoint_path=str(checkpoint_path),
            checkpoint_sha256=checkpoint_sha,
            training_method=TrainingMethod.SFT,
            training_run_id=training_run_id,
            training_config_sha256=(
                training_config_sha
            ),
            policy_runtime_manifest_sha256=(
                runtime_sha
            ),
            tokenizer_identity_manifest_sha256=(
                tokenizer_identity_sha
            ),
            chat_template_sha256=chat_template_sha,
            served_model_name=served_model_name,
            policy_version=policy_version,
            memory_version="MEMORY_M0_V1",
            raw_protocol_sha256=raw_protocol_sha,
            runtime_core_commit=runtime_core_commit,
            evaluator_commit=evaluator_commit,
        )

    parent_condition = make_condition(
        condition_id=PARENT_CHECKPOINT,
        checkpoint_path=PARENT_ADAPTER_PATH,
        checkpoint_sha=PARENT_ADAPTER_SHA,
        training_run_id="P4-R1-Q2-BAD-SEED17",
        training_config_sha=PARENT_TRAINING_CONFIG_SHA,
        runtime_sha=parent_runtime_sha,
        served_model_name=PARENT_CHECKPOINT,
        policy_version="PI1_BAD",
    )
    candidate_condition = make_condition(
        condition_id=CANDIDATE_CHECKPOINT,
        checkpoint_path=CANDIDATE_ADAPTER_PATH,
        checkpoint_sha=CANDIDATE_ADAPTER_SHA,
        training_run_id=(
            "HUMAN-T2-TRAIN17-CONTINUATION-V1"
        ),
        training_config_sha=(
            CANDIDATE_TRAINING_CONTRACT_SHA
        ),
        runtime_sha=candidate_runtime_sha,
        served_model_name=CANDIDATE_CHECKPOINT,
        policy_version=CANDIDATE_LOGICAL,
    )

    parent_condition_sha = (
        canonical_model_sha256(
            parent_condition
        )
    )
    candidate_condition_sha = (
        canonical_model_sha256(
            candidate_condition
        )
    )

    task_access_sha = (
        canonical_model_sha256(
            task_access
        )
    )
    if task_access_sha != TASK_ACCESS_SHA:
        raise Stop(
            "TASK_ACCESS_CANONICAL_SHA_CHANGED:"
            + task_access_sha
        )

    parent_schedule = build_condition_run_schedule(
        task_access_manifest=task_access,
        task_access_manifest_sha256=TASK_ACCESS_SHA,
        policy_condition=parent_condition,
        policy_condition_manifest_sha256=(
            parent_condition_sha
        ),
        run_purpose=(
            ConditionRunPurpose.P4_HARNESS_OFF_SELECT
        ),
        target_access_class=(
            DistillationAccessClass.SELECT_SUMMARY_ONLY
        ),
        replicate_seeds=REPLICATE_SEEDS,
        output_namespace=(
            "human_t2_offoff_parent_pi1_v1"
        ),
    )
    candidate_schedule = build_condition_run_schedule(
        task_access_manifest=task_access,
        task_access_manifest_sha256=TASK_ACCESS_SHA,
        policy_condition=candidate_condition,
        policy_condition_manifest_sha256=(
            candidate_condition_sha
        ),
        run_purpose=(
            ConditionRunPurpose.P4_HARNESS_OFF_SELECT
        ),
        target_access_class=(
            DistillationAccessClass.SELECT_SUMMARY_ONLY
        ),
        replicate_seeds=REPLICATE_SEEDS,
        output_namespace=(
            "human_t2_offoff_candidate_pi2_v1"
        ),
    )

    parent_schedule_sha = canonical_model_sha256(
        parent_schedule
    )
    candidate_schedule_sha = (
        canonical_model_sha256(
            candidate_schedule
        )
    )

    validate_master_schedule_set(
        schedules={
            "parent_pi1": parent_schedule,
            "candidate_pi2": candidate_schedule,
        },
        authorized_schedule_sha256={
            "parent_pi1": parent_schedule_sha,
            "candidate_pi2": candidate_schedule_sha,
        },
    )

    parent_grid = tuple(
        (
            cell.manifest_index,
            cell.task_id,
            cell.seed,
        )
        for cell in parent_schedule.cells
    )
    candidate_grid = tuple(
        (
            cell.manifest_index,
            cell.task_id,
            cell.seed,
        )
        for cell in candidate_schedule.cells
    )
    if parent_grid != candidate_grid:
        raise Stop(
            "TWIN_SCHEDULE_GRID_MISMATCH"
        )
    if len(parent_grid) != 85:
        raise Stop(
            "TWIN_SCHEDULE_CELL_COUNT_CHANGED:"
            + str(len(parent_grid))
        )

    selected_tasks = tuple(
        record
        for record in task_access.records
        if (
            record.access_class.value
            == "SELECT_SUMMARY_ONLY"
        )
    )
    if len(selected_tasks) != 17:
        raise Stop(
            "SELECT_TASK_COUNT_CHANGED"
        )

    artifacts = {
        "SELECT_SERVER_RUNTIME_MANIFEST_V1.json":
            server.to_dict(),
        "PARENT_SELECT_POLICY_RUNTIME_MANIFEST_V1.json":
            parent_runtime.to_dict(),
        "CANDIDATE_SELECT_POLICY_RUNTIME_MANIFEST_V1.json":
            candidate_runtime.to_dict(),
        "PARENT_POLICY_CONDITION_MANIFEST_V1.json":
            parent_condition.to_dict(),
        "CANDIDATE_POLICY_CONDITION_MANIFEST_V1.json":
            candidate_condition.to_dict(),
        "PARENT_CONDITION_RUN_SCHEDULE_V1.json":
            parent_schedule.to_dict(),
        "CANDIDATE_CONDITION_RUN_SCHEDULE_V1.json":
            candidate_schedule.to_dict(),
    }

    protocol = {
        "schema_id": "HUMAN_T2_TWIN_OFFOFF_PROTOCOL_EQUALITY_V1",
        "schema_version": 1,
        "status": "PASS",
        "evaluation_context": "P4_HARNESS_OFF_SELECT",
        "memory_state": "OFF",
        "harness_state": "OFF",
        "task_access_manifest_sha256": TASK_ACCESS_SHA,
        "task_access_class_counts": access_counts,
        "selected_task_count": 17,
        "replicate_seeds": list(REPLICATE_SEEDS),
        "paired_cell_count": 85,
        "total_condition_cell_count": 170,
        "grid_equal": True,
        "shared_server_runtime_manifest_sha256": (
            server_sha
        ),
        "shared_base_model_repository": base_repository,
        "shared_base_model_revision": base_revision,
        "shared_tokenizer_identity_manifest_sha256": (
            tokenizer_identity_sha
        ),
        "shared_chat_template_sha256": chat_template_sha,
        "shared_raw_protocol_sha256": raw_protocol_sha,
        "shared_runtime_core_commit": runtime_core_commit,
        "shared_evaluator_commit": evaluator_commit,
        "generic_select_binding_freeze_root_sha256": (
            fixed_head[
                "generic_select_binding_freeze_root_sha256"
            ]
        ),
        "parent": {
            "logical_condition_id": PARENT_LOGICAL,
            "checkpoint_instance_id": PARENT_CHECKPOINT,
            "adapter_bundle_sha256": PARENT_ADAPTER_SHA,
            "policy_runtime_manifest_sha256": (
                parent_runtime_sha
            ),
            "policy_condition_manifest_sha256": (
                parent_condition_sha
            ),
            "condition_run_schedule_sha256": (
                parent_schedule_sha
            ),
        },
        "candidate": {
            "logical_condition_id": CANDIDATE_LOGICAL,
            "checkpoint_instance_id": CANDIDATE_CHECKPOINT,
            "adapter_bundle_sha256": CANDIDATE_ADAPTER_SHA,
            "policy_runtime_manifest_sha256": (
                candidate_runtime_sha
            ),
            "policy_condition_manifest_sha256": (
                candidate_condition_sha
            ),
            "condition_run_schedule_sha256": (
                candidate_schedule_sha
            ),
            "diagnostic_only": True,
            "promotion_eligible": False,
        },
        "allowed_condition_differences": [
            "logical_condition_id",
            "checkpoint_instance_id",
            "served_model_name",
            "adapter_path",
            "adapter_bundle_sha256",
            "training_run_id",
            "training_config_sha256",
            "policy_version",
            "policy_condition_manifest_sha256",
            "policy_runtime_manifest_sha256",
            "condition_cell_id",
            "condition_run_schedule_sha256",
            "output_namespace",
        ],
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "protocol_equality_sha256": "",
    }
    protocol[
        "protocol_equality_sha256"
    ] = domain_sha256(
        protocol["schema_id"],
        protocol,
        "protocol_equality_sha256",
    )

    handoff = {
        "schema_id": "HUMAN_T2_OFFOFF_EXECUTION_HANDOFF_V1",
        "schema_version": 1,
        "status": "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "evaluation_context": "P4_HARNESS_OFF_SELECT",
        "parent_policy_id": PARENT_CHECKPOINT,
        "candidate_policy_id": CANDIDATE_CHECKPOINT,
        "parent_adapter_bundle_sha256": PARENT_ADAPTER_SHA,
        "candidate_adapter_bundle_sha256": CANDIDATE_ADAPTER_SHA,
        "task_access_manifest_sha256": TASK_ACCESS_SHA,
        "select_task_count": 17,
        "replicate_seeds": list(REPLICATE_SEEDS),
        "paired_cell_count": 85,
        "total_condition_cell_count": 170,
        "memory_off": True,
        "harness_off": True,
        "protocol_equality_sha256": protocol[
            "protocol_equality_sha256"
        ],
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "promotion_decision_authorized": False,
        "promotion_eligible": False,
        "next_gate": (
            "OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS"
        ),
        "handoff_sha256": "",
    }
    handoff["handoff_sha256"] = domain_sha256(
        handoff["schema_id"],
        handoff,
        "handoff_sha256",
    )

    return artifacts, protocol, handoff, {
        "server_runtime_sha256": server_sha,
        "parent_runtime_sha256": parent_runtime_sha,
        "candidate_runtime_sha256": candidate_runtime_sha,
        "parent_condition_sha256": parent_condition_sha,
        "candidate_condition_sha256": candidate_condition_sha,
        "parent_schedule_sha256": parent_schedule_sha,
        "candidate_schedule_sha256": candidate_schedule_sha,
    }


def write_review(
    *,
    fixed_head: dict,
    access_counts: dict,
    artifacts: dict,
    protocol: dict,
    handoff: dict,
    identities: dict,
) -> None:
    if OUTPUT_ROOT.exists():
        raise Stop(
            f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}"
        )
    if OUTPUT_ZIP.exists():
        raise Stop(
            f"OUTPUT_ZIP_ALREADY_EXISTS:{OUTPUT_ZIP}"
        )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=False,
    )

    bind_root = OUTPUT_ROOT / "bindings"
    bind_root.mkdir(
        parents=True,
        exist_ok=False,
    )
    for name, value in artifacts.items():
        (bind_root / name).write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    (OUTPUT_ROOT / "TWIN_OFFOFF_PROTOCOL_EQUALITY_V1.json").write_text(
        json.dumps(
            protocol,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "OFFOFF_EXECUTION_HANDOFF_V1.json").write_text(
        json.dumps(
            handoff,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "FIXED_HEAD_AUDIT_V1.json").write_text(
        json.dumps(
            fixed_head,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "IDENTITY_SHA256_V1.json").write_text(
        json.dumps(
            identities,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_id": "HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_MANIFEST_V1",
        "schema_version": 1,
        "review_status": "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
        "source_head": EXPECTED_HEAD,
        "generic_select_fixed_head_review_sha256": (
            EXPECTED_FIXED_HEAD_REVIEW_SHA
        ),
        "generic_select_binding_freeze_root_sha256": (
            fixed_head[
                "generic_select_binding_freeze_root_sha256"
            ]
        ),
        "task_access_manifest_sha256": TASK_ACCESS_SHA,
        "task_access_class_counts": access_counts,
        "select_task_count": 17,
        "replicate_seeds": list(
            EXPECTED_REPLICATE_SEEDS
        ),
        "paired_cell_count": 85,
        "total_condition_cell_count": 170,
        "parent_adapter_bundle_sha256": (
            PARENT_ADAPTER_SHA
        ),
        "candidate_adapter_bundle_sha256": (
            CANDIDATE_ADAPTER_SHA
        ),
        "protocol_equality_sha256": protocol[
            "protocol_equality_sha256"
        ],
        "offoff_handoff_sha256": handoff[
            "handoff_sha256"
        ],
        "evaluation_execution_authorized": False,
        "evaluation_execution_count": 0,
        "promotion_decision_authorized": False,
        "repository_commit_created": False,
        "repository_push_executed": False,
        "files": [],
        "next_gate": (
            "OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS"
        ),
    }

    files = []
    for path in sorted(
        OUTPUT_ROOT.rglob("*")
    ):
        if not path.is_file():
            continue
        files.append({
            "path": str(
                path.relative_to(OUTPUT_ROOT)
            ),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    manifest["files"] = files

    (OUTPUT_ROOT / "REVIEW_MANIFEST_V1.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(
            OUTPUT_ROOT.rglob("*")
        ):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(
                        OUTPUT_ROOT
                    ).as_posix(),
                )

    if not zipfile.is_zipfile(OUTPUT_ZIP):
        raise Stop(
            "OUTPUT_ZIP_INVALID"
        )
    with zipfile.ZipFile(
        OUTPUT_ZIP,
        "r",
    ) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stop(
                f"OUTPUT_ZIP_BAD_MEMBER:{bad}"
            )


def main() -> int:
    # Logs must be writable before fixed-head tests run.
    if OUTPUT_ROOT.exists():
        raise Stop(
            f"OUTPUT_ROOT_ALREADY_EXISTS:{OUTPUT_ROOT}"
        )
    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=False,
    )
    try:
        fixed_head = audit_fixed_head()
        task_access, access_counts, anchor = (
            load_task_access_and_anchor()
        )
        verify_adapter_and_training_artifacts()

        artifacts, protocol, handoff, identities = (
            build_twin_bindings(
                task_access=task_access,
                anchor=anchor,
                fixed_head=fixed_head,
                access_counts=access_counts,
            )
        )

        # Keep already-written test logs; write all review artifacts in the same root.
        bind_root = OUTPUT_ROOT / "bindings"
        bind_root.mkdir(parents=True, exist_ok=False)
        for name, value in artifacts.items():
            (bind_root / name).write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        for name, value in (
            ("TWIN_OFFOFF_PROTOCOL_EQUALITY_V1.json", protocol),
            ("OFFOFF_EXECUTION_HANDOFF_V1.json", handoff),
            ("FIXED_HEAD_AUDIT_V1.json", fixed_head),
            ("IDENTITY_SHA256_V1.json", identities),
        ):
            (OUTPUT_ROOT / name).write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        manifest = {
            "schema_id": "HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_MANIFEST_V1",
            "schema_version": 1,
            "review_status": "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
            "source_head": EXPECTED_HEAD,
            "generic_select_fixed_head_review_sha256": (
                EXPECTED_FIXED_HEAD_REVIEW_SHA
            ),
            "generic_select_binding_freeze_root_sha256": (
                fixed_head[
                    "generic_select_binding_freeze_root_sha256"
                ]
            ),
            "task_access_manifest_sha256": TASK_ACCESS_SHA,
            "task_access_class_counts": access_counts,
            "select_task_count": 17,
            "replicate_seeds": list(
                EXPECTED_REPLICATE_SEEDS
            ),
            "paired_cell_count": 85,
            "total_condition_cell_count": 170,
            "parent_adapter_bundle_sha256": PARENT_ADAPTER_SHA,
            "candidate_adapter_bundle_sha256": CANDIDATE_ADAPTER_SHA,
            "protocol_equality_sha256": protocol[
                "protocol_equality_sha256"
            ],
            "offoff_handoff_sha256": handoff[
                "handoff_sha256"
            ],
            "evaluation_execution_authorized": False,
            "evaluation_execution_count": 0,
            "promotion_decision_authorized": False,
            "repository_commit_created": False,
            "repository_push_executed": False,
            "files": [],
            "next_gate": (
                "OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS"
            ),
        }

        files = []
        for path in sorted(
            OUTPUT_ROOT.rglob("*")
        ):
            if not path.is_file():
                continue
            files.append({
                "path": str(
                    path.relative_to(OUTPUT_ROOT)
                ),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            })
        manifest["files"] = files

        (OUTPUT_ROOT / "REVIEW_MANIFEST_V1.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        if OUTPUT_ZIP.exists():
            raise Stop(
                f"OUTPUT_ZIP_ALREADY_EXISTS:{OUTPUT_ZIP}"
            )
        with zipfile.ZipFile(
            OUTPUT_ZIP,
            "x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in sorted(
                OUTPUT_ROOT.rglob("*")
            ):
                if path.is_file():
                    archive.write(
                        path,
                        path.relative_to(
                            OUTPUT_ROOT
                        ).as_posix(),
                    )
        if not zipfile.is_zipfile(
            OUTPUT_ZIP
        ):
            raise Stop(
                "OUTPUT_ZIP_INVALID"
            )
        with zipfile.ZipFile(
            OUTPUT_ZIP
        ) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise Stop(
                    f"OUTPUT_ZIP_BAD_MEMBER:{bad}"
                )

        print(
            "HUMAN_T2_TWIN_OFFOFF_BINDING_BUILD_PASS"
        )
        print(
            "GENERIC_SELECT_BINDING_FREEZE_ROOT_SHA256="
            + fixed_head[
                "generic_select_binding_freeze_root_sha256"
            ]
        )
        print(
            "TASK_ACCESS_CLASS_DEV_VISIBLE=117"
        )
        print(
            "TASK_ACCESS_CLASS_SELECT_SUMMARY_ONLY=17"
        )
        print(
            "TASK_ACCESS_CLASS_CONFIRMATORY_SEALED=0"
        )
        print(
            "TASK_ACCESS_CLASS_HISTORICALLY_EXPOSED=0"
        )
        print(
            "REPLICATE_SEEDS=[17,31,47,73,101]"
        )
        print(
            "PARENT_CELL_COUNT=85"
        )
        print(
            "CANDIDATE_CELL_COUNT=85"
        )
        print(
            "PAIRED_CELL_COUNT=85"
        )
        print(
            "TOTAL_CONDITION_CELL_COUNT=170"
        )
        print(
            "PROTOCOL_EQUALITY_SHA256="
            + protocol[
                "protocol_equality_sha256"
            ]
        )
        print(
            "OFFOFF_HANDOFF_SHA256="
            + handoff["handoff_sha256"]
        )
        print(
            "EVALUATION_EXECUTION_AUTHORIZED=false"
        )
        print(
            "EVALUATION_EXECUTION_COUNT=0"
        )
        print(
            "PROMOTION_DECISION_AUTHORIZED=false"
        )
        print(
            "REPOSITORY_COMMIT_CREATED=false"
        )
        print(
            "REPOSITORY_PUSH_EXECUTED=false"
        )
        print(
            "REVIEW_ZIP="
            + str(OUTPUT_ZIP)
        )
        print(
            "REVIEW_ZIP_SHA256="
            + sha256_file(OUTPUT_ZIP)
        )
        print(
            "NEXT_GATE=OFFOFF_EXECUTION_AUTHORIZATION_"
            "AND_RUNTIME_READINESS"
        )
        return 0
    except Exception:
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        raise SystemExit(
            "STOP=" + str(exc)
        )
