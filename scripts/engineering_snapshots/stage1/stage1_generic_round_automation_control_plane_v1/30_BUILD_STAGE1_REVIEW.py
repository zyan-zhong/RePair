from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import sys

from stage1_pkg.common import (
    Stage1PackageError,
    atomic_zip_directory,
    canonical_json_bytes,
    load_json,
    sha256_file,
    write_new_json,
)
from stage1_pkg.constants import (
    GENERIC_WORKTREE,
    OUTPUT_ROOT,
    REVIEW_ROOT,
    REVIEW_ZIP,
    STAGE0_CLOSEOUT_ZIP,
    STAGE0_GENERIC_PATCH_RECEIPT,
)


def _hex(ch: str) -> str:
    return ch * 64


def main() -> int:
    if REVIEW_ROOT.exists() or REVIEW_ROOT.is_symlink():
        raise Stage1PackageError(f"review root already exists: {REVIEW_ROOT}")
    if REVIEW_ZIP.exists() or REVIEW_ZIP.is_symlink():
        raise Stage1PackageError(f"review ZIP already exists: {REVIEW_ZIP}")

    repo_src = str(GENERIC_WORKTREE / "src")
    if repo_src not in sys.path:
        sys.path.insert(0, repo_src)

    from pchsi.round_control.benchmark_sealing import (
        BenchmarkResultSealV1,
        BenchmarkSplitV1,
    )
    from pchsi.round_control.bindings import validate_repo_component_bindings
    from pchsi.round_control.clean_data_gate import (
        CleanConsumerV1,
        CleanSplitV1,
        TrainPoolV1,
        authorize_clean_access,
    )
    from pchsi.round_control.lifecycle import RoundLifecycleV1, RoundStageV1
    from pchsi.round_control.orchestrator import next_action_for
    from pchsi.round_control.promotion import freeze_promotion_decision
    from pchsi.round_control.retention import (
        ArtifactKindV1,
        decide_cross_round_retention,
    )
    from pchsi.round_control.role_authority import (
        AuthorityPhaseV1,
        ResearchRoleV1,
        resolve_authority_plan,
    )
    from pchsi.round_control.trace_handoff import (
        ActorV1,
        AuthorityModeV1,
        RoleTraceRecordV1,
        RoundTraceLedgerV1,
    )
    from pchsi.research_intelligence.benchmark_registry import (
        SharedEvaluationProtocolV1,
    )
    from pchsi.research_intelligence.distillation import (
        build_local_role_supervision_dataset,
    )
    from pchsi.research_intelligence.reference_round import (
        freeze_reference_round_manifest,
    )
    from pchsi.research_intelligence.takeover import evaluate_takeover_gate

    dry_root = OUTPUT_ROOT / "dry_run"
    dry_root.mkdir(parents=True, exist_ok=True)

    component_binding = validate_repo_component_bindings(GENERIC_WORKTREE)
    write_new_json(
        dry_root / "STAGE1_REPO_COMPONENT_REUSE_BINDING_V1.json",
        component_binding,
    )

    takeover_metrics = {
        "completed_reference_round_count": 2,
        "full_round_go_count": 1,
        "strong_pre_shadow_round_count": 2,
        "strong_post_shadow_round_count": 2,
        "future_outcome_leakage_count": 0,
        "single_change_compliance_rate": 1.0,
        "budget_compliance_rate": 1.0,
        "evidence_validity_rate": 1.0,
        "human_field_revision_rate": 0.0,
        "repeated_nogo_avoidance_rate": 1.0,
        "downstream_benefits_per_budget_ratio_vs_human": 1.0,
    }
    takeover_path = dry_root / "SYNTHETIC_TAKEOVER_EVALUATION_V1.json"
    takeover = evaluate_takeover_gate(
        metrics=takeover_metrics,
        output=takeover_path,
    )

    human_plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW,
        takeover_evaluation=None,
    )
    strong_plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
        takeover_evaluation=takeover,
    )
    local_plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.LOCAL_PRIMARY_STRONG_AUDIT,
        takeover_evaluation=takeover,
    )

    train_update_grant = authorize_clean_access(
        split=CleanSplitV1.ALFWORLD_TRAIN,
        train_pool=TrainPoolV1.TRAIN_UPDATE,
        consumer=CleanConsumerV1.POLICY_TRAINING,
    )
    train_select_grant = authorize_clean_access(
        split=CleanSplitV1.ALFWORLD_TRAIN,
        train_pool=TrainPoolV1.TRAIN_SELECT,
        consumer=CleanConsumerV1.PROMOTION_GATE,
    )
    train_audit_grant = authorize_clean_access(
        split=CleanSplitV1.ALFWORLD_TRAIN,
        train_pool=TrainPoolV1.TRAIN_AUDIT,
        consumer=CleanConsumerV1.ROLE_TAKEOVER_AUDIT,
    )
    benchmark_grant = authorize_clean_access(
        split=CleanSplitV1.VALID_UNSEEN,
        train_pool=TrainPoolV1.NONE,
        consumer=CleanConsumerV1.FINAL_BENCHMARK,
    )
    leakage_blocked = False
    try:
        authorize_clean_access(
            split=CleanSplitV1.VALID_UNSEEN,
            train_pool=TrainPoolV1.NONE,
            consumer=CleanConsumerV1.HIERARCHICAL_ANALYZER,
        )
    except ValueError:
        leakage_blocked = True
    if not leakage_blocked:
        raise Stage1PackageError("clean data gate did not block benchmark leakage")

    lifecycle = RoundLifecycleV1.new(
        round_id="stage1-control-plane-dry-run-r001",
        parent_policy_id="pi0-clean",
    )
    route_trace = []
    for next_stage in (
        RoundStageV1.EVIDENCE_READY,
        RoundStageV1.ANALYSIS_READY,
        RoundStageV1.PRE_PLAN_FROZEN,
        RoundStageV1.EXPERIMENTS_COMPLETED,
        RoundStageV1.POST_PLAN_FROZEN,
        RoundStageV1.TRAINING_DATA_READY,
        RoundStageV1.TRAINING_COMPLETED,
        RoundStageV1.INTERNAL_EVALUATION_COMPLETED,
        RoundStageV1.PROMOTED,
        RoundStageV1.ROUND_CLOSED,
    ):
        action = next_action_for(lifecycle)
        route_trace.append(
            {
                "stage": lifecycle.current_stage.value,
                "component_ids": list(action.component_ids),
                "expected_output_stage": (
                    None
                    if action.expected_output_stage is None
                    else action.expected_output_stage.value
                ),
            }
        )
        lifecycle = lifecycle.advance(
            next_stage,
            evidence_sha256=_hex("a"),
        )
    route_trace.append(
        {
            "stage": lifecycle.current_stage.value,
            "component_ids": list(next_action_for(lifecycle).component_ids),
            "expected_output_stage": None,
        }
    )

    traces = (
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.ANALYZER,
            actor=ActorV1.HUMAN,
            authority_mode=AuthorityModeV1.PRIMARY,
            input_artifact_sha256=_hex("1"),
            output_artifact_sha256=_hex("2"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.ANALYZER,
            actor=ActorV1.STRONG,
            authority_mode=AuthorityModeV1.SHADOW,
            input_artifact_sha256=_hex("1"),
            output_artifact_sha256=_hex("3"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.RESEARCH_PLANNER_PRE,
            actor=ActorV1.HUMAN,
            authority_mode=AuthorityModeV1.PRIMARY,
            input_artifact_sha256=_hex("4"),
            output_artifact_sha256=_hex("5"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.RESEARCH_PLANNER_PRE,
            actor=ActorV1.STRONG,
            authority_mode=AuthorityModeV1.SHADOW,
            input_artifact_sha256=_hex("4"),
            output_artifact_sha256=_hex("6"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.RESEARCH_PLANNER_POST,
            actor=ActorV1.HUMAN,
            authority_mode=AuthorityModeV1.PRIMARY,
            input_artifact_sha256=_hex("7"),
            output_artifact_sha256=_hex("8"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
        RoleTraceRecordV1(
            round_id="stage1-control-plane-dry-run-r001",
            role=ResearchRoleV1.RESEARCH_PLANNER_POST,
            actor=ActorV1.STRONG,
            authority_mode=AuthorityModeV1.SHADOW,
            input_artifact_sha256=_hex("7"),
            output_artifact_sha256=_hex("9"),
            access_class="TRAIN_REFERENCE_ROUND",
            structured_output_only=True,
            provider_reasoning_artifact_required=False,
        ),
    )
    ledger = RoundTraceLedgerV1(
        round_id="stage1-control-plane-dry-run-r001",
        records=traces,
    )
    ledger.validate(require_strong_pre=True, require_strong_post=True)
    ledger_dict = ledger.to_dict()
    write_new_json(dry_root / "SYNTHETIC_ROUND_TRACE_LEDGER_V1.json", ledger_dict)

    reference_manifest_path = (
        dry_root / "SYNTHETIC_RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1.json"
    )
    reference_manifest = freeze_reference_round_manifest(
        {
            "round_id": "stage1-control-plane-dry-run-r001",
            "policy_lineage_sha256": _hex("a"),
            "round_evidence_package_sha256": _hex("1"),
            "human_pre_record_sha256": _hex("5"),
            "strong_pre_shadow_sha256": _hex("6"),
            "pre_adjudication_sha256": _hex("b"),
            "environment_result_package_sha256": _hex("7"),
            "human_post_record_sha256": _hex("8"),
            "strong_post_shadow_sha256": _hex("9"),
            "post_adjudication_sha256": _hex("c"),
            "verified_training_evidence_sha256": _hex("d"),
            "policy_evaluation_result_sha256": _hex("e"),
            "promotion_result": "PROMOTE",
            "go_nogo_status": "GO",
            "access_class": "TRAIN_REFERENCE_ROUND",
        },
        reference_manifest_path,
    )

    distillation_path = dry_root / "SYNTHETIC_LOCAL_ROLE_SUPERVISION_DATASET_V1.json"
    distillation = build_local_role_supervision_dataset(
        reference_round_paths=(reference_manifest_path,),
        output=distillation_path,
    )

    protocol = SharedEvaluationProtocolV1(
        prompt_contract_sha256=_hex("1"),
        history_contract_sha256=_hex("2"),
        menu_interface_contract_sha256=_hex("3"),
        parser_contract_sha256=_hex("4"),
        controller_harness_contract_sha256=_hex("5"),
        memory_condition_contract_sha256=_hex("6"),
        task_panel_sha256=_hex("7"),
        action_budget=30,
        model_call_budget=30,
        seed_schedule_sha256=_hex("8"),
        environment_source_sha256=_hex("9"),
        success_definition_sha256=_hex("a"),
        interaction_contract_sha256=_hex("b"),
        result_census_contract_sha256=_hex("c"),
    )
    protocol_sha = protocol.digest()

    benchmark_seal = BenchmarkResultSealV1.create(
        benchmark_split=BenchmarkSplitV1.VALID_UNSEEN,
        checkpoint_id="pi0-clean",
        shared_protocol_sha256=protocol_sha,
        result_artifact_sha256=_hex("d"),
    )

    pilot_retention = decide_cross_round_retention(
        origin_round_role="PILOT_ENGINEERING_ROUND_V1",
        artifact_kind=ArtifactKindV1.TASK_SPECIFIC_REPAIR,
        access_class="PILOT_CONTAMINATED",
    )
    strong_retention = decide_cross_round_retention(
        origin_round_role="CLEAN_TRAIN_ROUND_V1",
        artifact_kind=ArtifactKindV1.STRONG_STRUCTURED_TRACE,
        access_class="TRAIN_REFERENCE_ROUND",
    )

    promotion = freeze_promotion_decision(
        round_id="stage1-control-plane-dry-run-r001",
        decision="PROMOTE",
        decision_rule_id="PRE_REGISTERED_INTERNAL_SELECT_RULE_V1",
        evidence_access_class="TRAIN_SELECT",
        evidence_sha256=_hex("e"),
        parent_policy_id="pi0-clean",
        candidate_policy_id="pi1-human-clean",
    )

    dry_run = {
        "schema_id": "STAGE1_GENERIC_ROUND_CONTROL_PLANE_DRY_RUN_V1",
        "schema_version": 1,
        "status": "PASS",
        "lifecycle_final": lifecycle.to_dict(),
        "orchestrator_route_trace": route_trace,
        "clean_data_gate": {
            "train_update": train_update_grant.to_dict(),
            "train_select": train_select_grant.to_dict(),
            "train_audit": train_audit_grant.to_dict(),
            "valid_unseen_final_benchmark": benchmark_grant.to_dict(),
            "valid_unseen_to_analyzer_blocked": leakage_blocked,
        },
        "authority_profiles": {
            "human_primary": {
                role.value: human_plan.primary_actor(role)
                for role in ResearchRoleV1
            },
            "strong_primary": {
                role.value: strong_plan.primary_actor(role)
                for role in ResearchRoleV1
            },
            "local_primary": {
                role.value: local_plan.primary_actor(role)
                for role in ResearchRoleV1
            },
            "strong_trace_capture_required": True,
            "local_trace_capture_required_after_takeover": True,
        },
        "trace_handoff": {
            "trace_ledger_sha256": ledger_dict["trace_ledger_sha256"],
            "strong_teacher_record_count": len(
                ledger.localization_teacher_records()
            ),
            "provider_reasoning_artifact_required": False,
        },
        "existing_reference_round_compatibility": {
            "reference_round_manifest_sha256": reference_manifest[
                "reference_round_manifest_sha256"
            ],
            "local_role_supervision_dataset_sha256": distillation[
                "dataset_sha256"
            ],
            "local_role_supervision_example_count": len(
                distillation["examples"]
            ),
        },
        "benchmark_sealing": {
            "shared_protocol_sha256": protocol_sha,
            "benchmark_split": benchmark_seal.benchmark_split.value,
            "revealed": benchmark_seal.revealed,
            "benchmark_feedback_authorized": (
                benchmark_seal.benchmark_feedback_authorized
            ),
            "seal_sha256": benchmark_seal.seal_sha256,
        },
        "retention": {
            "pilot_semantic_reuse_allowed": pilot_retention.allowed,
            "pilot_semantic_destination": pilot_retention.destination,
            "strong_trace_reuse_allowed": strong_retention.allowed,
            "strong_trace_destination": strong_retention.destination,
        },
        "promotion": promotion.to_dict(),
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
        "benchmark_execution_count": 0,
    }
    dry_run["dry_run_sha256"] = hashlib.sha256(
        canonical_json_bytes(dry_run)
    ).hexdigest()
    write_new_json(
        dry_root / "STAGE1_GENERIC_ROUND_CONTROL_PLANE_DRY_RUN_V1.json",
        dry_run,
    )

    REVIEW_ROOT.mkdir(parents=True, exist_ok=False)
    evidence = REVIEW_ROOT / "evidence"
    authorities = REVIEW_ROOT / "authorities"
    evidence.mkdir()
    authorities.mkdir()

    for source in (
        OUTPUT_ROOT / "STAGE1_PRECONDITION_RECEIPT_V1.json",
        OUTPUT_ROOT / "STAGE1_CONTROL_PLANE_BUILD_RECEIPT_V1.json",
        dry_root / "STAGE1_REPO_COMPONENT_REUSE_BINDING_V1.json",
        dry_root / "STAGE1_GENERIC_ROUND_CONTROL_PLANE_DRY_RUN_V1.json",
        takeover_path,
        reference_manifest_path,
        distillation_path,
        dry_root / "SYNTHETIC_ROUND_TRACE_LEDGER_V1.json",
    ):
        shutil.copy2(source, evidence / source.name)

    shutil.copy2(
        STAGE0_GENERIC_PATCH_RECEIPT,
        authorities / STAGE0_GENERIC_PATCH_RECEIPT.name,
    )
    shutil.copy2(
        STAGE0_CLOSEOUT_ZIP,
        authorities / "HUMAN_PILOT_STAGE0_OFFOFF_CLOSEOUT_REVIEW_V1.zip",
    )

    build_receipt = load_json(
        OUTPUT_ROOT / "STAGE1_CONTROL_PLANE_BUILD_RECEIPT_V1.json"
    )
    review_manifest = {
        "schema_id": "STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_REVIEW_MANIFEST_V1",
        "schema_version": 1,
        "review_status": "READY_FOR_STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING",
        "stage1_control_plane_freeze_root_sha256": build_receipt[
            "stage1_control_plane_freeze_root_sha256"
        ],
        "dry_run_sha256": dry_run["dry_run_sha256"],
        "stage0_closeout_zip_sha256": sha256_file(STAGE0_CLOSEOUT_ZIP),
        "repo_component_binding_status": component_binding["binding_status"],
        "external_runtime_binding_status": "DEFERRED_TO_CONCRETE_RUNNER_BINDING",
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
        "benchmark_execution_count": 0,
        "repository_commit_created": False,
        "repository_push_executed": False,
        "next_gate": (
            "STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING_AND_"
            "HUMAN_STRONG_LOCAL_DRY_RUN"
        ),
    }
    review_manifest["review_manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(review_manifest)
    ).hexdigest()
    write_new_json(REVIEW_ROOT / "REVIEW_MANIFEST_V1.json", review_manifest)

    publication = atomic_zip_directory(REVIEW_ROOT, REVIEW_ZIP)
    print("STAGE1_GENERIC_ROUND_CONTROL_PLANE_REVIEW_READY")
    print("REVIEW_ZIP=" + publication["path"])
    print("REVIEW_ZIP_SHA256=" + publication["sha256"])
    print("MODEL_EXECUTION_COUNT=0")
    print("ENVIRONMENT_EXECUTION_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    print("BENCHMARK_EXECUTION_COUNT=0")
    print("REPOSITORY_COMMIT_CREATED=false")
    print("REPOSITORY_PUSH_EXECUTED=false")
    print(
        "NEXT_GATE=STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING_AND_"
        "HUMAN_STRONG_LOCAL_DRY_RUN"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
