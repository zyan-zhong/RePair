from __future__ import annotations

import hashlib
import pytest

from pchsi.research_intelligence.benchmark_registry import (
    BenchmarkEntryV1,
    BenchmarkLineageRegistryV1,
    BenchmarkModelStageV1,
    ComparabilityClassV1,
    ModelExecutionProfileV1,
    ProtocolFingerprintV1,
    ResultStatusV1,
    SharedEvaluationProtocolV1,
    required_metric_ids,
)


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def protocol(*, prompt: str = "prompt") -> SharedEvaluationProtocolV1:
    return ProtocolFingerprintV1(
        prompt_contract_sha256=h(prompt),
        history_contract_sha256=h("history"),
        menu_interface_contract_sha256=h("menu"),
        parser_contract_sha256=h("parser"),
        controller_harness_contract_sha256=h("off-off"),
        memory_condition_contract_sha256=h("memory-off"),
        task_panel_sha256=h("panel"),
        action_budget=30,
        model_call_budget=60,
        seed_schedule_sha256=h("seeds"),
        environment_source_sha256=h("env"),
        success_definition_sha256=h("success"),
        interaction_contract_sha256=h("sequential"),
        result_census_contract_sha256=h("complete-census"),
    )


def model(provider: str, name: str) -> ModelExecutionProfileV1:
    return ModelExecutionProfileV1(
        provider=provider,
        requested_model=name,
        returned_model_identity_policy="EXACT_OR_RECORDED",
        endpoint=(
            "/v1/responses"
            if provider == "openai"
            else "/v1/chat/completions"
        ),
        generation_contract_sha256=h(provider + "-generation"),
        tool_policy_sha256=h("no-tools"),
        statefulness_contract_sha256=h("stateless"),
        retry_contract_sha256=h("no-auto-retry"),
        provider_seed_mode=(
            "UNAVAILABLE_RECORDED_NOT_IMPUTED"
            if provider == "openai"
            else "FIXED"
        ),
        max_output_tokens=(32768 if provider == "openai" else 128),
        model_artifact_sha256=(None if provider == "openai" else h(name)),
        tokenizer_sha256=(
            None if provider == "openai" else h(name + "-tokenizer")
        ),
        adapter_sha256=None,
    )


def entry(
    entry_id: str,
    stage: BenchmarkModelStageV1,
    *,
    shared: SharedEvaluationProtocolV1 | None,
    execution: ModelExecutionProfileV1 | None,
    status: ResultStatusV1,
    comparability: ComparabilityClassV1,
) -> BenchmarkEntryV1:
    return BenchmarkEntryV1(
        entry_id=entry_id,
        display_name=entry_id,
        stage=stage,
        comparability=comparability,
        result_status=status,
        checkpoint_identity=entry_id,
        shared_protocol=shared,
        model_execution_profile=execution,
        result_artifact_sha256=(
            h(entry_id) if status is ResultStatusV1.COMPLETE else None
        ),
        source_or_citation="registered-source",
        comparability_note="explicit classification",
    )


def complete_registry() -> BenchmarkLineageRegistryV1:
    shared = protocol()
    return BenchmarkLineageRegistryV1(
        schema_version="BENCHMARK_LINEAGE_REGISTRY_V1",
        primary_protocol_entry_id="pi1",
        entries=(
            entry(
                "pi0",
                BenchmarkModelStageV1.RAW_BASE_PI0,
                shared=shared,
                execution=model("local-vllm", "qwen-pi0"),
                status=ResultStatusV1.COMPLETE,
                comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
            ),
            entry(
                "pi1",
                BenchmarkModelStageV1.PILOT_DISTILLED_PI1,
                shared=shared,
                execution=model("local-vllm", "qwen-pi1"),
                status=ResultStatusV1.COMPLETE,
                comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
            ),
            entry(
                "pi2",
                BenchmarkModelStageV1.PI2_HUMAN_REFERENCE,
                shared=None,
                execution=None,
                status=ResultStatusV1.PENDING,
                comparability=ComparabilityClassV1.PENDING_PROTOCOL_AUDIT,
            ),
            entry(
                "pi-star",
                BenchmarkModelStageV1.PI_STAR_AUTONOMOUS_FINAL,
                shared=None,
                execution=None,
                status=ResultStatusV1.PENDING,
                comparability=ComparabilityClassV1.PENDING_PROTOCOL_AUDIT,
            ),
            entry(
                "gpt-historical",
                BenchmarkModelStageV1.STRONG_MODEL_REFERENCE,
                shared=None,
                execution=None,
                status=(
                    ResultStatusV1.HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT
                ),
                comparability=ComparabilityClassV1.PENDING_PROTOCOL_AUDIT,
            ),
        ),
        registered_metrics=required_metric_ids(),
    )


def test_registry_contains_required_internal_lineage_and_metrics() -> None:
    registry = complete_registry()
    registry.validate()
    stages = {row.stage for row in registry.entries}
    assert BenchmarkModelStageV1.RAW_BASE_PI0 in stages
    assert BenchmarkModelStageV1.PI_STAR_AUTONOMOUS_FINAL in stages
    assert "PLANNER_BENEFITS_PER_BUDGET" in registry.registered_metrics


def test_historical_strong_model_cannot_be_marked_primary_comparable() -> None:
    with pytest.raises(ValueError):
        entry(
            "gpt",
            BenchmarkModelStageV1.STRONG_MODEL_REFERENCE,
            shared=protocol(),
            execution=model("openai", "gpt-5.6-sol"),
            status=(
                ResultStatusV1.HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT
            ),
            comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
        ).validate()


def test_primary_comparable_entries_must_share_exact_protocol() -> None:
    registry = complete_registry()
    entries = list(registry.entries)
    entries[0] = entry(
        "pi0",
        BenchmarkModelStageV1.RAW_BASE_PI0,
        shared=protocol(prompt="different"),
        execution=model("local-vllm", "qwen-pi0"),
        status=ResultStatusV1.COMPLETE,
        comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
    )
    bad = BenchmarkLineageRegistryV1(
        schema_version=registry.schema_version,
        primary_protocol_entry_id=registry.primary_protocol_entry_id,
        entries=tuple(entries),
        registered_metrics=registry.registered_metrics,
    )
    with pytest.raises(ValueError, match="shared protocol"):
        bad.validate()


def test_model_identity_difference_does_not_break_shared_protocol() -> None:
    shared = protocol()
    local = entry(
        "local",
        BenchmarkModelStageV1.PILOT_DISTILLED_PI1,
        shared=shared,
        execution=model("local-vllm", "qwen-pi1"),
        status=ResultStatusV1.COMPLETE,
        comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
    )
    strong = entry(
        "strong",
        BenchmarkModelStageV1.STRONG_MODEL_REFERENCE,
        shared=shared,
        execution=model("openai", "gpt-5.6-sol"),
        status=ResultStatusV1.COMPLETE,
        comparability=ComparabilityClassV1.PRIMARY_COMPARABLE,
    )
    assert (
        local.model_execution_profile.digest()
        != strong.model_execution_profile.digest()
    )
