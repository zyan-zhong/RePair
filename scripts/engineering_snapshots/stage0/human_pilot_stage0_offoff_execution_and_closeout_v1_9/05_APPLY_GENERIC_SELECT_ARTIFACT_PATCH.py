from pathlib import Path

from stage0.generic_select_artifact_patch import (
    apply_or_verify_generic_select_artifact_patch,
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    receipt = apply_or_verify_generic_select_artifact_patch(
        package_root=root,
    )
    print("GENERIC_SELECT_ARTIFACT_IDENTITY_PATCH_PASS")
    print(
        "PATCH_FREEZE_ROOT_SHA256="
        + receipt[
            "generic_select_artifact_patch_freeze_root_sha256"
        ]
    )
    print("MODEL_EXECUTION_COUNT=0")
    print("ENVIRONMENT_EXECUTION_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
