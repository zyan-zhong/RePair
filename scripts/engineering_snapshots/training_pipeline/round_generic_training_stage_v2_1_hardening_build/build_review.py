from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from round_training.contracts import load_stage_context


PACKAGE_ROOT = Path(__file__).resolve().parent
PROFILE_BINDING = (
    PACKAGE_ROOT
    / "profiles/human_reference_t2/ROUND_TRAINING_STAGE_BINDING_V1.json"
)
OUTPUT_ROOT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "round_generic_training_stage_v2_1_review"
)
BUNDLE_PATH = OUTPUT_ROOT.parent / (
    "ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_BUNDLE.zip"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_files() -> list[Path]:
    excluded = {"PACKAGE_FILES.sha256", "README.txt"}
    return [
        path
        for path in sorted(PACKAGE_ROOT.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name not in excluded
        and path.suffix != ".log"
    ]


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise SystemExit(
            f"STOP=REVIEW_OUTPUT_ALREADY_EXISTS:{OUTPUT_ROOT}"
        )
    if BUNDLE_PATH.exists():
        raise SystemExit(
            f"STOP=REVIEW_BUNDLE_ALREADY_EXISTS:{BUNDLE_PATH}"
        )

    context = load_stage_context(PROFILE_BINDING)
    files = [
        {
            "path": str(path.relative_to(PACKAGE_ROOT)),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in package_files()
    ]
    freeze_payload = {
        "files": files,
        "stage_binding_sha256": context.binding[
            "stage_binding_sha256"
        ],
        "training_contract_file_sha256": context.binding[
            "training_contract_ref"
        ]["sha256"],
        "sample_order_file_sha256": context.binding[
            "sample_order_ref"
        ]["sha256"],
        "runtime_adapter_sha256": context.binding[
            "runtime_adapter_ref"
        ]["sha256"],
    }
    freeze_root = hashlib.sha256(
        json.dumps(
            freeze_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_id": "ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_MANIFEST",
        "schema_version": 1,
        "review_status": "READY_FOR_FIXED_HEAD_CODE_REVIEW",
        "runner_freeze_root_sha256": freeze_root,
        "files": files,
        "current_profile_id": context.binding["profile_id"],
        "current_round_id": context.binding["round_id"],
        "current_optimizer_step_count": context.training_contract[
            "budget"
        ]["optimizer_steps"],
        "current_target_loss_token_count": context.training_contract[
            "budget"
        ]["target_loss_token_budget"],
        "generic_stage_receipts_enabled": True,
        "generic_artifact_index_enabled": True,
        "external_authorization_required": True,
        "model_initialization_smoke_required": True,
        "training_execution_authorized": False,
        "training_execution_count": 0,
        "model_load_count": 0,
        "slurm_submission_count": 0,
        "next_gate": "GENERIC_TRAINING_STAGE_V2_1_FIXED_HEAD_REVIEW",
    }
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
    (OUTPUT_ROOT / "RUNNER_FREEZE_ROOT_SHA256.txt").write_text(
        freeze_root + "\n",
        encoding="utf-8",
    )

    package_copy = OUTPUT_ROOT / "package"
    for path in package_files():
        destination = package_copy / path.relative_to(PACKAGE_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    with zipfile.ZipFile(
        BUNDLE_PATH,
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

    print("ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_READY")
    print("RUNNER_FREEZE_ROOT_SHA256=" + freeze_root)
    print("REVIEW_BUNDLE=" + str(BUNDLE_PATH))
    print("REVIEW_BUNDLE_SHA256=" + sha256_file(BUNDLE_PATH))
    print("TRAINING_EXECUTION_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    print("NEXT_GATE=GENERIC_TRAINING_STAGE_V2_1_FIXED_HEAD_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
