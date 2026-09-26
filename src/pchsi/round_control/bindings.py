from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.canonical import (
    directory_manifest_sha256,
    sha256_file,
)


REPO_COMPONENT_BINDINGS: dict[str, tuple[str, ...]] = {
    "EVIDENCE_PACKAGE": (
        "src/pchsi/reference_loop/analyzer_evidence_pack.py",
    ),
    "HIERARCHICAL_ANALYZER": (
        "src/pchsi/analyzer",
    ),
    "PERSISTENT_FAILURE_EXPERIENCE": (
        "src/pchsi/memory",
    ),
    "RESEARCH_PLANNER_PRE_POST": (
        "src/pchsi/research_intelligence/role_neutral.py",
        "src/pchsi/research_intelligence/research_planner_reference_trace.py",
        "src/pchsi/research_intelligence/reference_round.py",
    ),
    "DETERMINISTIC_DATA_BUILDER": (
        "src/pchsi/reference_loop/approved_materialization.py",
    ),
    "SELECT_EVALUATOR": (
        "src/pchsi/evaluation",
    ),
    "PROMOTION_ROLLBACK_CONTRACTS": (
        "src/pchsi/research_intelligence/takeover.py",
        "src/pchsi/research_intelligence/reference_round.py",
    ),
    "STRONG_TRACE_STORAGE": (
        "src/pchsi/research_intelligence/distillation.py",
        "src/pchsi/research_intelligence/research_planner_reference_trace.py",
    ),
}

REQUIRED_REUSE_COMPONENT_IDS = frozenset(
    {
        "EVIDENCE_PACKAGE",
        "HIERARCHICAL_ANALYZER",
        "PERSISTENT_FAILURE_EXPERIENCE",
        "RESEARCH_PLANNER_PRE_POST",
        "SAME_STATE_F0F1",
        "TRAINING_DATA_PLAN",
        "DETERMINISTIC_DATA_BUILDER",
        "SCHEMA_AWARE_RENDERER",
        "GENERIC_TRAINING_STAGE_V2_1",
        "MODEL_INIT_SMOKE",
        "TRAINING_RECEIPTS",
        "SELECT_EVALUATOR",
        "GENERIC_SELECT_POLICY_BINDING",
        "PROMOTION_ROLLBACK_CONTRACTS",
        "STRONG_TRACE_STORAGE",
    }
)


def validate_repo_component_bindings(repo_root: Path) -> dict[str, object]:
    repo_root = Path(repo_root)
    components: dict[str, object] = {}
    for component_id, relatives in REPO_COMPONENT_BINDINGS.items():
        sources = []
        for relative in relatives:
            path = repo_root / relative
            if path.is_symlink() or not path.exists():
                raise ValueError(
                    f"reuse binding source missing for {component_id}: {path}"
                )
            if path.is_dir():
                digest = directory_manifest_sha256(path)
                source_type = "DIRECTORY"
            elif path.is_file():
                digest = sha256_file(path)
                source_type = "FILE"
            else:
                raise ValueError(f"reuse binding is not file/directory: {path}")
            sources.append(
                {
                    "path": relative,
                    "source_type": source_type,
                    "sha256": digest,
                }
            )
        components[component_id] = {
            "binding_status": "PASS",
            "sources": sources,
        }
    return {
        "schema_id": "STAGE1_REPO_COMPONENT_REUSE_BINDING_V1",
        "schema_version": 1,
        "binding_status": "PASS",
        "components": components,
        "external_runtime_components": {
            component_id: {
                "binding_status": "DEFERRED_TO_CONCRETE_RUNNER_BINDING",
            }
            for component_id in sorted(
                REQUIRED_REUSE_COMPONENT_IDS - set(REPO_COMPONENT_BINDINGS)
            )
        },
    }
