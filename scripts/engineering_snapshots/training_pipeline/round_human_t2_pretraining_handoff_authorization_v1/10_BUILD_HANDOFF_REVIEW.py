from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

from handoff.common import HandoffError, sha256_file
from handoff.handoff_builder import build_handoff_and_candidate


PACKAGE_ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = (
    PACKAGE_ROOT
    / "config/"
    "ROUND_PRETRAINING_HANDOFF_BUILD_CONTRACT_V1.json"
)
OUTPUT_PARENT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"
)
OUTPUT_ROOT = (
    OUTPUT_PARENT
    / "round_human_t2_pretraining_handoff_authorization_v1_review"
)
REVIEW_BUNDLE = (
    OUTPUT_PARENT
    / "ROUND_HUMAN_T2_PRETRAINING_HANDOFF_AUTHORIZATION_REVIEW_V1.zip"
)


def main() -> int:
    if REVIEW_BUNDLE.exists():
        raise HandoffError(
            f"REVIEW_BUNDLE_ALREADY_EXISTS:{REVIEW_BUNDLE}"
        )

    build_handoff_and_candidate(
        contract_path=CONTRACT_PATH,
        output_root=OUTPUT_ROOT,
    )

    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "path": str(path.relative_to(OUTPUT_ROOT)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    handoff = json.loads(
        (
            OUTPUT_ROOT
            / "ROUND_PRETRAINING_HANDOFF_RECEIPT_V1.json"
        ).read_text(encoding="utf-8")
    )
    authorization = json.loads(
        (
            OUTPUT_ROOT
            / "ROUND_TRAINING_EXECUTION_AUTHORIZATION_CANDIDATE_V1.json"
        ).read_text(encoding="utf-8")
    )

    manifest = {
        "schema_id": (
            "ROUND_HUMAN_T2_PRETRAINING_HANDOFF_"
            "AUTHORIZATION_REVIEW_MANIFEST_V1"
        ),
        "schema_version": 1,
        "review_status": "READY_FOR_FORMAL_TRAINING_AUTHORIZATION_REVIEW",
        "round_id": handoff["round_id"],
        "profile_id": handoff["profile_id"],
        "pretraining_handoff_receipt_sha256": handoff[
            "handoff_receipt_sha256"
        ],
        "authorization_candidate_sha256": authorization[
            "authorization_sha256"
        ],
        "authorization_status": authorization[
            "authorization_status"
        ],
        "formal_training_authorized": False,
        "training_execution_count": 0,
        "optimizer_steps": 3,
        "target_loss_tokens": 151,
        "diagnostic_only": True,
        "promotion_eligible": False,
        "files": files,
        "next_gate": "FORMAL_TRAINING_EXECUTION_AUTHORIZATION_REVIEW",
    }
    manifest_path = OUTPUT_ROOT / "REVIEW_MANIFEST_V1.json"
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
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(OUTPUT_ROOT).as_posix(),
                )

    print("PRETRAINING_HANDOFF_AUTHORIZATION_REVIEW_READY")
    print(
        "PRETRAINING_HANDOFF_RECEIPT_SHA256="
        + handoff["handoff_receipt_sha256"]
    )
    print(
        "AUTHORIZATION_CANDIDATE_SHA256="
        + authorization["authorization_sha256"]
    )
    print("AUTHORIZATION_STATUS=NOT_AUTHORIZED")
    print("FORMAL_TRAINING_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    print("REVIEW_BUNDLE=" + str(REVIEW_BUNDLE))
    print("REVIEW_BUNDLE_SHA256=" + sha256_file(REVIEW_BUNDLE))
    print(
        "NEXT_GATE=FORMAL_TRAINING_EXECUTION_AUTHORIZATION_REVIEW"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
