#!/usr/bin/env python3
"""Materialize a deterministic, outcome-blind manual reference-round readiness pack.

The script inventories existing assets. It does not call any model, execute an
environment, run F0/F1, train a policy, or finalize a Human Researcher PRE.
Missing assets remain explicit QUERY_REQUIRED items.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable


SCHEMA_VERSION = "REFERENCE_ROUND_READINESS_V2"


@dataclass(frozen=True)
class RequiredAsset:
    asset_id: str
    relative_path: str
    purpose: str
    required_for_human_pre: bool = True


REQUIRED_ASSETS: tuple[RequiredAsset, ...] = (
    RequiredAsset(
        "HUMAN_RESEARCHER_TEMPLATE_V2",
        "docs/research/HUMAN_TRAINING_RESEARCHER_TEMPLATE_V2.md",
        "Human reference-round PRE/POST scientific template",
    ),
    RequiredAsset(
        "ROLE_LOCALIZATION_ROADMAP",
        "docs/research/ROLE_LOCALIZATION_AND_UNIFICATION_ROADMAP.md",
        "Human -> strong-model -> local unified-role transition",
    ),
    RequiredAsset(
        "CURRENT_RESEARCHER_RUNTIME",
        "src/pchsi/cognitive_runtime/researcher.py",
        "Current Human/API Researcher finalization runtime",
    ),
    RequiredAsset(
        "HUMAN_PRE_SCHEMA",
        "configs/cognitive_runtime/schemas/human_researcher_pre_v1.json",
        "Current Human Researcher PRE schema",
    ),
    RequiredAsset(
        "HUMAN_POST_SCHEMA",
        "configs/cognitive_runtime/schemas/human_researcher_post_v1.json",
        "Current Human Researcher POST schema",
    ),
    RequiredAsset(
        "API_PRE_SHADOW_SCHEMA",
        "configs/cognitive_runtime/schemas/api_researcher_pre_shadow_v1.json",
        "Strong-model PRE shadow schema",
    ),
    RequiredAsset(
        "API_POST_SHADOW_SCHEMA",
        "configs/cognitive_runtime/schemas/api_researcher_post_shadow_v1.json",
        "Strong-model POST shadow schema",
    ),
    RequiredAsset(
        "LOCAL_PRE_SUPERVISION_SCHEMA",
        "configs/cognitive_runtime/schemas/local_researcher_pre_supervision_v1.json",
        "Local Planner PRE supervision view",
    ),
    RequiredAsset(
        "LOCAL_POST_SUPERVISION_SCHEMA",
        "configs/cognitive_runtime/schemas/local_researcher_post_supervision_v1.json",
        "Local Planner POST supervision view",
    ),
    RequiredAsset(
        "FORMAL_ANALYZER_CANONICAL_ARCHIVE",
        "docs/analyzer/FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md",
        "Canonical Analyzer design and metric authority",
    ),
    RequiredAsset(
        "FORMAL_ANALYZER_EXPERIMENT_MANIFEST",
        "experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json",
        "Registered Analyzer reference universe",
    ),
    RequiredAsset(
        "FORMAL_ANALYZER_RESULT_MANIFEST",
        "experiments/formal_analyzer/pi1_reference_v1/RESULT_MANIFEST.json",
        "Current Analyzer result/archive binding",
    ),
    RequiredAsset(
        "MEMORY_ROLE_PACK_CONTRACT",
        "configs/memory/failure_memory_role_pack_contract_v1.json",
        "Policy/Analyzer/Researcher Memory visibility separation",
    ),
    RequiredAsset(
        "REPAIR_DISCOVERY_F0F1_PROTOCOL",
        "docs/protocol/REPAIR_DISCOVERY_AND_SAME_STATE_VERIFICATION_PROTOCOL_V1.md",
        "Registered candidate-to-F0/F1 verification protocol",
    ),
    RequiredAsset(
        "F0F1_REPAIR_VERIFICATION_V2",
        "docs/protocol/F0F1_REPAIR_VERIFICATION_V2.md",
        "Formal paired repair verification contract",
    ),
    RequiredAsset(
        "PROJECT_ASSET_REUSE_MATRIX",
        "docs/project/PROJECT_ASSET_REUSE_MATRIX_V1.md",
        "Explicit reuse/non-reimplementation map",
    ),
    RequiredAsset(
        "REFERENCE_LOOP_WORKFLOW",
        "docs/project/REFERENCE_LOOP_WORKFLOW_COORDINATION_V1.md",
        "Reference-loop stage coordination",
    ),
    RequiredAsset(
        "ROUND_EVIDENCE_PACKAGE_CONTRACT",
        "docs/runtime_researcher/ROUND_EVIDENCE_PACKAGE_V1.md",
        "Round-level evidence boundary",
    ),
)

DISCOVERY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "ANALYZER_ARTIFACTS",
        (
            "experiments/formal_analyzer/pi1_reference_v1/**/*.json",
            "experiments/formal_analyzer/pi1_reference_v1/**/*.jsonl",
        ),
    ),
    (
        "ROUND1_NO_GO_AND_TRAINING",
        (
            "experiments/round1/**/*.json",
            "reports/**/*NO_GO*",
            "docs/**/*NO_GO*",
        ),
    ),
    (
        "MEMORY_RESEARCHER_EXPORTS",
        (
            "experiments/failure_memory/**/*.json",
            "artifacts/**/*RESEARCHER_MEMORY_PACK*.json",
            "artifacts/**/*ANALYZER_MEMORY_PACK*.json",
        ),
    ),
    (
        "F0F1_AND_VERIFIER_ASSETS",
        (
            "src/pchsi/**/*f0*f1*.py",
            "src/pchsi/**/*counterfactual*.py",
            "src/pchsi/**/*verifier*.py",
            "scripts/**/*f0*f1*.py",
            "scripts/**/*counterfactual*.py",
        ),
    ),
    (
        "TRAINER_AND_EVALUATOR_ASSETS",
        (
            "src/pchsi/**/*trainer*.py",
            "src/pchsi/**/*training*.py",
            "src/pchsi/**/*evaluator*.py",
            "scripts/**/*train*.py",
            "scripts/**/*evaluat*.py",
        ),
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def inventory_required(repo: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in REQUIRED_ASSETS:
        path = repo / asset.relative_path
        exists = path.is_file() and not path.is_symlink()
        rows.append(
            {
                "asset_id": asset.asset_id,
                "relative_path": asset.relative_path,
                "purpose": asset.purpose,
                "required_for_human_pre": asset.required_for_human_pre,
                "status": "PRESENT" if exists else "MISSING_QUERY_REQUIRED",
                "sha256": sha256_file(path) if exists else None,
                "size_bytes": path.stat().st_size if exists else None,
            }
        )
    return rows


def discover(repo: Path) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for category, patterns in DISCOVERY_PATTERNS:
        paths: set[Path] = set()
        for pattern in patterns:
            for path in repo.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    paths.add(path)
        output[category] = [
            {
                "relative_path": path.relative_to(repo).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(paths)
        ]
    return output


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_text_once(path: Path, text: str) -> None:
    write_once(path, text.encode("utf-8"))


def markdown_worksheet(
    *,
    round_id: str,
    parent_policy_id: str,
    head: str,
    evidence_cutoff_sha256: str,
    missing_assets: list[str],
    discovery: dict[str, list[dict[str, Any]]],
) -> str:
    missing_text = "无" if not missing_assets else "、".join(missing_assets)
    category_lines = []
    for category, rows in discovery.items():
        category_lines.append(f"- `{category}`：{len(rows)} 个已发现文件")
    return f"""# Human Training Researcher PRE Worksheet V2 — Candidate

