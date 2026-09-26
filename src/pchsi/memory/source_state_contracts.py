from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    require_nonnegative_int,
    sha256_bytes,
    strict_json_loads,
)


def _exact(value: object, expected: frozenset[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields mismatch: missing={sorted(expected-observed)} "
            f"unknown={sorted(observed-expected)}"
        )
    return value


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{name} must be nonempty NUL-free str")
    return value


def _budget_dict(value: BudgetState) -> dict[str, object]:
    if not isinstance(value, BudgetState):
        raise TypeError("budget_state must be BudgetState")
    return {
        "policy_attempt_count": value.policy_attempt_count,
        "environment_step_count": value.environment_step_count,
        "protocol_failure_count": value.protocol_failure_count,
        "inadmissible_action_count": value.inadmissible_action_count,
        "consecutive_nonexecuted_attempt_count": value.consecutive_nonexecuted_attempt_count,
    }


def _budget_from(value: object) -> BudgetState:
    p = _exact(value, frozenset({
        "policy_attempt_count",
        "environment_step_count",
        "protocol_failure_count",
        "inadmissible_action_count",
        "consecutive_nonexecuted_attempt_count",
    }), "budget state")
    return BudgetState(**p)


def _domain_sha(domain: bytes, payload: object) -> str:
    return sha256_bytes(domain + b"\0" + canonical_json_bytes(payload))


@dataclass(frozen=True, slots=True)
class ReplayTransitionExpectationV1:
    environment_step_index: int
    action: str
    pre_observation_sha256: str
    pre_menu_sequence_sha256: str
    resulting_observation_sha256: str
    resulting_menu_sequence_sha256: str
    score: int | float
    done: bool
    won: bool

    def __post_init__(self) -> None:
        require_nonnegative_int("environment_step_index", self.environment_step_index)
        _text("action", self.action)
        for name in (
            "pre_observation_sha256",
            "pre_menu_sequence_sha256",
            "resulting_observation_sha256",
            "resulting_menu_sequence_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if type(self.score) not in (int, float):
            raise TypeError("score must be int or float")
        if type(self.done) is not bool or type(self.won) is not bool:
            raise TypeError("done/won must be bool")
        if self.won and not self.done:
            raise ValueError("won requires done")

    def to_dict(self) -> dict[str, object]:
        return {
            "environment_step_index": self.environment_step_index,
            "action": self.action,
            "pre_observation_sha256": self.pre_observation_sha256,
            "pre_menu_sequence_sha256": self.pre_menu_sequence_sha256,
            "resulting_observation_sha256": self.resulting_observation_sha256,
            "resulting_menu_sequence_sha256": self.resulting_menu_sequence_sha256,
            "score": self.score,
            "done": self.done,
            "won": self.won,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ReplayTransitionExpectationV1":
        p = _exact(value, frozenset({
            "environment_step_index","action","pre_observation_sha256",
            "pre_menu_sequence_sha256","resulting_observation_sha256",
            "resulting_menu_sequence_sha256","score","done","won",
        }), "replay transition")
        return cls(**p)


@dataclass(frozen=True, slots=True)
class SourceDecisionStateFingerprintV1:
    schema_id: str
    schema_version: int
    source_task_id: str
    source_gamefile_sha256: str
    source_bundle_sha256: str
    source_policy_condition: str
    executed_prefix_sha256: str
    observation_sha256: str
    menu_sequence_sha256: str
    memory_m0_sha256: str
    interface_feedback_code: str | None
    budget_state: BudgetState
    model_call_index: int
    base_policy_input_sha256: str
    fingerprint_sha256: str | None

    _KEYS: ClassVar[frozenset[str]] = frozenset({
        "schema_id","schema_version","source_task_id","source_gamefile_sha256",
        "source_bundle_sha256","source_policy_condition","executed_prefix_sha256",
        "observation_sha256","menu_sequence_sha256","memory_m0_sha256",
        "interface_feedback_code","budget_state","model_call_index",
        "base_policy_input_sha256","fingerprint_sha256",
    })

    def __post_init__(self) -> None:
        if self.schema_id != "SOURCE_DECISION_STATE_FINGERPRINT_V1" or self.schema_version != 1:
            raise ValueError("source fingerprint schema mismatch")
        _text("source_task_id", self.source_task_id)
        _text("source_policy_condition", self.source_policy_condition)
        for name in (
            "source_gamefile_sha256","source_bundle_sha256","executed_prefix_sha256",
            "observation_sha256","menu_sequence_sha256","memory_m0_sha256",
            "base_policy_input_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.interface_feedback_code is not None:
            _text("interface_feedback_code", self.interface_feedback_code)
        _budget_dict(self.budget_state)
        require_nonnegative_int("model_call_index", self.model_call_index)
        expected = _domain_sha(
            b"SOURCE_DECISION_STATE_FINGERPRINT_V1",
            self._payload_without_sha(),
        )
        if self.fingerprint_sha256 is None:
            object.__setattr__(self, "fingerprint_sha256", expected)
        elif self.fingerprint_sha256 != expected:
            raise ValueError("fingerprint_sha256 mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_task_id": self.source_task_id,
            "source_gamefile_sha256": self.source_gamefile_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_policy_condition": self.source_policy_condition,
            "executed_prefix_sha256": self.executed_prefix_sha256,
            "observation_sha256": self.observation_sha256,
            "menu_sequence_sha256": self.menu_sequence_sha256,
            "memory_m0_sha256": self.memory_m0_sha256,
            "interface_feedback_code": self.interface_feedback_code,
            "budget_state": _budget_dict(self.budget_state),
            "model_call_index": self.model_call_index,
            "base_policy_input_sha256": self.base_policy_input_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_sha(), "fingerprint_sha256": self.fingerprint_sha256}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "SourceDecisionStateFingerprintV1":
        p = _exact(value, cls._KEYS, "source fingerprint")
        return cls(
            schema_id=p["schema_id"],
            schema_version=p["schema_version"],
            source_task_id=p["source_task_id"],
            source_gamefile_sha256=p["source_gamefile_sha256"],
            source_bundle_sha256=p["source_bundle_sha256"],
            source_policy_condition=p["source_policy_condition"],
            executed_prefix_sha256=p["executed_prefix_sha256"],
            observation_sha256=p["observation_sha256"],
            menu_sequence_sha256=p["menu_sequence_sha256"],
            memory_m0_sha256=p["memory_m0_sha256"],
            interface_feedback_code=p["interface_feedback_code"],
            budget_state=_budget_from(p["budget_state"]),
            model_call_index=p["model_call_index"],
            base_policy_input_sha256=p["base_policy_input_sha256"],
            fingerprint_sha256=p["fingerprint_sha256"],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "SourceDecisionStateFingerprintV1":
        return cls.from_dict(strict_json_loads(value))


def build_source_decision_state_fingerprint_v1(**kwargs) -> SourceDecisionStateFingerprintV1:
    return SourceDecisionStateFingerprintV1(
        schema_id="SOURCE_DECISION_STATE_FINGERPRINT_V1",
        schema_version=1,
        fingerprint_sha256=None,
        **kwargs,
    )


@dataclass(frozen=True, slots=True)
class RegisteredReplaySourceV1:
    schema_id: str
    schema_version: int
    source_task_id: str
    exact_gamefile: str
    source_gamefile_sha256: str
    source_bundle_sha256: str
    source_policy_condition: str
    runtime_manifest_sha256: str
    executed_prefix_sha256: str
    reset_observation_sha256: str
    reset_menu_sequence_sha256: str
    transitions: tuple[ReplayTransitionExpectationV1, ...]
    memory_m0_sha256: str
    interface_feedback_code: str | None
    budget_state: BudgetState
    model_call_index: int
    base_policy_input_sha256: str
    expected_source_fingerprint: SourceDecisionStateFingerprintV1

    _KEYS: ClassVar[frozenset[str]] = frozenset({
        "schema_id","schema_version","source_task_id","exact_gamefile",
        "source_gamefile_sha256","source_bundle_sha256","source_policy_condition",
        "runtime_manifest_sha256","executed_prefix_sha256","reset_observation_sha256",
        "reset_menu_sequence_sha256","transitions","memory_m0_sha256",
        "interface_feedback_code","budget_state","model_call_index",
        "base_policy_input_sha256","expected_source_fingerprint",
    })

    def __post_init__(self) -> None:
        if self.schema_id != "REGISTERED_SOURCE_STATE_REPLAY_V1" or self.schema_version != 1:
            raise ValueError("registered replay schema mismatch")
        _text("source_task_id", self.source_task_id)
        _text("source_policy_condition", self.source_policy_condition)
        _text("exact_gamefile", self.exact_gamefile)
        if not Path(self.exact_gamefile).is_absolute():
            raise ValueError("exact_gamefile must be absolute")
        for name in (
            "source_gamefile_sha256","source_bundle_sha256","runtime_manifest_sha256",
            "executed_prefix_sha256","reset_observation_sha256",
            "reset_menu_sequence_sha256","memory_m0_sha256","base_policy_input_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.interface_feedback_code is not None:
            _text("interface_feedback_code", self.interface_feedback_code)
        _budget_dict(self.budget_state)
        require_nonnegative_int("model_call_index", self.model_call_index)
        if type(self.transitions) is not tuple:
            raise TypeError("transitions must be tuple")
        if any(not isinstance(x, ReplayTransitionExpectationV1) for x in self.transitions):
            raise TypeError("invalid transition")
        for index, transition in enumerate(self.transitions):
            if transition.environment_step_index != index:
                raise ValueError("environment step indices must be contiguous")
        current_obs = self.reset_observation_sha256
        current_menu = self.reset_menu_sequence_sha256
        for transition in self.transitions:
            if transition.pre_observation_sha256 != current_obs:
                raise ValueError("replay observation chain discontinuity")
            if transition.pre_menu_sequence_sha256 != current_menu:
                raise ValueError("replay menu chain discontinuity")
            current_obs = transition.resulting_observation_sha256
            current_menu = transition.resulting_menu_sequence_sha256
        expected = build_source_decision_state_fingerprint_v1(
            source_task_id=self.source_task_id,
            source_gamefile_sha256=self.source_gamefile_sha256,
            source_bundle_sha256=self.source_bundle_sha256,
            source_policy_condition=self.source_policy_condition,
            executed_prefix_sha256=self.executed_prefix_sha256,
            observation_sha256=current_obs,
            menu_sequence_sha256=current_menu,
            memory_m0_sha256=self.memory_m0_sha256,
            interface_feedback_code=self.interface_feedback_code,
            budget_state=self.budget_state,
            model_call_index=self.model_call_index,
            base_policy_input_sha256=self.base_policy_input_sha256,
        )
        if expected != self.expected_source_fingerprint:
            raise ValueError("expected source fingerprint mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_task_id": self.source_task_id,
            "exact_gamefile": self.exact_gamefile,
            "source_gamefile_sha256": self.source_gamefile_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_policy_condition": self.source_policy_condition,
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
            "executed_prefix_sha256": self.executed_prefix_sha256,
            "reset_observation_sha256": self.reset_observation_sha256,
            "reset_menu_sequence_sha256": self.reset_menu_sequence_sha256,
            "transitions": [x.to_dict() for x in self.transitions],
            "memory_m0_sha256": self.memory_m0_sha256,
            "interface_feedback_code": self.interface_feedback_code,
            "budget_state": _budget_dict(self.budget_state),
            "model_call_index": self.model_call_index,
            "base_policy_input_sha256": self.base_policy_input_sha256,
            "expected_source_fingerprint": self.expected_source_fingerprint.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "RegisteredReplaySourceV1":
        p = _exact(value, cls._KEYS, "registered replay source")
        raw = p["transitions"]
        if not isinstance(raw, list):
            raise TypeError("transitions must be array")
        return cls(
            schema_id=p["schema_id"],
            schema_version=p["schema_version"],
            source_task_id=p["source_task_id"],
            exact_gamefile=p["exact_gamefile"],
            source_gamefile_sha256=p["source_gamefile_sha256"],
            source_bundle_sha256=p["source_bundle_sha256"],
            source_policy_condition=p["source_policy_condition"],
            runtime_manifest_sha256=p["runtime_manifest_sha256"],
            executed_prefix_sha256=p["executed_prefix_sha256"],
            reset_observation_sha256=p["reset_observation_sha256"],
            reset_menu_sequence_sha256=p["reset_menu_sequence_sha256"],
            transitions=tuple(ReplayTransitionExpectationV1.from_dict(x) for x in raw),
            memory_m0_sha256=p["memory_m0_sha256"],
            interface_feedback_code=p["interface_feedback_code"],
            budget_state=_budget_from(p["budget_state"]),
            model_call_index=p["model_call_index"],
            base_policy_input_sha256=p["base_policy_input_sha256"],
            expected_source_fingerprint=SourceDecisionStateFingerprintV1.from_dict(
                p["expected_source_fingerprint"]
            ),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "RegisteredReplaySourceV1":
        return cls.from_dict(strict_json_loads(value))


@dataclass(frozen=True, slots=True)
class SourceStateReplayReportV1:
    schema_id: str
    schema_version: int
    source_fingerprint_sha256: str
    replay_fingerprint_sha256: str
    transition_count: int
    status: str
    failure_code: str | None
    report_sha256: str | None

    def __post_init__(self) -> None:
        if self.schema_id != "SOURCE_STATE_REPLAY_REPORT_V1" or self.schema_version != 1:
            raise ValueError("replay report schema mismatch")
        require_lower_sha256("source_fingerprint_sha256", self.source_fingerprint_sha256)
        require_lower_sha256("replay_fingerprint_sha256", self.replay_fingerprint_sha256)
        require_nonnegative_int("transition_count", self.transition_count)
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("invalid replay report status")
        if (self.status == "PASS") != (self.failure_code is None):
            raise ValueError("failure_code/status mismatch")
        expected = _domain_sha(b"SOURCE_STATE_REPLAY_REPORT_V1", self._payload())
        if self.report_sha256 is None:
            object.__setattr__(self, "report_sha256", expected)
        elif self.report_sha256 != expected:
            raise ValueError("report_sha256 mismatch")

    def _payload(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "replay_fingerprint_sha256": self.replay_fingerprint_sha256,
            "transition_count": self.transition_count,
            "status": self.status,
            "failure_code": self.failure_code,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())
