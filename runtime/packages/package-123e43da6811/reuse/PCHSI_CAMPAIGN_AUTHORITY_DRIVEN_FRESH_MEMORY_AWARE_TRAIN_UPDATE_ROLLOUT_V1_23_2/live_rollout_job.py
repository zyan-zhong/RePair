from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

from safe_io import (
    canonical_bytes,
    load_json,
    safe_extract_zip,
    sha_file,
    write_new_bytes,
    write_new_json,
)




def find_capsule_file_by_sha(
    root: Path,
    *,
    expected_sha256: str,
    suffixes: tuple[str, ...] | None = None,
) -> Path:
    matches = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        try:
            if sha_file(path) == expected_sha256:
                matches.append(path.resolve())
        except OSError:
            continue
    if not matches:
        raise ValueError("CAPSULE_CONTENT_SHA_NOT_FOUND:" + expected_sha256)
    # Multiple byte-identical aliases are one content authority.
    return sorted(matches, key=str)[0]

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILED:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    if cp.returncode:
        raise RuntimeError(
            "GIT_FAILED:" + ":".join(args) + ":" + cp.stderr.strip()
        )
    return cp.stdout.strip()


def write_status_terminal(
    path: Path,
    *,
    status: str,
    state_root: Path,
    payload: dict[str, object] | None = None,
) -> None:
    value = {
        "schema_id": "PCHSI_V1232_JOB_TERMINAL_V1",
        "schema_version": 1,
        "status": status,
        "state_root": str(state_root),
        "payload": {} if payload is None else payload,
    }
    if path.exists():
        # The batch job owns this terminal path. Never overwrite a prior terminal.
        return
    write_new_json(path, value)


def _version(distribution: str, module_name: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        module = importlib.import_module(module_name)
        value = getattr(module, "__version__", None)
        if not isinstance(value, str) or not value:
            raise RuntimeError("PACKAGE_VERSION_UNRESOLVED:" + distribution)
        return value


def _source_sha(obj: object) -> tuple[str, str]:
    path = inspect.getsourcefile(obj)
    if path is None:
        raise RuntimeError("SOURCE_PATH_UNRESOLVED:" + repr(obj))
    resolved = Path(path).resolve()
    return str(resolved), sha_file(resolved)


def build_environment_runtime_manifest(
    *,
    output_path: Path,
    implementation_src: Path,
) -> str:
    from pchsi.evaluation.canonical_evidence import sha256_file
    from pchsi.evaluation.environment_runtime_manifest import (
        EnvironmentRuntimeInputs,
        SourceIdentity,
        build_environment_runtime_manifest,
    )

    import textworld.gym
    from alfworld.agents.environment.alfred_tw_env import (
        AlfredTWEnv,
        AlfredDemangler,
        AlfredInfos,
    )

    objects = (
        ("AlfredTWEnv", AlfredTWEnv),
        ("AlfredDemangler", AlfredDemangler),
        ("AlfredInfos", AlfredInfos),
        ("textworld.gym.register_games", textworld.gym.register_games),
    )
    sources = tuple(
        SourceIdentity(
            logical_name=name,
            source_path=_source_sha(obj)[0],
            sha256=_source_sha(obj)[1],
        )
        for name, obj in objects
    )

    inputs = EnvironmentRuntimeInputs(
        python_version=sys.version.split()[0],
        python_executable_sha256=sha256_file(Path(sys.executable)),
        alfworld_version=_version("alfworld", "alfworld"),
        textworld_version=_version("textworld", "textworld"),
        gym_version=_version("gym", "gym"),
        source_identities=sources,
        wrapper_order=(
            "AlfredDemangler(shuffle=false)",
            "AlfredInfos",
        ),
        env_infos=(
            "won",
            "admissible_commands",
            "extra.gamefile",
        ),
        batch_size=1,
        asynchronous=False,
        auto_reset=False,
        max_episode_steps=31,
        process_start_method="spawn",
    )
    build_environment_runtime_manifest(
        inputs=inputs,
        output_path=output_path,
    )
    return sha_file(output_path)


class CachedTokenizerFactory:
    def __init__(self):
        self._tokenizer = None
        self._kwargs = None

    def load(self, **kwargs):
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            self._kwargs = dict(kwargs)
            model_path = kwargs.pop("model_path")
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                **kwargs,
            )
        else:
            expected = dict(self._kwargs)
            if dict(kwargs) != expected:
                raise ValueError("TOKENIZER_FACTORY_ARGUMENTS_CHANGED")
        return self._tokenizer


