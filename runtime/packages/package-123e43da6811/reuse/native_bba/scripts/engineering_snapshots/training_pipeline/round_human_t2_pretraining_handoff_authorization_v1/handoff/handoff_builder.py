from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from .common import (
    HandoffError,
    domain_sha256,
    load_json,
    require_file_sha,
    sha256_file,
    write_json_create_once,
)
from .smoke_review_audit import audit_smoke_review_bundle


def verify_slurm_accounting(job_contract: dict[str, Any]) -> dict[str, Any]:
    job_id = job_contract["job_id"]
    result = subprocess.run(
        [
            "sacct",
            "-n",
            "-P",
            "-j",
            job_id,
            "--format=JobIDRaw,State,ExitCode,Elapsed,NodeList",
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise HandoffError(
            f"SLURM_ACCOUNTING_QUERY_FAILED:{result.returncode}:"
            f"{result.stderr.strip()}"
        )
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        rows.append(
            {
                "job_id_raw": parts[0],
                "state": parts[1],
                "exit_code": parts[2],
                "elapsed": parts[3],
                "node_list": parts[4],
            }
        )
    primary = next(
        (row for row in rows if row["job_id_raw"] == job_id),
        None,
    )
    if primary is None:
        raise HandoffError("SLURM_PRIMARY_JOB_ROW_MISSING")
    if primary["state"] != job_contract["expected_state"]:
        raise HandoffError(
            f"SLURM_JOB_STATE_CHANGED:{primary['state']}:"
            f"{job_contract['expected_state']}"
        )
    if primary["exit_code"] != job_contract["expected_exit_code"]:
        raise HandoffError(
            f"SLURM_JOB_EXIT_CODE_CHANGED:{primary['exit_code']}:"
            f"{job_contract['expected_exit_code']}"
        )
    return {
        "schema_id": "SLURM_JOB_ACCOUNTING_EVIDENCE_V1",
        "schema_version": 1,
        "job_id": job_id,
        "primary": primary,
        "rows": rows,
    }


def verify_fixed_head_files(contract: dict[str, Any]) -> dict[str, Any]:
    stage = contract["reviewed_training_stage"]
    verified = []
    for logical_name, specification in (
        ("TRAINING_STAGE_BINDING", stage["stage_binding"]),
        ("ROUND_LOCAL_TRAINING_CONTRACT", stage["training_contract"]),
        ("ROUND_SAMPLE_ORDER_MANIFEST", stage["sample_order"]),
        ("RUNTIME_ADAPTER", stage["runtime_adapter"]),
        ("TRAINER_ROLE_BINDING", stage["trainer_role_binding"]),
    ):
        path = Path(specification["path"]).resolve()
        expected = specification.get(
            "file_sha256",
            specification.get("sha256"),
        )
        require_file_sha(path, expected, logical_name)
        verified.append(
            {
                "logical_name": logical_name,
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    binding = load_json(
        Path(stage["stage_binding"]["path"]).resolve()
    )
    if binding.get("stage_binding_sha256") != (
        stage["stage_binding"]["domain_sha256"]
    ):
        raise HandoffError("STAGE_BINDING_DOMAIN_SHA_CHANGED")
    if binding.get("previous_stage_receipt_sha256") is not None:
        raise HandoffError("REVIEWED_STAGE_BINDING_PREDECESSOR_CHANGED")
    return {
        "verified_files": verified,
        "stage_binding": binding,
    }


def verify_upstream_authorities(
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    verified = []
    for specification in contract[
        "upstream_scientific_authorities"
    ]:
        path = Path(specification["path"]).resolve()
        require_file_sha(
            path,
            specification["sha256"],
            "UPSTREAM_" + specification["logical_name"],
        )
        verified.append(
            {
                **specification,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return verified


def build_handoff_and_candidate(
    *,
    contract_path: Path,
    output_root: Path,
) -> dict[str, Path]:
    contract = load_json(contract_path)
    if contract.get("build_status") != "REVIEW_ONLY":
        raise HandoffError("BUILD_CONTRACT_NOT_REVIEW_ONLY")
    if contract.get("formal_training_authorized") is not False:
        raise HandoffError("BUILD_CONTRACT_AUTHORIZES_TRAINING")
    if contract.get("training_execution_count") != 0:
        raise HandoffError("BUILD_CONTRACT_TRAINING_COUNT_NOT_ZERO")

    smoke_spec = contract["smoke_review_bundle"]
    smoke = audit_smoke_review_bundle(
        Path(smoke_spec["path"]).resolve(),
        expected_bundle_sha256=smoke_spec["sha256"],
        expected_member_count=smoke_spec["expected_member_count"],
        expected_runner_freeze_root_sha256=(
            contract["reviewed_training_stage"][
                "runner_freeze_root_sha256"
            ]
        ),
        expected_stage_binding_domain_sha256=(
            contract["reviewed_training_stage"][
                "stage_binding"
            ]["domain_sha256"]
        ),
        expected_initial_trainable_sha256=(
            contract["parent_policy"][
                "final_trainable_parameter_sha256"
            ]
        ),
    )
    slurm = verify_slurm_accounting(contract["smoke_job"])
    fixed_head = verify_fixed_head_files(contract)
    upstream = verify_upstream_authorities(contract)

    if output_root.exists():
        raise HandoffError(
            f"HANDOFF_REVIEW_OUTPUT_ALREADY_EXISTS:{output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=False)

    smoke_audit = {
        "schema_id": "MODEL_INIT_SMOKE_RESULT_AUDIT_V1",
        "schema_version": 1,
        "audit_status": "PASS",
        "round_id": contract["round_id"],
        "profile_id": contract["profile_id"],
        "smoke_review_bundle_sha256": smoke[
            "bundle_sha256"
        ],
        "runner_freeze_root_sha256": (
            contract["reviewed_training_stage"][
                "runner_freeze_root_sha256"
            ]
        ),
        "stage_binding_domain_sha256": (
            contract["reviewed_training_stage"][
                "stage_binding"
            ]["domain_sha256"]
        ),
        "smoke_result_domain_sha256": smoke[
            "smoke_result"
        ]["result_sha256"],
        "smoke_terminal_stage_receipt_sha256": smoke[
            "terminal_receipt"
        ]["stage_receipt_sha256"],
        "observed_initial_trainable_parameter_sha256": smoke[
            "smoke_result"
        ]["observed_initial_trainable_parameter_sha256"],
        "model_load_count": 1,
        "forward_count": 0,
        "backward_count": 0,
        "optimizer_step_count": 0,
        "training_execution_count": 0,
        "slurm_job_accounting": slurm,
        "audit_sha256": "",
    }
    smoke_audit["audit_sha256"] = domain_sha256(
        smoke_audit["schema_id"],
        smoke_audit,
        sha_field="audit_sha256",
    )

    source_refs = []
    for row in fixed_head["verified_files"]:
        source_refs.append(
            {
                **row,
                "retention_class": (
                    "VALIDATED_SCIENTIFIC_ARTIFACT"
                ),
            }
        )
    source_refs.extend(upstream)
    source_refs.append(
        {
            "logical_name": "MODEL_INIT_SMOKE_REVIEW_BUNDLE",
            "path": str(
                Path(
                    contract["smoke_review_bundle"]["path"]
                ).resolve()
            ),
            "sha256": smoke["bundle_sha256"],
            "size_bytes": Path(
                contract["smoke_review_bundle"]["path"]
            ).resolve().stat().st_size,
            "retention_class": (
                "VALIDATED_SCIENTIFIC_ARTIFACT"
            ),
        }
    )

    source_index = {
        "schema_id": "ROUND_PRETRAINING_SOURCE_ARTIFACT_INDEX_V1",
        "schema_version": 1,
        "round_id": contract["round_id"],
        "profile_id": contract["profile_id"],
        "artifacts": source_refs,
        "artifact_index_sha256": "",
    }
    source_index["artifact_index_sha256"] = domain_sha256(
        source_index["schema_id"],
        source_index,
        sha_field="artifact_index_sha256",
    )

    handoff = {
        "schema_id": "ROUND_PRETRAINING_HANDOFF_RECEIPT_V1",
        "schema_version": 1,
        "round_id": contract["round_id"],
        "profile_id": contract["profile_id"],
        "handoff_status": (
            "READY_FOR_FORMAL_TRAINING_AUTHORIZATION_REVIEW"
        ),
        "scientific_role": "PRETRAINING_HANDOFF",
        "parent_policy_id": contract[
            "parent_policy"
        ]["policy_id"],
        "parent_adapter_bundle_sha256": contract[
            "parent_policy"
        ]["adapter_bundle_sha256"],
        "parent_final_trainable_parameter_sha256": contract[
            "parent_policy"
        ]["final_trainable_parameter_sha256"],
        "f0f1_authority_package_sha256": next(
            row["sha256"]
            for row in upstream
            if row["logical_name"]
            == "HUMAN_REFERENCE_F0F1_AUTHORITY_PACKAGE"
        ),
        "post_adjudicated_training_evidence_sha256": next(
            row["sha256"]
            for row in upstream
            if row["logical_name"]
            == "POST_ADJUDICATED_TRAINING_EVIDENCE_INPUT"
        ),
        "research_planner_training_plan_file_sha256": next(
            row["sha256"]
            for row in upstream
            if row["logical_name"]
            == "RESEARCH_PLANNER_TRAINING_PLAN"
        ),
        "research_planner_training_plan_domain_sha256": next(
            row["domain_sha256"]
            for row in upstream
            if row["logical_name"]
            == "RESEARCH_PLANNER_TRAINING_PLAN"
        ),
        "trainer_native_dataset_manifest_file_sha256": next(
            row["sha256"]
            for row in upstream
            if row["logical_name"]
            == "T2_TRAINER_NATIVE_DATASET_MANIFEST"
        ),
        "trainer_native_dataset_manifest_domain_sha256": next(
            row["domain_sha256"]
            for row in upstream
            if row["logical_name"]
            == "T2_TRAINER_NATIVE_DATASET_MANIFEST"
        ),
        "trainer_native_dataset_sha256": next(
            row["sha256"]
            for row in upstream
            if row["logical_name"]
            == "T2_TRAINER_NATIVE_DATASET"
        ),
        "training_stage_runner_freeze_root_sha256": (
            contract["reviewed_training_stage"][
                "runner_freeze_root_sha256"
            ]
        ),
        "training_stage_binding_file_sha256": (
            contract["reviewed_training_stage"][
                "stage_binding"
            ]["file_sha256"]
        ),
        "training_stage_binding_domain_sha256": (
            contract["reviewed_training_stage"][
                "stage_binding"
            ]["domain_sha256"]
        ),
        "model_init_smoke_audit_sha256": smoke_audit[
            "audit_sha256"
        ],
        "model_init_smoke_result_domain_sha256": smoke[
            "smoke_result"
        ]["result_sha256"],
        "model_init_smoke_terminal_receipt_sha256": smoke[
            "terminal_receipt"
        ]["stage_receipt_sha256"],
        "source_artifact_index_sha256": source_index[
            "artifact_index_sha256"
        ],
        "row_count": contract[
            "current_training_budget"
        ]["row_count"],
        "epochs": contract[
            "current_training_budget"
        ]["epochs"],
        "optimizer_steps": contract[
            "current_training_budget"
        ]["optimizer_steps"],
        "target_loss_tokens": contract[
            "current_training_budget"
        ]["target_loss_tokens"],
        "training_seed": contract[
            "current_training_budget"
        ]["training_seed"],
        "data_seed": contract[
            "current_training_budget"
        ]["data_seed"],
        "diagnostic_only": True,
        "promotion_eligible": False,
        "formal_training_authorized": False,
        "training_execution_count": 0,
        "handoff_receipt_sha256": "",
    }
    handoff["handoff_receipt_sha256"] = domain_sha256(
        handoff["schema_id"],
        handoff,
        sha_field="handoff_receipt_sha256",
    )

    candidate_spec = contract[
        "execution_authorization_candidate"
    ]
    authorization = {
        "schema_id": "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        "schema_version": 1,
        "authorization_status": "NOT_AUTHORIZED",
        "round_id": contract["round_id"],
        "stage_id": fixed_head[
            "stage_binding"
        ]["stage_id"],
        "profile_id": contract["profile_id"],
        "stage_binding_sha256": contract[
            "reviewed_training_stage"
        ]["stage_binding"]["domain_sha256"],
        "runner_freeze_root_sha256": contract[
            "reviewed_training_stage"
        ]["runner_freeze_root_sha256"],
        "execution_attempt_id": candidate_spec[
            "execution_attempt_id"
        ],
        "authorized_output_dir": candidate_spec[
            "authorized_output_dir"
        ],
        "stage_attempt_root": candidate_spec[
            "stage_attempt_root"
        ],
        "authorized_optimizer_steps": contract[
            "current_training_budget"
        ]["optimizer_steps"],
        "authorized_target_loss_tokens": contract[
            "current_training_budget"
        ]["target_loss_tokens"],
        "diagnostic_only": True,
        "promotion_eligible": False,
        "training_execution_count_before": 0,
        "pretraining_handoff_receipt_sha256": handoff[
            "handoff_receipt_sha256"
        ],
        "model_init_smoke_result_domain_sha256": smoke[
            "smoke_result"
        ]["result_sha256"],
        "authorization_sha256": "",
    }
    authorization["authorization_sha256"] = domain_sha256(
        authorization["schema_id"],
        authorization,
        sha_field="authorization_sha256",
    )

    paths = {
        "smoke_audit": output_root / "MODEL_INIT_SMOKE_RESULT_AUDIT_V1.json",
        "source_index": output_root / "ROUND_PRETRAINING_SOURCE_ARTIFACT_INDEX_V1.json",
        "handoff": output_root / "ROUND_PRETRAINING_HANDOFF_RECEIPT_V1.json",
        "authorization": output_root / (
            "ROUND_TRAINING_EXECUTION_AUTHORIZATION_CANDIDATE_V1.json"
        ),
    }
    write_json_create_once(paths["smoke_audit"], smoke_audit)
    write_json_create_once(paths["source_index"], source_index)
    write_json_create_once(paths["handoff"], handoff)
    write_json_create_once(paths["authorization"], authorization)

    evidence_root = output_root / "smoke_review_evidence"
    evidence_root.mkdir(parents=True, exist_ok=False)
    import zipfile
    with zipfile.ZipFile(
        Path(contract["smoke_review_bundle"]["path"]).resolve(),
        "r",
    ) as archive:
        for name in (
            "REVIEW_MANIFEST_V1.json",
            "authorities/smoke_authorization.json",
            "authorities/smoke_binding.json",
            "evidence/input_artifact_index.json",
            "evidence/output_artifact_index.json",
            "evidence/smoke_result.json",
            "evidence/started_stage_receipt.json",
            "evidence/terminal_stage_receipt.json",
        ):
            destination = evidence_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))

    return paths
