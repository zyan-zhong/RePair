from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


_ANALYZER_STAGES = ("L-A0", "L-A1", "G-A2", "G-A3", "C", "X")


@dataclass(frozen=True, slots=True)
class StrongPrimaryBindingReadinessV1:
    analyzer_primary_runtime_ready: bool
    planner_pre_primary_transport_ready: bool
    planner_post_primary_transport_ready: bool
    role_neutral_primary_contract_ready: bool
    local_shadow_checkpoint_ready: bool
    human_gate_dependency_absent_for_primary: bool
    execution_authorized: bool

    @property
    def ready_for_strong_primary_local_shadow(self) -> bool:
        return all(
            (
                self.analyzer_primary_runtime_ready,
                self.planner_pre_primary_transport_ready,
                self.planner_post_primary_transport_ready,
                self.role_neutral_primary_contract_ready,
                self.local_shadow_checkpoint_ready,
                self.human_gate_dependency_absent_for_primary,
            )
        ) and self.execution_authorized is True

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "STRONG_PRIMARY_BINDING_READINESS_V1",
            "schema_version": 1,
            "analyzer_primary_runtime_ready": self.analyzer_primary_runtime_ready,
            "planner_pre_primary_transport_ready": self.planner_pre_primary_transport_ready,
            "planner_post_primary_transport_ready": self.planner_post_primary_transport_ready,
            "role_neutral_primary_contract_ready": self.role_neutral_primary_contract_ready,
            "local_shadow_checkpoint_ready": self.local_shadow_checkpoint_ready,
            "human_gate_dependency_absent_for_primary": self.human_gate_dependency_absent_for_primary,
            "execution_authorized": self.execution_authorized,
            "ready_for_strong_primary_local_shadow": self.ready_for_strong_primary_local_shadow,
        }


def _stage6ak_local_analyzer_ready(
    *,
    checkpoint_manifest: Path,
    result_authority: Path | None,
) -> bool:
    checkpoint = json.loads(
        checkpoint_manifest.read_text(encoding="utf-8")
    )
    checkpoint_ready = (
        checkpoint.get("schema_id")
        == "LOCAL_ANALYZER_BOOTSTRAP_CHECKPOINT_AUTHORITY_V1"
        and checkpoint.get("role") == "LOCAL_ANALYZER"
        and checkpoint.get("status") == "BOOTSTRAP_CHECKPOINT_FROZEN"
        and checkpoint.get("checkpoint_role")
        == "BOOTSTRAP_WARM_START_NOT_TAKEOVER"
        and checkpoint.get("shadow_qualification_required") is True
        and checkpoint.get("takeover_authorized") is False
        and checkpoint.get("strong_primary_launch_blocking") is False
        and isinstance(checkpoint.get("adapter_dir"), str)
        and bool(checkpoint.get("adapter_dir"))
        and isinstance(
            checkpoint.get("adapter_artifact_manifest_sha256"),
            str,
        )
        and len(checkpoint["adapter_artifact_manifest_sha256"]) == 64
    )
    if not checkpoint_ready:
        return False
    if result_authority is None:
        return True
    result = json.loads(
        result_authority.read_text(encoding="utf-8")
    )
    return (
        result.get("schema_id")
        == "STAGE6AK_LOCAL_ANALYZER_FULL_BOOTSTRAP_RESULT_AUTHORITY_V1"
        and result.get("status") == "PASS"
        and result.get("bootstrap_checkpoint_frozen") is True
        and result.get(
            "local_analyzer_shadow_readiness_gate_authorized"
        ) is True
        and result.get("local_analyzer_takeover_authorized") is False
        and result.get("strong_primary_launch_blocking") is False
    )


def _legacy_combined_local_ri_ready(
    *,
    manifest: Path,
) -> bool:
    value = json.loads(manifest.read_text(encoding="utf-8"))
    return (
        value.get("local_training_executed") is True
        and value.get("local_shadow_authorized") is True
        and isinstance(value.get("analyzer_checkpoint_id"), str)
        and bool(value.get("analyzer_checkpoint_id"))
        and isinstance(
            value.get("research_planner_checkpoint_id"),
            str,
        )
        and bool(value.get("research_planner_checkpoint_id"))
    )


