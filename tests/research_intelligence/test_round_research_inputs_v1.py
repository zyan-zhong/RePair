from __future__ import annotations

import hashlib
import json

import pytest

from pchsi.memory.consumer_views import (
    ResearcherMemoryViewV1,
    ResearcherPurposeV1,
)
from pchsi.reference_loop.canonical import (
    domain_hash,
)
from pchsi.research_intelligence.round_research_inputs import (
    build_human_evidence_binding_candidate_v1,
    build_researcher_round_input_package_v1,
    round_evidence_semantic_sha256,
)


def _memory() -> dict[str, object]:
    view = ResearcherMemoryViewV1(
        snapshot_sha256="f" * 64,
        purpose=(
            ResearcherPurposeV1
            .ROUND_RESEARCH_PLANNING
        ),
        train_side_records=(
            {
                "source_partition": (
                    "TRAIN_MEMORY_SOURCE"
                ),
                "memory_lineage_id": "1" * 64,
            },
        ),
        round_evidence={
            "historical_go_nogo": (
                "pi0-to-pi1 NO-GO"
            ),
        },
        heldout_aggregate_metrics={},
    )
    return view.to_dict()


def _round_evidence(
    memory_sha: str | None,
) -> dict[str, object]:
    value = {
        "schema_id": (
            "ROUND_EVIDENCE_PACKAGE_V1"
        ),
        "schema_version": 1,
        "round_id": "round-k",
        "policy_lineage_sha256": "1" * 64,
        "policy_checkpoint_sha256": "2" * 64,
        "policy_config_sha256": "3" * 64,
        "task_set_manifest_sha256": "4" * 64,
        "rollout_census_sha256": "5" * 64,
        "mechanical_failure_census_sha256": (
            "6" * 64
        ),
        (
            "analyzer_formal_"
            "result_manifest_sha256"
        ): "7" * 64,
        "analyzer_metric_report_sha256": (
            "8" * 64
        ),
        "researcher_memory_pack_sha256": (
            memory_sha
        ),
        "historical_f0f1_summary_sha256": (
            "9" * 64
        ),
        "historical_go_nogo_ledger_sha256": (
            "b" * 64
        ),
        (
            "previous_researcher_"
            "decisions_sha256"
        ): None,
        "training_history_sha256": "c" * 64,
        (
            "resource_budget_"
            "manifest_sha256"
        ): "d" * 64,
        (
            "code_config_diff_"
            "manifest_sha256"
        ): "e" * 64,
        "forbidden_future_outcomes_absent": (
            True
        ),
        "sealed_test_details_absent": True,
        "round_evidence_package_sha256": (
            "0" * 64
        ),
    }
    value["round_evidence_package_sha256"] = (
        domain_hash(
            "ROUND_EVIDENCE_PACKAGE_V1",
            value,
            excluded_field=(
                "round_evidence_package_sha256"
            ),
        )
    )
    return value


def _file_sha(
    value: dict[str, object],
) -> str:
    data = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    return hashlib.sha256(data).hexdigest()


def test_round_evidence_self_hash_excludes_self_field(
) -> None:
    memory = _memory()
    value = _round_evidence(
        str(memory["view_sha256"])
    )
    assert (
        round_evidence_semantic_sha256(value)
        == value["round_evidence_package_sha256"]
    )


def test_round_evidence_rejects_hash_with_self_field_included(
) -> None:
    memory = _memory()
    value = _round_evidence(
        str(memory["view_sha256"])
    )
    value["round_evidence_package_sha256"] = (
        domain_hash(
            "ROUND_EVIDENCE_PACKAGE_V1",
            value,
        )
    )
    with pytest.raises(
        ValueError,
        match="self-hash",
    ):
        round_evidence_semantic_sha256(value)