def _registration_id(activation: str, task_index: int) -> str:
    # Content-derived and stable; no round/model literal.
    return "pchsi-" + activation[:12] + "-" + f"{task_index:04d}"


def _cell_terminal_payload(
    *,
    cell,
    result,
    classification: str,
    terminal_receipt_path: Path | None,
    terminal_receipt: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "schema_id": "ROUND_ROLLOUT_CELL_TERMINAL_V1",
        "schema_version": 1,
        "scientific_cell_id": cell.scientific_cell_id,
        "execution_attempt_id": cell.execution_attempt_id,
        "task_index": cell.cell.task_index,
        "task_id": cell.cell.task_id,
        "status": classification,
        "success": (
            result.success
            if classification in {"SCIENTIFIC_SUCCESS", "SCIENTIFIC_FAILURE"}
            else None
        ),
        "scientific_outcome_status": result.scientific_outcome_status.value,
        "operational_finalization_status": (
            result.operational_finalization_status.value
        ),
        "termination_reason": result.termination_reason,
        "attempt_terminal_receipt_path": (
            None if terminal_receipt_path is None else str(terminal_receipt_path)
        ),
        "attempt_terminal_receipt": terminal_receipt,
    }


def classify_episode_result(
    *,
    result,
    terminal_receipt: dict[str, object] | None,
) -> str:
    sci = result.scientific_outcome_status.value
    operational = result.operational_finalization_status.value

    scientific_operational_ok = operational == "PUBLISHED"
    if operational == "CLOSE_FAILED_RECORDED":
        scientific_operational_ok = (
            isinstance(terminal_receipt, dict)
            and terminal_receipt.get("error_code")
            == "WORKER_REAPED_NO_CONTAMINATION"
        )

    if scientific_operational_ok:
        if sci == "SUCCESS" and result.success is True:
            return "SCIENTIFIC_SUCCESS"
        if sci == "TASK_FAILURE" and result.success is False:
            return "SCIENTIFIC_FAILURE"

    if (
        sci == "NOT_PRODUCED"
        and result.termination_reason == "PROTOCOL_CONFIGURATION_ERROR"
    ):
        return "PROTOCOL_INVALID"
    return "INFRASTRUCTURE_INVALID"


