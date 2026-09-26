"""Round-generic, role-neutral Researcher input assembly.

This adapter reuses already frozen Evidence, Analyzer, Memory and Researcher
assets. It does not implement a second Analyzer, Memory system, verifier,
trainer, evaluator or promotion gate.

The same input package is consumed by Human, Strong-API-shadow and later Local
Researcher implementations. Scientific decisions remain separate artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import hashlib

from pchsi.cognitive_runtime.schema_registry import (
    validate_artifact,
)
from pchsi.memory.consumer_views import (
    ResearcherMemoryViewV1,
    ResearcherPurposeV1,
)
from pchsi.reference_loop.canonical import domain_hash


FORBIDDEN_RESEARCHER_PRE_KEYS = frozenset(
    {
        "current_f0f1_outcomes",
        "current_selected_f0f1_outcomes",
        "future_pi2_evaluation",
        "current_human_pre",
        "human_pre_record",
        "api_shadow_output",
        "strong_model_benchmark_per_task_results",
        "sealed_test_trajectory",
    }
)


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            ch not in "0123456789abcdef"
            for ch in value
        )
    ):
        raise ValueError(
            f"{name} must be 64 lowercase hex"
        )
    return value


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def round_evidence_semantic_sha256(
    value: Mapping[str, object],
) -> str:
    payload = dict(value)
    validate_artifact(
        "ROUND_EVIDENCE_PACKAGE_V1",
        payload,
    )
    embedded = _require_sha(
        payload["round_evidence_package_sha256"],
        "round_evidence_package_sha256",
    )
    observed = domain_hash(
        "ROUND_EVIDENCE_PACKAGE_V1",
        payload,
        excluded_field=(
            "round_evidence_package_sha256"
        ),
    )
    if observed != embedded:
        raise ValueError(
            "Round Evidence self-hash mismatch"
        )
    if (
        payload[
            "forbidden_future_outcomes_absent"
        ]
        is not True
    ):
        raise ValueError(
            "Round Evidence future-outcome gate failed"
        )
    if (
        payload["sealed_test_details_absent"]
        is not True
    ):
        raise ValueError(
            "Round Evidence sealed-test gate failed"
        )
    forbidden = (
        FORBIDDEN_RESEARCHER_PRE_KEYS.intersection(
            _walk_keys(payload)
        )
    )
    if forbidden:
        raise ValueError(
            "Round Evidence leaks future/sealed keys: "
            + repr(sorted(forbidden))
        )
    return observed


def researcher_memory_view_from_dict(
    value: Mapping[str, object],
) -> ResearcherMemoryViewV1:
    payload = dict(value)
    expected_keys = {
        "schema_id",
        "schema_version",
        "snapshot_sha256",
        "purpose",
        "train_side_records",
        "round_evidence",
        "heldout_aggregate_metrics",
        "direct_environment_action_authority",
        "benefit_harm_authority",
        (
            "may_propose_one_"
            "principal_system_change"
        ),
        "view_sha256",
    }
    if set(payload) != expected_keys:
        raise ValueError(
            "Researcher Memory view keyset mismatch"
        )
    if (
        payload["schema_id"]
        != "RESEARCHER_MEMORY_VIEW_V1"
    ):
        raise ValueError(
            "Researcher Memory schema mismatch"
        )
    if payload["schema_version"] != 1:
        raise ValueError(
            "Researcher Memory version mismatch"
        )
    if (
        payload[
            "direct_environment_action_authority"
        ]
        is not False
    ):
        raise ValueError(
            "Researcher Memory cannot act "
            "in environment"
        )
    if (
        payload["benefit_harm_authority"]
        is not False
    ):
        raise ValueError(
            "Researcher Memory cannot assign "
            "causal outcomes"
        )
    if (
        payload[
            "may_propose_one_principal_system_change"
        ]
        is not True
    ):
        raise ValueError(
            "Researcher Memory planning "
            "authority mismatch"
        )
    forbidden = (
        FORBIDDEN_RESEARCHER_PRE_KEYS.intersection(
            _walk_keys(payload)
        )
    )
    if forbidden:
        raise ValueError(
            "Researcher Memory leaks "
            "future/sealed keys: "
            + repr(sorted(forbidden))
        )

    view = ResearcherMemoryViewV1(
        snapshot_sha256=str(
            payload["snapshot_sha256"]
        ),
        purpose=ResearcherPurposeV1(
            str(payload["purpose"])
        ),
        train_side_records=tuple(
            payload["train_side_records"]
        ),
        round_evidence=dict(
            payload["round_evidence"]
        ),
        heldout_aggregate_metrics=dict(
            payload[
                "heldout_aggregate_metrics"
            ]
        ),
        view_sha256=str(
            payload["view_sha256"]
        ),
    )
    if (
        view.purpose
        is not ResearcherPurposeV1
        .ROUND_RESEARCH_PLANNING
    ):
        raise ValueError(
            "Human PRE requires "
            "ROUND_RESEARCH_PLANNING Memory view"
        )
    return view


@dataclass(frozen=True, slots=True)
class ResearcherRoundInputPackageV1:
    round_id: str
    parent_policy_id: str
    round_evidence_package_sha256: str
    round_evidence_file_sha256: str
    researcher_memory_view_sha256: str
    researcher_memory_file_sha256: str
    researcher_memory_binding_mode: str
    current_policy_scorecard: dict[str, object]
    analyzer_evidence: dict[str, object]
    historical_failure_experience: dict[
        str, object
    ]
    experiment_history: dict[str, object]
    resource_and_cost: dict[str, object]
    role_visibility: dict[str, object]
    authority_boundary: dict[str, object]
    input_package_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.round_id, str)
            or not self.round_id
        ):
            raise ValueError("round_id required")
        if (
            not isinstance(
                self.parent_policy_id,
                str,
            )
            or not self.parent_policy_id
        ):
            raise ValueError(
                "parent_policy_id required"
            )
        for name in (
            "round_evidence_package_sha256",
            "round_evidence_file_sha256",
            "researcher_memory_view_sha256",
            "researcher_memory_file_sha256",
        ):
            _require_sha(
                getattr(self, name),
                name,
            )
        if (
            self.researcher_memory_binding_mode
            not in {
                "RESEARCHER_MEMORY_VIEW_SHA256",
                "RESEARCHER_MEMORY_FILE_SHA256",
                "ROUND_INPUT_PACKAGE_AUTHORITY",
            }
        ):
            raise ValueError(
                "unsupported Researcher "
                "Memory binding mode"
            )

        for name in (
            "current_policy_scorecard",
            "analyzer_evidence",
            "historical_failure_experience",
            "experiment_history",
            "resource_and_cost",
            "role_visibility",
            "authority_boundary",
        ):
            if not isinstance(
                getattr(self, name),
                dict,
            ):
                raise TypeError(
                    f"{name} must be object"
                )

        forbidden = (
            FORBIDDEN_RESEARCHER_PRE_KEYS
            .intersection(
                _walk_keys(
                    self._without_sha()
                )
            )
        )
        if forbidden:
            raise ValueError(
                "Researcher input package leaks "
                "forbidden keys: "
                + repr(sorted(forbidden))
            )

        expected = domain_hash(
            "RESEARCHER_ROUND_INPUT_PACKAGE_V1",
            self._without_sha(),
        )
        if self.input_package_sha256 is None:
            object.__setattr__(
                self,
                "input_package_sha256",
                expected,
            )
        elif (
            self.input_package_sha256
            != expected
        ):
            raise ValueError(
                "Researcher input package "
                "SHA mismatch"
            )

    def _without_sha(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id": (
                "RESEARCHER_ROUND_INPUT_PACKAGE_V1"
            ),
            "schema_version": 1,
            "round_id": self.round_id,
            "parent_policy_id": (
                self.parent_policy_id
            ),
            "round_evidence_package_sha256": (
                self.round_evidence_package_sha256
            ),
            "round_evidence_file_sha256": (
                self.round_evidence_file_sha256
            ),
            "researcher_memory_view_sha256": (
                self.researcher_memory_view_sha256
            ),
            "researcher_memory_file_sha256": (
                self.researcher_memory_file_sha256
            ),
            "researcher_memory_binding_mode": (
                self.researcher_memory_binding_mode
            ),
            "current_policy_scorecard": (
                self.current_policy_scorecard
            ),
            "analyzer_evidence": (
                self.analyzer_evidence
            ),
            "historical_failure_experience": (
                self.historical_failure_experience
            ),
            "experiment_history": (
                self.experiment_history
            ),
            "resource_and_cost": (
                self.resource_and_cost
            ),
            "role_visibility": (
                self.role_visibility
            ),
            "authority_boundary": (
                self.authority_boundary
            ),
        }

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            **self._without_sha(),
            "input_package_sha256": (
                self.input_package_sha256
            ),
        }


def build_researcher_round_input_package_v1(
    *,
    round_evidence: Mapping[str, object],
    round_evidence_file_sha256: str,
    researcher_memory: Mapping[str, object],
    researcher_memory_file_sha256: str,
    parent_policy_id: str,
) -> ResearcherRoundInputPackageV1:
    round_payload = dict(round_evidence)
    round_sha = (
        round_evidence_semantic_sha256(
            round_payload
        )
    )
    view = researcher_memory_view_from_dict(
        researcher_memory
    )

    _require_sha(
        round_evidence_file_sha256,
        "round_evidence_file_sha256",
    )
    _require_sha(
        researcher_memory_file_sha256,
        "researcher_memory_file_sha256",
    )

    expected_memory = round_payload[
        "researcher_memory_pack_sha256"
    ]
    if expected_memory == view.view_sha256:
        binding_mode = (
            "RESEARCHER_MEMORY_VIEW_SHA256"
        )
    elif (
        expected_memory
        == researcher_memory_file_sha256
    ):
        binding_mode = (
            "RESEARCHER_MEMORY_FILE_SHA256"
        )
    elif expected_memory is None:
        binding_mode = (
            "ROUND_INPUT_PACKAGE_AUTHORITY"
        )
    else:
        raise ValueError(
            "Round Evidence Researcher Memory "
            "identity does not match the "
            "selected round-level view"
        )

    current_policy_scorecard = {
        "policy_lineage_sha256": (
            round_payload[
                "policy_lineage_sha256"
            ]
        ),
        "policy_checkpoint_sha256": (
            round_payload[
                "policy_checkpoint_sha256"
            ]
        ),
        "policy_config_sha256": (
            round_payload[
                "policy_config_sha256"
            ]
        ),
        "task_set_manifest_sha256": (
            round_payload[
                "task_set_manifest_sha256"
            ]
        ),
        "rollout_census_sha256": (
            round_payload[
                "rollout_census_sha256"
            ]
        ),
        "mechanical_failure_census_sha256": (
            round_payload[
                "mechanical_failure_census_sha256"
            ]
        ),
    }

    analyzer_evidence = {
        "formal_result_manifest_sha256": (
            round_payload[
                "analyzer_formal_result_manifest_sha256"
            ]
        ),
        "metric_report_sha256": (
            round_payload[
                "analyzer_metric_report_sha256"
            ]
        ),
        "repair_effect_authority": False,
    }

    historical_failure_experience = {
        "researcher_memory_view_sha256": (
            view.view_sha256
        ),
        "snapshot_sha256": (
            view.snapshot_sha256
        ),
        "purpose": view.purpose.value,
        "train_side_record_count": len(
            view.train_side_records
        ),
        "heldout_aggregate_metric_key_count": (
            len(
                view.heldout_aggregate_metrics
            )
        ),
        (
            "historical_experience_"
            "is_not_causal_authority"
        ): True,
    }

    experiment_history = {
        "historical_f0f1_summary_sha256": (
            round_payload[
                "historical_f0f1_summary_sha256"
            ]
        ),
        "historical_go_nogo_ledger_sha256": (
            round_payload[
                "historical_go_nogo_ledger_sha256"
            ]
        ),
        (
            "previous_researcher_"
            "decisions_sha256"
        ): (
            round_payload[
                "previous_researcher_decisions_sha256"
            ]
        ),
        "training_history_sha256": (
            round_payload[
                "training_history_sha256"
            ]
        ),
        "code_config_diff_manifest_sha256": (
            round_payload[
                "code_config_diff_manifest_sha256"
            ]
        ),
    }

    resource_and_cost = {
        "resource_budget_manifest_sha256": (
            round_payload[
                "resource_budget_manifest_sha256"
            ]
        ),
        "budget_interpretation_status": (
            "BOUND_INPUT_HUMAN_PRE_"
            "MUST_SELECT_EXACT_BUDGET"
        ),
    }

    role_visibility = {
        "human_reference": {
            "round_evidence_package_sha256": (
                round_sha
            ),
            "researcher_memory_view_sha256": (
                view.view_sha256
            ),
        },
        "strong_api_shadow": {
            "round_evidence_package_sha256": (
                round_sha
            ),
            "researcher_memory_view_sha256": (
                view.view_sha256
            ),
            "human_pre_visible": False,
            "human_pre_hash_visible": False,
        },
        "local_shadow_future": {
            "round_evidence_package_sha256": (
                round_sha
            ),
            "researcher_memory_view_sha256": (
                view.view_sha256
            ),
            "human_pre_visible": False,
        },
        (
            "same_visible_evidence_"
            "for_pre_comparison"
        ): True,
    }

    authority_boundary = {
        "may_identify_bottleneck": True,
        (
            "may_discover_or_compose_"
            "key_repair"
        ): True,
        (
            "may_select_one_"
            "principal_change"
        ): True,
        (
            "may_freeze_verification_"
            "and_training_plan"
        ): True,
        "may_execute_environment_action": False,
        (
            "may_assign_benefit_harm_"
            "neutral_uncertain"
        ): False,
        "may_promote_policy": False,
        "causal_authority": (
            "INDEPENDENT_ENVIRONMENT_"
            "VERIFIER_ONLY"
        ),
        "promotion_authority": (
            "DETERMINISTIC_INDEPENDENT_"
            "GATE_ONLY"
        ),
        "current_future_outcomes_visible": False,
        "benchmark_per_task_results_visible": False,
    }

    return ResearcherRoundInputPackageV1(
        round_id=str(
            round_payload["round_id"]
        ),
        parent_policy_id=parent_policy_id,
        round_evidence_package_sha256=(
            round_sha
        ),
        round_evidence_file_sha256=(
            round_evidence_file_sha256
        ),
        researcher_memory_view_sha256=str(
            view.view_sha256
        ),
        researcher_memory_file_sha256=(
            researcher_memory_file_sha256
        ),
        researcher_memory_binding_mode=(
            binding_mode
        ),
        current_policy_scorecard=(
            current_policy_scorecard
        ),
        analyzer_evidence=analyzer_evidence,
        historical_failure_experience=(
            historical_failure_experience
        ),
        experiment_history=experiment_history,
        resource_and_cost=resource_and_cost,
        role_visibility=role_visibility,
        authority_boundary=authority_boundary,
    )


def build_human_evidence_binding_candidate_v1(
    package: ResearcherRoundInputPackageV1,
) -> dict[str, object]:
    value = {
        "schema_id": (
            "HUMAN_REFERENCE_EVIDENCE_BINDING_V1"
        ),
        "round_id": package.round_id,
        "parent_policy_id": (
            package.parent_policy_id
        ),
        "evidence_cutoff_sha256": (
            package.input_package_sha256
        ),
        "round_evidence_package_sha256": (
            package.round_evidence_package_sha256
        ),
        "researcher_memory_pack_file_sha256": (
            package.researcher_memory_file_sha256
        ),
        "evidence_binding_sha256": "0" * 64,
    }
    value["evidence_binding_sha256"] = (
        domain_hash(
            "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
            value,
            excluded_field=(
                "evidence_binding_sha256"
            ),
        )
    )
    return value



def researcher_round_input_package_from_dict(
    value: Mapping[str, object],
) -> ResearcherRoundInputPackageV1:
    payload = dict(value)
    expected = {
        "schema_id",
        "schema_version",
        "round_id",
        "parent_policy_id",
        "round_evidence_package_sha256",
        "round_evidence_file_sha256",
        "researcher_memory_view_sha256",
        "researcher_memory_file_sha256",
        "researcher_memory_binding_mode",
        "current_policy_scorecard",
        "analyzer_evidence",
        "historical_failure_experience",
        "experiment_history",
        "resource_and_cost",
        "role_visibility",
        "authority_boundary",
        "input_package_sha256",
    }
    if set(payload) != expected:
        raise ValueError(
            "Researcher round input keyset mismatch"
        )
    if (
        payload["schema_id"]
        != "RESEARCHER_ROUND_INPUT_PACKAGE_V1"
        or payload["schema_version"] != 1
    ):
        raise ValueError(
            "Researcher round input schema mismatch"
        )
    return ResearcherRoundInputPackageV1(
        round_id=str(payload["round_id"]),
        parent_policy_id=str(
            payload["parent_policy_id"]
        ),
        round_evidence_package_sha256=str(
            payload[
                "round_evidence_package_sha256"
            ]
        ),
        round_evidence_file_sha256=str(
            payload[
                "round_evidence_file_sha256"
            ]
        ),
        researcher_memory_view_sha256=str(
            payload[
                "researcher_memory_view_sha256"
            ]
        ),
        researcher_memory_file_sha256=str(
            payload[
                "researcher_memory_file_sha256"
            ]
        ),
        researcher_memory_binding_mode=str(
            payload[
                "researcher_memory_binding_mode"
            ]
        ),
        current_policy_scorecard=dict(
            payload["current_policy_scorecard"]
        ),
        analyzer_evidence=dict(
            payload["analyzer_evidence"]
        ),
        historical_failure_experience=dict(
            payload[
                "historical_failure_experience"
            ]
        ),
        experiment_history=dict(
            payload["experiment_history"]
        ),
        resource_and_cost=dict(
            payload["resource_and_cost"]
        ),
        role_visibility=dict(
            payload["role_visibility"]
        ),
        authority_boundary=dict(
            payload["authority_boundary"]
        ),
        input_package_sha256=str(
            payload["input_package_sha256"]
        ),
    )


def build_shared_researcher_pre_projection_v1(
    *,
    round_evidence: Mapping[str, object],
    researcher_memory: Mapping[str, object],
    round_research_input: Mapping[str, object],
    observed_round_evidence_file_sha256: str,
    observed_researcher_memory_file_sha256: str,
) -> dict[str, object]:
    round_payload = dict(round_evidence)
    memory_payload = dict(researcher_memory)
    input_package = (
        researcher_round_input_package_from_dict(
            round_research_input
        )
    )

    round_sha = (
        round_evidence_semantic_sha256(
            round_payload
        )
    )
    memory_view = (
        researcher_memory_view_from_dict(
            memory_payload
        )
    )

    if (
        round_sha
        != input_package
        .round_evidence_package_sha256
    ):
        raise ValueError(
            "shared PRE projection Round Evidence "
            "identity mismatch"
        )
    if (
        observed_round_evidence_file_sha256
        != input_package
        .round_evidence_file_sha256
    ):
        raise ValueError(
            "shared PRE projection Round Evidence "
            "file mismatch"
        )
    if (
        memory_view.view_sha256
        != input_package
        .researcher_memory_view_sha256
    ):
        raise ValueError(
            "shared PRE projection Memory "
            "view mismatch"
        )
    if (
        observed_researcher_memory_file_sha256
        != input_package
        .researcher_memory_file_sha256
    ):
        raise ValueError(
            "shared PRE projection Memory "
            "file mismatch"
        )

    projection = {
        "schema_id": (
            "SHARED_RESEARCHER_PRE_PROJECTION_V1"
        ),
        "round_evidence_package_sha256": (
            round_sha
        ),
        "round_evidence_package": (
            round_payload
        ),
        "researcher_memory_view_sha256": (
            memory_view.view_sha256
        ),
        "researcher_memory_view": (
            memory_payload
        ),
        "round_research_input_package_sha256": (
            input_package.input_package_sha256
        ),
        "round_research_input_package": (
            input_package.to_dict()
        ),
        "human_pre_visible": False,
        "human_pre_hash_visible": False,
        "future_current_round_outcomes_visible": (
            False
        ),
        "benchmark_per_task_results_visible": (
            False
        ),
    }
    forbidden = (
        FORBIDDEN_RESEARCHER_PRE_KEYS
        .intersection(_walk_keys(projection))
    )
    if forbidden:
        raise ValueError(
            "shared PRE projection leaks "
            "forbidden keys: "
            + repr(sorted(forbidden))
        )
    return projection