> 本文件是**人工填写候选表**，不是已经批准或冻结的 PRE。它只绑定当前可见资产，不能自动选择 bottleneck、repair 或训练方法。

## 0. 固定身份

- round_id: `{round_id}`
- parent_policy_id: `{parent_policy_id}`
- repository_head: `{head}`
- evidence_cutoff_sha256: `{evidence_cutoff_sha256}`
- missing_required_assets: {missing_text}

## 1. 当前可见事实与证据边界

- 仅使用本 readiness pack 中哈希绑定的 train-side / DEV / round-level artifacts。
- 不允许读取 sealed evaluation 的逐任务 trajectory、observation、menu 或未来 F0/F1 outcome。
- Analyzer/Memory 只提供 diagnosis、historical support 和 candidate lineage。
- Environment Verifier 才能签发 Benefit / Harm / Neutral / Uncertain。

发现的资产类别：
{chr(10).join(category_lines)}

## 2. Policy failure profile

- 总体与 task-family 表现：
- 主要失败机制及支持/反证：
- 已保护的成功能力：
- 第一轮 π0→π1 NO-GO 中不应重复的路线：

## 3. 候选 bottleneck portfolio

每个候选必须填写：evidence、counterevidence、expected value、verification cost、harm risk、task-family scope、是否重复历史 NO-GO。

