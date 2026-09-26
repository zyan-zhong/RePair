from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import zipfile

from formal_exec.common import (
    FormalExecutionError,
    load_json,
    require_domain_sha,
    sha256_file,
)


AUTH_FILE = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json')
WITNESS_FILE = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/FORMAL_TRAINING_EXECUTION_APPROVAL_WITNESS_V1.json')
OUTPUT_DIR = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_v1/human-t2-train17-continuation-v1-a000')
ATTEMPT_ROOT = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_stage_attempts_v1/human-t2-train17-continuation-v1-a000')
REVIEW_ZIP = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/ROUND_HUMAN_T2_FORMAL_TRAINING_REVIEW_V1.zip')
REVIEW_ROOT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "round_human_t2_formal_training_review_v1"
)

EXPECTED_PARENT_ADAPTER = (
    "b296f2254b1fa1f2e141dffd3f6b5af"
    "903f839df4790ffcb245fd8dd57773ace"
)
EXPECTED_PARENT_PARAMETER_SHA = (
    "1801dc72946471ac3ada1ab61967c86d"
    "03874b209d9342db94b0054cccdb3dac"
)
EXPECTED_STAGE_BINDING_SHA = (
    "9185d27c16789689906eddc67759a628"
    "0572016cbfd1f1122ec18f608462853e"
)
EXPECTED_DATASET_SHA = (
    "ae5fa948fe75a56c287e0a0907021124"
    "2a0a933bc0a1011486b186bba824ea39"
)
EXPECTED_PLAN_DOMAIN_SHA = (
    "282fe712c85641c47f9c29f2b942c6b"
    "94528d22a942345d4ac57553ab95697d2"
)