def test_builds_five_lane_role_neutral_input(
) -> None:
    memory = _memory()
    evidence = _round_evidence(
        str(memory["view_sha256"])
    )
    package = (
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                _file_sha(memory)
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )
    )
    payload = package.to_dict()

    assert {
        "current_policy_scorecard",
        "analyzer_evidence",
        "historical_failure_experience",
        "experiment_history",
        "resource_and_cost",
    }.issubset(payload)

    assert (
        payload["role_visibility"][
            (
                "same_visible_evidence_"
                "for_pre_comparison"
            )
        ]
        is True
    )
    assert (
        payload["authority_boundary"][
            (
                "may_assign_benefit_harm_"
                "neutral_uncertain"
            )
        ]
        is False
    )
    assert (
        payload["authority_boundary"][
            "benchmark_per_task_results_visible"
        ]
        is False
    )


def test_input_package_rejects_memory_identity_mismatch(
) -> None:
    memory = _memory()
    evidence = _round_evidence("0" * 64)

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                "b" * 64
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )


def test_evidence_binding_cutoff_is_input_package_identity(
) -> None:
    memory = _memory()
    evidence = _round_evidence(
        str(memory["view_sha256"])
    )
    package = (
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                "b" * 64
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )
    )
    binding = (
        build_human_evidence_binding_candidate_v1(
            package
        )
    )

    assert (
        binding["evidence_cutoff_sha256"]
        == package.input_package_sha256
    )
    assert (
        binding[
            "round_evidence_package_sha256"
        ]
        == package.round_evidence_package_sha256
    )


def test_rejects_benchmark_result_leakage(
) -> None:
    memory = _memory()
    memory["round_evidence"] = {
        (
            "strong_model_benchmark_"
            "per_task_results"
        ): ["forbidden"],
    }

    with pytest.raises(
        ValueError,
        match="future/sealed",
    ):
        build_researcher_round_input_package_v1(
            round_evidence=_round_evidence(
                str(memory["view_sha256"])
            ),
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                "b" * 64
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )


def test_null_round_memory_field_is_bound_by_input_package(
) -> None:
    memory = _memory()
    evidence = _round_evidence(None)
    package = (
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                "b" * 64
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )
    )
    assert (
        package.researcher_memory_binding_mode
        == "ROUND_INPUT_PACKAGE_AUTHORITY"
    )



def test_shared_projection_binds_all_three_common_inputs(
) -> None:
    from pchsi.research_intelligence.round_research_inputs import (
        build_shared_researcher_pre_projection_v1,
    )

    memory = _memory()
    evidence = _round_evidence(
        str(memory["view_sha256"])
    )
    memory_file_sha = _file_sha(memory)
    package = (
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                memory_file_sha
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )
    )

    projection = (
        build_shared_researcher_pre_projection_v1(
            round_evidence=evidence,
            researcher_memory=memory,
            round_research_input=(
                package.to_dict()
            ),
            observed_round_evidence_file_sha256=(
                "a" * 64
            ),
            observed_researcher_memory_file_sha256=(
                memory_file_sha
            ),
        )
    )

    assert projection[
        "round_evidence_package"
    ] == evidence
    assert projection[
        "researcher_memory_view"
    ] == memory
    assert projection[
        "round_research_input_package"
    ] == package.to_dict()
    assert projection[
        "human_pre_visible"
    ] is False
    assert projection[
        "human_pre_hash_visible"
    ] is False


def test_shared_projection_rejects_different_memory_bytes(
) -> None:
    from pchsi.research_intelligence.round_research_inputs import (
        build_shared_researcher_pre_projection_v1,
    )

    memory = _memory()
    evidence = _round_evidence(
        str(memory["view_sha256"])
    )
    package = (
        build_researcher_round_input_package_v1(
            round_evidence=evidence,
            round_evidence_file_sha256=(
                "a" * 64
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=(
                "b" * 64
            ),
            parent_policy_id=(
                "PILOT_DISTILLED_PI1"
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="Memory file mismatch",
    ):
        build_shared_researcher_pre_projection_v1(
            round_evidence=evidence,
            researcher_memory=memory,
            round_research_input=(
                package.to_dict()
            ),
            observed_round_evidence_file_sha256=(
                "a" * 64
            ),
            observed_researcher_memory_file_sha256=(
                "c" * 64
            ),
        )