| bottleneck_id | evidence | counterevidence | expected value | cost | harm risk | scope | prior NO-GO? |
|---|---|---|---:|---:|---:|---|---|
| | | | | | | | |

## 4. 高价值 repair portfolio

Research Planner 不只排序实验，还应：

1. 从 Analyzer / Failure Experience 中找到关键 source-bound repairs；
2. 必要时在保持 lineage 的前提下抽象或组合 repair program；
3. 对证据不足的方向请求额外分析或 ABSTAIN；
4. 只选择一个 principal scientific change；
5. 不执行动作，不签发因果 outcome。

| candidate/program | source states | lineage | mechanism | high-value rationale | verification calls | decision |
|---|---|---|---|---|---:|---|
| | | | | | | |

## 5. 单一主要改变

- selected_bottleneck_id:
- selected_principal_change_id:
- falsifiable_hypothesis:
- selected repair program:
- rejected directions and reasons:
- deferred directions and reasons:

## 6. 验证与训练计划

- screening F0/F1 budget:
- formal paired F0/F1 budget:
- Benefit/Harm/Neutral/Uncertain rule:
- T0–T5 training arms:
- OFF/OFF evaluation panel:
- stop rule:

## 7. 后续角色接管监督

- Strong API Researcher PRE shadow：仅在 Human PRE 冻结后运行。
- Strong API POST shadow：仅在 round evidence 完整后运行。
- Local Research Planner supervision：保留 raw teacher/human artifact、field edits、environment outcome 和 final decision。
- 最终目标：Policy / Analyzer / Research Planner 由**同一个 Qwen2.5-3B checkpoint**的不同 role mode 承担；独立 verifier、Memory governance 和 deterministic promotion gate 不并入模型权限。
"""


def benchmark_skeleton(
    *,
    round_id: str,
    parent_policy_id: str,
    evidence_cutoff_sha256: str,
    discovered: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "schema_version": "BENCHMARK_LINEAGE_CANDIDATE_V1",
        "round_id": round_id,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "entries": [
            {
                "stage": "RAW_BASE_PI0",
                "display_name": "Raw base policy",
                "status": "HISTORICAL_ASSET_QUERY_REQUIRED",
                "comparability": "PENDING_PROTOCOL_AUDIT",
            },
            {
                "stage": "PILOT_DISTILLED_PI1",
                "display_name": "Pilot-distilled policy",
                "checkpoint_identity": parent_policy_id,
                "status": "CURRENT_PARENT_IDENTITY_REQUIRES_PROTOCOL_REGISTRATION",
                "comparability": "PENDING_PROTOCOL_AUDIT",
            },
            {
                "stage": "PI2_HUMAN_REFERENCE",
                "display_name": "Human-reference-round policy",
                "status": "PENDING_TRAINING_AND_OFF_OFF_EVALUATION",
                "comparability": "PENDING_PROTOCOL_AUDIT",
            },
            {
                "stage": "PI_STAR_AUTONOMOUS_FINAL",
                "display_name": "Final self-improvement-system policy",
                "status": "PENDING_FRESH_AUTONOMOUS_ROUND",
                "comparability": "PENDING_PROTOCOL_AUDIT",
            },
            {
                "stage": "RELATED_WORK_REPRODUCED",
                "display_name": "Relevant reproduced baselines",
                "status": "EXPLICIT_REGISTRATION_REQUIRED",
                "comparability": "SECONDARY_REPRODUCED",
            },
            {
                "stage": "STRONG_MODEL_REFERENCE",
                "display_name": "Strong-model reference",
                "status": "HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT",
                "comparability": "PENDING_PROTOCOL_AUDIT",
                "note": "Historical strong-model results must remain context-only until the shared protocol fingerprint is matched.",
            },
        ],
        "shared_evaluation_protocol_required_fields": [
            "prompt/history",
            "menu/action interface",
            "parser/controllers/harness/memory condition",
            "task split/panel",
            "action/model-call budgets",
            "seed schedule",
            "ALFWorld/source revision",
            "success definition",
            "sequential interaction and result census",
        ],
        "model_execution_profile_required_fields": [
            "provider/requested/returned model identity",
            "model/tokenizer/adapter hashes when exposed",
            "generation/reasoning contract",
            "tools/statefulness/retry policy",
            "provider seed availability",
            "tokens/latency/cost",
        ],
        "discovered_evaluation_asset_count": len(
            discovered.get("TRAINER_AND_EVALUATOR_ASSETS", [])
        ),
    }


def repair_input_skeleton(
    *,
    round_id: str,
    parent_policy_id: str,
    evidence_cutoff_sha256: str,
    discovery: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    analyzer = discovery.get("ANALYZER_ARTIFACTS", [])
    memory = discovery.get("MEMORY_RESEARCHER_EXPORTS", [])
    return {
        "schema_version": "RESEARCH_REPAIR_PORTFOLIO_INPUT_V1",
        "round_id": round_id,
        "parent_policy_id": parent_policy_id,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "analyzer_artifacts": analyzer,
        "memory_researcher_exports": memory,
        "candidate_repairs": [],
        "repair_programs": [],
        "requires_human_completion": True,
        "causal_outcomes_visible": False,
        "next_authority": "HUMAN_TRAINING_RESEARCHER_PRE_REVIEW",
    }


def researcher_comparison_manifest(
    *, round_id: str, evidence_cutoff_sha256: str
) -> dict[str, Any]:
    return {
        "schema_version": "RESEARCHER_COMPARISON_MANIFEST_V1",
        "round_id": round_id,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "common_controls": [
            "same candidate universe",
            "same visible evidence",
            "same verification budget",
            "same token budget",
            "same task-family information",
            "future outcomes hidden",
        ],
        "arms": [
            {"arm_id": "R0_FIFO", "role": "DETERMINISTIC_BASELINE"},
            {"arm_id": "R1_FREQUENCY_ONLY", "role": "DETERMINISTIC_BASELINE"},
            {"arm_id": "R2_HUMAN_REFERENCE", "role": "PRIMARY_THIS_ROUND"},
            {"arm_id": "R3_STRONG_API_SHADOW", "role": "SHADOW_AFTER_R2_FREEZE"},
        ],
        "metrics": [
            "Benefits per verification budget",
            "Harm",
            "Neutral",
            "calls per Benefit",
            "task-family coverage",
            "duplicate mechanism rate",
            "repeated-NO-GO rate",
            "single-change compliance",
            "human field revision rate",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--parent-policy-id", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output_dir).resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit("STOP=REPO_NOT_A_GIT_WORKTREE")
    if output.exists():
        raise SystemExit("STOP=READINESS_OUTPUT_ALREADY_EXISTS")

    head = git_output(repo, "rev-parse", "HEAD")
    if head != args.expected_head:
        raise SystemExit(
            f"STOP=UNEXPECTED_REPOSITORY_HEAD expected={args.expected_head} observed={head}"
        )
    if git_output(repo, "status", "--porcelain"):
        raise SystemExit("STOP=REPOSITORY_NOT_CLEAN")

    required = inventory_required(repo)
    discovery = discover(repo)
    missing = [row["asset_id"] for row in required if row["status"] != "PRESENT"]

    evidence_binding = {
        "repository_head": head,
        "required_assets": required,
        "discovered_assets": discovery,
    }
    evidence_cutoff_sha256 = hashlib.sha256(
        canonical_json_bytes(evidence_binding)
    ).hexdigest()

    status = (
        "READY_FOR_HUMAN_PRE_COMPLETION"
        if not missing
        else "QUERY_REQUIRED_MISSING_ASSETS"
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "round_id": args.round_id,
        "parent_policy_id": args.parent_policy_id,
        "repository_head": head,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "required_assets": required,
        "missing_required_assets": missing,
        "discovered_assets": discovery,
        "scientific_execution": False,
        "model_call": False,
        "environment_execution": False,
        "f0_f1_execution": False,
        "training_execution": False,
        "human_pre_finalized": False,
        "next_gate": (
            "HUMAN_PRE_MANUAL_COMPLETION_AND_REVIEW"
            if not missing
            else "RUN_TARGETED_QUERY_PACKAGE_FOR_MISSING_ASSETS"
        ),
    }

    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "REFERENCE_ROUND_READINESS_V2.json", canonical_json_bytes(report))
    write_text_once(
        output / "HUMAN_RESEARCHER_PRE_WORKSHEET_V2.md",
        markdown_worksheet(
            round_id=args.round_id,
            parent_policy_id=args.parent_policy_id,
            head=head,
            evidence_cutoff_sha256=evidence_cutoff_sha256,
            missing_assets=missing,
            discovery=discovery,
        ),
    )
    write_once(
        output / "BENCHMARK_LINEAGE_CANDIDATE_V1.json",
        canonical_json_bytes(
            benchmark_skeleton(
                round_id=args.round_id,
                parent_policy_id=args.parent_policy_id,
                evidence_cutoff_sha256=evidence_cutoff_sha256,
                discovered=discovery,
            )
        ),
    )
    write_once(
        output / "RESEARCH_REPAIR_PORTFOLIO_INPUT_V1.json",
        canonical_json_bytes(
            repair_input_skeleton(
                round_id=args.round_id,
                parent_policy_id=args.parent_policy_id,
                evidence_cutoff_sha256=evidence_cutoff_sha256,
                discovery=discovery,
            )
        ),
    )
    write_once(
        output / "RESEARCHER_COMPARISON_MANIFEST_V1.json",
        canonical_json_bytes(
            researcher_comparison_manifest(
                round_id=args.round_id,
                evidence_cutoff_sha256=evidence_cutoff_sha256,
            )
        ),
    )
    write_text_once(
        output / "NEXT_GATE.txt",
        report["next_gate"] + "\n",
    )

    file_rows = []
    for path in sorted(output.iterdir()):
        if path.is_file():
            file_rows.append(f"{sha256_file(path)}  {path.name}")
    write_text_once(output / "SHA256SUMS.txt", "\n".join(file_rows) + "\n")

    print(f"REFERENCE_ROUND_READINESS_STATUS={status}")
    print(f"EVIDENCE_CUTOFF_SHA256={evidence_cutoff_sha256}")
    print(f"MISSING_REQUIRED_ASSET_COUNT={len(missing)}")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
