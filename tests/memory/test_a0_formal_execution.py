from __future__ import annotations

import pytest

from pchsi.memory.a0_formal_execution import (
    A0CellResultV1,
    A0FrozenCellExecutionIdentityV1,
    A0InfrastructureRetryRecordV1,
    A0PromptCensusRecordV1,
)


def _identity():
    return A0FrozenCellExecutionIdentityV1(
        cell_id="1" * 64,
        source_fingerprint_sha256="2" * 64,
        arm_id="M3",
        continuation_seed=17,
        policy_runtime_manifest_sha256="3" * 64,
        decoding_contract_sha256="4" * 64,
        active_snapshot_sha256="5" * 64,
        representation_template_sha256="6" * 64,
    )


def test_prompt_census_forbids_truncation_and_context_overflow():
    value = A0PromptCensusRecordV1(
        cell_id="1" * 64,
        policy_call_index=0,
        raw_prompt_sha256="2" * 64,
        rendered_prompt_sha256="3" * 64,
        rendered_token_ids_sha256="4" * 64,
        prompt_token_count=100,
        max_generation_tokens=128,
        context_window_tokens=4096,
        truncation_applied=False,
        fits_context=True,
    )
    assert value.fits_context is True

    payload = value.to_dict()
    payload["truncation_applied"] = True
    with pytest.raises(ValueError, match="truncation"):
        A0PromptCensusRecordV1(**payload)

    with pytest.raises(ValueError, match="fits_context"):
        A0PromptCensusRecordV1(
            cell_id="1" * 64,
            policy_call_index=0,
            raw_prompt_sha256="2" * 64,
            rendered_prompt_sha256="3" * 64,
            rendered_token_ids_sha256="4" * 64,
            prompt_token_count=4000,
            max_generation_tokens=128,
            context_window_tokens=4096,
            truncation_applied=False,
            fits_context=True,
        )


def test_frozen_cell_identity_is_content_addressed():
    value = _identity()
    assert len(value.execution_identity_sha256) == 64
    payload = value.to_dict()
    payload["execution_identity_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="identity SHA"):
        A0FrozenCellExecutionIdentityV1(**payload)


def test_infrastructure_retry_must_preserve_exact_identity_and_has_no_outcome():
    identity = _identity().execution_identity_sha256
    value = A0InfrastructureRetryRecordV1(
        cell_id="1" * 64,
        original_execution_identity_sha256=identity,
        retry_execution_identity_sha256=identity,
        failure_stage="POLICY_TRANSPORT",
        pre_result_infrastructure_failure=True,
        scientific_outcome_produced=False,
    )
    assert value.scientific_outcome_produced is False

    with pytest.raises(ValueError, match="changed frozen"):
        A0InfrastructureRetryRecordV1(
            cell_id="1" * 64,
            original_execution_identity_sha256=identity,
            retry_execution_identity_sha256="f" * 64,
            failure_stage="POLICY_TRANSPORT",
            pre_result_infrastructure_failure=True,
            scientific_outcome_produced=False,
        )


def test_cell_result_separates_infra_failure_from_scientific_terminal():
    identity = _identity().execution_identity_sha256
    good = A0CellResultV1(
        cell_id="1" * 64,
        source_state_id="2" * 64,
        arm_id="M0",
        continuation_seed=17,
        execution_identity_sha256=identity,
        scientific_outcome_produced=True,
        terminal_success=False,
        evidence_complete=True,
        pre_result_infrastructure_failure=False,
        final_budget_sha256="7" * 64,
        prompt_census_count=2,
        policy_call_count=2,
        environment_step_count_from_source=1,
    )
    assert good.terminal_success is False

    infra = A0CellResultV1(
        cell_id="1" * 64,
        source_state_id="2" * 64,
        arm_id="M0",
        continuation_seed=17,
        execution_identity_sha256=identity,
        scientific_outcome_produced=False,
        terminal_success=None,
        evidence_complete=False,
        pre_result_infrastructure_failure=True,
        final_budget_sha256=None,
        prompt_census_count=0,
        policy_call_count=0,
        environment_step_count_from_source=0,
    )
    assert infra.terminal_success is None
