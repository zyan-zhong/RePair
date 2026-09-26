from __future__ import annotations

from pathlib import Path

PACKAGE_ID = "HUMAN_PILOT_STAGE0_OFFOFF_EXECUTION_AND_CLOSEOUT_V1_9"
APPROVAL_TOKEN = "APPROVE_HUMAN_PILOT_STAGE0_OFFOFF_V1"

EXPECTED_SOURCE_HEAD = "daef26b9cde45182ada534d96335da3ea451f12f"
GENERIC_WORKTREE = Path(
    "/data/run01/scwb204/sdar_repro/badcase/github_exports/"
    "pchsi-wt-generic-select-policy-binding-human-offoff-v1"
)
PYTHON = Path(
    "/data/home/scwb204/run/sdar_repro/conda_envs/"
    "sdar_sft_py312/bin/python"
)
CONDA_SH = Path(
    "/data/apps/miniforge3/25.11.0-1/etc/profile.d/conda.sh"
)
CONDA_ENV = Path(
    "/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312"
)

GENERIC_FIXED_HEAD_REVIEW = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "GENERIC_SELECT_POLICY_ARTIFACT_BINDING_HUMAN_OFFOFF_REVIEW_V1.zip"
)
GENERIC_FIXED_HEAD_REVIEW_SHA256 = (
    "842d6e6549ab2de8e9b29ab30fddcd6d34f0d4c5d15436d4360f1a43e30fc4fe"
)
TWIN_REVIEW = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_V1_1.zip"
)
TWIN_REVIEW_SHA256 = (
    "bdbd56c6a5132026f5429b5aa2a46e6907e733f1e8be80b8021f8ee445dad569"
)

TASK_ACCESS = Path(
    "/data/home/scwb204/pchsi_evidence/p1b_materialized_access_v1/"
    "task_access_manifest.json"
)
TASK_ACCESS_SHA256 = (
    "5b8859a50478601cc054423af88fb57f5c31d95b96aeb67ab528987274eb9718"
)

E1_READINESS_ROOT = Path(
    "/data/home/scwb204/pchsi_evidence/e1_readiness_v1_05e4c688"
)
E1_DESIGN_MERGE_COMMIT = (
    "5cddface67c220c8c799d1b0699cf611d7ffc78a"
)
E1_POLICY_REQUEST_SOURCE_RELATIVE_PATH = (
    "src/pchsi/evaluation/policy_request.py"
)
E1_POLICY_REQUEST_SCHEMA_SHA256 = (
    "a0edd1091b57224b70f3f403838e9f166ea8af0358da0661f1e636252bd0fc3a"
)
E1_READINESS_SUMMARY = E1_READINESS_ROOT / "readiness_summary.json"
ENVIRONMENT_RUNTIME_MANIFEST = (
    E1_READINESS_ROOT / "alfworld_environment_runtime_manifest_v1.json"
)

BASE_MODEL_PATH = Path(
    "/data/run01/scwb204/.cache/huggingface/hub/"
    "models--Qwen--Qwen2.5-3B-Instruct/snapshots/"
    "aa8e72537993ba99e69dfaafa59ed015b17504d1"
)
BASE_MODEL_REVISION = "aa8e72537993ba99e69dfaafa59ed015b17504d1"

PARENT_LOGICAL_ID = "P4-R1-Q2-BAD"
PARENT_CHECKPOINT_ID = "P4-R1-Q2-BAD-TRAIN17"
PARENT_ADAPTER_SHA256 = (
    "b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"
)
PARENT_ADAPTER_PATH = Path(
    "/data/run01/scwb204/pchsi/p2/"
    "p4_r1_q2_bad_checkpoint_set_v1_frozen/seed_17/adapter"
)

CANDIDATE_LOGICAL_ID = "P4-R2-HUMAN-T2-DIAGNOSTIC"
CANDIDATE_CHECKPOINT_ID = "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17"
CANDIDATE_ADAPTER_SHA256 = (
    "908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e"
)
CANDIDATE_ADAPTER_PATH = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1/"
    "human_t2_train17_continuation_v1/"
    "human-t2-train17-continuation-v1-a000/adapter"
)

PROTOCOL_EQUALITY_SHA256 = (
    "d831c966daf214955683541d4a0434b85feb6ee696eb854bec301a334297ebca"
)
OFFOFF_HANDOFF_SHA256 = (
    "22c9ad08bc0a74f315d03170bd5cffc645f113c06603c5dff161778cf70e211a"
)
REPLICATE_SEEDS = (17, 31, 47, 73, 101)
SELECT_TASK_COUNT = 17
PAIRED_CELL_COUNT = 85
TOTAL_CONDITION_CELL_COUNT = 170

ROUND_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/experiments/"
    "human_reference_round_pi1_pi2_v1"
)
STAGE0_ROOT = ROUND_ROOT / "human_pilot_stage0_offoff_v1"
GENERIC_SELECT_ARTIFACT_PATCH_ROOT = (
    STAGE0_ROOT / "generic_select_artifact_patch_v1"
)
GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT = (
    GENERIC_SELECT_ARTIFACT_PATCH_ROOT
    / "GENERIC_SELECT_ARTIFACT_PATCH_RECEIPT_V1.json"
)
PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"
AUTHORIZATION_ROOT = STAGE0_ROOT / "authorization_v1_9"
EXECUTION_ROOT = STAGE0_ROOT / "execution"
REVIEW_ROOT = STAGE0_ROOT / "review_v1"
FINAL_REVIEW_ZIP = Path(
    "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/"
    "HUMAN_PILOT_STAGE0_OFFOFF_CLOSEOUT_REVIEW_V1.zip"
)
