from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CleanRoleActorBindingV1:
    logical_role: str
    actor: str
    entrypoint_relative_path: str
    stage_id: str | None
    transport_kind: str
    blind_input_required: bool
    human_content_visibility_allowed: bool


def human_primary_strong_shadow_bindings(repo_root: Path) -> tuple[CleanRoleActorBindingV1, ...]:
    repo_root = Path(repo_root).resolve()
    analyzer_stages = ("L-A0", "L-A1", "G-A2", "G-A3", "C", "X")
    human_analyzer = tuple(
        CleanRoleActorBindingV1(
            logical_role="ANALYZER",
            actor="HUMAN",
            entrypoint_relative_path="scripts/analyzer/freeze_human_analyzer_primary_v1.py",
            stage_id=stage_id,
            transport_kind="HUMAN_FREEZE",
            blind_input_required=True,
            human_content_visibility_allowed=True,
        )
        for stage_id in analyzer_stages
    )
    strong_analyzer = tuple(
        CleanRoleActorBindingV1(
            logical_role="ANALYZER",
            actor="STRONG",
            entrypoint_relative_path="src/pchsi/cognitive_runtime/orchestrator.py",
            stage_id=stage_id,
            transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",
            blind_input_required=True,
            human_content_visibility_allowed=False,
        )
        for stage_id in analyzer_stages
    )
    bindings = human_analyzer + strong_analyzer + (
        CleanRoleActorBindingV1(
            logical_role="RESEARCH_PLANNER_PRE",
            actor="HUMAN",
            entrypoint_relative_path="scripts/research_intelligence/freeze_human_researcher_pre_v2.py",
            stage_id=None,
            transport_kind="HUMAN_FREEZE",
            blind_input_required=True,
            human_content_visibility_allowed=True,
        ),
        CleanRoleActorBindingV1(
            logical_role="RESEARCH_PLANNER_PRE",
            actor="STRONG",
            entrypoint_relative_path="scripts/research_intelligence/run_researcher_pre_shadow_v6.py",
            stage_id="R-PRE-SHADOW-HYDRATED-V2",
            transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",
            blind_input_required=True,
            human_content_visibility_allowed=False,
        ),
        CleanRoleActorBindingV1(
            logical_role="RESEARCH_PLANNER_POST",
            actor="HUMAN",
            entrypoint_relative_path="scripts/research_intelligence/freeze_human_researcher_post_v1.py",
            stage_id=None,
            transport_kind="HUMAN_FREEZE",
            blind_input_required=False,
            human_content_visibility_allowed=True,
        ),
        CleanRoleActorBindingV1(
            logical_role="RESEARCH_PLANNER_POST",
            actor="STRONG",
            entrypoint_relative_path="src/pchsi/cognitive_runtime/orchestrator.py",
            stage_id="R-POST-SHADOW",
            transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",
            blind_input_required=True,
            human_content_visibility_allowed=False,
        ),
    )
    for binding in bindings:
        path = repo_root / binding.entrypoint_relative_path
        if path.is_symlink() or not path.is_file():
            raise ValueError("registered role actor entrypoint missing: " + binding.entrypoint_relative_path)

    strong_pre = (repo_root / "scripts/research_intelligence/run_researcher_pre_shadow_v6.py").read_text(encoding="utf-8")
    required_blind_guards = (
        "human_pre_content_hidden_from_strong_pre_shadow",
        "human_pre_content_visible",
        "human_pre_hash_visible",
        "strong_model_benchmark_per_task_results_visible",
    )
    if any(token not in strong_pre for token in required_blind_guards):
        raise ValueError("Strong PRE blind-input guards are incomplete")

    cognitive_manifest = repo_root / "configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json"
    if cognitive_manifest.is_symlink() or not cognitive_manifest.is_file():
        raise ValueError("cognitive runtime manifest missing")
    manifest_text = cognitive_manifest.read_text(encoding="utf-8")
    required_stages = (*analyzer_stages, "R-PRE-SHADOW-HYDRATED-V2", "R-POST-SHADOW")
    for stage_id in required_stages:
        if f'"stage_id": "{stage_id}"' not in manifest_text:
            raise ValueError("registered cognitive runtime stage missing: " + stage_id)
    return bindings


def strong_primary_local_shadow_bindings(repo_root: Path) -> tuple[CleanRoleActorBindingV1, ...]:
    # Strong-primary bindings only; Local shadow remains separately gated.
    repo_root=Path(repo_root).resolve()
    analyzer=("L-A0","L-A1","G-A2","G-A3","C","X")
    bindings=tuple(CleanRoleActorBindingV1(logical_role="ANALYZER",actor="STRONG_API_PRIMARY",entrypoint_relative_path="src/pchsi/cognitive_runtime/orchestrator.py",stage_id=s,transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",blind_input_required=True,human_content_visibility_allowed=False) for s in analyzer)+(
      CleanRoleActorBindingV1(logical_role="RESEARCH_PLANNER_PRE",actor="STRONG_API_PRIMARY",entrypoint_relative_path="src/pchsi/cognitive_runtime/orchestrator.py",stage_id="R-PRE-PRIMARY-V1",transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",blind_input_required=True,human_content_visibility_allowed=False),
      CleanRoleActorBindingV1(logical_role="RESEARCH_PLANNER_POST",actor="STRONG_API_PRIMARY",entrypoint_relative_path="src/pchsi/cognitive_runtime/orchestrator.py",stage_id="R-POST-PRIMARY-V1",transport_kind="EXISTING_COGNITIVE_RUNTIME_P2",blind_input_required=True,human_content_visibility_allowed=False),
    )
    for row in bindings:
        p=repo_root/row.entrypoint_relative_path
        if p.is_symlink() or not p.is_file():raise ValueError("Strong-primary entrypoint missing: "+row.entrypoint_relative_path)
    return bindings
