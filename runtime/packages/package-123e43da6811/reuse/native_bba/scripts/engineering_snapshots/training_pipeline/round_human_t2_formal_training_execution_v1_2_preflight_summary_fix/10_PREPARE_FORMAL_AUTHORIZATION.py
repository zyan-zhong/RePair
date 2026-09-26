from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import zipfile

from formal_exec.common import (
    FormalExecutionError,
    domain_sha256,
    require_domain_sha,
    require_file_sha,
    write_json_create_once,
)


REVIEW_ZIP = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/ROUND_HUMAN_T2_PRETRAINING_HANDOFF_AUTHORIZATION_REVIEW_V1.zip')
EXPECTED_REVIEW_ZIP_SHA256 = (
    "8d9b88a4e42df9f60003b4081137839a"
    "4a8b186662af5456a376051b424f8ae0"
)
EXPECTED_HANDOFF_SHA256 = (
    "da2fcddefd52782be7640a50326e9bf7"
    "c035d00f929e051e35150464786bf323"
)
EXPECTED_CANDIDATE_SHA256 = (
    "9b07895477f1c0e97fa25835d69466e8"
    "f365d5d31993daeb3ee30a665ea6c060"
)
EXPECTED_SMOKE_AUDIT_SHA256 = (
    "77675dc1fdd989e3792c2dc334429400"
    "4e108640523ea2ecbebee2f7f3a10a16"
)
EXPECTED_SMOKE_RESULT_SHA256 = (
    "25c1a02301fd2f68746f9bdcae3d6777"
    "a47b425961fc2ba64349b000e791786b"
)
EXPECTED_RUNNER_FREEZE_ROOT = (
    "c6918c25da0cba986ef80f05f4c14401"
    "1835bca5592e4c81cc6a58cb198dd37e"
)
EXPECTED_STAGE_BINDING_SHA256 = (
    "9185d27c16789689906eddc67759a628"
    "0572016cbfd1f1122ec18f608462853e"
)
EXPECTED_APPROVAL_TOKEN = 'APPROVE_HUMAN_T2_FORMAL_TRAINING_V1'
AUTH_ROOT = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000')
AUTH_FILE = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json')
WITNESS_FILE = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/FORMAL_TRAINING_EXECUTION_APPROVAL_WITNESS_V1.json')


def load_zip_json(
    archive: zipfile.ZipFile,
    name: str,
) -> dict:
    try:
        value = json.loads(
            archive.read(name).decode("utf-8")
        )
    except KeyError as exc:
        raise FormalExecutionError(
            f"REVIEW_MEMBER_MISSING:{name}"
        ) from exc
    if not isinstance(value, dict):
        raise FormalExecutionError(
            f"REVIEW_MEMBER_NOT_OBJECT:{name}"
        )
    return value


