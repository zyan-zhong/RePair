from __future__ import annotations

from types import SimpleNamespace

import pytest

from pchsi.memory.token_budget_calibration import (
    ANALYZER_AUTHORITY,
    ANALYZER_RESULT_SCHEMA_V1,
    TokenBudgetAnalyzerResultV1,
    build_calibration_fm2_payload_v1,
    build_complete_window_fm1_payload_v1,
)
from pchsi.memory.token_budget_contract import (
    COVERAGE_TARGET_V1,
    LIBRARY_TOTAL_CANDIDATES_V1,
    SINGLE_RECORD_CANDIDATES_V1,
    choose_smallest_ceiling_v1,
    required_coverage_count_v1,
)


def _analyzer(
    *,
    start: int = 1,
    onset: int = 2,
    final: int = 4,
):
    return TokenBudgetAnalyzerResultV1(
        schema_id=ANALYZER_RESULT_SCHEMA_V1,
        schema_version=1,
        failure_id="FM-TB-F00-deadbeefdead",
        status="ANALYZED",
        relevant_start_model_call_index=start,
        failure_onset_model_call_index=onset,
        final_model_call_index=final,
        activation_cues=("visible precondition",),
        failure_pattern="candidate failure mechanism",
        release_cues=("visible state changes",),
        non_applicability_cues=(),
        authority=ANALYZER_AUTHORITY,
        request_id="req-1",
        response_model="gpt-5.6-sol",
        response_sha256="a" * 64,
    )


def _source(call_count: int = 6):
    calls = []
    traces = []
    transitions = []

    for index in range(call_count):
        calls.append(
            SimpleNamespace(
                model_call_index=index,
                observation=f"observation-{index}",
                interface_feedback_before=(
                    None
                    if index == 0
                    else "INVALID_ACTION_V1"
                ),
            )
        )
        traces.append(
            SimpleNamespace(
                model_call_index=index,
                literal_action=f"attempt-{index}",
                normalized_action=f"attempt-{index}",
                submitted_environment_action=(
                    f"attempt-{index}"
                    if index % 2 == 0
                    else None
                ),
                execution_status=SimpleNamespace(
                    value=(
                        "executed"
                        if index % 2 == 0
                        else "not_executed"
                    )
                ),
            )
        )
        if index % 2 == 0:
            transitions.append(
                SimpleNamespace(
                    model_call_index=index,
                    pre_action_observation=(
                        f"observation-{index}"
                    ),
                    resulting_observation=(
                        f"result-{index}"
                    ),
                    pre_action_admissible_commands=(
                        "look",
                    ),
                    resulting_admissible_commands=(
                        "look",
                        "next",
                    ),
                )
            )

    return SimpleNamespace(
        policy_calls=tuple(calls),
        traces=tuple(traces),
        public_transitions=tuple(transitions),
    )


def test_coverage_rule_uses_ceiling_not_sample_max():
    # 27/30 = 90%. Three longer outliers must not force the operating ceiling.
    counts = (
        *(300 for _ in range(10)),
        *(500 for _ in range(17)),
        700,
        720,
        900,
    )
    assert len(counts) == 30
    assert required_coverage_count_v1(30) == 27

    selected = choose_smallest_ceiling_v1(
        observed_token_counts=tuple(counts),
        candidates=SINGLE_RECORD_CANDIDATES_V1,
        coverage_target=COVERAGE_TARGET_V1,
    )
    assert selected == 512


def test_single_candidate_640_handles_current_514_case_when_rule_requires_it():
    counts = (
        *(300 for _ in range(9)),
        *(514 for _ in range(18)),
        700,
        720,
        730,
    )
    assert choose_smallest_ceiling_v1(
        observed_token_counts=tuple(counts),
        candidates=SINGLE_RECORD_CANDIDATES_V1,
        coverage_target=0.90,
    ) == 640


def test_library_candidate_rule_selects_smallest_qualifying_ceiling():
    counts = (
        520,
        530,
        540,
        550,
        560,
        580,
        590,
        700,
        750,
        900,
    )
    assert choose_smallest_ceiling_v1(
        observed_token_counts=counts,
        candidates=LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=0.90,
    ) == 768


def test_no_candidate_is_fail_closed():
    with pytest.raises(ValueError):
        choose_smallest_ceiling_v1(
            observed_token_counts=(5000,) * 30,
            candidates=SINGLE_RECORD_CANDIDATES_V1,
            coverage_target=0.90,
        )


def test_calibration_fm1_is_complete_contiguous_analyzer_window():
    payload = build_complete_window_fm1_payload_v1(
        source=_source(),
        analyzer_result=_analyzer(
            start=1,
            onset=2,
            final=4,
        ),
    )

    assert payload.relevant_start.model_call_index == 1
    assert tuple(
        event.model_call_index
        for event in payload.events
    ) == (1, 2, 3, 4)

    assert tuple(
        event.execution_status
        for event in payload.events
    ) == (
        "not_executed",
        "executed",
        "not_executed",
        "executed",
    )

    assert tuple(
        event.visible_state_change_disposition
        for event in payload.events
    ) == (
        "NONEXECUTED",
        "OBSERVATION_AND_MENU_CHANGED",
        "NONEXECUTED",
        "OBSERVATION_AND_MENU_CHANGED",
    )


def test_calibration_fm2_is_descriptive_and_recovery_empty():
    payload = build_calibration_fm2_payload_v1(
        _analyzer()
    )

    assert payload.activation_cues == (
        "visible precondition",
    )
    assert len(payload.failure_pattern) == 1
    assert (
        payload.failure_pattern[0].authority
        == "SEMANTIC_HYPOTHESIS"
    )
    assert payload.recovery_procedure == ()


def test_analyzer_abstain_carries_no_window_or_semantics():
    result = TokenBudgetAnalyzerResultV1(
        schema_id=ANALYZER_RESULT_SCHEMA_V1,
        schema_version=1,
        failure_id="FM-TB-F00-deadbeefdead",
        status="ABSTAIN",
        relevant_start_model_call_index=None,
        failure_onset_model_call_index=None,
        final_model_call_index=None,
        activation_cues=(),
        failure_pattern="",
        release_cues=(),
        non_applicability_cues=(),
        authority=ANALYZER_AUTHORITY,
        request_id="req-2",
        response_model="gpt-5.6-sol",
        response_sha256="b" * 64,
    )
    assert result.status == "ABSTAIN"
