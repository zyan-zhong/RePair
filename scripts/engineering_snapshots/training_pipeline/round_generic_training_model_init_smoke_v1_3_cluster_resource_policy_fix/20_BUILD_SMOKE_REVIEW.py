from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

from smoke.common import (
    SmokeError,
    load_json_object,
    require_domain_sha,
    sha256_file,
)
from smoke.smoke_runner import (
    BINDING_PATH,
    AUTHORIZATION_PATH,
    verify_authorization,
    verify_reviewed_fixed_head,
)


OUTPUT_PARENT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"
)
REVIEW_ROOT = (
    OUTPUT_PARENT
    / "round_generic_training_model_init_smoke_v1_review"
)
REVIEW_BUNDLE = (
    OUTPUT_PARENT
    / "ROUND_GENERIC_TRAINING_MODEL_INIT_SMOKE_REVIEW_V1.zip"
)


def main() -> int:
    review, binding = verify_reviewed_fixed_head()
    authorization = verify_authorization(binding)

    attempt_root = Path(binding["attempt_root"]).resolve()
    result_root = Path(binding["result_root"]).resolve()

    required = {
        "input_artifact_index.json": attempt_root
        / "input_artifact_index.json",
        "started_stage_receipt.json": attempt_root
        / "started_stage_receipt.json",
        "output_artifact_index.json": attempt_root
        / "output_artifact_index.json",
        "terminal_stage_receipt.json": attempt_root
        / "terminal_stage_receipt.json",
        "smoke_result.json": result_root / "smoke_result.json",
    }
    for label, path in required.items():
        if not path.is_file() or path.is_symlink():
            raise SmokeError(f"SMOKE_REVIEW_FILE_MISSING:{label}:{path}")

    result = load_json_object(required["smoke_result.json"])
    require_domain_sha(
        result,
        schema_id=(
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_RESULT_V1"
        ),
        sha_field="result_sha256",
    )
    started = load_json_object(
        required["started_stage_receipt.json"]
    )
    terminal = load_json_object(
        required["terminal_stage_receipt.json"]
    )
    output_index = load_json_object(
        required["output_artifact_index.json"]
    )

    expected_result = {
        "status": "PASS",
        "round_id": binding["round_id"],
        "profile_id": binding["profile_id"],
        "stage_binding_sha256": (
            binding["training_stage_binding_domain_sha256"]
        ),
        "reviewed_training_stage_freeze_root_sha256": (
            binding["reviewed_training_stage_freeze_root_sha256"]
        ),
        "smoke_binding_sha256": binding["smoke_binding_sha256"],
        "authorization_sha256": authorization[
            "authorization_sha256"
        ],
        "expected_initial_trainable_parameter_sha256": (
            "1801dc72946471ac3ada1ab61967c86d03874b209d9342db94b0054cccdb3dac"
        ),
        "observed_initial_trainable_parameter_sha256": (
            "1801dc72946471ac3ada1ab61967c86d03874b209d9342db94b0054cccdb3dac"
        ),
        "post_check_trainable_parameter_sha256": (
            "1801dc72946471ac3ada1ab61967c86d03874b209d9342db94b0054cccdb3dac"
        ),
        "forward_count": 0,
        "backward_count": 0,
        "optimizer_constructed": False,
        "optimizer_step_count": 0,
        "training_execution_count": 0,
        "model_unloaded": True,
    }
    observed_result = {
        key: result.get(key)
        for key in expected_result
    }
    if observed_result != expected_result:
        raise SmokeError(
            "SMOKE_RESULT_CONTRACT_MISMATCH:"
            + repr(observed_result)
            + ":"
            + repr(expected_result)
        )

    if started.get("terminal_status") != "STARTED":
        raise SmokeError("SMOKE_STARTED_RECEIPT_STATUS_CHANGED")
    if terminal.get("terminal_status") != "ACCEPTED":
        raise SmokeError("SMOKE_TERMINAL_RECEIPT_NOT_ACCEPTED")
    if terminal.get("model_training_executed") is not False:
        raise SmokeError("SMOKE_RECEIPT_CLAIMS_TRAINING")
    if terminal.get("model_training_execution_status") != (
        "NOT_EXECUTED"
    ):
        raise SmokeError("SMOKE_TRAINING_STATUS_CHANGED")
    if terminal.get("started_from_receipt_sha256") != (
        started.get("stage_receipt_sha256")
    ):
        raise SmokeError("SMOKE_RECEIPT_CHAIN_BROKEN")
    if terminal.get("output_artifact_index_sha256") != (
        output_index.get("artifact_index_sha256")
    ):
        raise SmokeError("SMOKE_OUTPUT_INDEX_BINDING_BROKEN")

    if REVIEW_ROOT.exists():
        raise SmokeError(
            f"SMOKE_REVIEW_ROOT_ALREADY_EXISTS:{REVIEW_ROOT}"
        )
    if REVIEW_BUNDLE.exists():
        raise SmokeError(
            f"SMOKE_REVIEW_BUNDLE_ALREADY_EXISTS:{REVIEW_BUNDLE}"
        )

    REVIEW_ROOT.mkdir(parents=True, exist_ok=False)
    files = []
    for logical_name, source in required.items():
        destination = REVIEW_ROOT / "evidence" / logical_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        files.append(
            {
                "logical_name": logical_name,
                "path": str(destination.relative_to(REVIEW_ROOT)),
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
            }
        )

    for logical_name, source in (
        ("smoke_binding.json", BINDING_PATH),
        ("smoke_authorization.json", AUTHORIZATION_PATH),
    ):
        destination = REVIEW_ROOT / "authorities" / logical_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        files.append(
            {
                "logical_name": logical_name,
                "path": str(destination.relative_to(REVIEW_ROOT)),
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
            }
        )

    manifest = {
        "schema_id": (
            "ROUND_GENERIC_TRAINING_MODEL_INIT_SMOKE_REVIEW_MANIFEST_V1"
        ),
        "schema_version": 1,
        "review_status": "READY_FOR_SMOKE_RESULT_REVIEW",
        "round_id": binding["round_id"],
        "profile_id": binding["profile_id"],
        "reviewed_training_stage_freeze_root_sha256": (
            review["runner_freeze_root_sha256"]
        ),
        "smoke_binding_sha256": binding["smoke_binding_sha256"],
        "authorization_sha256": authorization[
            "authorization_sha256"
        ],
        "smoke_result_domain_sha256": result["result_sha256"],
        "terminal_stage_receipt_sha256": terminal[
            "stage_receipt_sha256"
        ],
        "files": files,
        "model_load_count": 1,
        "forward_count": 0,
        "backward_count": 0,
        "optimizer_step_count": 0,
        "training_execution_count": 0,
        "formal_training_authorized": False,
        "next_gate": (
            "MODEL_INIT_SMOKE_RESULT_REVIEW_AND_"
            "PRETRAINING_HANDOFF_RECEIPT"
        ),
    }
    manifest_path = REVIEW_ROOT / "REVIEW_MANIFEST_V1.json"
    manifest_path.write_text(
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
        REVIEW_BUNDLE,
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

    print("MODEL_INIT_SMOKE_REVIEW_BUNDLE_READY")
    print("REVIEW_BUNDLE=" + str(REVIEW_BUNDLE))
    print("REVIEW_BUNDLE_SHA256=" + sha256_file(REVIEW_BUNDLE))
    print("MODEL_LOAD_COUNT=1")
    print("OPTIMIZER_STEP_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    print(
        "NEXT_GATE=MODEL_INIT_SMOKE_RESULT_REVIEW_"
        "AND_PRETRAINING_HANDOFF_RECEIPT"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
