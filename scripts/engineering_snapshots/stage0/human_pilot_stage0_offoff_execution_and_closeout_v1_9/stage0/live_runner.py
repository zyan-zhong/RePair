from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from .common import (
    Stage0Error,
    domain_sha256,
    load_json_object,
    sha256_file,
)
from .constants import (
    AUTHORIZATION_ROOT,
    BASE_MODEL_PATH,
    CANDIDATE_CHECKPOINT_ID,
    EXECUTION_ROOT,
    EXPECTED_SOURCE_HEAD,
    GENERIC_WORKTREE,
    PARENT_CHECKPOINT_ID,
    PREFLIGHT_ROOT,
    STAGE0_ROOT,
    TASK_ACCESS,
    TASK_ACCESS_SHA256,
    TWIN_REVIEW,
)
from .attempt_recovery import (
    audit_cell_attempt_state,
)
from .receipts import (
    append_receipt,
    load_receipts,
    make_cell_receipt,
)
from .twin_contract import load_twin_review


def _load_attempt_auditor(repo_root: Path):
    path = repo_root / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    spec = importlib.util.spec_from_file_location(
        "_stage0_attempt_auditor",
        path,
    )
    if spec is None or spec.loader is None:
        raise Stage0Error("ATTEMPT_AUDITOR_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _traj_file(gamefile: Path) -> Path:
    for name in ("traj_data.json", "traj_data.jsonl"):
        candidate = gamefile.parent / name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return gamefile


def _execution_identity(bound):
    return getattr(
        bound,
        "execution_identity",
        bound,
    )


def _bound_cell_fields(bound) -> tuple[str, int, str, int]:
    scheduled_cell_id = getattr(
        bound,
        "scheduled_cell_id",
        None,
    )
    task_index = getattr(
        bound,
        "task_index",
        None,
    )
    task_id = getattr(
        bound,
        "task_id",
        None,
    )
    seed = getattr(
        bound,
        "seed",
        None,
    )
    if not isinstance(scheduled_cell_id, str) or not scheduled_cell_id:
        raise Stage0Error("BOUND_CELL_IDENTITY_MISSING")
    if type(task_index) is not int:
        raise Stage0Error("BOUND_CELL_TASK_INDEX_INVALID")
    if not isinstance(task_id, str) or not task_id:
        raise Stage0Error("BOUND_CELL_TASK_ID_INVALID")
    if type(seed) is not int:
        raise Stage0Error("BOUND_CELL_SEED_INVALID")
    return scheduled_cell_id, task_index, task_id, seed


def _wire_value(value):
    return getattr(value, "value", value)


def _validate_authorization() -> dict[str, Any]:
    path = AUTHORIZATION_ROOT / "STAGE0_EXECUTION_AUTHORIZATION_V1.json"
    value = load_json_object(path)
    if value.get("authorization_status") != "APPROVED":
        raise Stage0Error("STAGE0_AUTHORIZATION_NOT_APPROVED")
    expected = value.get("authorization_sha256")
    observed = domain_sha256(
        value["schema_id"],
        value,
        sha_field="authorization_sha256",
    )
    if expected != observed:
        raise Stage0Error("STAGE0_AUTHORIZATION_HASH_CHANGED")
    if value.get("paper_efficacy_evidence") is not False:
        raise Stage0Error("STAGE0_AUTHORIZATION_PAPER_BOUNDARY_CHANGED")
    if value.get("promotion_eligible") is not False:
        raise Stage0Error("STAGE0_AUTHORIZATION_PROMOTION_BOUNDARY_CHANGED")
    return value


def _load_repo_types():
    if str(GENERIC_WORKTREE / "src") not in sys.path:
        sys.path.insert(0, str(GENERIC_WORKTREE / "src"))
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    from pchsi.evaluation.artifact_publisher import ArtifactPublisher
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
    from pchsi.evaluation.condition_run_schedule import ConditionRunScheduleV1
    from pchsi.evaluation.distillation_access import TaskAccessManifestV1
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.episode_evaluator import (
        EpisodeDependencies,
        EpisodeExecutionConfig,
        run_single_episode,
    )
    from pchsi.evaluation.policy_client import HttpPolicyTransport, PolicyClient
    from pchsi.evaluation.policy_condition import PolicyConditionManifestV1
    from pchsi.evaluation.rendered_prompt import (
        HuggingFaceTokenizerFactory,
        LocalTokenizerPromptRenderer,
    )
    from pchsi.evaluation.run_schedule import execution_attempt_id
    from pchsi.evaluation.select_execution_identity import (
        bind_select_condition_cell,
        build_select_execution_profile,
        validate_select_execution_profile_binding,
    )
    from pchsi.evaluation.select_policy_runtime import SelectPolicyRuntimeManifestV1
    from pchsi.evaluation.task_manifest import FrozenTaskRecord
    return locals()


def _condition_bundle(
    *,
    values: dict[str, dict],
    prefix: str,
    types: dict[str, Any],
    task_access,
):
    condition = types["PolicyConditionManifestV1"].from_dict(
        values[f"bindings/{prefix}_POLICY_CONDITION_MANIFEST_V1.json"]
    )
    runtime = types["SelectPolicyRuntimeManifestV1"].from_dict(
        values[f"bindings/{prefix}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json"]
    )
    schedule = types["ConditionRunScheduleV1"].from_dict(
        values[f"bindings/{prefix}_CONDITION_RUN_SCHEDULE_V1.json"]
    )
    condition_sha = types["canonical_model_sha256"](condition)
    runtime_sha = types["sha256_bytes"](
        types["canonical_json_bytes"](runtime.to_dict())
    )
    schedule_sha = types["canonical_model_sha256"](schedule)
    if schedule.task_access_manifest_sha256 != TASK_ACCESS_SHA256:
        raise Stage0Error("LIVE_SCHEDULE_TASK_ACCESS_CHANGED")
    return condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha


def _recover_or_execute_cell(
    *,
    label: str,
    cell,
    task_access_record,
    condition,
    runtime,
    condition_sha: str,
    runtime_sha: str,
    schedule_sha: str,
    preflight: dict[str, Any],
    base_url: str,
    types: dict[str, Any],
    attempt_auditor,
    condition_root: Path,
) -> dict[str, Any]:
    bound = types["bind_select_condition_cell"](
        schedule_cell=cell,
        task_access=task_access_record,
        policy_condition=condition,
        policy_runtime=runtime,
        task_access_manifest_sha256=TASK_ACCESS_SHA256,
        policy_condition_manifest_sha256=condition_sha,
        condition_run_schedule_sha256=schedule_sha,
        select_policy_runtime_manifest_sha256=runtime_sha,
    )
    identity = _execution_identity(bound)
    profile = types["build_select_execution_profile"](identity)
    types["validate_select_execution_profile_binding"](
        identity=identity,
        profile=profile,
    )
    (
        scheduled_cell_id,
        task_index,
        task_id,
        seed,
    ) = _bound_cell_fields(bound)

    ledger = condition_root / "cell_receipts.jsonl"
    existing = load_receipts(ledger)
    by_cell = {row["condition_cell_id"]: row for row in existing}
    if scheduled_cell_id in by_cell:
        return by_cell[scheduled_cell_id]

    evaluator_root = condition_root / "evaluator_run"
    recovery = audit_cell_attempt_state(
        evaluator_root=evaluator_root,
        scheduled_cell_id=scheduled_cell_id,
    )
    previous = (
        None
        if not existing
        else existing[-1]["receipt_sha256"]
    )

    published_attempt_ids = recovery[
        "published_attempt_ids"
    ]
    if published_attempt_ids:
        attempt_id = published_attempt_ids[0]
        attempt_dir = (
            evaluator_root
            / "attempts"
            / attempt_id
        )
        loaded = attempt_auditor.load_attempt_directory_v1(
            attempt_dir
        )
        if loaded.episode_artifact.task_id != task_id:
            raise Stage0Error(
                "RECOVERED_ATTEMPT_TASK_CHANGED"
            )
        if type(loaded.episode_artifact.success) is not bool:
            raise Stage0Error(
                "RECOVERED_ATTEMPT_NO_SCIENTIFIC_OUTCOME"
            )
        receipt = make_cell_receipt(
            condition_id=condition.policy_condition_id,
            condition_cell_id=scheduled_cell_id,
            manifest_index=task_index,
            task_id=task_id,
            seed=seed,
            execution_attempt_id=attempt_id,
            attempt_bundle_sha256=(
                loaded.attempt_bundle.attempt_bundle_sha256
            ),
            success=loaded.episode_artifact.success,
            termination_reason=loaded.episode_artifact.termination_reason,
            previous_receipt_sha256=previous,
        )
        append_receipt(
            ledger,
            receipt,
        )
        return receipt

    attempt_ordinal = recovery[
        "next_attempt_ordinal"
    ]
    if type(attempt_ordinal) is not int:
        raise Stage0Error(
            "NEXT_ATTEMPT_ORDINAL_UNAVAILABLE:"
            + scheduled_cell_id
        )
    attempt_id = types["execution_attempt_id"](
        scheduled_cell_id=scheduled_cell_id,
        attempt_ordinal=attempt_ordinal,
    )
    if (
        attempt_id
        != recovery[
            "next_execution_attempt_id"
        ]
    ):
        raise Stage0Error(
            "NEXT_ATTEMPT_IDENTITY_CHANGED:"
            + scheduled_cell_id
        )

    attempt_dir = (
        evaluator_root
        / "attempts"
        / attempt_id
    )

    gamefile = Path(task_access_record.gamefile)
    if gamefile.is_symlink() or not gamefile.is_file():
        raise Stage0Error(f"LIVE_GAMEFILE_INVALID:{gamefile}")
    if sha256_file(gamefile) != task_access_record.gamefile_sha256:
        raise Stage0Error("LIVE_GAMEFILE_SHA256_CHANGED")
    if _sha1_file(gamefile) != task_access_record.gamefile_sha1:
        raise Stage0Error("LIVE_GAMEFILE_SHA1_CHANGED")

    task = types["FrozenTaskRecord"](
        index=task_index,
        task_id=task_id,
        split=_wire_value(task_access_record.dataset_split),
        task_type=_wire_value(task_access_record.task_type),
        gamefile=str(gamefile),
        gamefile_sha1=task_access_record.gamefile_sha1,
        root=str(gamefile.parent),
        traj_file=str(_traj_file(gamefile)),
    )
    environment = types["SpawnedAlfworldAdapter"].start(
        exact_gamefile=gamefile,
        registration_id=(
            "human-stage0-"
            + label.lower()
            + "-"
            + f"{task_index:05d}"
            + "-"
            + str(seed)
        ),
        runtime_manifest_sha256=preflight[
            "environment_runtime_manifest_sha256"
        ],
    )
    try:
        renderer = types["LocalTokenizerPromptRenderer"](
            model_path=str(BASE_MODEL_PATH),
            revision=preflight["base_model_revision"],
            chat_template_sha256=preflight["chat_template_sha256"],
            tokenizer_factory=types["HuggingFaceTokenizerFactory"](),
        )
        policy_client = types["PolicyClient"](
            transport=types["HttpPolicyTransport"](
                base_url=base_url,
                timeout_seconds=180.0,
            )
        )
        publisher = types["ArtifactPublisher"](run_root=evaluator_root)
        config = types["EpisodeExecutionConfig"](
            run_id="human-pilot-stage0-" + label.lower(),
            cell=bound,
            execution_attempt_id=attempt_id,
            attempt_ordinal=attempt_ordinal,
            task=task,
            seed=seed,
            evaluator_commit=preflight["evaluator_commit"],
            design_merge_commit=preflight["design_merge_commit"],
            runtime_core_commit=preflight["runtime_core_commit"],
            raw_protocol_sha256=preflight["raw_protocol_sha256"],
            split_access_sha256=identity.task_access_manifest_sha256,
            gamefile_identity_manifest_sha256=preflight[
                "gamefile_identity_manifest_sha256"
            ],
            environment_runtime_manifest_sha256=preflight[
                "environment_runtime_manifest_sha256"
            ],
            policy_runtime_manifest_sha256=runtime_sha,
            policy_request_schema_sha256=preflight[
                "policy_request_schema_sha256"
            ],
            run_schedule_sha256=schedule_sha,
            gamefile_sha256=task_access_record.gamefile_sha256,
            task_access_manifest_sha256=(
                identity.task_access_manifest_sha256
            ),
            policy_condition_manifest_sha256=(
                identity.policy_condition_manifest_sha256
            ),
            condition_run_schedule_sha256=(
                identity.condition_run_schedule_sha256
            ),
            access_class=identity.access_class,
            policy_condition_id=identity.policy_condition_id,
            condition_cell_id=identity.condition_cell_id,
            evaluation_context=identity.evaluation_context,
            select_execution_identity=identity,
        )
        result = types["run_single_episode"](
            config=config,
            dependencies=types["EpisodeDependencies"](
                environment=environment,
                policy_client=policy_client,
                prompt_renderer=renderer,
                artifact_publisher=publisher,
                policy_execution_profile=profile,
            ),
        )
    finally:
        try:
            environment.close()
        except BaseException as cleanup_error:
            print(
                "STAGE0_ENVIRONMENT_CLEANUP_ERROR="
                + type(cleanup_error).__name__,
                file=sys.stderr,
            )
    if (
        result.attempt_bundle is None
        or type(result.success) is not bool
    ):
        raise Stage0Error(
            "LIVE_CELL_NOT_PRODUCED:"
            + attempt_id
            + ":scientific="
            + result.scientific_outcome_status.value
            + ":operational="
            + result.operational_finalization_status.value
            + ":reason="
            + result.termination_reason
        )
    if result.operational_finalization_status.value != "PUBLISHED":
        raise Stage0Error("LIVE_CELL_NOT_PUBLISHED")

    loaded = attempt_auditor.load_attempt_directory_v1(attempt_dir)
    if loaded.attempt_bundle.attempt_bundle_sha256 != (
        result.attempt_bundle.attempt_bundle_sha256
    ):
        raise Stage0Error("LIVE_CELL_PUBLISHED_BUNDLE_CHANGED")

    receipt = make_cell_receipt(
        condition_id=condition.policy_condition_id,
        condition_cell_id=scheduled_cell_id,
        manifest_index=task_index,
        task_id=task_id,
        seed=seed,
        execution_attempt_id=attempt_id,
        attempt_bundle_sha256=result.attempt_bundle.attempt_bundle_sha256,
        success=result.success,
        termination_reason=result.termination_reason,
        previous_receipt_sha256=previous,
    )
    append_receipt(ledger, receipt)
    return receipt


def execute_stage0(
    *,
    base_url: str,
    stop_before_monotonic: float | None = None,
) -> dict[str, Any]:
    _validate_authorization()
    preflight = load_json_object(
        PREFLIGHT_ROOT / "OFFLINE_PREFLIGHT_RECEIPT_V1.json"
    )
    twin = load_twin_review(TWIN_REVIEW)
    types = _load_repo_types()
    task_access = types["TaskAccessManifestV1"].from_json(TASK_ACCESS.read_bytes())
    access_by_index = {row.manifest_index: row for row in task_access.records}
    attempt_auditor = _load_attempt_auditor(GENERIC_WORKTREE)

    bundles = {}
    for prefix, label in (("PARENT", "parent"), ("CANDIDATE", "candidate")):
        bundles[label] = _condition_bundle(
            values=twin["values"],
            prefix=prefix,
            types=types,
            task_access=task_access,
        )

    parent_schedule = bundles["parent"][2]
    candidate_schedule = bundles["candidate"][2]
    parent_grid = [
        (cell.manifest_index, cell.task_id, cell.seed)
        for cell in parent_schedule.cells
    ]
    candidate_grid = [
        (cell.manifest_index, cell.task_id, cell.seed)
        for cell in candidate_schedule.cells
    ]
    if parent_grid != candidate_grid:
        raise Stage0Error("LIVE_TWIN_GRID_CHANGED")

    EXECUTION_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = STAGE0_ROOT / "stage0_execution.lock"
    lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Stage0Error("STAGE0_EXECUTION_ALREADY_ACTIVE") from exc

        graceful_partial = False
        for ordinal, parent_cell in enumerate(
            parent_schedule.cells
        ):
            candidate_cell = candidate_schedule.cells[ordinal]

            parent_existing = {
                row["condition_cell_id"]
                for row in load_receipts(
                    EXECUTION_ROOT
                    / "parent/cell_receipts.jsonl"
                )
            }
            candidate_existing = {
                row["condition_cell_id"]
                for row in load_receipts(
                    EXECUTION_ROOT
                    / "candidate/cell_receipts.jsonl"
                )
            }
            parent_done = (
                parent_cell.condition_cell_id
                in parent_existing
            )
            candidate_done = (
                candidate_cell.condition_cell_id
                in candidate_existing
            )

            if (
                stop_before_monotonic is not None
                and time.monotonic()
                >= stop_before_monotonic
                and parent_done == candidate_done
            ):
                graceful_partial = True
                break

            for label, cell in (
                ("parent", parent_cell),
                ("candidate", candidate_cell),
            ):
                condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha = (
                    bundles[label]
                )
                access_record = access_by_index.get(cell.manifest_index)
                if access_record is None:
                    raise Stage0Error("LIVE_TASK_ACCESS_RECORD_MISSING")
                receipt = _recover_or_execute_cell(
                    label=label,
                    cell=cell,
                    task_access_record=access_record,
                    condition=condition,
                    runtime=runtime,
                    condition_sha=condition_sha,
                    runtime_sha=runtime_sha,
                    schedule_sha=schedule_sha,
                    preflight=preflight,
                    base_url=base_url,
                    types=types,
                    attempt_auditor=attempt_auditor,
                    condition_root=EXECUTION_ROOT / label,
                )
                print(
                    "STAGE0_CELL_COMPLETE"
                    + " condition=" + label
                    + " ordinal=" + str(ordinal)
                    + " task_id=" + receipt["task_id"]
                    + " seed=" + str(receipt["seed"])
                    + " success=" + str(receipt["success"]).lower()
                    + " receipt_sha256=" + receipt["receipt_sha256"]
                )
    finally:
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(lock_descriptor)

    parent_count = len(load_receipts(EXECUTION_ROOT / "parent/cell_receipts.jsonl"))
    candidate_count = len(load_receipts(EXECUTION_ROOT / "candidate/cell_receipts.jsonl"))
    return {
        "parent_cell_count": parent_count,
        "candidate_cell_count": candidate_count,
        "total_condition_cell_count":
            parent_count + candidate_count,
        "graceful_partial": graceful_partial,
    }
