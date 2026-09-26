from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pchsi.reference_loop.canonical import (
    directory_manifest_sha256,
    sha256_file,
)

from .bindings import REQUIRED_REUSE_COMPONENT_IDS
from .common import hashed_payload, require_text


class BindingKindV1(str, Enum):
    REPO_NATIVE = "REPO_NATIVE"
    ENGINEERING_SNAPSHOT = "ENGINEERING_SNAPSHOT"
    PORT_CONTRACT = "PORT_CONTRACT"


@dataclass(frozen=True)
class ConcreteComponentBindingV1:
    component_id: str
    binding_kind: BindingKindV1
    source_paths: tuple[str, ...]
    entrypoint: str | None
    adapter_required: bool
    scientific_execution_authorized: bool
    source_identity_sha256: str
    binding_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "CONCRETE_COMPONENT_BINDING_V1",
            "schema_version": 1,
            "component_id": self.component_id,
            "binding_kind": self.binding_kind.value,
            "source_paths": list(self.source_paths),
            "entrypoint": self.entrypoint,
            "adapter_required": self.adapter_required,
            "scientific_execution_authorized": self.scientific_execution_authorized,
            "source_identity_sha256": self.source_identity_sha256,
            "binding_sha256": self.binding_sha256,
        }


_BINDING_SPECS: dict[str, dict[str, object]] = {
    "EVIDENCE_PACKAGE": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/reference_loop/analyzer_evidence_pack.py",
        ),
        "entrypoint": "pchsi.reference_loop.analyzer_evidence_pack",
        "adapter_required": False,
    },
    "HIERARCHICAL_ANALYZER": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/analyzer",
        ),
        "entrypoint": "pchsi.analyzer",
        "adapter_required": True,
    },
    "PERSISTENT_FAILURE_EXPERIENCE": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/memory",
        ),
        "entrypoint": "pchsi.memory",
        "adapter_required": True,
    },
    "RESEARCH_PLANNER_PRE_POST": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/research_intelligence/role_neutral.py",
            "src/pchsi/research_intelligence/"
            "research_planner_reference_trace.py",
            "src/pchsi/research_intelligence/reference_round.py",
        ),
        "entrypoint": (
            "pchsi.research_intelligence.reference_round"
        ),
        "adapter_required": True,
    },
    "SAME_STATE_F0F1": {
        "binding_kind": BindingKindV1.PORT_CONTRACT,
        "source_paths": (
            "src/pchsi/evaluation/episode_evaluator.py",
            "src/pchsi/evaluation/run_schedule.py",
            "src/pchsi/evaluation/result_audit.py",
        ),
        "entrypoint": None,
        "adapter_required": True,
    },
    "TRAINING_DATA_PLAN": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/research_intelligence/reference_round.py",
            "src/pchsi/reference_loop/approved_materialization.py",
        ),
        "entrypoint": (
            "pchsi.reference_loop.approved_materialization"
        ),
        "adapter_required": True,
    },
    "DETERMINISTIC_DATA_BUILDER": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/reference_loop/approved_materialization.py",
        ),
        "entrypoint": (
            "pchsi.reference_loop.approved_materialization"
        ),
        "adapter_required": False,
    },
    "SCHEMA_AWARE_RENDERER": {
        "binding_kind": BindingKindV1.ENGINEERING_SNAPSHOT,
        "source_paths": (
            "scripts/engineering_snapshots/training_pipeline/"
            "qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_"
            "preflight_v1_7_2/tools/renderer_adapter_core.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_"
            "preflight_v1_7_2/contracts/"
            "SCHEMA_AWARE_RENDERER_ADAPTER_CONTRACT_V1.json",
        ),
        "entrypoint": None,
        "adapter_required": True,
    },
    "GENERIC_TRAINING_STAGE_V2_1": {
        "binding_kind": BindingKindV1.ENGINEERING_SNAPSHOT,
        "source_paths": (
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_stage_v2_1_hardening_build/"
            "round_training/stage_runner.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_stage_v2_1_hardening_build/"
            "round_training/contracts.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_stage_v2_1_hardening_build/"
            "round_training/receipts.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_stage_v2_1_hardening_build/"
            "round_training/adapters/frozen_formal_train_peft.py",
        ),
        "entrypoint": "round_training.stage_runner",
        "adapter_required": True,
    },
    "MODEL_INIT_SMOKE": {
        "binding_kind": BindingKindV1.ENGINEERING_SNAPSHOT,
        "source_paths": (
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_model_init_smoke_v1_3_cluster_"
            "resource_policy_fix/smoke/smoke_runner.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_model_init_smoke_v1_3_cluster_"
            "resource_policy_fix/smoke/model_init_adapter.py",
        ),
        "entrypoint": None,
        "adapter_required": True,
    },
    "TRAINING_RECEIPTS": {
        "binding_kind": BindingKindV1.ENGINEERING_SNAPSHOT,
        "source_paths": (
            "scripts/engineering_snapshots/training_pipeline/"
            "round_generic_training_stage_v2_1_hardening_build/"
            "round_training/stage_runner.py",
            "scripts/engineering_snapshots/training_pipeline/"
            "round_human_t2_formal_training_execution_v1_2_"
            "preflight_summary_fix/formal_exec/common.py",
        ),
        "entrypoint": None,
        "adapter_required": True,
    },
    "SELECT_EVALUATOR": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/evaluation/episode_evaluator.py",
            "src/pchsi/evaluation/select_policy_runtime.py",
            "src/pchsi/evaluation/select_execution_identity.py",
            "src/pchsi/evaluation/select_result_audit.py",
        ),
        "entrypoint": "pchsi.evaluation.episode_evaluator",
        "adapter_required": True,
    },
    "GENERIC_SELECT_POLICY_BINDING": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/evaluation/select_policy_runtime.py",
            "src/pchsi/evaluation/select_execution_identity.py",
            "src/pchsi/evaluation/select_result_audit.py",
            "configs/evaluation/schemas/"
            "select_policy_runtime_manifest_v1.json",
            "configs/evaluation/schemas/"
            "select_server_runtime_manifest_v1.json",
        ),
        "entrypoint": (
            "pchsi.evaluation.select_policy_runtime"
        ),
        "adapter_required": False,
    },
    "PROMOTION_ROLLBACK_CONTRACTS": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/round_control/promotion.py",
            "src/pchsi/research_intelligence/takeover.py",
            "src/pchsi/research_intelligence/reference_round.py",
        ),
        "entrypoint": "pchsi.round_control.promotion",
        "adapter_required": False,
    },
    "STRONG_TRACE_STORAGE": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/research_intelligence/reference_round.py",
            "src/pchsi/research_intelligence/distillation.py",
            "src/pchsi/research_intelligence/"
            "research_planner_reference_trace.py",
        ),
        "entrypoint": (
            "pchsi.research_intelligence.distillation"
        ),
        "adapter_required": False,
    },
    "AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION": {
        "binding_kind": BindingKindV1.REPO_NATIVE,
        "source_paths": (
            "src/pchsi/round_control/next_round.py",
            "src/pchsi/round_control/promotion.py",
            "src/pchsi/round_control/lifecycle.py",
            "src/pchsi/round_control/retention.py",
        ),
        "entrypoint": "pchsi.round_control.next_round",
        "adapter_required": False,
    },
}


