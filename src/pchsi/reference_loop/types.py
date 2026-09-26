"""Internal immutable normalized evidence types."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BudgetCounters:
    policy_attempt_count: int
    environment_step_count: int
    protocol_failure_count: int
    inadmissible_action_count: int
    consecutive_nonexecuted_attempt_count: int

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> "BudgetCounters":
        return cls(
            policy_attempt_count=int(value["policy_attempt_count"]),
            environment_step_count=int(value["environment_step_count"]),
            protocol_failure_count=int(value["protocol_failure_count"]),
            inadmissible_action_count=int(value["inadmissible_action_count"]),
            consecutive_nonexecuted_attempt_count=int(
                value["consecutive_nonexecuted_attempt_count"]
            ),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "policy_attempt_count": self.policy_attempt_count,
            "environment_step_count": self.environment_step_count,
            "protocol_failure_count": self.protocol_failure_count,
            "inadmissible_action_count": self.inadmissible_action_count,
            "consecutive_nonexecuted_attempt_count": (
                self.consecutive_nonexecuted_attempt_count
            ),
        }


@dataclass(frozen=True, slots=True)
class NormalizedPolicyCall:
    model_call_index: int
    environment_step_count_before: int
    provider_request_id: str
    public_task_goal: str
    prompt_text: str
    observation: str
    admissible_commands: tuple[str, ...]
    raw_response_text: str
    executed_history: tuple[tuple[str, str], ...]
    budget_before: BudgetCounters


@dataclass(frozen=True, slots=True)
class NormalizedTrace:
    model_call_index: int
    environment_step_index: int | None
    execution_status: str
    public_task_goal: str
    observation: str
    prompt_text: str
    admissible_commands: tuple[str, ...]
    raw_model_response: str
    literal_action: str
    normalized_action: str | None
    parser_status: str
    parser_error: str | None
    attempt_outcome: str | None
    failure_stage: str | None
    failure_code: str | None
    submitted_environment_action: str | None
    final_executed_action: str | None
    resulting_observation: str | None
    episode_termination_reason: str | None
    budget_before: BudgetCounters
    budget_after: BudgetCounters
    provenance: dict[str, object]


@dataclass(frozen=True, slots=True)
class NormalizedTransition:
    scheduled_cell_id: str
    execution_attempt_id: str
    model_call_index: int
    environment_step_index: int
    submitted_action: str
    pre_observation: str
    pre_menu: tuple[str, ...]
    resulting_observation: str
    resulting_menu: tuple[str, ...]
    done: bool
    won: bool
    score: int | float


@dataclass(frozen=True, slots=True)
class ValidatedAttemptBundle:
    bundle_root: Path
    episode: dict[str, object]
    policy_calls: tuple[NormalizedPolicyCall, ...]
    traces: tuple[NormalizedTrace, ...]
    transitions: tuple[NormalizedTransition, ...]
    source_file_sha256s: tuple[tuple[str, str], ...]
    episode_semantic_sha256: str
    attempt_bundle_sha256: str
    alignment_census: dict[str, int | str | bool]

    @property
    def source_file_sha_map(self) -> dict[str, str]:
        return dict(self.source_file_sha256s)

    @property
    def task_id(self) -> str:
        return str(self.episode["task_id"])

    @property
    def gamefile_sha256(self) -> str:
        return str(self.episode["gamefile_sha256"])

    @property
    def checkpoint_instance_id(self) -> str | None:
        raw = self.episode.get("checkpoint_instance_id")
        return None if raw is None else str(raw)

    @property
    def logical_condition_id(self) -> str | None:
        raw = self.episode.get("logical_condition_id")
        return None if raw is None else str(raw)

    @property
    def access_class(self) -> str | None:
        raw = self.episode.get("access_class")
        return None if raw is None else str(raw)


def jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value
