#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import (
    ContractError,
    finalize,
    load_json_object,
    write_new_json,
)


def main() -> int:
    native = load_json_object(
        Path(os.environ["NATIVE_ROOT"])
        / "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json"
    )
    bridge = load_json_object(Path(os.environ["V16_NORMATIVE_BRIDGE_PATH"]))
    plan = load_json_object(Path(os.environ["STRONG_PLAN_PATH"]))
    parent = load_json_object(Path(os.environ["PARENT_CHECKPOINT_SET_MANIFEST"]))

    if bridge.get("normative_bridge_sha256") != os.environ[
        "EXPECTED_V16_NORMATIVE_BRIDGE_SHA256"
    ]:
        raise ContractError("V16_NORMATIVE_BRIDGE_IDENTITY_CHANGED")
    if plan.get("training_plan_sha256") != os.environ[
        "EXPECTED_STRONG_PLAN_SHA256"
    ]:
        raise ContractError("STRONG_PLAN_IDENTITY_CHANGED")

    checkpoints = parent.get("checkpoints")
    train17 = [
        row for row in checkpoints
        if isinstance(row, dict)
        and row.get("training_seed") == 17
    ]
    if len(train17) != 1:
        raise ContractError("TRAIN17_PARENT_NOT_EXACTLY_ONE")

    recipe = plan.get("policy_training_recipe")
    if not isinstance(recipe, dict):
        raise ContractError("POLICY_TRAINING_RECIPE_MISSING")

    preflight = finalize(
        "TRAINER_EXECUTION_PREFLIGHT_V5",
        "trainer_preflight_v5_sha256",
        {
            "schema_id": "TRAINER_EXECUTION_PREFLIGHT_V5",
            "schema_version": 5,
            "round_kind": "HUMAN_REFERENCE_ROUND",
            "parent_policy_id": os.environ["PARENT_POLICY_ID"],
            "parent_policy_training_seed": 17,
            "parent_adapter_relative_path": train17[0].get(
                "adapter_relative_path"
            ),
            "parent_adapter_bundle_sha256": train17[0].get(
                "adapter_bundle_sha256"
            ),
            "foundation_repository": os.environ[
                "QWEN_FOUNDATION_REPOSITORY"
            ],
            "foundation_revision": os.environ[
                "QWEN_FOUNDATION_REVISION"
            ],
            "research_planner_training_plan_sha256": plan[
                "training_plan_sha256"
            ],
            "trainer_native_dataset_manifest_sha256": native[
                "trainer_native_dataset_manifest_sha256"
            ],
            "trainer_native_row_count": native["sample_count"],
            "training_seed": recipe.get("training_seed"),
            "epochs": recipe.get("epochs"),
            "unique_sample_budget": recipe.get(
                "unique_sample_budget"
            ),
            "training_token_budget": recipe.get(
                "training_token_budget"
            ),
            "one_pass_target_loss_token_count": native[
                "one_pass_target_loss_token_count"
            ],
            "selected_arm_ids": plan.get("selected_arm_ids"),
            "diagnostic_only": True,
            "promotion_eligible": False,
            "raw_base_reinitialization_allowed": False,
            "parent_lora_continuation_required": True,
            "memory_off_harness_off_evaluation_required": True,
            "trainer_execution_authorized": False,
            "blocking_reasons": [
                "PARENT_TRAIN17_LORA_CONTINUATION_TRAINER_RUNNER_REVIEW_REQUIRED",
                "EXPLICIT_GPU_TRAINING_EXECUTION_APPROVAL_REQUIRED",
            ],
            "next_gate": (
                "BUILD_AND_REVIEW_PARENT_TRAIN17_LORA_CONTINUATION_TRAINER_RUNNER"
            ),
            "training_execution_count": 0,
        },
    )

    # Human-readable Chinese mainline is a view, not a decision authority.
    mainline = finalize(
        "RESEARCH_MAINLINE_ZH_VIEW_V1",
        "research_mainline_zh_view_sha256",
        {
            "schema_id": "RESEARCH_MAINLINE_ZH_VIEW_V1",
            "schema_version": 1,
            "说明": (
                "这是中文展示视图，不替代任何科研 authority；"
                "所有决定仍以对应英文机器 artifact 的 SHA 为准。"
            ),
            "当前总主线": (
                "人工参考轮：真实失败 → Human/Strong PRE → 同状态 F0/F1 → "
                "Human/Strong POST → Strong 训练计划 → 确定性数据构造 → "
                "Qwen Trainer 原生数据 → π2-human 诊断训练 → "
                "Memory OFF + Harness OFF 评估 → 人工参考轮收尾 → "
                "Strong 主导 fresh round → Local Qwen 自主 fresh round"
            ),
            "当前所在阶段": (
                "已经完成 Trainer 原生数据准备；下一步审核并构建 "
                "Train17 LoRA 继续训练 runner。"
            ),
            "人工参考轮的作用": [
                "建立失败分析思路与字段规范",
                "建立 PRE/POST 严格科研流程",
                "建立 F0/F1 因果验证规范",
                "建立 Benefit/Harm/Neutral/Uncertain 四类处理规范",
                "建立 Failure Experience、适用条件与反例规范",
                "建立 T0-T6 训练层级与启用规则",
                "建立数据语义、mixture、预算、停止与回滚规范",
                "产生可用于 Strong/Local Planner 学习的完整 teacher traces",
            ],
            "Strong接管如何继承人工轮": {
                "必须继承": [
                    "分析规范",
                    "artifact schema",
                    "证据标准",
                    "PRE/POST 纪律",
                    "B/H/N/U 路由规则",
                    "T0-T6 训练规范",
                    "Data Builder / Trainer / Promotion Gate 权限边界",
                    "人工参考轮 teacher curriculum",
                ],
                "fresh_round必须重新决定": [
                    "当前父策略",
                    "fresh failure cohort",
                    "当前 bottleneck",
                    "repair portfolio",
                    "实验与预算",
                    "F0/F1 结果",
                    "最终训练 routes",
                    "mixture 与训练 recipe",
                    "promotion/rollback",
                ],
                "核心原则": (
                    "继承规范与 teacher traces；重置 fresh-round 答案。"
                ),
            },
            "Local自主轮如何继承": (
                "Local Qwen Planner 继承人工参考轮和 Strong 主导 fresh round "
                "产生的 teacher curriculum，并保持同一套 artifact contract；"
                "最终 routine Human 决策=0、routine Strong API 调用=0。"
            ),
            "本轮不可混淆": [
                "当前是 Human Reference Round，不是 Strong takeover round",
                "当前 π2 是 human diagnostic candidate，不可宣称 autonomous improvement",
                "当前 T2 Neutral/Uncertain diagnostic 数据不是 verified positive",
                "Strong takeover 必须在人工参考轮完成并收尾后开启 fresh round",
            ],
            "当前已完成": [
                "Human PRE",
                "Strong PRE shadow",
                "PRE adjudication",
                "12 states × 5 paired repeats × F0/F1",
                "60/60 Neutral 终局结果",
                "Neutral 局部机制审计",
                "Human POST",
                "Strong POST shadow",
                "POST adjudication",
                "Strong Research Planner training plan",
                "8 个 semantic datasets",
                "历史 Q2 renderer schema census",
                "Human→Strong normative bridge",
                "历史 renderer 84/84 精确回放",
                "12 条 Policy T2 Trainer 原生数据",
            ],
            "下一步": [
                "构建并审核 Train17 LoRA 继续训练 runner",
                "显式 GPU 训练批准",
                "生成 π2-human diagnostic checkpoint",
                "跑 Memory OFF + Harness OFF 对照评估",
                "关闭 Human Reference Round",
                "进入 Strong primary fresh round",
            ],
            "权威引用": {
                "v16_normative_bridge_sha256": bridge[
                    "normative_bridge_sha256"
                ],
                "strong_training_plan_sha256": plan[
                    "training_plan_sha256"
                ],
                "trainer_native_dataset_manifest_sha256": native[
                    "trainer_native_dataset_manifest_sha256"
                ],
                "trainer_preflight_v5_sha256": preflight[
                    "trainer_preflight_v5_sha256"
                ],
            },
            "strong_takeover_execution_ready": False,
            "local_autonomous_execution_ready": False,
            "trainer_execution_authorized": False,
            "training_execution_count": 0,
        },
    )

    mainline_root = Path(os.environ["MAINLINE_ROOT"])
    preflight_root = Path(os.environ["PREFLIGHT_ROOT"])
    mainline_root.mkdir(parents=True, exist_ok=False)
    preflight_root.mkdir(parents=True, exist_ok=False)

    write_new_json(
        mainline_root / "RESEARCH_MAINLINE_ZH_VIEW_V1.json",
        mainline,
    )
    write_new_json(
        preflight_root / "TRAINER_EXECUTION_PREFLIGHT_V5.json",
        preflight,
    )

    print("【阶段40】中文科研主线与 Trainer 预检：通过")
    print("中文主线_SHA256=" + mainline["research_mainline_zh_view_sha256"])
    print("TRAINER_PREFLIGHT_V5_SHA256=" + preflight["trainer_preflight_v5_sha256"])
    print("当前阶段=Trainer原生数据已准备，下一步审核Train17_LoRA继续训练Runner")
    print("人工参考轮与Strong接管关系=继承规范与TeacherTraces_重置FreshRound答案")
    print("STRONG_TAKEOVER_EXECUTION_READY=false")
    print("LOCAL_AUTONOMOUS_EXECUTION_READY=false")
    print("TRAINER_EXECUTION_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