def synthetic_terminal(
    *,
    cell,
    reason: str,
) -> dict[str, object]:
    return {
        "schema_id": "ROUND_ROLLOUT_CELL_TERMINAL_V1",
        "schema_version": 1,
        "scientific_cell_id": cell.scientific_cell_id,
        "execution_attempt_id": cell.execution_attempt_id,
        "task_index": cell.cell.task_index,
        "task_id": cell.cell.task_id,
        "status": "INFRASTRUCTURE_INVALID",
        "success": None,
        "scientific_outcome_status": "NOT_PRODUCED",
        "operational_finalization_status": "NOT_STARTED",
        "termination_reason": reason,
        "attempt_terminal_receipt_path": None,
        "attempt_terminal_receipt": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-root", required=True)
    ap.add_argument("--v1230-output-root", required=True)
    ap.add_argument("--capsule", required=True)
    args = ap.parse_args()

    package = Path(__file__).resolve().parent
    state_root = Path(args.state_root).resolve()
    v1230 = Path(args.v1230_output_root).resolve()
    capsule = Path(args.capsule).resolve()
    terminal_path = state_root / "PCHSI_V1232_JOB_TERMINAL_V1.json"

    service = None
    service_started = False
    service_log_out = None
    service_log_err = None
    rollout_started_at = time.time()

    try:
        authority = load_json(package / "V1232_INPUT_CAPSULE_AUTHORITY_V1.json")
        operational_policy = load_json(
            package / "V1232_LIVE_ROLLOUT_OPERATIONAL_POLICY_V1.json"
        )
        if sha_file(capsule) != authority["capsule_sha256"]:
            raise RuntimeError("V1232_CAPSULE_IDENTITY_CHANGED")

        extracted = state_root / "capsule"
        if not extracted.exists():
            safe_extract_zip(capsule, extracted)

        execution_binding_path = (
            extracted / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json"
        )
        slurm_plan_path = (
            extracted / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1.json"
        )
        allocation_contract_path = (
            extracted / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_ALLOCATION_PREFLIGHT_V1.json"
        )
        execution_binding = load_json(execution_binding_path)
        slurm_plan = load_json(slurm_plan_path)
        allocation_contract = load_json(allocation_contract_path)

        train_authority = execution_binding.get("train_update_authority")
        runtime_authority = execution_binding.get("runtime_authority")
        memory_authority = execution_binding.get("memory_authority")
        if not isinstance(train_authority, dict):
            raise RuntimeError("V1232_TRAIN_AUTHORITY_MISSING")
        if not isinstance(runtime_authority, dict):
            raise RuntimeError("V1232_RUNTIME_AUTHORITY_MISSING")
        if not isinstance(memory_authority, dict):
            raise RuntimeError("V1232_MEMORY_AUTHORITY_MISSING")

        runtime_path = find_capsule_file_by_sha(
            extracted,
            expected_sha256=runtime_authority["runtime_binding_file_sha256"],
            suffixes=(".json",),
        )
        memory_identity_path = find_capsule_file_by_sha(
            extracted,
            expected_sha256=memory_authority["runtime_identity_file_sha256"],
            suffixes=(".json",),
        )
        manifest_path = find_capsule_file_by_sha(
            extracted,
            expected_sha256=train_authority["manifest_sha256"],
            suffixes=(".jsonl",),
        )

        runtime = load_json(runtime_path)
        memory_identity = load_json(memory_identity_path)

        worktree = v1230 / "build/worktree"
        expected_head = execution_binding.get("implementation_head")
        if git(worktree, "rev-parse", "HEAD") != expected_head:
            raise RuntimeError("V1232_IMPLEMENTATION_HEAD_CHANGED")
        if git(worktree, "status", "--porcelain=v1", "--untracked-files=all"):
            raise RuntimeError("V1232_IMPLEMENTATION_WORKTREE_DIRTY")

        sys.path.insert(0, str(worktree / "src"))

        # Validate actual allocation before any service/model/environment call.
        allocation_mod = load_module(
            "v1232_allocation_preflight",
            extracted / "allocation_preflight.py",
        )
        import torch
        allocation_result = allocation_mod.validate_live_allocation(
            allocation_contract,
            os.environ,
            cuda_device_count=torch.cuda.device_count(),
        )
        allocation_result["cuda_device_names"] = [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ]
        write_new_json(
            state_root / "PCHSI_V1232_ALLOCATION_PREFLIGHT_RESULT_V1.json",
            allocation_result,
        )

        # Redirect all process-local caches into the large run filesystem.
        cache_root = state_root / "runtime_cache"
        cache_map = {
            "HOME": cache_root / "home",
            "XDG_CACHE_HOME": cache_root / "xdg",
            "HF_HOME": cache_root / "hf",
            "HUGGINGFACE_HUB_CACHE": cache_root / "hf_hub",
            "TRANSFORMERS_CACHE": cache_root / "transformers",
            "CUDA_CACHE_PATH": cache_root / "cuda",
            "TORCHINDUCTOR_CACHE_DIR": cache_root / "torchinductor",
            "TRITON_CACHE_DIR": cache_root / "triton",
            "NUMBA_CACHE_DIR": cache_root / "numba",
            "MPLCONFIGDIR": cache_root / "mpl",
        }
        for name, path in cache_map.items():
            path.mkdir(parents=True, exist_ok=True)
            os.environ[name] = str(path)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        service_mod = load_module(
            "v1232_policy_runtime_service",
            extracted / "policy_runtime_lifecycle_source/policy_runtime_service.py",
        )

        # Never adopt an arbitrary pre-existing localhost service on the bound endpoint.
        preprobe = service_mod.probe_policy_runtime_service(
            runtime,
            timeout_seconds=1.0,
        )
        write_new_json(
            state_root / "PCHSI_V1232_PRELAUNCH_ENDPOINT_PROBE_V1.json",
            preprobe,
        )
        if preprobe.get("tcp_connect_ok") is True:
            raise RuntimeError("V1232_PREEXISTING_BOUND_ENDPOINT_OCCUPIED")

        launch = execution_binding.get("service_launch_contract")
        if not isinstance(launch, dict):
            raise RuntimeError("V1232_SERVICE_LAUNCH_CONTRACT_MISSING")
        launch_command = launch.get("launch_command")
        if (
            not isinstance(launch_command, list)
            or not launch_command
            or not all(isinstance(x, str) and x for x in launch_command)
        ):
            raise RuntimeError("V1232_SERVICE_LAUNCH_ARGV_INVALID")

        service_stdout_path = state_root / "vllm.stdout.log"
        service_stderr_path = state_root / "vllm.stderr.log"
        service_log_out = service_stdout_path.open("wb")
        service_log_err = service_stderr_path.open("wb")
        service = subprocess.Popen(
            launch_command,
            cwd=worktree,
            env=dict(os.environ),
            stdout=service_log_out,
            stderr=service_log_err,
            start_new_session=True,
        )
        service_started = True
        write_new_json(
            state_root / "PCHSI_V1232_SERVICE_START_RECEIPT_V1.json",
            {
                "schema_id": "PCHSI_V1232_SERVICE_START_RECEIPT_V1",
                "schema_version": 1,
                "owned_service_pid": service.pid,
                "owned_process_group": True,
                "launch_command": launch_command,
                "launch_contract_sha256": launch.get("launch_contract_sha256"),
                "human_pid_selection_performed": False,
            },
        )

        deadline = (
            time.monotonic()
            + float(operational_policy["service_startup_timeout_seconds"])
        )
        readiness = None
        while time.monotonic() < deadline:
            if service.poll() is not None:
                raise RuntimeError(
                    "V1232_VLLM_EXITED_BEFORE_READINESS:"
                    + str(service.returncode)
                )
            readiness = service_mod.probe_policy_runtime_service(
                runtime,
                timeout_seconds=max(
                    0.2,
                    min(
                        2.0,
                        float(operational_policy["service_probe_interval_seconds"]),
                    ),
                ),
            )
            if readiness.get("ready") is True:
                break
            time.sleep(float(operational_policy["service_probe_interval_seconds"]))

        if not isinstance(readiness, dict) or readiness.get("ready") is not True:
            raise RuntimeError("V1232_VLLM_READINESS_TIMEOUT")
        readiness = service_mod.readiness_with_sha(readiness)
        write_new_json(
            state_root / "PCHSI_V1232_SERVICE_READINESS_V1.json",
            readiness,
        )

        # Import execution components only after the exact service is ready.
        from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
        from pchsi.evaluation.artifact_publisher import ArtifactPublisher
        from pchsi.evaluation.budget import BudgetLimits
        from pchsi.evaluation.canonical_evidence import sha256_file
        from pchsi.evaluation.environment_runtime_manifest import (
            EnvironmentRuntimeManifestV1,
        )
        from pchsi.evaluation.episode_evaluator import (
            EpisodeDependencies,
            EpisodeExecutionConfig,
            run_single_episode,
        )
        from pchsi.evaluation.policy_attempt_adapter import (
            BoundI1PolicyExecutionProfileV1,
            RoundMemoryPolicyAttemptAdapterV1,
        )
        from pchsi.evaluation.policy_client import (
            HttpPolicyTransport,
            PolicyClient,
        )
        from pchsi.evaluation.rendered_prompt import (
            LocalTokenizerPromptRenderer,
        )
        from pchsi.round_control.clean_execution_binding import (
            build_clean_train_schedule,
            load_clean_train_pool_records,
        )
        from pchsi.round_control.rollout_collection import (
            RoundEpisodeTerminalV1,
            RoundRolloutCollectionRequestV1,
            RoundRolloutExecutionBindingV1,
            build_failure_cohort,
            seal_rollout_universe,
        )

        if sha_file(manifest_path) != train_authority["manifest_sha256"]:
            raise RuntimeError("V1232_TRAIN_UPDATE_CAPSULE_MANIFEST_SHA_CHANGED")
        records = load_clean_train_pool_records(
            manifest_path=manifest_path,
            expected_manifest_sha256=train_authority["manifest_sha256"],
            train_root=Path(train_authority["train_root"]),
            expected_pool="TRAIN_UPDATE",
            expected_count=train_authority["row_count"],
        )
        schedule = build_clean_train_schedule(
            records=records,
            train_pool="TRAIN_UPDATE",
            seed=train_authority["rollout_seed"],
        )
        if len(schedule) != len(records):
            raise AssertionError("V1232_SCHEDULE_COUNT_INTERNAL")

        evidence_root = state_root / "round_evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)

        schedule_artifact = {
            "schema_id": "ROUND_TRAIN_UPDATE_SCHEDULE_V1",
            "schema_version": 1,
            "train_manifest_sha256": train_authority["manifest_sha256"],
            "rollout_seed": train_authority["rollout_seed"],
            "cell_count": len(schedule),
            "cells": [
                {
                    "scientific_cell_id": cell.scientific_cell_id,
                    "scheduled_cell_id": cell.cell.scheduled_cell_id,
                    "execution_attempt_id": cell.execution_attempt_id,
                    "task_index": cell.cell.task_index,
                    "task_id": cell.cell.task_id,
                    "seed": cell.cell.seed,
                }
                for cell in schedule
            ],
        }
        schedule_path = evidence_root / "ROUND_TRAIN_UPDATE_SCHEDULE_V1.json"
        write_new_json(schedule_path, schedule_artifact)
        schedule_sha = sha_file(schedule_path)

        access_artifact = {
            "schema_id": "ROUND_TRAIN_UPDATE_ACCESS_AUTHORITY_V1",
            "schema_version": 1,
            "pool": "TRAIN_UPDATE",
            "manifest_sha256": train_authority["manifest_sha256"],
            "row_count": len(records),
            "benchmark_feedback_authorized": False,
            "valid_seen_authorized": False,
            "valid_unseen_authorized": False,
            "train_select_authorized": False,
            "train_audit_authorized": False,
        }
        access_path = evidence_root / "ROUND_TRAIN_UPDATE_ACCESS_AUTHORITY_V1.json"
        write_new_json(access_path, access_artifact)
        access_sha = sha_file(access_path)

        gamefile_artifact = {
            "schema_id": "ROUND_TRAIN_UPDATE_GAMEFILE_IDENTITY_V1",
            "schema_version": 1,
            "train_manifest_sha256": train_authority["manifest_sha256"],
            "record_count": len(records),
            "records": [
                {
                    "task_index": record.index,
                    "task_id": record.task_id,
                    "gamefile": record.gamefile,
                    "gamefile_sha1": record.gamefile_sha1,
                    "gamefile_sha256": sha_file(Path(record.gamefile)),
                }
                for record in records
            ],
        }
        gamefile_path = evidence_root / "ROUND_TRAIN_UPDATE_GAMEFILE_IDENTITY_V1.json"
        write_new_json(gamefile_path, gamefile_artifact)
        gamefile_manifest_sha = sha_file(gamefile_path)

        env_runtime_path = (
            evidence_root / "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json"
        )
        environment_runtime_sha = build_environment_runtime_manifest(
            output_path=env_runtime_path,
            implementation_src=worktree / "src",
        )

        protocol_artifact = {
            "schema_id": "ROUND_MEMORY_AWARE_ROLLOUT_PROTOCOL_V1",
            "schema_version": 1,
            "implementation_head": expected_head,
            "execution_binding_sha256": sha_file(execution_binding_path),
            "policy_request_schema_sha256": execution_binding[
                "policy_request_schema_sha256"
            ],
            "train_update_manifest_sha256": train_authority["manifest_sha256"],
            "memory_snapshot_sha256": memory_identity["active_snapshot_sha256"],
            "budget_limits": asdict(BudgetLimits()),
            "task_retry_count": operational_policy["task_retry_count"],
            "schedule_mode": operational_policy["rollout_schedule_mode"],
            "benchmark_feedback_authorized": False,
            "same_round_memory_writeback_authorized": False,
            "training_execution_authorized": False,
        }
        protocol_path = evidence_root / "ROUND_MEMORY_AWARE_ROLLOUT_PROTOCOL_V1.json"
        write_new_json(protocol_path, protocol_artifact)
        protocol_sha = sha_file(protocol_path)

        profile_data = execution_binding["policy_execution_profile"]
        profile = BoundI1PolicyExecutionProfileV1(
            served_model_name=profile_data["served_model_name"],
            continuation_request_contract=profile_data[
                "continuation_request_contract"
            ],
            policy_version=profile_data["policy_version"],
        )
        profile_artifact = {
            "schema_id": "ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1",
            "schema_version": 1,
            "profile_kind": profile.profile_id,
            "arm_id": profile.arm_id,
            "policy_version": profile.policy_version,
            "served_model_name": profile.served_model_name,
            "continuation_request_contract": profile.continuation_request_contract,
        }
        profile_path = evidence_root / "ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json"
        write_new_json(profile_path, profile_artifact)
        profile_sha = sha_file(profile_path)

        request = RoundRolloutCollectionRequestV1(
            round_id=execution_binding["round_id"],
            execution_attempt_id=state_root.name,
            parent_policy_id=execution_binding["parent_policy_id"],
            parent_policy_artifact_sha256=runtime[
                "policy_runtime_manifest_sha256"
            ],
            policy_runtime_binding_sha256=sha_file(runtime_path),
            execution_profile_sha256=profile_sha,
            train_update_manifest_sha256=train_authority["manifest_sha256"],
            round_memory_runtime_authority_sha256=sha_file(memory_identity_path),
            round_start_memory_snapshot_sha256=memory_identity[
                "active_snapshot_sha256"
            ],
            token_budget_contract_sha256=memory_identity[
                "token_budget_contract_sha256"
            ],
            execution_namespace=state_root.name,
            rollout_seed=train_authority["rollout_seed"],
        )
        request_path = evidence_root / "ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json"
        write_new_json(request_path, request.to_dict())

        execution_contract = RoundRolloutExecutionBindingV1(
            request_sha256=request.request_sha256,
            rollout_control_source_sha256=sha_file(
                worktree / "src/pchsi/round_control/rollout_collection.py"
            ),
            clean_execution_binding_source_sha256=sha_file(
                worktree / "src/pchsi/round_control/clean_execution_binding.py"
            ),
            episode_evaluator_source_sha256=sha_file(
                worktree / "src/pchsi/evaluation/episode_evaluator.py"
            ),
            attempt_receipts_source_sha256=sha_file(
                worktree / "src/pchsi/round_control/attempt_receipts.py"
            ),
            policy_runtime_adapter_sha256=sha_file(
                worktree / "src/pchsi/evaluation/policy_attempt_adapter.py"
            ),
            scientific_execution_authorized=True,
        )
        exec_contract_path = (
            evidence_root / "ROUND_ROLLOUT_EXECUTION_BINDING_V1.json"
        )
        write_new_json(exec_contract_path, execution_contract.to_dict())

        tokenizer_factory = CachedTokenizerFactory()
        renderer = LocalTokenizerPromptRenderer(
            model_path=runtime["base_model_local_path"],
            revision=runtime["tokenizer_revision"],
            chat_template_sha256=runtime["chat_template_sha256"],
            tokenizer_factory=tokenizer_factory,
        )
        policy_client = PolicyClient(
            transport=HttpPolicyTransport(
                base_url=runtime["policy_base_url"],
                timeout_seconds=float(
                    operational_policy["policy_http_timeout_seconds"]
                ),
            )
        )
        memory_adapter = RoundMemoryPolicyAttemptAdapterV1(
            runtime_identity_path=memory_identity_path,
            expected_runtime_identity_file_sha256=sha_file(
                memory_identity_path
            ),
        )
        publisher = ArtifactPublisher(
            run_root=state_root / "rollout_run"
        )

        terminal_root = state_root / "rollout_cell_terminals"
        terminal_root.mkdir(parents=True, exist_ok=True)

        by_index = {record.index: record for record in records}
        terminal_rows = []
        abort_after_invalid = False

        for ordinal, cell in enumerate(schedule):
            sidecar = terminal_root / f"{ordinal:04d}.json"
            if sidecar.exists():
                raise RuntimeError(
                    "V1232_UNEXPECTED_PREEXISTING_CELL_TERMINAL:"
                    + str(sidecar)
                )

            if abort_after_invalid:
                payload = synthetic_terminal(
                    cell=cell,
                    reason="ABORTED_AFTER_PRIOR_INFRASTRUCTURE_OR_PROTOCOL_INVALID",
                )
                write_new_json(sidecar, payload)
                terminal_rows.append(
                    RoundEpisodeTerminalV1(
                        scientific_cell_id=cell.scientific_cell_id,
                        execution_attempt_id=cell.execution_attempt_id,
                        task_id=cell.cell.task_id,
                        task_index=cell.cell.task_index,
                        status="INFRASTRUCTURE_INVALID",
                        success=None,
                        terminal_receipt_sha256=sha_file(sidecar),
                    )
                )
                continue

            if service.poll() is not None:
                payload = synthetic_terminal(
                    cell=cell,
                    reason="POLICY_SERVICE_EXITED_BEFORE_CELL",
                )
                write_new_json(sidecar, payload)
                terminal_rows.append(
                    RoundEpisodeTerminalV1(
                        scientific_cell_id=cell.scientific_cell_id,
                        execution_attempt_id=cell.execution_attempt_id,
                        task_id=cell.cell.task_id,
                        task_index=cell.cell.task_index,
                        status="INFRASTRUCTURE_INVALID",
                        success=None,
                        terminal_receipt_sha256=sha_file(sidecar),
                    )
                )
                abort_after_invalid = True
                continue

            task = by_index[cell.cell.task_index]
            environment = None
            try:
                environment = SpawnedAlfworldAdapter.start(
                    exact_gamefile=Path(task.gamefile),
                    registration_id=_registration_id(
                        state_root.name,
                        task.index,
                    ),
                    runtime_manifest_sha256=environment_runtime_sha,
                )

                config = EpisodeExecutionConfig(
                    run_id=state_root.name,
                    cell=cell.cell,
                    execution_attempt_id=cell.execution_attempt_id,
                    attempt_ordinal=cell.attempt_ordinal,
                    task=task,
                    seed=cell.cell.seed,
                    evaluator_commit=expected_head,
                    design_merge_commit=expected_head,
                    runtime_core_commit=expected_head,
                    raw_protocol_sha256=protocol_sha,
                    split_access_sha256=access_sha,
                    gamefile_identity_manifest_sha256=gamefile_manifest_sha,
                    environment_runtime_manifest_sha256=environment_runtime_sha,
                    policy_runtime_manifest_sha256=runtime[
                        "policy_runtime_manifest_sha256"
                    ],
                    policy_request_schema_sha256=execution_binding[
                        "policy_request_schema_sha256"
                    ],
                    run_schedule_sha256=schedule_sha,
                    gamefile_sha256=sha_file(Path(task.gamefile)),
                    budget_limits=BudgetLimits(),
                )
                result = run_single_episode(
                    config=config,
                    dependencies=EpisodeDependencies(
                        environment=environment,
                        policy_client=policy_client,
                        prompt_renderer=renderer,
                        artifact_publisher=publisher,
                        policy_execution_profile=profile,
                        policy_attempt_adapter=memory_adapter,
                    ),
                )
            except BaseException as cell_error:
                if environment is not None:
                    try:
                        environment.close()
                    except BaseException:
                        pass
                payload = synthetic_terminal(
                    cell=cell,
                    reason=(
                        "CELL_EXECUTION_EXCEPTION:"
                        + type(cell_error).__name__
                    ),
                )
                payload["exception_message"] = str(cell_error)[:1000]
                write_new_json(sidecar, payload)
                terminal_rows.append(
                    RoundEpisodeTerminalV1(
                        scientific_cell_id=cell.scientific_cell_id,
                        execution_attempt_id=cell.execution_attempt_id,
                        task_id=cell.cell.task_id,
                        task_index=cell.cell.task_index,
                        status="INFRASTRUCTURE_INVALID",
                        success=None,
                        terminal_receipt_sha256=sha_file(sidecar),
                    )
                )
                abort_after_invalid = True
                continue

            attempt_terminal_path = (
                state_root
                / "rollout_run"
                / "attempt_ledger"
                / f"{cell.execution_attempt_id}.terminal.json"
            )
            attempt_terminal = (
                load_json(attempt_terminal_path)
                if attempt_terminal_path.is_file()
                else None
            )
            classification = classify_episode_result(
                result=result,
                terminal_receipt=attempt_terminal,
            )
            payload = _cell_terminal_payload(
                cell=cell,
                result=result,
                classification=classification,
                terminal_receipt_path=(
                    attempt_terminal_path
                    if attempt_terminal_path.is_file()
                    else None
                ),
                terminal_receipt=attempt_terminal,
            )
            write_new_json(sidecar, payload)
            terminal_rows.append(
                RoundEpisodeTerminalV1(
                    scientific_cell_id=cell.scientific_cell_id,
                    execution_attempt_id=cell.execution_attempt_id,
                    task_id=cell.cell.task_id,
                    task_index=cell.cell.task_index,
                    status=classification,
                    success=(
                        result.success
                        if classification
                        in {"SCIENTIFIC_SUCCESS", "SCIENTIFIC_FAILURE"}
                        else None
                    ),
                    terminal_receipt_sha256=sha_file(sidecar),
                )
            )
            if classification in {
                "INFRASTRUCTURE_INVALID",
                "PROTOCOL_INVALID",
            }:
                abort_after_invalid = True

        universe = seal_rollout_universe(
            request_sha256=request.request_sha256,
            terminals=tuple(terminal_rows),
        )
        universe_path = evidence_root / "ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json"
        write_new_json(universe_path, universe.to_dict())

        failure_path = None
        if universe.scientific_rollout_valid:
            cohort = build_failure_cohort(universe)
            failure_path = (
                evidence_root
                / "ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json"
            )
            write_new_json(failure_path, cohort.to_dict())

        handoff = {
            "schema_id": "ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1",
            "schema_version": 1,
            "round_id": execution_binding["round_id"],
            "parent_policy_id": execution_binding["parent_policy_id"],
            "rollout_request_path": str(request_path),
            "rollout_request_sha256": sha_file(request_path),
            "rollout_execution_binding_path": str(exec_contract_path),
            "rollout_execution_binding_sha256": sha_file(exec_contract_path),
            "rollout_universe_path": str(universe_path),
            "rollout_universe_sha256": sha_file(universe_path),
            "failure_cohort_path": (
                None if failure_path is None else str(failure_path)
            ),
            "failure_cohort_sha256": (
                None if failure_path is None else sha_file(failure_path)
            ),
            "attempt_bundle_root": str(state_root / "rollout_run" / "attempts"),
            "attempt_ledger_root": str(
                state_root / "rollout_run" / "attempt_ledger"
            ),
            "scheduled_count": universe.scheduled_count,
            "success_count": universe.success_count,
            "failure_count": universe.failure_count,
            "infrastructure_invalid_count": (
                universe.infrastructure_invalid_count
            ),
            "protocol_invalid_count": universe.protocol_invalid_count,
            "scientific_rollout_valid": universe.scientific_rollout_valid,
            "human_selection_performed": False,
            "benchmark_feedback_used": False,
            "memory_writeback_performed": False,
            "training_execution_performed": False,
            "next": (
                "AUTOMATIC_EVIDENCE_AND_ANALYZER_HANDOFF_FROM_V1232_ROLLOUT"
                if universe.scientific_rollout_valid
                else "CAMPAIGN_INFRA_INVALID_FRESH_ATTEMPT_GOVERNANCE"
            ),
        }
        handoff_path = evidence_root / "ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json"
        write_new_json(handoff_path, handoff)

        final_status = (
            "FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_COMPLETE_VALID"
            if universe.scientific_rollout_valid
            else "FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_PROTOCOL_INFRA_INVALID"
        )
        write_status_terminal(
            terminal_path,
            status=final_status,
            state_root=state_root,
            payload={
                "round_id": execution_binding["round_id"],
                "parent_policy_id": execution_binding["parent_policy_id"],
                "scheduled_count": universe.scheduled_count,
                "success_count": universe.success_count,
                "failure_count": universe.failure_count,
                "infrastructure_invalid_count": (
                    universe.infrastructure_invalid_count
                ),
                "protocol_invalid_count": universe.protocol_invalid_count,
                "scientific_rollout_valid": universe.scientific_rollout_valid,
                "handoff_path": str(handoff_path),
                "handoff_sha256": sha_file(handoff_path),
                "provider_external_api_calls": 0,
                "training_execution_count": 0,
                "memory_writeback_count": 0,
                "human_scientific_decision_count": 0,
                "elapsed_seconds": time.time() - rollout_started_at,
            },
        )
        return 0 if universe.scientific_rollout_valid else 20

    except BaseException as error:
        error_payload = {
            "schema_id": "PCHSI_V1232_JOB_EXCEPTION_V1",
            "schema_version": 1,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "provider_external_api_calls": 0,
            "training_execution_count": 0,
            "human_scientific_decision_count": 0,
        }
        exception_path = state_root / "PCHSI_V1232_JOB_EXCEPTION_V1.json"
        if not exception_path.exists():
            write_new_json(exception_path, error_payload)
        write_status_terminal(
            terminal_path,
            status="V1232_JOB_FAILED_FAIL_CLOSED",
            state_root=state_root,
            payload={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "exception_path": str(exception_path),
            },
        )
        return 1

    finally:
        teardown = {
            "schema_id": "PCHSI_V1232_SERVICE_TEARDOWN_RECEIPT_V1",
            "schema_version": 1,
            "service_started": service_started,
            "owned_service_pid": (
                None if service is None else service.pid
            ),
            "signal_target_is_owned_process_group": True,
            "human_pid_selection_performed": False,
            "sigterm_sent": False,
            "sigkill_sent": False,
            "returncode": (
                None if service is None else service.poll()
            ),
        }
        if service is not None and service.poll() is None:
            try:
                os.killpg(service.pid, signal.SIGTERM)
                teardown["sigterm_sent"] = True
            except ProcessLookupError:
                pass
            try:
                service.wait(
                    timeout=float(
                        load_json(
                            package
                            / "V1232_LIVE_ROLLOUT_OPERATIONAL_POLICY_V1.json"
                        )["service_shutdown_grace_seconds"]
                    )
                )
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(service.pid, signal.SIGKILL)
                    teardown["sigkill_sent"] = True
                except ProcessLookupError:
                    pass
                service.wait()
        if service is not None:
            teardown["returncode"] = service.poll()

        if service_log_out is not None:
            service_log_out.close()
        if service_log_err is not None:
            service_log_err.close()

        teardown_path = (
            state_root / "PCHSI_V1232_SERVICE_TEARDOWN_RECEIPT_V1.json"
        )
        if not teardown_path.exists():
            try:
                write_new_json(teardown_path, teardown)
            except BaseException:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
