from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from smoke.smoke_runner import (
    verify_authorization,
    verify_reviewed_fixed_head,
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"STOP=MODULE_IMPORT_SPEC_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    review, binding = verify_reviewed_fixed_head()
    authorization = verify_authorization(binding)

    reviewed_root = Path(
        binding["reviewed_training_stage_root"]
    ).resolve()
    if str(reviewed_root) not in sys.path:
        sys.path.insert(0, str(reviewed_root))

    from round_training.contracts import load_stage_context

    context = load_stage_context(
        Path(binding["training_stage_binding_path"])
    )
    if context.binding["stage_binding_sha256"] != (
        binding["training_stage_binding_domain_sha256"]
    ):
        raise SystemExit("STOP=STAGE_BINDING_DOMAIN_SHA_CHANGED")

    reviewed_adapter = load_module(
        context.runtime_adapter_path,
        "reviewed_runtime_adapter_offline_preflight",
    )
    summary = reviewed_adapter.validate_profile_without_model_load(
        context
    )

    if summary["record_count"] != 12:
        raise SystemExit("STOP=OFFLINE_PREFLIGHT_ROW_COUNT_CHANGED")
    if summary["optimizer_step_count"] != 3:
        raise SystemExit(
            "STOP=OFFLINE_PREFLIGHT_OPTIMIZER_STEP_COUNT_CHANGED"
        )
    if summary["optimizer_group_target_loss_tokens"] != [
        43,
        53,
        55,
    ]:
        raise SystemExit(
            "STOP=OFFLINE_PREFLIGHT_TARGET_TOKEN_GROUPS_CHANGED"
        )

    print("MODEL_INIT_SMOKE_OFFLINE_PREFLIGHT_PASS")
    print(
        "reviewed_training_stage_freeze_root_sha256="
        + review["runner_freeze_root_sha256"]
    )
    print(
        "authorization_sha256="
        + authorization["authorization_sha256"]
    )
    print("CURRENT_T2_ROW_COUNT=12")
    print("CURRENT_T2_OPTIMIZER_STEP_COUNT=3")
    print("MODEL_LOAD_COUNT=0")
    print("OPTIMIZER_STEP_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