def require_regular_file(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise FormalExecutionError(
            f"{label}_FILE_INVALID:{path}"
        )


def main() -> int:
    auth = load_json(AUTH_FILE)
    witness = load_json(WITNESS_FILE)
    require_domain_sha(
        auth,
        schema_id="ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        sha_field="authorization_sha256",
    )
    require_domain_sha(
        witness,
        schema_id=(
            "HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL_WITNESS_V1"
        ),
        sha_field="approval_witness_sha256",
    )

    if auth.get("authorization_status") != "APPROVED":
        raise FormalExecutionError(
            "TRAINING_REVIEW_AUTH_NOT_APPROVED"
        )
    if auth.get("approval_witness_sha256") != (
        witness.get("approval_witness_sha256")
    ):
        raise FormalExecutionError(
            "TRAINING_REVIEW_APPROVAL_WITNESS_MISMATCH"
        )

    files = {
        "input_artifact_index.json":
            ATTEMPT_ROOT / "input_artifact_index.json",
        "started_stage_receipt.json":
            ATTEMPT_ROOT / "started_stage_receipt.json",
        "output_artifact_index.json":
            ATTEMPT_ROOT / "output_artifact_index.json",
        "terminal_stage_receipt.json":
            ATTEMPT_ROOT / "terminal_stage_receipt.json",
        "training_step_ledger.jsonl":
            OUTPUT_DIR / "training_step_ledger.jsonl",
        "formal_run_manifest.json":
            OUTPUT_DIR / "formal_run_manifest.json",
        "adapter_artifact_manifest.json":
            OUTPUT_DIR / "adapter_artifact_manifest.json",
    }
    for label, path in files.items():
        require_regular_file(path, label)

    input_index = load_json(files["input_artifact_index.json"])
    output_index = load_json(files["output_artifact_index.json"])
    started = load_json(files["started_stage_receipt.json"])
    terminal = load_json(files["terminal_stage_receipt.json"])
    run_manifest = load_json(files["formal_run_manifest.json"])
    adapter_manifest = load_json(files["adapter_artifact_manifest.json"])

    require_domain_sha(
        input_index,
        schema_id="ROUND_ARTIFACT_INDEX_V1",
        sha_field="artifact_index_sha256",
    )
    require_domain_sha(
        output_index,
        schema_id="ROUND_ARTIFACT_INDEX_V1",
        sha_field="artifact_index_sha256",
    )
    require_domain_sha(
        started,
        schema_id="ROUND_STAGE_RECEIPT_V1",
        sha_field="stage_receipt_sha256",
    )
    require_domain_sha(
        terminal,
        schema_id="ROUND_STAGE_RECEIPT_V1",
        sha_field="stage_receipt_sha256",
    )

    if started.get("terminal_status") != "STARTED":
        raise FormalExecutionError(
            "TRAINING_STARTED_RECEIPT_STATUS_CHANGED"
        )
    if terminal.get("terminal_status") != "ACCEPTED":
        raise FormalExecutionError(
            "TRAINING_TERMINAL_RECEIPT_NOT_ACCEPTED"
        )
    if terminal.get("model_training_executed") is not True:
        raise FormalExecutionError(
            "TRAINING_TERMINAL_RECEIPT_EXECUTION_FLAG_CHANGED"
        )
    if terminal.get("model_training_execution_status") != "COMPLETED":
        raise FormalExecutionError(
            "TRAINING_TERMINAL_EXECUTION_STATUS_CHANGED"
        )
    if terminal.get("started_from_receipt_sha256") != (
        started.get("stage_receipt_sha256")
    ):
        raise FormalExecutionError(
            "TRAINING_STAGE_RECEIPT_CHAIN_BROKEN"
        )
    if terminal.get("output_artifact_index_sha256") != (
        output_index.get("artifact_index_sha256")
    ):
        raise FormalExecutionError(
            "TRAINING_OUTPUT_INDEX_BINDING_BROKEN"
        )
    if terminal.get("authorization_sha256") != (
        auth.get("authorization_sha256")
    ):
        raise FormalExecutionError(
            "TRAINING_AUTHORIZATION_BINDING_BROKEN"
        )

    expected_run = {
        "schema_id": "ROUND_TRAINING_FORMAL_RUN_MANIFEST_V1",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "profile_id": (
            "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC_PROFILE_V1"
        ),
        "condition_id": "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC",
        "run_status": "FORMAL_TRAINING_COMPLETED",
        "diagnostic_only": True,
        "promotion_eligible": False,
        "formal_training_seed": 17,
        "data_seed": 17,
        "parent_policy_id": "PILOT_DISTILLED_PI1",
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "parent_final_trainable_parameter_sha256": (
            EXPECTED_PARENT_PARAMETER_SHA
        ),
        "stage_binding_sha256": EXPECTED_STAGE_BINDING_SHA,
        "trainer_native_dataset_sha256": EXPECTED_DATASET_SHA,
        "research_planner_training_plan_domain_sha256": (
            EXPECTED_PLAN_DOMAIN_SHA
        ),
        "optimizer_step_count": 3,
        "dataset_pass_count": 1,
        "target_loss_token_count": 151,
        "all_losses_finite": True,
        "all_grad_norms_finite": True,
        "checkpoint_rule": "FINAL_STEP_ONLY",
        "intermediate_scientific_checkpoint_used": False,
        "early_stopping_used": False,
        "within_training_evaluation_used": False,
        "resume_from_checkpoint_used": False,
    }
    observed_run = {
        key: run_manifest.get(key)
        for key in expected_run
    }
    if observed_run != expected_run:
        raise FormalExecutionError(
            "FORMAL_RUN_MANIFEST_CONTRACT_CHANGED:"
            + repr(observed_run)
            + ":"
            + repr(expected_run)
        )

    expected_adapter = {
        "schema_id": "ROUND_TRAINING_ADAPTER_ARTIFACT_MANIFEST_V1",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "profile_id": (
            "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC_PROFILE_V1"
        ),
        "parent_adapter_bundle_sha256": EXPECTED_PARENT_ADAPTER,
        "diagnostic_only": True,
        "promotion_eligible": False,
    }
    observed_adapter = {
        key: adapter_manifest.get(key)
        for key in expected_adapter
    }
    if observed_adapter != expected_adapter:
        raise FormalExecutionError(
            "ADAPTER_ARTIFACT_MANIFEST_CONTRACT_CHANGED:"
            + repr(observed_adapter)
            + ":"
            + repr(expected_adapter)
        )

    candidate_adapter_bundle = adapter_manifest.get(
        "adapter_bundle_sha256"
    )
    if (
        not isinstance(candidate_adapter_bundle, str)
        or len(candidate_adapter_bundle) != 64
        or candidate_adapter_bundle == EXPECTED_PARENT_ADAPTER
    ):
        raise FormalExecutionError(
            "CANDIDATE_ADAPTER_BUNDLE_SHA_INVALID"
        )

    ledger_rows = [
        json.loads(line)
        for line in files[
            "training_step_ledger.jsonl"
        ].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(ledger_rows) != 3:
        raise FormalExecutionError(
            f"TRAINING_STEP_LEDGER_ROW_COUNT_CHANGED:{len(ledger_rows)}"
        )

    if REVIEW_ROOT.exists():
        raise FormalExecutionError(
            f"TRAINING_REVIEW_ROOT_ALREADY_EXISTS:{REVIEW_ROOT}"
        )
    if REVIEW_ZIP.exists():
        raise FormalExecutionError(
            f"TRAINING_REVIEW_ZIP_ALREADY_EXISTS:{REVIEW_ZIP}"
        )
    REVIEW_ROOT.mkdir(parents=True, exist_ok=False)

    evidence_files = []
    for logical_name, source in files.items():
        destination = REVIEW_ROOT / "evidence" / logical_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        evidence_files.append({
            "logical_name": logical_name,
            "path": str(destination.relative_to(REVIEW_ROOT)),
            "sha256": sha256_file(destination),
            "size_bytes": destination.stat().st_size,
        })

    for logical_name, source in (
        ("approved_authorization.json", AUTH_FILE),
        ("approval_witness.json", WITNESS_FILE),
    ):
        destination = REVIEW_ROOT / "authority" / logical_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        evidence_files.append({
            "logical_name": logical_name,
            "path": str(destination.relative_to(REVIEW_ROOT)),
            "sha256": sha256_file(destination),
            "size_bytes": destination.stat().st_size,
        })

    slurm_context = {
        "schema_id": "HUMAN_T2_FORMAL_TRAINING_SLURM_CONTEXT_V1",
        "schema_version": 1,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_job_name": os.environ.get("SLURM_JOB_NAME"),
        "slurm_job_partition": os.environ.get("SLURM_JOB_PARTITION"),
        "slurm_job_nodelist": os.environ.get("SLURM_JOB_NODELIST"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    slurm_path = REVIEW_ROOT / "evidence/slurm_runtime_context.json"
    slurm_path.write_text(
        json.dumps(
            slurm_context,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    evidence_files.append({
        "logical_name": "slurm_runtime_context.json",
        "path": str(slurm_path.relative_to(REVIEW_ROOT)),
        "sha256": sha256_file(slurm_path),
        "size_bytes": slurm_path.stat().st_size,
    })

    review_manifest = {
        "schema_id": "HUMAN_T2_FORMAL_TRAINING_REVIEW_MANIFEST_V1",
        "schema_version": 1,
        "review_status": "READY_FOR_FORMAL_TRAINING_RESULT_AUDIT",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "profile_id": (
            "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC_PROFILE_V1"
        ),
        "condition_id": "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC",
        "execution_attempt_id": 'human-t2-train17-continuation-v1-a000',
        "approved_authorization_sha256": auth[
            "authorization_sha256"
        ],
        "approval_witness_sha256": witness[
            "approval_witness_sha256"
        ],
        "terminal_stage_receipt_sha256": terminal[
            "stage_receipt_sha256"
        ],
        "output_artifact_index_sha256": output_index[
            "artifact_index_sha256"
        ],
        "candidate_adapter_bundle_sha256": candidate_adapter_bundle,
        "formal_training_seed": 17,
        "data_seed": 17,
        "row_count": 12,
        "optimizer_step_count": 3,
        "target_loss_token_count": 151,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "evaluation_executed": False,
        "promotion_decision_executed": False,
        "next_gate": (
            "FORMAL_TRAINING_RESULT_AUDIT_AND_OFF_OFF_EVALUATION_HANDOFF"
        ),
        "files": evidence_files,
    }
    manifest_path = REVIEW_ROOT / "REVIEW_MANIFEST_V1.json"
    manifest_path.write_text(
        json.dumps(
            review_manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    with zipfile.ZipFile(
        REVIEW_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(REVIEW_ROOT.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(REVIEW_ROOT).as_posix(),
                )

    print("HUMAN_T2_FORMAL_TRAINING_REVIEW_READY")
    print(
        "CANDIDATE_ADAPTER_BUNDLE_SHA256="
        + candidate_adapter_bundle
    )
    print(
        "TERMINAL_STAGE_RECEIPT_SHA256="
        + terminal["stage_receipt_sha256"]
    )
    print("OPTIMIZER_STEP_COUNT=3")
    print("TARGET_LOSS_TOKEN_COUNT=151")
    print("DIAGNOSTIC_ONLY=true")
    print("PROMOTION_ELIGIBLE=false")
    print("EVALUATION_EXECUTED=false")
    print("REVIEW_ZIP=" + str(REVIEW_ZIP))
    print("REVIEW_ZIP_SHA256=" + sha256_file(REVIEW_ZIP))
    print(
        "NEXT_GATE=FORMAL_TRAINING_RESULT_AUDIT_"
        "AND_OFF_OFF_EVALUATION_HANDOFF"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
