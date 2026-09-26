from __future__ import annotations

from pathlib import Path

PACKAGE_ID = "STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_V1"
APPROVAL_TOKEN = "APPROVE_STAGE1_GENERIC_ROUND_CONTROL_PLANE_V1"

EXPECTED_SOURCE_HEAD = "daef26b9cde45182ada534d96335da3ea451f12f"
GENERIC_WORKTREE = Path(
    "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
    "pchsi-wt-generic-select-policy-binding-human-offoff-v1"
)

STAGE0_CLOSEOUT_ZIP = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "HUMAN_PILOT_STAGE0_OFFOFF_CLOSEOUT_REVIEW_V1.zip"
)
STAGE0_CLOSEOUT_ZIP_SHA256 = (
    "7d29e40bf7c5f7df8869382071529a90fc2a44c1f3acc29d0e0b367d941bdba3"
)
STAGE0_CLOSEOUT_SHA256 = (
    "02beba4f0d7377742da10cd67460ce0df9cb919f01dc0b1acd524d20717953c0"
)
STAGE0_HANDOFF_SHA256 = (
    "cbfce1f127e6bdad4313073cc4a0998164d573d200bf6e33c82a9ff3d04bdbe5"
)

STAGE0_GENERIC_PATCH_RECEIPT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1/"
    "human_pilot_stage0_offoff_v1/"
    "generic_select_artifact_patch_v1/"
    "GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT_V1.json"
)
STAGE0_GENERIC_PATCH_FREEZE_ROOT_SHA256 = (
    "15d323f5b6ca6869901819341663145f3c30253e2d29cde886dc8c66566577cf"
)

OUTPUT_ROOT = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "stage1_generic_round_automation_control_plane_v1_output"
)
REVIEW_ROOT = OUTPUT_ROOT / "review"
REVIEW_ZIP = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_REVIEW_V1.zip"
)

PREEXISTING_CHANGED_PATHS = frozenset({
    "configs/evaluation/schemas/e1_episode_artifact_v1.json",
    "configs/evaluation/schemas/select_policy_runtime_manifest_v1.json",
    "configs/evaluation/schemas/select_server_runtime_manifest_v1.json",
    "src/pchsi/evaluation/action_trace.py",
    "src/pchsi/evaluation/schema_models.py",
    "src/pchsi/evaluation/select_execution_identity.py",
    "src/pchsi/evaluation/select_policy_runtime.py",
    "src/pchsi/evaluation/select_result_audit.py",
    "tests/evaluation/test_generic_select_artifact_identity_v1.py",
    "tests/evaluation/test_generic_select_policy_artifact_binding_v1.py",
})

STAGE1_NEW_PATHS = frozenset({
    "src/pchsi/round_control/__init__.py",
    "src/pchsi/round_control/benchmark_sealing.py",
    "src/pchsi/round_control/bindings.py",
    "src/pchsi/round_control/clean_data_gate.py",
    "src/pchsi/round_control/common.py",
    "src/pchsi/round_control/lifecycle.py",
    "src/pchsi/round_control/orchestrator.py",
    "src/pchsi/round_control/promotion.py",
    "src/pchsi/round_control/retention.py",
    "src/pchsi/round_control/role_authority.py",
    "src/pchsi/round_control/trace_handoff.py",
    "tests/round_control/test_bindings.py",
    "tests/round_control/test_clean_data_gate.py",
    "tests/round_control/test_lifecycle.py",
    "tests/round_control/test_promotion_orchestrator.py",
    "tests/round_control/test_retention_and_benchmark.py",
    "tests/round_control/test_role_authority.py",
    "tests/round_control/test_trace_handoff.py",
    "docs/stage1/STAGE1_GENERIC_ROUND_CONTROL_PLANE_DESIGN_V1.md",
    "docs/stage1/STAGE1_GENERIC_ROUND_CONTROL_PLANE_IMPLEMENTATION_PLAN_V1.md",
})
