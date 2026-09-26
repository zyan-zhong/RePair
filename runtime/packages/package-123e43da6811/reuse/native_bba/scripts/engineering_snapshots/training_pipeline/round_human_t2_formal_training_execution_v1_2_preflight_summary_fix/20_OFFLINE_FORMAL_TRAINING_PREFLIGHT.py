from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

from formal_exec.common import (
    FormalExecutionError,
    load_json,
    require_domain_sha,
    require_file_sha,
)


V21_ROOT_LOGICAL = Path('/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/round_generic_training_stage_v2_1_hardening_build')
STAGE_BINDING = (
    V21_ROOT_LOGICAL
    / "profiles/human_reference_t2/"
    "ROUND_TRAINING_STAGE_BINDING_V1.json"
)
AUTH_FILE = Path('/data/run01/scwb204/sdar_repro/badcase/experiments/human_reference_round_pi1_pi2_v1/human_t2_train17_continuation_authorization_v1/human-t2-train17-continuation-v1-a000/ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1.json')
EXPECTED_STAGE_BINDING_FILE_SHA = (
    "3c4b9954e5feea8ef7f682c2df1328f"
    "4413f7e4e2e650ce61aea91d8602e379a"
)
EXPECTED_STAGE_BINDING_DOMAIN_SHA = (
    "9185d27c16789689906eddc67759a628"
    "0572016cbfd1f1122ec18f608462853e"
)
EXPECTED_RUNNER_FREEZE_ROOT = (
    "c6918c25da0cba986ef80f05f4c14401"
    "1835bca5592e4c81cc6a58cb198dd37e"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )
    if spec is None or spec.loader is None:
        raise FormalExecutionError(
            f"MODULE_IMPORT_SPEC_FAILED:{path}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if not V21_ROOT_LOGICAL.is_dir():
        raise FormalExecutionError(
            f"V21_ROOT_MISSING:{V21_ROOT_LOGICAL}"
        )

    require_file_sha(
        STAGE_BINDING,
        EXPECTED_STAGE_BINDING_FILE_SHA,
        "V21_STAGE_BINDING",
    )
    binding = load_json(STAGE_BINDING)
    if binding.get("stage_binding_sha256") != (
        EXPECTED_STAGE_BINDING_DOMAIN_SHA
    ):
        raise FormalExecutionError(
            "V21_STAGE_BINDING_DOMAIN_SHA_CHANGED"
        )

    auth = load_json(AUTH_FILE)
    require_domain_sha(
        auth,
        schema_id="ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        sha_field="authorization_sha256",
    )
    if auth.get("authorization_status") != "APPROVED":
        raise FormalExecutionError(
            "FORMAL_TRAINING_AUTHORIZATION_NOT_APPROVED"
        )
    if auth.get("runner_freeze_root_sha256") != (
        EXPECTED_RUNNER_FREEZE_ROOT
    ):
        raise FormalExecutionError(
            "AUTHORIZATION_RUNNER_FREEZE_ROOT_CHANGED"
        )

    root_text = str(V21_ROOT_LOGICAL.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    from round_training.contracts import (
        load_execution_authorization,
        load_stage_context,
    )
    from round_training.stage_runner import (
        reject_ambient_environment,
    )

    context = load_stage_context(STAGE_BINDING)
    reject_ambient_environment(context)

    load_execution_authorization(
        AUTH_FILE,
        context=context,
        runner_freeze_root_sha256=(
            EXPECTED_RUNNER_FREEZE_ROOT
        ),
    )

    adapter_path = context.runtime_adapter_path
    adapter = load_module(
        adapter_path,
        "formal_training_preflight_adapter",
    )
    summary = adapter.validate_profile_without_model_load(
        context
    )

    expected_summary = {
        "record_count": 12,
        "optimizer_step_count": 3,
        "optimizer_group_target_loss_tokens": [43, 53, 55],
        "direct_input_artifact_count": 8,
        "parent_adapter_bundle_sha256": (
            "b296f2254b1fa1f2e141dffd3f6b5af"
            "903f839df4790ffcb245fd8dd57773ace"
        ),
    }
    if summary != expected_summary:
        raise FormalExecutionError(
            "FORMAL_TRAINING_PREFLIGHT_SUMMARY_CHANGED:"
            + repr(summary)
            + ":"
            + repr(expected_summary)
        )

    print("FORMAL_TRAINING_OFFLINE_PREFLIGHT_PASS")
    print("CURRENT_T2_ROW_COUNT=12")
    print("OPTIMIZER_STEP_COUNT=3")
    print("TARGET_LOSS_TOKEN_GROUPS=[43,53,55]")
    print("TARGET_LOSS_TOKEN_TOTAL=151")
    print("DIAGNOSTIC_ONLY=true")
    print("PROMOTION_ELIGIBLE=false")
    print("TRAINING_EXECUTION_COUNT_BEFORE=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