def inspect_strong_primary_binding_readiness(
    *,
    repo_root: Path,
    local_checkpoint_manifest: Path | None = None,
    local_result_authority: Path | None = None,
    execution_authorized: bool = False,
) -> StrongPrimaryBindingReadinessV1:
    """Inspect existing assets without inventing a Local Planner checkpoint."""

    repo_root = Path(repo_root).resolve()

    runtime_manifest_path = (
        repo_root
        / "configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json"
    )
    runtime_manifest = json.loads(
        runtime_manifest_path.read_text(encoding="utf-8")
    )
    stage_ids = {
        str(row.get("stage_id"))
        for row in runtime_manifest.get("stage_rows", [])
        if isinstance(row, dict)
    }
    analyzer_ready = set(_ANALYZER_STAGES) <= stage_ids

    role_neutral_text = (
        repo_root / "src/pchsi/research_intelligence/role_neutral.py"
    ).read_text(encoding="utf-8")
    role_neutral_ready = all(
        token in role_neutral_text
        for token in (
            'STRONG_API_PRIMARY = "STRONG_API_PRIMARY"',
            'LOCAL_SHADOW = "LOCAL_SHADOW"',
            "class ResearcherPreDecisionV1",
            "class ResearcherPostInterpretationV1",
        )
    )

    binding_text = (
        repo_root / "src/pchsi/round_control/clean_role_actor_binding.py"
    ).read_text(encoding="utf-8")
    explicit_primary_factory = (
        "strong_primary_local_shadow_bindings" in binding_text
    )

    pre_text = (
        repo_root / "src/pchsi/cognitive_runtime/researcher_hydrated.py"
    ).read_text(encoding="utf-8")
    pre_shadow_human_gate = (
        'projection.get("human_pre_gate_satisfied") is not True'
        in pre_text
    )
    pre_primary_stage = (
        "STRONG_RESEARCHER_PRE_PRIMARY" in pre_text
        or "R-PRE-PRIMARY" in runtime_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    post_text = (
        repo_root / "src/pchsi/cognitive_runtime/researcher.py"
    ).read_text(encoding="utf-8")
    post_primary_stage = (
        "STRONG_RESEARCHER_POST_PRIMARY" in post_text
        or "R-POST-PRIMARY" in runtime_manifest_path.read_text(
            encoding="utf-8"
        )
    )

    local_ready = False
    if local_checkpoint_manifest is not None:
        local_checkpoint_manifest = Path(local_checkpoint_manifest)
        if (
            local_checkpoint_manifest.is_file()
            and not local_checkpoint_manifest.is_symlink()
        ):
            value = json.loads(
                local_checkpoint_manifest.read_text(encoding="utf-8")
            )
            if (
                value.get("schema_id")
                == "LOCAL_ANALYZER_BOOTSTRAP_CHECKPOINT_AUTHORITY_V1"
            ):
                local_ready = _stage6ak_local_analyzer_ready(
                    checkpoint_manifest=local_checkpoint_manifest,
                    result_authority=(
                        Path(local_result_authority)
                        if local_result_authority is not None
                        else None
                    ),
                )
            else:
                local_ready = _legacy_combined_local_ri_ready(
                    manifest=local_checkpoint_manifest
                )

    no_human_gate_dependency = bool(
        explicit_primary_factory
        and pre_primary_stage
        and post_primary_stage
    )
    if pre_shadow_human_gate and not pre_primary_stage:
        no_human_gate_dependency = False

    return StrongPrimaryBindingReadinessV1(
        analyzer_primary_runtime_ready=analyzer_ready,
        planner_pre_primary_transport_ready=bool(
            explicit_primary_factory and pre_primary_stage
        ),
        planner_post_primary_transport_ready=bool(
            explicit_primary_factory and post_primary_stage
        ),
        role_neutral_primary_contract_ready=role_neutral_ready,
        local_shadow_checkpoint_ready=local_ready,
        human_gate_dependency_absent_for_primary=no_human_gate_dependency,
        execution_authorized=bool(execution_authorized),
    )