def main() -> int:
    approval = os.environ.get(
        "HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL"
    )
    if approval != EXPECTED_APPROVAL_TOKEN:
        raise FormalExecutionError(
            "EXPLICIT_FORMAL_TRAINING_EXECUTION_APPROVAL_REQUIRED"
        )

    require_file_sha(
        REVIEW_ZIP,
        EXPECTED_REVIEW_ZIP_SHA256,
        "PRETRAINING_REVIEW_ZIP",
    )

    if AUTH_ROOT.exists():
        if not AUTH_FILE.is_file() or not WITNESS_FILE.is_file():
            raise FormalExecutionError(
                f"AUTHORIZATION_ROOT_INCOMPLETE:{AUTH_ROOT}"
            )

        existing_witness = json.loads(
            WITNESS_FILE.read_text(encoding="utf-8")
        )
        existing_auth = json.loads(
            AUTH_FILE.read_text(encoding="utf-8")
        )
        require_domain_sha(
            existing_witness,
            schema_id=(
                "HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL_WITNESS_V1"
            ),
            sha_field="approval_witness_sha256",
        )
        require_domain_sha(
            existing_auth,
            schema_id="ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
            sha_field="authorization_sha256",
        )

        expected_existing = {
            "authorization_status": "APPROVED",
            "approval_token_id": EXPECTED_APPROVAL_TOKEN,
            "pretraining_review_zip_sha256": EXPECTED_REVIEW_ZIP_SHA256,
            "authorization_candidate_sha256": EXPECTED_CANDIDATE_SHA256,
            "pretraining_handoff_receipt_sha256": EXPECTED_HANDOFF_SHA256,
            "model_init_smoke_result_domain_sha256": (
                EXPECTED_SMOKE_RESULT_SHA256
            ),
            "runner_freeze_root_sha256": EXPECTED_RUNNER_FREEZE_ROOT,
            "stage_binding_sha256": EXPECTED_STAGE_BINDING_SHA256,
            "execution_attempt_id": "human-t2-train17-continuation-v1-a000",
            "authorized_optimizer_steps": 3,
            "authorized_target_loss_tokens": 151,
            "diagnostic_only": True,
            "promotion_eligible": False,
            "training_execution_count_before": 0,
        }
        observed_existing = {
            key: existing_auth.get(key)
            for key in expected_existing
        }
        if observed_existing != expected_existing:
            raise FormalExecutionError(
                "EXISTING_AUTHORIZATION_CONTRACT_CHANGED:"
                + repr(observed_existing)
                + ":"
                + repr(expected_existing)
            )
        if existing_auth.get("approval_witness_sha256") != (
            existing_witness.get("approval_witness_sha256")
        ):
            raise FormalExecutionError(
                "EXISTING_AUTHORIZATION_WITNESS_BINDING_BROKEN"
            )
        if existing_witness.get("approval_token_id") != (
            EXPECTED_APPROVAL_TOKEN
        ):
            raise FormalExecutionError(
                "EXISTING_APPROVAL_WITNESS_TOKEN_CHANGED"
            )

        print("FORMAL_TRAINING_AUTHORIZATION_REUSED")
        print(
            "APPROVAL_WITNESS_SHA256="
            + existing_witness["approval_witness_sha256"]
        )
        print(
            "APPROVED_AUTHORIZATION_SHA256="
            + existing_auth["authorization_sha256"]
        )
        print("AUTHORIZATION_STATUS=APPROVED")
        print("OPTIMIZER_STEPS=3")
        print("TARGET_LOSS_TOKENS=151")
        print("DIAGNOSTIC_ONLY=true")
        print("PROMOTION_ELIGIBLE=false")
        print("TRAINING_EXECUTION_COUNT_BEFORE=0")
        return 0

    with zipfile.ZipFile(REVIEW_ZIP, "r") as archive:
        if archive.testzip() is not None:
            raise FormalExecutionError(
                "PRETRAINING_REVIEW_ZIP_CRC_FAILED"
            )

        manifest = load_zip_json(
            archive,
            "REVIEW_MANIFEST_V1.json",
        )
        audit = load_zip_json(
            archive,
            "MODEL_INIT_SMOKE_RESULT_AUDIT_V1.json",
        )
        handoff = load_zip_json(
            archive,
            "ROUND_PRETRAINING_HANDOFF_RECEIPT_V1.json",
        )
        candidate = load_zip_json(
            archive,
            "ROUND_TRAINING_EXECUTION_AUTHORIZATION_CANDIDATE_V1.json",
        )

    if manifest.get("review_status") != (
        "READY_FOR_FORMAL_TRAINING_AUTHORIZATION_REVIEW"
    ):
        raise FormalExecutionError(
            "PRETRAINING_REVIEW_STATUS_CHANGED"
        )
    if manifest.get("authorization_status") != "NOT_AUTHORIZED":
        raise FormalExecutionError(
            "PRETRAINING_REVIEW_ALREADY_AUTHORIZED"
        )
    if manifest.get("formal_training_authorized") is not False:
        raise FormalExecutionError(
            "PRETRAINING_REVIEW_FORMAL_TRAINING_AUTH_CHANGED"
        )
    if manifest.get("training_execution_count") != 0:
        raise FormalExecutionError(
            "PRETRAINING_REVIEW_TRAINING_COUNT_NOT_ZERO"
        )

    require_domain_sha(
        audit,
        schema_id="MODEL_INIT_SMOKE_RESULT_AUDIT_V1",
        sha_field="audit_sha256",
    )
    if audit["audit_sha256"] != EXPECTED_SMOKE_AUDIT_SHA256:
        raise FormalExecutionError(
            "SMOKE_AUDIT_SHA_CHANGED"
        )
    if audit.get("audit_status") != "PASS":
        raise FormalExecutionError(
            "SMOKE_AUDIT_NOT_PASS"
        )
    if audit.get("smoke_result_domain_sha256") != (
        EXPECTED_SMOKE_RESULT_SHA256
    ):
        raise FormalExecutionError(
            "SMOKE_RESULT_DOMAIN_SHA_CHANGED"
        )
    if audit.get("optimizer_step_count") != 0:
        raise FormalExecutionError(
            "SMOKE_OPTIMIZER_STEP_COUNT_NOT_ZERO"
        )
    if audit.get("training_execution_count") != 0:
        raise FormalExecutionError(
            "SMOKE_TRAINING_COUNT_NOT_ZERO"
        )

    require_domain_sha(
        handoff,
        schema_id="ROUND_PRETRAINING_HANDOFF_RECEIPT_V1",
        sha_field="handoff_receipt_sha256",
    )
    if handoff["handoff_receipt_sha256"] != (
        EXPECTED_HANDOFF_SHA256
    ):
        raise FormalExecutionError(
            "PRETRAINING_HANDOFF_SHA_CHANGED"
        )
    if handoff.get("handoff_status") != (
        "READY_FOR_FORMAL_TRAINING_AUTHORIZATION_REVIEW"
    ):
        raise FormalExecutionError(
            "PRETRAINING_HANDOFF_STATUS_CHANGED"
        )
    if handoff.get("formal_training_authorized") is not False:
        raise FormalExecutionError(
            "PRETRAINING_HANDOFF_ALREADY_AUTHORIZED"
        )
    if handoff.get("training_execution_count") != 0:
        raise FormalExecutionError(
            "PRETRAINING_HANDOFF_TRAINING_COUNT_NOT_ZERO"
        )

    require_domain_sha(
        candidate,
        schema_id="ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        sha_field="authorization_sha256",
    )
    if candidate["authorization_sha256"] != (
        EXPECTED_CANDIDATE_SHA256
    ):
        raise FormalExecutionError(
            "AUTHORIZATION_CANDIDATE_SHA_CHANGED"
        )

    expected_candidate = {
        "authorization_status": "NOT_AUTHORIZED",
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "stage_id": "TRAINING_EXECUTION",
        "profile_id": (
            "HUMAN_T2_UNVERIFIED_REPAIR_DIAGNOSTIC_PROFILE_V1"
        ),
        "stage_binding_sha256": EXPECTED_STAGE_BINDING_SHA256,
        "runner_freeze_root_sha256": EXPECTED_RUNNER_FREEZE_ROOT,
        "execution_attempt_id": 'human-t2-train17-continuation-v1-a000',
        "authorized_output_dir": '/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_v1/human-t2-train17-continuation-v1-a000',
        "stage_attempt_root": '/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_stage_attempts_v1/human-t2-train17-continuation-v1-a000',
        "authorized_optimizer_steps": 3,
        "authorized_target_loss_tokens": 151,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "training_execution_count_before": 0,
        "pretraining_handoff_receipt_sha256": (
            EXPECTED_HANDOFF_SHA256
        ),
        "model_init_smoke_result_domain_sha256": (
            EXPECTED_SMOKE_RESULT_SHA256
        ),
    }
    observed_candidate = {
        key: candidate.get(key)
        for key in expected_candidate
    }
    if observed_candidate != expected_candidate:
        raise FormalExecutionError(
            "AUTHORIZATION_CANDIDATE_CONTRACT_CHANGED:"
            + repr(observed_candidate)
            + ":"
            + repr(expected_candidate)
        )

    witness = {
        "schema_id": (
            "HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL_WITNESS_V1"
        ),
        "schema_version": 1,
        "approval_token_id": EXPECTED_APPROVAL_TOKEN,
        "round_id": candidate["round_id"],
        "profile_id": candidate["profile_id"],
        "stage_id": candidate["stage_id"],
        "pretraining_review_zip_sha256": (
            EXPECTED_REVIEW_ZIP_SHA256
        ),
        "pretraining_handoff_receipt_sha256": (
            EXPECTED_HANDOFF_SHA256
        ),
        "authorization_candidate_sha256": (
            EXPECTED_CANDIDATE_SHA256
        ),
        "model_init_smoke_audit_sha256": (
            EXPECTED_SMOKE_AUDIT_SHA256
        ),
        "model_init_smoke_result_domain_sha256": (
            EXPECTED_SMOKE_RESULT_SHA256
        ),
        "runner_freeze_root_sha256": (
            EXPECTED_RUNNER_FREEZE_ROOT
        ),
        "stage_binding_sha256": (
            EXPECTED_STAGE_BINDING_SHA256
        ),
        "execution_attempt_id": candidate[
            "execution_attempt_id"
        ],
        "authorized_optimizer_steps": 3,
        "authorized_target_loss_tokens": 151,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "training_execution_count_before": 0,
        "approval_witness_sha256": "",
    }
    witness["approval_witness_sha256"] = domain_sha256(
        witness["schema_id"],
        witness,
        sha_field="approval_witness_sha256",
    )

    authorized = dict(candidate)
    authorized["authorization_status"] = "APPROVED"
    authorized["approval_token_id"] = EXPECTED_APPROVAL_TOKEN
    authorized["approval_witness_sha256"] = witness[
        "approval_witness_sha256"
    ]
    authorized["pretraining_review_zip_sha256"] = (
        EXPECTED_REVIEW_ZIP_SHA256
    )
    authorized["authorization_candidate_sha256"] = (
        EXPECTED_CANDIDATE_SHA256
    )
    authorized["authorization_sha256"] = ""
    authorized["authorization_sha256"] = domain_sha256(
        authorized["schema_id"],
        authorized,
        sha_field="authorization_sha256",
    )

    AUTH_ROOT.mkdir(parents=True, exist_ok=False)
    write_json_create_once(
        WITNESS_FILE,
        witness,
    )
    write_json_create_once(
        AUTH_FILE,
        authorized,
    )

    print("FORMAL_TRAINING_AUTHORIZATION_PREPARED")
    print(
        "APPROVAL_WITNESS_SHA256="
        + witness["approval_witness_sha256"]
    )
    print(
        "APPROVED_AUTHORIZATION_SHA256="
        + authorized["authorization_sha256"]
    )
    print("AUTHORIZATION_STATUS=APPROVED")
    print("OPTIMIZER_STEPS=3")
    print("TARGET_LOSS_TOKENS=151")
    print("DIAGNOSTIC_ONLY=true")
    print("PROMOTION_ELIGIBLE=false")
    print("TRAINING_EXECUTION_COUNT_BEFORE=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