def required_concrete_component_ids() -> frozenset[str]:
    return frozenset(
        set(REQUIRED_REUSE_COMPONENT_IDS)
        | {
            "AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION",
        }
    )


def _source_identity(repo_root: Path, paths: tuple[str, ...]) -> str:
    identities: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists() or path.is_symlink():
            raise ValueError(f"required binding source missing or symlinked: {relative}")
        if path.is_dir():
            identities.append(directory_manifest_sha256(path))
        elif path.is_file():
            identities.append(sha256_file(path))
        else:
            raise ValueError(f"unsupported binding source type: {relative}")
    from pchsi.reference_loop.canonical import canonical_json_without_newline
    import hashlib
    return hashlib.sha256(
        canonical_json_without_newline(identities)
    ).hexdigest()


def build_concrete_component_bindings(
    repo_root: Path,
) -> tuple[ConcreteComponentBindingV1, ...]:
    repo_root = repo_root.resolve()
    bindings: list[ConcreteComponentBindingV1] = []

    for component_id in sorted(_BINDING_SPECS):
        spec = _BINDING_SPECS[component_id]
        source_paths = tuple(spec["source_paths"])
        source_identity = _source_identity(repo_root, source_paths)
        payload = {
            "schema_id": "CONCRETE_COMPONENT_BINDING_V1",
            "schema_version": 1,
            "component_id": component_id,
            "binding_kind": spec["binding_kind"].value,
            "source_paths": list(source_paths),
            "entrypoint": spec["entrypoint"],
            "adapter_required": spec["adapter_required"],
            "scientific_execution_authorized": False,
            "source_identity_sha256": source_identity,
        }
        hashed = hashed_payload(
            domain="CONCRETE_COMPONENT_BINDING_V1",
            hash_field="binding_sha256",
            payload=payload,
        )
        bindings.append(
            ConcreteComponentBindingV1(
                component_id=component_id,
                binding_kind=spec["binding_kind"],
                source_paths=source_paths,
                entrypoint=spec["entrypoint"],
                adapter_required=bool(spec["adapter_required"]),
                scientific_execution_authorized=False,
                source_identity_sha256=source_identity,
                binding_sha256=hashed["binding_sha256"],
            )
        )

    return tuple(bindings)


def binding_map(
    bindings: tuple[ConcreteComponentBindingV1, ...],
) -> dict[str, ConcreteComponentBindingV1]:
    observed: dict[str, ConcreteComponentBindingV1] = {}
    for binding in bindings:
        require_text("component_id", binding.component_id)
        if binding.component_id in observed:
            raise ValueError(f"duplicate component binding: {binding.component_id}")
        observed[binding.component_id] = binding
    if set(observed) != set(required_concrete_component_ids()):
        raise ValueError("concrete component binding registry is incomplete")
    return observed
