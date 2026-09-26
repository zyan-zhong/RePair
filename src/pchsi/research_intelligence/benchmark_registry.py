"""Benchmark lineage with shared evaluation protocol separated from model identity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class BenchmarkModelStageV1(str, Enum):
    RAW_BASE_PI0 = "RAW_BASE_PI0"
    PILOT_DISTILLED_PI1 = "PILOT_DISTILLED_PI1"
    PI2_HUMAN_REFERENCE = "PI2_HUMAN_REFERENCE"
    PI_STAR_AUTONOMOUS_FINAL = "PI_STAR_AUTONOMOUS_FINAL"
    RELATED_WORK_REPRODUCED = "RELATED_WORK_REPRODUCED"
    STRONG_MODEL_REFERENCE = "STRONG_MODEL_REFERENCE"


class ComparabilityClassV1(str, Enum):
    PRIMARY_COMPARABLE = "PRIMARY_COMPARABLE"
    SECONDARY_REPRODUCED = "SECONDARY_REPRODUCED"
    CONTEXT_ONLY_INCOMPARABLE = "CONTEXT_ONLY_INCOMPARABLE"
    PENDING_PROTOCOL_AUDIT = "PENDING_PROTOCOL_AUDIT"


class ResultStatusV1(str, Enum):
    COMPLETE = "COMPLETE"
    PENDING = "PENDING"
    HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT = (
        "HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT"
    )
    EXTERNAL_REPORTED_ONLY = "EXTERNAL_REPORTED_ONLY"


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_sha256(value: str, name: str) -> None:
    _require_text(value, name)
    if len(value) != 64 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")


def _optional_sha256(value: str | None, name: str) -> None:
    if value is not None:
        _require_sha256(value, name)


@dataclass(frozen=True)
class SharedEvaluationProtocolV1:
    """Model-independent task/interface/environment comparability contract."""

    prompt_contract_sha256: str
    history_contract_sha256: str
    menu_interface_contract_sha256: str
    parser_contract_sha256: str
    controller_harness_contract_sha256: str
    memory_condition_contract_sha256: str
    task_panel_sha256: str
    action_budget: int
    model_call_budget: int
    seed_schedule_sha256: str
    environment_source_sha256: str
    success_definition_sha256: str
    interaction_contract_sha256: str
    result_census_contract_sha256: str

    def validate(self) -> None:
        for field_name in (
            "prompt_contract_sha256",
            "history_contract_sha256",
            "menu_interface_contract_sha256",
            "parser_contract_sha256",
            "controller_harness_contract_sha256",
            "memory_condition_contract_sha256",
            "task_panel_sha256",
            "seed_schedule_sha256",
            "environment_source_sha256",
            "success_definition_sha256",
            "interaction_contract_sha256",
            "result_census_contract_sha256",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        if type(self.action_budget) is not int or self.action_budget <= 0:
            raise ValueError("action_budget must be a positive int")
        if type(self.model_call_budget) is not int or self.model_call_budget <= 0:
            raise ValueError("model_call_budget must be a positive int")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "prompt_contract_sha256": self.prompt_contract_sha256,
            "history_contract_sha256": self.history_contract_sha256,
            "menu_interface_contract_sha256": (
                self.menu_interface_contract_sha256
            ),
            "parser_contract_sha256": self.parser_contract_sha256,
            "controller_harness_contract_sha256": (
                self.controller_harness_contract_sha256
            ),
            "memory_condition_contract_sha256": (
                self.memory_condition_contract_sha256
            ),
            "task_panel_sha256": self.task_panel_sha256,
            "action_budget": self.action_budget,
            "model_call_budget": self.model_call_budget,
            "seed_schedule_sha256": self.seed_schedule_sha256,
            "environment_source_sha256": self.environment_source_sha256,
            "success_definition_sha256": self.success_definition_sha256,
            "interaction_contract_sha256": self.interaction_contract_sha256,
            "result_census_contract_sha256": (
                self.result_census_contract_sha256
            ),
        }

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def differences(
        self,
        other: "SharedEvaluationProtocolV1",
    ) -> tuple[str, ...]:
        if not isinstance(other, SharedEvaluationProtocolV1):
            raise TypeError("other must be SharedEvaluationProtocolV1")
        left = self.to_dict()
        right = other.to_dict()
        return tuple(key for key in left if left[key] != right[key])


# Compatibility symbol for already-published imports.  Its meaning is corrected:
# it now identifies only the shared evaluation protocol, never model weights.
ProtocolFingerprintV1 = SharedEvaluationProtocolV1


@dataclass(frozen=True)
class ModelExecutionProfileV1:
    """Provider/model execution identity; recorded, but allowed to differ."""

    provider: str
    requested_model: str
    returned_model_identity_policy: str
    endpoint: str
    generation_contract_sha256: str
    tool_policy_sha256: str
    statefulness_contract_sha256: str
    retry_contract_sha256: str
    provider_seed_mode: str
    max_output_tokens: int
    model_artifact_sha256: str | None = None
    tokenizer_sha256: str | None = None
    adapter_sha256: str | None = None

    def validate(self) -> None:
        for field_name in (
            "provider",
            "requested_model",
            "returned_model_identity_policy",
            "endpoint",
            "provider_seed_mode",
        ):
            _require_text(getattr(self, field_name), field_name)
        for field_name in (
            "generation_contract_sha256",
            "tool_policy_sha256",
            "statefulness_contract_sha256",
            "retry_contract_sha256",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        _optional_sha256(
            self.model_artifact_sha256,
            "model_artifact_sha256",
        )
        _optional_sha256(self.tokenizer_sha256, "tokenizer_sha256")
        _optional_sha256(self.adapter_sha256, "adapter_sha256")
        if type(self.max_output_tokens) is not int or self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive int")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "provider": self.provider,
            "requested_model": self.requested_model,
            "returned_model_identity_policy": (
                self.returned_model_identity_policy
            ),
            "endpoint": self.endpoint,
            "generation_contract_sha256": self.generation_contract_sha256,
            "tool_policy_sha256": self.tool_policy_sha256,
            "statefulness_contract_sha256": (
                self.statefulness_contract_sha256
            ),
            "retry_contract_sha256": self.retry_contract_sha256,
            "provider_seed_mode": self.provider_seed_mode,
            "max_output_tokens": self.max_output_tokens,
            "model_artifact_sha256": self.model_artifact_sha256,
            "tokenizer_sha256": self.tokenizer_sha256,
            "adapter_sha256": self.adapter_sha256,
        }

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class BenchmarkEntryV1:
    entry_id: str
    display_name: str
    stage: BenchmarkModelStageV1
    comparability: ComparabilityClassV1
    result_status: ResultStatusV1
    checkpoint_identity: str | None
    shared_protocol: SharedEvaluationProtocolV1 | None
    model_execution_profile: ModelExecutionProfileV1 | None
    result_artifact_sha256: str | None
    source_or_citation: str
    comparability_note: str

    @property
    def protocol_fingerprint(self) -> SharedEvaluationProtocolV1 | None:
        """Compatibility read alias for pre-correction callers."""

        return self.shared_protocol

    def validate(self) -> None:
        for name in (
            "entry_id",
            "display_name",
            "source_or_citation",
            "comparability_note",
        ):
            _require_text(getattr(self, name), name)
        _optional_sha256(
            self.result_artifact_sha256,
            "result_artifact_sha256",
        )
        if self.shared_protocol is not None:
            self.shared_protocol.validate()
        if self.model_execution_profile is not None:
            self.model_execution_profile.validate()
        if self.comparability is ComparabilityClassV1.PRIMARY_COMPARABLE:
            if self.shared_protocol is None:
                raise ValueError(
                    "PRIMARY_COMPARABLE requires shared evaluation protocol"
                )
            if self.model_execution_profile is None:
                raise ValueError(
                    "PRIMARY_COMPARABLE requires model execution profile"
                )
            if self.result_status is not ResultStatusV1.COMPLETE:
                raise ValueError(
                    "PRIMARY_COMPARABLE entry must have COMPLETE result"
                )
        if self.stage is BenchmarkModelStageV1.STRONG_MODEL_REFERENCE:
            if (
                self.result_status
                is ResultStatusV1.HISTORICAL_RESULT_REQUIRES_PROTOCOL_AUDIT
                and self.comparability
                is not ComparabilityClassV1.PENDING_PROTOCOL_AUDIT
            ):
                raise ValueError(
                    "historical strong-model result must remain pending audit"
                )
        if self.stage is BenchmarkModelStageV1.RELATED_WORK_REPRODUCED:
            if (
                self.result_status is ResultStatusV1.EXTERNAL_REPORTED_ONLY
                and self.comparability
                is not ComparabilityClassV1.CONTEXT_ONLY_INCOMPARABLE
            ):
                raise ValueError(
                    "externally reported related-work result is context-only"
                )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "entry_id": self.entry_id,
            "display_name": self.display_name,
            "stage": self.stage.value,
            "comparability": self.comparability.value,
            "result_status": self.result_status.value,
            "checkpoint_identity": self.checkpoint_identity,
            "shared_protocol": (
                None
                if self.shared_protocol is None
                else self.shared_protocol.to_dict()
            ),
            "model_execution_profile": (
                None
                if self.model_execution_profile is None
                else self.model_execution_profile.to_dict()
            ),
            "result_artifact_sha256": self.result_artifact_sha256,
            "source_or_citation": self.source_or_citation,
            "comparability_note": self.comparability_note,
        }


_REQUIRED_INTERNAL_STAGES = {
    BenchmarkModelStageV1.RAW_BASE_PI0,
    BenchmarkModelStageV1.PILOT_DISTILLED_PI1,
    BenchmarkModelStageV1.PI2_HUMAN_REFERENCE,
    BenchmarkModelStageV1.PI_STAR_AUTONOMOUS_FINAL,
}

_REQUIRED_METRICS = {
    "TASK_SUCCESS",
    "TASK_FAMILY_SUCCESS",
    "PROTECTED_SUCCESS_REGRESSION",
    "PAIRED_TASK_LEVEL_INTERVAL",
    "EVRY_REGISTERED_UNIVERSE",
    "BENEFIT_COUNT",
    "HARM_COUNT",
    "NEUTRAL_COUNT",
    "UNCERTAIN_COUNT",
    "PROPOSAL_COVERAGE",
    "BENEFIT_PRECISION",
    "ENV_CALLS_PER_BENEFIT",
    "TOKENS_PER_BENEFIT",
    "COST_PER_BENEFIT",
    "TIME_TO_FIRST_BENEFIT",
    "FAILURE_ONSET_EXACT",
    "FAILURE_ONSET_PLUS_MINUS_ONE",
    "CRITICAL_WINDOW_IOU",
    "EVIDENCE_CITATION_PRECISION",
    "UNSUPPORTED_FACT_RATE",
    "COUNTEREVIDENCE_COVERAGE",
    "ABSTENTION_CALIBRATION",
    "INVALID_ACTION_RATE",
    "NO_EFFECT_RATE",
    "LOOP_REVISIT_RATE",
    "STEPS",
    "TOKENS",
    "LATENCY",
    "PLANNER_BENEFITS_PER_BUDGET",
    "PLANNER_TASK_FAMILY_COVERAGE",
    "PLANNER_DUPLICATE_MECHANISM_RATE",
    "PLANNER_REPEATED_NO_GO_RATE",
    "PLANNER_SINGLE_CHANGE_COMPLIANCE",
    "PLANNER_HUMAN_EDIT_RATE",
}


@dataclass(frozen=True)
class BenchmarkLineageRegistryV1:
    schema_version: str
    primary_protocol_entry_id: str
    entries: tuple[BenchmarkEntryV1, ...]
    registered_metrics: tuple[str, ...]

    def validate(self) -> None:
        if self.schema_version != "BENCHMARK_LINEAGE_REGISTRY_V1":
            raise ValueError("unexpected benchmark registry schema version")
        entry_ids = [entry.entry_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("duplicate benchmark entry_id")
        for entry in self.entries:
            entry.validate()
        entry_map = {entry.entry_id: entry for entry in self.entries}
        if self.primary_protocol_entry_id not in entry_map:
            raise ValueError("primary protocol entry not found")
        primary = entry_map[self.primary_protocol_entry_id]
        if primary.shared_protocol is None:
            raise ValueError("primary protocol entry requires shared protocol")

        observed_stages = {entry.stage for entry in self.entries}
        missing_stages = _REQUIRED_INTERNAL_STAGES - observed_stages
        if missing_stages:
            raise ValueError(
                "missing required internal benchmark stages: "
                + ", ".join(
                    sorted(stage.value for stage in missing_stages)
                )
            )

        for entry in self.entries:
            if entry.comparability is ComparabilityClassV1.PRIMARY_COMPARABLE:
                assert entry.shared_protocol is not None
                differences = primary.shared_protocol.differences(
                    entry.shared_protocol
                )
                if differences:
                    raise ValueError(
                        f"PRIMARY_COMPARABLE entry {entry.entry_id} "
                        f"differs on shared protocol {differences}"
                    )

        metrics = set(self.registered_metrics)
        missing_metrics = _REQUIRED_METRICS - metrics
        if missing_metrics:
            raise ValueError(
                "benchmark metric registry is incomplete: "
                + ", ".join(sorted(missing_metrics))
            )
        if len(self.registered_metrics) != len(metrics):
            raise ValueError("registered_metrics contains duplicates")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "primary_protocol_entry_id": self.primary_protocol_entry_id,
            "entries": [entry.to_dict() for entry in self.entries],
            "registered_metrics": list(self.registered_metrics),
        }


def required_metric_ids() -> tuple[str, ...]:
    return tuple(sorted(_REQUIRED_METRICS))


def freeze_benchmark_registry(
    registry: BenchmarkLineageRegistryV1,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    registry.validate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = output / "BENCHMARK_LINEAGE_REGISTRY_V1.json"
    sidecar = output / "BENCHMARK_LINEAGE_REGISTRY_V1.json.sha256"
    if result.exists() or sidecar.exists():
        raise FileExistsError("benchmark registry output already exists")
    data = _canonical(registry.to_dict())
    digest = hashlib.sha256(data).hexdigest()
    result.write_bytes(data)
    sidecar.write_text(
        f"{digest}  {result.name}\n",
        encoding="utf-8",
    )
    return result, sidecar
