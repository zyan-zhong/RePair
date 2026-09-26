"""Factual source and registration contracts for Failure Memory V1.

This module covers only Unit-2 Task 1:

- authoritative task-access source binding;
- registered failure-sequence window identity;
- exact source-record pointers.

It does not reconstruct a failure sequence, infer a failure mechanism,
generate recovery guidance, perform retrieval, or execute a policy or
environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .task_access import (
    MemoryTaskAccessClass,
    canonical_task_gamefile_group_id,
)


SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1 = (
    "SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1"
)

REGISTERED_FAILURE_SEQUENCE_WINDOW_V1 = (
    "REGISTERED_FAILURE_SEQUENCE_WINDOW_V1"
)

REGISTERED_BOUNDARY_LABEL = (
    "REGISTERED_BOUNDARY_LABEL"
)

TASK_ACCESS_PROTECTED_MANIFEST_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)

_ALLOWED_SOURCE_RECORD_MEMBERS = frozenset(
    {
        "attempt.json",
        "action_traces.jsonl",
        "policy_calls.jsonl",
        "public_transitions.jsonl",
        "SHA256SUMS",
    }
)


def _require_text(
    name: str,
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be str"
        )

    if not value:
        raise ValueError(
            f"{name} must be non-empty"
        )

    if any(
        character in value
        for character in (
            "\x00",
            "\r",
            "\n",
        )
    ):
        raise ValueError(
            f"{name} contains a forbidden character"
        )

    return value


def _require_lower_sha256(
    name: str,
    value: object,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be str"
        )

    if (
        len(value) != 64
        or any(
            character
            not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"{name} must be a 64-character "
            "lowercase hexadecimal SHA-256"
        )

    return value


def _require_nonnegative_int(
    name: str,
    value: object,
) -> int:
    if type(value) is not int:
        raise TypeError(
            f"{name} must be int"
        )

    if value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )

    return value


def _expect_exact_keys(
    *,
    payload: dict[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    observed = frozenset(
        payload
    )

    if observed == expected:
        return

    missing = sorted(
        expected - observed
    )

    unknown = sorted(
        observed - expected
    )

    raise ValueError(
        f"{label} fields do not match contract: "
        f"missing={missing}, unknown={unknown}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SequenceSourceTaskAccessBindingV1:
    """Bind one source episode to the frozen active Memory-source role."""

    SCHEMA_ID: ClassVar[str] = (
        SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1
    )

    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int

    task_access_protected_manifest_sha256: str

    task_access_record_line_index: int
    task_access_record_sha256: str

    task_gamefile_group_id: str
    dataset_relative_gamefile: str
    gamefile_sha256: str

    task_type: str
    split: str
    access_class: str

    _KEYS: ClassVar[frozenset[str]] = (
        frozenset(
            {
                "schema_id",
                "schema_version",
                (
                    "task_access_protected_"
                    "manifest_sha256"
                ),
                (
                    "task_access_record_"
                    "line_index"
                ),
                (
                    "task_access_record_"
                    "sha256"
                ),
                "task_gamefile_group_id",
                "dataset_relative_gamefile",
                "gamefile_sha256",
                "task_type",
                "split",
                "access_class",
            }
        )
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            self.schema_id
            != self.SCHEMA_ID
        ):
            raise ValueError(
                "schema_id mismatch"
            )

        if (
            type(self.schema_version)
            is not int
        ):
            raise TypeError(
                "schema_version must be int"
            )

        if (
            self.schema_version
            != self.SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version mismatch"
            )

        observed_manifest_sha = (
            _require_lower_sha256(
                (
                    "task_access_protected_"
                    "manifest_sha256"
                ),
                (
                    self
                    .task_access_protected_manifest_sha256
                ),
            )
        )

        if (
            observed_manifest_sha
            != TASK_ACCESS_PROTECTED_MANIFEST_SHA256
        ):
            raise ValueError(
                "task-access protected manifest "
                "authority mismatch"
            )

        _require_nonnegative_int(
            "task_access_record_line_index",
            self.task_access_record_line_index,
        )

        _require_lower_sha256(
            "task_access_record_sha256",
            self.task_access_record_sha256,
        )

        _require_lower_sha256(
            "task_gamefile_group_id",
            self.task_gamefile_group_id,
        )

        _require_lower_sha256(
            "gamefile_sha256",
            self.gamefile_sha256,
        )

        expected_group_id = (
            canonical_task_gamefile_group_id(
                relative_gamefile=(
                    self.dataset_relative_gamefile
                ),
                gamefile_sha256=(
                    self.gamefile_sha256
                ),
            )
        )

        if (
            self.task_gamefile_group_id
            != expected_group_id
        ):
            raise ValueError(
                "task_gamefile_group_id does not "
                "match the frozen task/gamefile "
                "identity derivation"
            )

        _require_text(
            "task_type",
            self.task_type,
        )

        if self.split != "train":
            raise ValueError(
                "active Failure Memory source "
                "must use train split"
            )

        if (
            self.access_class
            != (
                MemoryTaskAccessClass
                .TRAIN_MEMORY_SOURCE
                .value
            )
        ):
            raise ValueError(
                "active Failure Memory source "
                "must be TRAIN_MEMORY_SOURCE"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id":
                self.schema_id,

            "schema_version":
                self.schema_version,

            (
                "task_access_protected_"
                "manifest_sha256"
            ):
                self
                .task_access_protected_manifest_sha256,

            "task_access_record_line_index":
                self.task_access_record_line_index,

            "task_access_record_sha256":
                self.task_access_record_sha256,

            "task_gamefile_group_id":
                self.task_gamefile_group_id,

            "dataset_relative_gamefile":
                self.dataset_relative_gamefile,

            "gamefile_sha256":
                self.gamefile_sha256,

            "task_type":
                self.task_type,

            "split":
                self.split,

            "access_class":
                self.access_class,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "SequenceSourceTaskAccessBindingV1":
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "task-access binding must be "
                "a JSON object"
            )

        if any(
            not isinstance(
                key,
                str,
            )
            for key in value
        ):
            raise TypeError(
                "task-access binding keys "
                "must be strings"
            )

        _expect_exact_keys(
            payload=value,
            expected=cls._KEYS,
            label="task-access binding",
        )

        return cls(
            schema_id=value["schema_id"],
            schema_version=value[
                "schema_version"
            ],
            task_access_protected_manifest_sha256=(
                value[
                    "task_access_protected_"
                    "manifest_sha256"
                ]
            ),
            task_access_record_line_index=(
                value[
                    "task_access_record_"
                    "line_index"
                ]
            ),
            task_access_record_sha256=(
                value[
                    "task_access_record_"
                    "sha256"
                ]
            ),
            task_gamefile_group_id=value[
                "task_gamefile_group_id"
            ],
            dataset_relative_gamefile=value[
                "dataset_relative_gamefile"
            ],
            gamefile_sha256=value[
                "gamefile_sha256"
            ],
            task_type=value["task_type"],
            split=value["split"],
            access_class=value[
                "access_class"
            ],
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SourceRecordPointerV1:
    """Exact pointer from Unit-2 evidence back to one sealed source record."""

    bundle_member_name: str
    zero_based_line_index: int
    exact_record_sha256: str
    whole_member_sha256: str

    _KEYS: ClassVar[frozenset[str]] = (
        frozenset(
            {
                "bundle_member_name",
                "zero_based_line_index",
                "exact_record_sha256",
                "whole_member_sha256",
            }
        )
    )

    def __post_init__(
        self,
    ) -> None:
        member = _require_text(
            "bundle_member_name",
            self.bundle_member_name,
        )

        if (
            member
            not in _ALLOWED_SOURCE_RECORD_MEMBERS
        ):
            raise ValueError(
                "bundle_member_name is not "
                "an authorized attempt-bundle member"
            )

        _require_nonnegative_int(
            "zero_based_line_index",
            self.zero_based_line_index,
        )

        _require_lower_sha256(
            "exact_record_sha256",
            self.exact_record_sha256,
        )

        _require_lower_sha256(
            "whole_member_sha256",
            self.whole_member_sha256,
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "bundle_member_name":
                self.bundle_member_name,

            "zero_based_line_index":
                self.zero_based_line_index,

            "exact_record_sha256":
                self.exact_record_sha256,

            "whole_member_sha256":
                self.whole_member_sha256,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "SourceRecordPointerV1":
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "source-record pointer must "
                "be a JSON object"
            )

        if any(
            not isinstance(
                key,
                str,
            )
            for key in value
        ):
            raise TypeError(
                "source-record pointer keys "
                "must be strings"
            )

        _expect_exact_keys(
            payload=value,
            expected=cls._KEYS,
            label="source-record pointer",
        )

        return cls(
            bundle_member_name=value[
                "bundle_member_name"
            ],
            zero_based_line_index=value[
                "zero_based_line_index"
            ],
            exact_record_sha256=value[
                "exact_record_sha256"
            ],
            whole_member_sha256=value[
                "whole_member_sha256"
            ],
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RegisteredFailureSequenceWindowV1:
    """Externally registered factual range without semantic promotion."""

    SCHEMA_ID: ClassVar[str] = (
        REGISTERED_FAILURE_SEQUENCE_WINDOW_V1
    )

    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int

    registration_id: str

    registration_authority_type: str
    registration_protocol_id: str

    registration_artifact_sha256: str
    registration_record_sha256: str

    source_bundle_sha256: str
    source_attempt_id: str
    source_task_id: str

    source_round: str
    source_condition: str

    relevant_start_model_call_index: int
    registered_failure_onset_model_call_index: int
    final_model_call_index: int

    registered_recovery_start_model_call_index: (
        int | None
    )

    registered_recovery_final_model_call_index: (
        int | None
    )

    _KEYS: ClassVar[frozenset[str]] = (
        frozenset(
            {
                "schema_id",
                "schema_version",
                "registration_id",
                (
                    "registration_"
                    "authority_type"
                ),
                (
                    "registration_"
                    "protocol_id"
                ),
                (
                    "registration_"
                    "artifact_sha256"
                ),
                (
                    "registration_"
                    "record_sha256"
                ),
                "source_bundle_sha256",
                "source_attempt_id",
                "source_task_id",
                "source_round",
                "source_condition",
                (
                    "relevant_start_"
                    "model_call_index"
                ),
                (
                    "registered_failure_onset_"
                    "model_call_index"
                ),
                "final_model_call_index",
                (
                    "registered_recovery_start_"
                    "model_call_index"
                ),
                (
                    "registered_recovery_final_"
                    "model_call_index"
                ),
            }
        )
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            self.schema_id
            != self.SCHEMA_ID
        ):
            raise ValueError(
                "schema_id mismatch"
            )

        if (
            type(self.schema_version)
            is not int
        ):
            raise TypeError(
                "schema_version must be int"
            )

        if (
            self.schema_version
            != self.SCHEMA_VERSION
        ):
            raise ValueError(
                "schema_version mismatch"
            )

        _require_text(
            "registration_id",
            self.registration_id,
        )

        if (
            self.registration_authority_type
            != REGISTERED_BOUNDARY_LABEL
        ):
            raise ValueError(
                "registration authority must be "
                "REGISTERED_BOUNDARY_LABEL"
            )

        _require_text(
            "registration_protocol_id",
            self.registration_protocol_id,
        )

        _require_lower_sha256(
            "registration_artifact_sha256",
            self.registration_artifact_sha256,
        )

        _require_lower_sha256(
            "registration_record_sha256",
            self.registration_record_sha256,
        )

        _require_lower_sha256(
            "source_bundle_sha256",
            self.source_bundle_sha256,
        )

        for name in (
            "source_attempt_id",
            "source_task_id",
            "source_round",
            "source_condition",
        ):
            _require_text(
                name,
                getattr(
                    self,
                    name,
                ),
            )

        relevant_start = (
            _require_nonnegative_int(
                (
                    "relevant_start_"
                    "model_call_index"
                ),
                (
                    self
                    .relevant_start_model_call_index
                ),
            )
        )

        failure_onset = (
            _require_nonnegative_int(
                (
                    "registered_failure_onset_"
                    "model_call_index"
                ),
                (
                    self
                    .registered_failure_onset_model_call_index
                ),
            )
        )

        final_call = (
            _require_nonnegative_int(
                "final_model_call_index",
                self.final_model_call_index,
            )
        )

        if not (
            relevant_start
            <= failure_onset
            <= final_call
        ):
            raise ValueError(
                "registered model-call order "
                "must satisfy relevant_start "
                "<= failure_onset <= final"
            )

        recovery_start = (
            self
            .registered_recovery_start_model_call_index
        )

        recovery_final = (
            self
            .registered_recovery_final_model_call_index
        )

        if (
            recovery_start is None
        ) != (
            recovery_final is None
        ):
            raise ValueError(
                "registered recovery range must "
                "be both null or both non-null"
            )

        if (
            recovery_start is not None
            and recovery_final is not None
        ):
            recovery_start = (
                _require_nonnegative_int(
                    (
                        "registered_recovery_start_"
                        "model_call_index"
                    ),
                    recovery_start,
                )
            )

            recovery_final = (
                _require_nonnegative_int(
                    (
                        "registered_recovery_final_"
                        "model_call_index"
                    ),
                    recovery_final,
                )
            )

            if not (
                failure_onset
                <= recovery_start
                <= recovery_final
                <= final_call
            ):
                raise ValueError(
                    "registered recovery range "
                    "must satisfy failure_onset "
                    "<= recovery_start "
                    "<= recovery_final <= final"
                )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id":
                self.schema_id,

            "schema_version":
                self.schema_version,

            "registration_id":
                self.registration_id,

            "registration_authority_type":
                self.registration_authority_type,

            "registration_protocol_id":
                self.registration_protocol_id,

            "registration_artifact_sha256":
                self.registration_artifact_sha256,

            "registration_record_sha256":
                self.registration_record_sha256,

            "source_bundle_sha256":
                self.source_bundle_sha256,

            "source_attempt_id":
                self.source_attempt_id,

            "source_task_id":
                self.source_task_id,

            "source_round":
                self.source_round,

            "source_condition":
                self.source_condition,

            "relevant_start_model_call_index":
                self.relevant_start_model_call_index,

            (
                "registered_failure_onset_"
                "model_call_index"
            ):
                self
                .registered_failure_onset_model_call_index,

            "final_model_call_index":
                self.final_model_call_index,

            (
                "registered_recovery_start_"
                "model_call_index"
            ):
                self
                .registered_recovery_start_model_call_index,

            (
                "registered_recovery_final_"
                "model_call_index"
            ):
                self
                .registered_recovery_final_model_call_index,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "RegisteredFailureSequenceWindowV1":
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "registered sequence window must "
                "be a JSON object"
            )

        if any(
            not isinstance(
                key,
                str,
            )
            for key in value
        ):
            raise TypeError(
                "registered sequence window keys "
                "must be strings"
            )

        _expect_exact_keys(
            payload=value,
            expected=cls._KEYS,
            label="registered sequence window",
        )

        return cls(
            schema_id=value["schema_id"],
            schema_version=value[
                "schema_version"
            ],
            registration_id=value[
                "registration_id"
            ],
            registration_authority_type=value[
                "registration_authority_type"
            ],
            registration_protocol_id=value[
                "registration_protocol_id"
            ],
            registration_artifact_sha256=value[
                "registration_artifact_sha256"
            ],
            registration_record_sha256=value[
                "registration_record_sha256"
            ],
            source_bundle_sha256=value[
                "source_bundle_sha256"
            ],
            source_attempt_id=value[
                "source_attempt_id"
            ],
            source_task_id=value[
                "source_task_id"
            ],
            source_round=value[
                "source_round"
            ],
            source_condition=value[
                "source_condition"
            ],
            relevant_start_model_call_index=value[
                "relevant_start_model_call_index"
            ],
            registered_failure_onset_model_call_index=(
                value[
                    "registered_failure_onset_"
                    "model_call_index"
                ]
            ),
            final_model_call_index=value[
                "final_model_call_index"
            ],
            registered_recovery_start_model_call_index=(
                value[
                    "registered_recovery_start_"
                    "model_call_index"
                ]
            ),
            registered_recovery_final_model_call_index=(
                value[
                    "registered_recovery_final_"
                    "model_call_index"
                ]
            ),
        )

# ==========================================================================
# Unit 2 / Task 2 — Canonical factual experience wire contract
# ==========================================================================

import hashlib as _hashlib
import math as _math

from pchsi.evaluation.budget import BudgetState as _BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes as _canonical_json_bytes,
    strict_json_loads as _strict_json_loads,
)


_SEQUENCE_FAILURE_EXPERIENCE_V1 = "SEQUENCE_FAILURE_EXPERIENCE_V1"
_VISIBLE_STATE_CHANGE_DISPOSITIONS = frozenset(
    {
        "NONEXECUTED",
        "NO_VISIBLE_STATE_CHANGE",
        "OBSERVATION_CHANGED",
        "MENU_CHANGED",
        "OBSERVATION_AND_MENU_CHANGED",
        "ENVIRONMENT_ERROR",
    }
)
_EPISODE_TERMINAL_DISPOSITIONS = frozenset(
    {
        "INCLUDED_REGISTERED_WINDOW",
        "OUTSIDE_REGISTERED_WINDOW",
    }
)
_SOURCE_BUNDLE_MEMBER_ORDER = (
    "attempt.json",
    "action_traces.jsonl",
    "policy_calls.jsonl",
    "public_transitions.jsonl",
    "SHA256SUMS",
)


def _task2_require_optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _require_text(name, value)


def _task2_require_bool_or_none(name: str, value: object) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool or None")
    return value


def _task2_require_finite_or_none(name: str, value: object) -> int | float | None:
    if value is None:
        return None
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be int, float or None")
    if isinstance(value, float) and not _math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _task2_require_string_tuple(name: str, value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    return tuple(_require_text(f"{name} item", item) for item in value)


def _task2_require_int_tuple(name: str, value: object) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    result = tuple(_require_nonnegative_int(f"{name} item", item) for item in value)
    if tuple(sorted(result)) != result or len(set(result)) != len(result):
        raise ValueError(f"{name} must be strictly increasing and unique")
    return result


def _task2_budget_to_dict(value: _BudgetState | None) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, _BudgetState):
        raise TypeError("budget must be BudgetState or None")
    return {
        "policy_attempt_count": value.policy_attempt_count,
        "environment_step_count": value.environment_step_count,
        "protocol_failure_count": value.protocol_failure_count,
        "inadmissible_action_count": value.inadmissible_action_count,
        "consecutive_nonexecuted_attempt_count": (
            value.consecutive_nonexecuted_attempt_count
        ),
    }


def _task2_budget_from_dict(value: object) -> _BudgetState:
    if not isinstance(value, dict):
        raise TypeError("budget wire value must be object")
    expected = frozenset(
        {
            "policy_attempt_count",
            "environment_step_count",
            "protocol_failure_count",
            "inadmissible_action_count",
            "consecutive_nonexecuted_attempt_count",
        }
    )
    _expect_exact_keys(payload=value, expected=expected, label="budget")
    return _BudgetState(
        policy_attempt_count=value["policy_attempt_count"],
        environment_step_count=value["environment_step_count"],
        protocol_failure_count=value["protocol_failure_count"],
        inadmissible_action_count=value["inadmissible_action_count"],
        consecutive_nonexecuted_attempt_count=(
            value["consecutive_nonexecuted_attempt_count"]
        ),
    )


def _task2_optional_budget_from_dict(value: object) -> _BudgetState | None:
    if value is None:
        return None
    return _task2_budget_from_dict(value)


def _task2_pointer_from_wire(value: object) -> SourceRecordPointerV1:
    return SourceRecordPointerV1.from_dict(value)


def _task2_pointer_to_wire(value: SourceRecordPointerV1 | None) -> object:
    if value is None:
        return None
    if not isinstance(value, SourceRecordPointerV1):
        raise TypeError("source pointer must be SourceRecordPointerV1 or None")
    return value.to_dict()


@dataclass(frozen=True, slots=True)
class SequenceFailureEventV1:
    model_call_index: int
    execution_status: str
    attempt_outcome: str
    parser_status: str
    parser_error: str | None
    literal_action: str
    normalized_action: str | None
    admissibility_status: str
    interface_feedback_before: str | None
    policy_attempt_count_before: int
    policy_attempt_count_after: int
    environment_step_count_before: int
    environment_step_count_after: int
    protocol_failure_count_before: int
    protocol_failure_count_after: int
    inadmissible_action_count_before: int
    inadmissible_action_count_after: int
    consecutive_nonexecuted_attempt_count_before: int
    consecutive_nonexecuted_attempt_count_after: int
    pre_observation: str
    pre_observation_sha256: str
    pre_admissible_commands: tuple[str, ...]
    pre_admissible_commands_sha256: str
    raw_model_response: str
    raw_model_response_sha256: str
    submitted_environment_action: str | None
    resulting_observation: str | None
    resulting_observation_sha256: str | None
    resulting_admissible_commands: tuple[str, ...] | None
    resulting_admissible_commands_sha256: str | None
    environment_step_index: int | None
    score: int | float | None
    done: bool | None
    won: bool | None
    visible_state_change_disposition: str
    trace_source_pointer: SourceRecordPointerV1
    policy_call_source_pointer: SourceRecordPointerV1
    public_transition_source_pointer: SourceRecordPointerV1 | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_call_index",
            "execution_status",
            "attempt_outcome",
            "parser_status",
            "parser_error",
            "literal_action",
            "normalized_action",
            "admissibility_status",
            "interface_feedback_before",
            "policy_attempt_count_before",
            "policy_attempt_count_after",
            "environment_step_count_before",
            "environment_step_count_after",
            "protocol_failure_count_before",
            "protocol_failure_count_after",
            "inadmissible_action_count_before",
            "inadmissible_action_count_after",
            "consecutive_nonexecuted_attempt_count_before",
            "consecutive_nonexecuted_attempt_count_after",
            "pre_observation",
            "pre_observation_sha256",
            "pre_admissible_commands",
            "pre_admissible_commands_sha256",
            "raw_model_response",
            "raw_model_response_sha256",
            "submitted_environment_action",
            "resulting_observation",
            "resulting_observation_sha256",
            "resulting_admissible_commands",
            "resulting_admissible_commands_sha256",
            "environment_step_index",
            "score",
            "done",
            "won",
            "visible_state_change_disposition",
            "trace_source_pointer",
            "policy_call_source_pointer",
            "public_transition_source_pointer",
        }
    )

    def __post_init__(self) -> None:
        _require_nonnegative_int("model_call_index", self.model_call_index)
        for name in (
            "execution_status",
            "attempt_outcome",
            "parser_status",
            "literal_action",
            "admissibility_status",
            "pre_observation",
            "raw_model_response",
        ):
            if name in {"literal_action", "pre_observation", "raw_model_response"}:
                if not isinstance(getattr(self, name), str):
                    raise TypeError(f"{name} must be str")
            else:
                _require_text(name, getattr(self, name))
        _task2_require_optional_text("parser_error", self.parser_error)
        if self.normalized_action is not None and not isinstance(self.normalized_action, str):
            raise TypeError("normalized_action must be str or None")
        _task2_require_optional_text("interface_feedback_before", self.interface_feedback_before)
        for name in (
            "policy_attempt_count_before",
            "policy_attempt_count_after",
            "environment_step_count_before",
            "environment_step_count_after",
            "protocol_failure_count_before",
            "protocol_failure_count_after",
            "inadmissible_action_count_before",
            "inadmissible_action_count_after",
            "consecutive_nonexecuted_attempt_count_before",
            "consecutive_nonexecuted_attempt_count_after",
        ):
            _require_nonnegative_int(name, getattr(self, name))
        if self.policy_attempt_count_after != self.policy_attempt_count_before + 1:
            raise ValueError("policy attempt count must increase by one")
        if self.environment_step_count_after - self.environment_step_count_before not in (0, 1):
            raise ValueError("environment step count delta must be zero or one")
        _require_lower_sha256("pre_observation_sha256", self.pre_observation_sha256)
        _task2_require_string_tuple("pre_admissible_commands", self.pre_admissible_commands)
        _require_lower_sha256(
            "pre_admissible_commands_sha256",
            self.pre_admissible_commands_sha256,
        )
        _require_lower_sha256("raw_model_response_sha256", self.raw_model_response_sha256)
        if self.submitted_environment_action is not None and not isinstance(
            self.submitted_environment_action, str
        ):
            raise TypeError("submitted_environment_action must be str or None")
        if self.resulting_observation is None:
            if self.resulting_observation_sha256 is not None:
                raise ValueError("resulting_observation_sha256 requires resulting_observation")
        else:
            if not isinstance(self.resulting_observation, str):
                raise TypeError("resulting_observation must be str or None")
            _require_lower_sha256(
                "resulting_observation_sha256",
                self.resulting_observation_sha256,
            )
        if self.resulting_admissible_commands is None:
            if self.resulting_admissible_commands_sha256 is not None:
                raise ValueError(
                    "resulting_admissible_commands_sha256 requires resulting_admissible_commands"
                )
        else:
            _task2_require_string_tuple(
                "resulting_admissible_commands",
                self.resulting_admissible_commands,
            )
            _require_lower_sha256(
                "resulting_admissible_commands_sha256",
                self.resulting_admissible_commands_sha256,
            )
        if self.environment_step_index is not None:
            _require_nonnegative_int("environment_step_index", self.environment_step_index)
        _task2_require_finite_or_none("score", self.score)
        _task2_require_bool_or_none("done", self.done)
        _task2_require_bool_or_none("won", self.won)
        if self.visible_state_change_disposition not in _VISIBLE_STATE_CHANGE_DISPOSITIONS:
            raise ValueError("visible_state_change_disposition is invalid")
        if not isinstance(self.trace_source_pointer, SourceRecordPointerV1):
            raise TypeError("trace_source_pointer must be SourceRecordPointerV1")
        if not isinstance(self.policy_call_source_pointer, SourceRecordPointerV1):
            raise TypeError("policy_call_source_pointer must be SourceRecordPointerV1")
        if self.public_transition_source_pointer is not None and not isinstance(
            self.public_transition_source_pointer, SourceRecordPointerV1
        ):
            raise TypeError(
                "public_transition_source_pointer must be SourceRecordPointerV1 or None"
            )
        if self.execution_status == "executed":
            if self.environment_step_index is None:
                raise ValueError("executed event requires environment_step_index")
            if self.public_transition_source_pointer is None:
                raise ValueError("executed event requires public transition pointer")
        elif self.execution_status in {"not_executed", "environment_error"}:
            if self.public_transition_source_pointer is not None:
                raise ValueError("non-public-transition event must not bind public transition")
        else:
            raise ValueError("execution_status is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "model_call_index": self.model_call_index,
            "execution_status": self.execution_status,
            "attempt_outcome": self.attempt_outcome,
            "parser_status": self.parser_status,
            "parser_error": self.parser_error,
            "literal_action": self.literal_action,
            "normalized_action": self.normalized_action,
            "admissibility_status": self.admissibility_status,
            "interface_feedback_before": self.interface_feedback_before,
            "policy_attempt_count_before": self.policy_attempt_count_before,
            "policy_attempt_count_after": self.policy_attempt_count_after,
            "environment_step_count_before": self.environment_step_count_before,
            "environment_step_count_after": self.environment_step_count_after,
            "protocol_failure_count_before": self.protocol_failure_count_before,
            "protocol_failure_count_after": self.protocol_failure_count_after,
            "inadmissible_action_count_before": self.inadmissible_action_count_before,
            "inadmissible_action_count_after": self.inadmissible_action_count_after,
            "consecutive_nonexecuted_attempt_count_before": (
                self.consecutive_nonexecuted_attempt_count_before
            ),
            "consecutive_nonexecuted_attempt_count_after": (
                self.consecutive_nonexecuted_attempt_count_after
            ),
            "pre_observation": self.pre_observation,
            "pre_observation_sha256": self.pre_observation_sha256,
            "pre_admissible_commands": list(self.pre_admissible_commands),
            "pre_admissible_commands_sha256": self.pre_admissible_commands_sha256,
            "raw_model_response": self.raw_model_response,
            "raw_model_response_sha256": self.raw_model_response_sha256,
            "submitted_environment_action": self.submitted_environment_action,
            "resulting_observation": self.resulting_observation,
            "resulting_observation_sha256": self.resulting_observation_sha256,
            "resulting_admissible_commands": (
                None
                if self.resulting_admissible_commands is None
                else list(self.resulting_admissible_commands)
            ),
            "resulting_admissible_commands_sha256": (
                self.resulting_admissible_commands_sha256
            ),
            "environment_step_index": self.environment_step_index,
            "score": self.score,
            "done": self.done,
            "won": self.won,
            "visible_state_change_disposition": self.visible_state_change_disposition,
            "trace_source_pointer": self.trace_source_pointer.to_dict(),
            "policy_call_source_pointer": self.policy_call_source_pointer.to_dict(),
            "public_transition_source_pointer": _task2_pointer_to_wire(
                self.public_transition_source_pointer
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "SequenceFailureEventV1":
        if not isinstance(value, dict):
            raise TypeError("sequence event wire value must be object")
        _expect_exact_keys(payload=value, expected=cls._KEYS, label="sequence event")
        resulting_commands = value["resulting_admissible_commands"]
        return cls(
            model_call_index=value["model_call_index"],
            execution_status=value["execution_status"],
            attempt_outcome=value["attempt_outcome"],
            parser_status=value["parser_status"],
            parser_error=value["parser_error"],
            literal_action=value["literal_action"],
            normalized_action=value["normalized_action"],
            admissibility_status=value["admissibility_status"],
            interface_feedback_before=value["interface_feedback_before"],
            policy_attempt_count_before=value["policy_attempt_count_before"],
            policy_attempt_count_after=value["policy_attempt_count_after"],
            environment_step_count_before=value["environment_step_count_before"],
            environment_step_count_after=value["environment_step_count_after"],
            protocol_failure_count_before=value["protocol_failure_count_before"],
            protocol_failure_count_after=value["protocol_failure_count_after"],
            inadmissible_action_count_before=value["inadmissible_action_count_before"],
            inadmissible_action_count_after=value["inadmissible_action_count_after"],
            consecutive_nonexecuted_attempt_count_before=(
                value["consecutive_nonexecuted_attempt_count_before"]
            ),
            consecutive_nonexecuted_attempt_count_after=(
                value["consecutive_nonexecuted_attempt_count_after"]
            ),
            pre_observation=value["pre_observation"],
            pre_observation_sha256=value["pre_observation_sha256"],
            pre_admissible_commands=tuple(value["pre_admissible_commands"]),
            pre_admissible_commands_sha256=value["pre_admissible_commands_sha256"],
            raw_model_response=value["raw_model_response"],
            raw_model_response_sha256=value["raw_model_response_sha256"],
            submitted_environment_action=value["submitted_environment_action"],
            resulting_observation=value["resulting_observation"],
            resulting_observation_sha256=value["resulting_observation_sha256"],
            resulting_admissible_commands=(
                None if resulting_commands is None else tuple(resulting_commands)
            ),
            resulting_admissible_commands_sha256=(
                value["resulting_admissible_commands_sha256"]
            ),
            environment_step_index=value["environment_step_index"],
            score=value["score"],
            done=value["done"],
            won=value["won"],
            visible_state_change_disposition=value["visible_state_change_disposition"],
            trace_source_pointer=_task2_pointer_from_wire(value["trace_source_pointer"]),
            policy_call_source_pointer=_task2_pointer_from_wire(
                value["policy_call_source_pointer"]
            ),
            public_transition_source_pointer=(
                None
                if value["public_transition_source_pointer"] is None
                else _task2_pointer_from_wire(value["public_transition_source_pointer"])
            ),
        )


@dataclass(frozen=True, slots=True)
class SequenceFailureRelevantStartV1:
    model_call_index: int
    public_task_goal: str
    public_task_goal_sha256: str
    observation: str
    observation_sha256: str
    admissible_commands: tuple[str, ...]
    admissible_commands_sha256: str
    interface_feedback_before: str | None
    budget_state_before: _BudgetState
    required_preceding_model_call_range: tuple[int, ...]
    required_preceding_environment_step_indices: tuple[int, ...]
    required_preceding_prefix_source_binding: tuple[SourceRecordPointerV1, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_call_index",
            "public_task_goal",
            "public_task_goal_sha256",
            "observation",
            "observation_sha256",
            "admissible_commands",
            "admissible_commands_sha256",
            "interface_feedback_before",
            "budget_state_before",
            "required_preceding_model_call_range",
            "required_preceding_environment_step_indices",
            "required_preceding_prefix_source_binding",
        }
    )

    def __post_init__(self) -> None:
        k = _require_nonnegative_int("model_call_index", self.model_call_index)
        if not isinstance(self.public_task_goal, str):
            raise TypeError("public_task_goal must be str")
        _require_lower_sha256("public_task_goal_sha256", self.public_task_goal_sha256)
        if not isinstance(self.observation, str):
            raise TypeError("observation must be str")
        _require_lower_sha256("observation_sha256", self.observation_sha256)
        _task2_require_string_tuple("admissible_commands", self.admissible_commands)
        _require_lower_sha256("admissible_commands_sha256", self.admissible_commands_sha256)
        _task2_require_optional_text("interface_feedback_before", self.interface_feedback_before)
        if not isinstance(self.budget_state_before, _BudgetState):
            raise TypeError("budget_state_before must be BudgetState")
        if type(self.required_preceding_model_call_range) is not tuple:
            raise TypeError("required_preceding_model_call_range must be tuple")
        expected_range = () if k == 0 else (0, k - 1)
        if self.required_preceding_model_call_range != expected_range:
            raise ValueError("required_preceding_model_call_range must cover complete prefix")
        _task2_require_int_tuple(
            "required_preceding_environment_step_indices",
            self.required_preceding_environment_step_indices,
        )
        if any(index >= self.budget_state_before.environment_step_count for index in self.required_preceding_environment_step_indices):
            raise ValueError("preceding environment index exceeds start budget")
        if type(self.required_preceding_prefix_source_binding) is not tuple:
            raise TypeError("required_preceding_prefix_source_binding must be tuple")
        if len(self.required_preceding_prefix_source_binding) != k:
            raise ValueError("preceding prefix source binding must contain one policy-call pointer per prior call")
        for pointer in self.required_preceding_prefix_source_binding:
            if not isinstance(pointer, SourceRecordPointerV1):
                raise TypeError("preceding prefix binding must contain SourceRecordPointerV1")
            if pointer.bundle_member_name != "policy_calls.jsonl":
                raise ValueError("preceding prefix binding must use policy_calls.jsonl")

    def to_dict(self) -> dict[str, object]:
        return {
            "model_call_index": self.model_call_index,
            "public_task_goal": self.public_task_goal,
            "public_task_goal_sha256": self.public_task_goal_sha256,
            "observation": self.observation,
            "observation_sha256": self.observation_sha256,
            "admissible_commands": list(self.admissible_commands),
            "admissible_commands_sha256": self.admissible_commands_sha256,
            "interface_feedback_before": self.interface_feedback_before,
            "budget_state_before": _task2_budget_to_dict(self.budget_state_before),
            "required_preceding_model_call_range": list(
                self.required_preceding_model_call_range
            ),
            "required_preceding_environment_step_indices": list(
                self.required_preceding_environment_step_indices
            ),
            "required_preceding_prefix_source_binding": [
                pointer.to_dict() for pointer in self.required_preceding_prefix_source_binding
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> "SequenceFailureRelevantStartV1":
        if not isinstance(value, dict):
            raise TypeError("relevant-start wire value must be object")
        _expect_exact_keys(payload=value, expected=cls._KEYS, label="relevant start")
        range_value = value["required_preceding_model_call_range"]
        if not isinstance(range_value, list):
            raise TypeError("required_preceding_model_call_range must be JSON array")
        env_value = value["required_preceding_environment_step_indices"]
        if not isinstance(env_value, list):
            raise TypeError("required_preceding_environment_step_indices must be JSON array")
        binding_value = value["required_preceding_prefix_source_binding"]
        if not isinstance(binding_value, list):
            raise TypeError("required_preceding_prefix_source_binding must be JSON array")
        return cls(
            model_call_index=value["model_call_index"],
            public_task_goal=value["public_task_goal"],
            public_task_goal_sha256=value["public_task_goal_sha256"],
            observation=value["observation"],
            observation_sha256=value["observation_sha256"],
            admissible_commands=tuple(value["admissible_commands"]),
            admissible_commands_sha256=value["admissible_commands_sha256"],
            interface_feedback_before=value["interface_feedback_before"],
            budget_state_before=_task2_budget_from_dict(value["budget_state_before"]),
            required_preceding_model_call_range=tuple(range_value),
            required_preceding_environment_step_indices=tuple(env_value),
            required_preceding_prefix_source_binding=tuple(
                SourceRecordPointerV1.from_dict(item) for item in binding_value
            ),
        )


@dataclass(frozen=True, slots=True)
class SequenceFailureObservedEndV1:
    model_call_index: int
    budget_state_after: _BudgetState
    episode_terminal_disposition: str
    termination_reason: str | None
    final_success: bool | None
    final_done: bool | None
    final_won: bool | None
    final_budget: _BudgetState | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_call_index",
            "budget_state_after",
            "episode_terminal_disposition",
            "termination_reason",
            "final_success",
            "final_done",
            "final_won",
            "final_budget",
        }
    )

    def __post_init__(self) -> None:
        _require_nonnegative_int("model_call_index", self.model_call_index)
        if not isinstance(self.budget_state_after, _BudgetState):
            raise TypeError("budget_state_after must be BudgetState")
        if self.episode_terminal_disposition not in _EPISODE_TERMINAL_DISPOSITIONS:
            raise ValueError("episode_terminal_disposition is invalid")
        _task2_require_optional_text("termination_reason", self.termination_reason)
        _task2_require_bool_or_none("final_success", self.final_success)
        _task2_require_bool_or_none("final_done", self.final_done)
        _task2_require_bool_or_none("final_won", self.final_won)
        if self.final_budget is not None and not isinstance(self.final_budget, _BudgetState):
            raise TypeError("final_budget must be BudgetState or None")
        terminal_fields = (
            self.termination_reason,
            self.final_success,
            self.final_done,
            self.final_won,
            self.final_budget,
        )
        if self.episode_terminal_disposition == "OUTSIDE_REGISTERED_WINDOW":
            if any(value is not None for value in terminal_fields):
                raise ValueError("terminal fields must be null outside registered window")
        else:
            if any(value is None for value in terminal_fields):
                raise ValueError("included terminal window requires complete terminal fields")

    def to_dict(self) -> dict[str, object]:
        return {
            "model_call_index": self.model_call_index,
            "budget_state_after": _task2_budget_to_dict(self.budget_state_after),
            "episode_terminal_disposition": self.episode_terminal_disposition,
            "termination_reason": self.termination_reason,
            "final_success": self.final_success,
            "final_done": self.final_done,
            "final_won": self.final_won,
            "final_budget": _task2_budget_to_dict(self.final_budget),
        }

    @classmethod
    def from_dict(cls, value: object) -> "SequenceFailureObservedEndV1":
        if not isinstance(value, dict):
            raise TypeError("observed-end wire value must be object")
        _expect_exact_keys(payload=value, expected=cls._KEYS, label="observed end")
        return cls(
            model_call_index=value["model_call_index"],
            budget_state_after=_task2_budget_from_dict(value["budget_state_after"]),
            episode_terminal_disposition=value["episode_terminal_disposition"],
            termination_reason=value["termination_reason"],
            final_success=value["final_success"],
            final_done=value["final_done"],
            final_won=value["final_won"],
            final_budget=_task2_optional_budget_from_dict(value["final_budget"]),
        )


@dataclass(frozen=True, slots=True)
class SequenceFailureExperienceV1:
    experience_id: str | None
    schema_id: str
    schema_version: int
    source_round: str
    source_condition: str
    source_task_id: str
    source_gamefile_group_id: str
    source_bundle_sha256: str
    source_attempt_id: str
    task_access_binding: SequenceSourceTaskAccessBindingV1
    registration_binding: RegisteredFailureSequenceWindowV1
    relevant_start: SequenceFailureRelevantStartV1
    observed_sequence: tuple[SequenceFailureEventV1, ...]
    observed_end: SequenceFailureObservedEndV1
    included_environment_step_indices: tuple[int, ...]
    source_bundle_member_sha256: tuple[tuple[str, str], ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "experience_id",
            "schema_id",
            "schema_version",
            "source_round",
            "source_condition",
            "source_task_id",
            "source_gamefile_group_id",
            "source_bundle_sha256",
            "source_attempt_id",
            "task_access_binding",
            "registration_binding",
            "relevant_start",
            "observed_sequence",
            "observed_end",
            "included_environment_step_indices",
            "source_bundle_member_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != _SEQUENCE_FAILURE_EXPERIENCE_V1:
            raise ValueError("sequence experience schema_id mismatch")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("sequence experience schema_version mismatch")
        for name in ("source_round", "source_condition", "source_task_id", "source_attempt_id"):
            _require_text(name, getattr(self, name))
        _require_lower_sha256("source_gamefile_group_id", self.source_gamefile_group_id)
        _require_lower_sha256("source_bundle_sha256", self.source_bundle_sha256)
        if not isinstance(self.task_access_binding, SequenceSourceTaskAccessBindingV1):
            raise TypeError("task_access_binding type mismatch")
        if not isinstance(self.registration_binding, RegisteredFailureSequenceWindowV1):
            raise TypeError("registration_binding type mismatch")
        if not isinstance(self.relevant_start, SequenceFailureRelevantStartV1):
            raise TypeError("relevant_start type mismatch")
        if type(self.observed_sequence) is not tuple or not self.observed_sequence:
            raise ValueError("observed_sequence must be a non-empty tuple")
        if any(not isinstance(item, SequenceFailureEventV1) for item in self.observed_sequence):
            raise TypeError("observed_sequence must contain SequenceFailureEventV1")
        observed_calls = tuple(item.model_call_index for item in self.observed_sequence)
        expected_calls = tuple(
            range(
                self.registration_binding.relevant_start_model_call_index,
                self.registration_binding.final_model_call_index + 1,
            )
        )
        if observed_calls != expected_calls:
            raise ValueError("observed_sequence must match exact registered call range")
        if self.relevant_start.model_call_index != observed_calls[0]:
            raise ValueError("relevant_start must equal first observed model call")
        if not isinstance(self.observed_end, SequenceFailureObservedEndV1):
            raise TypeError("observed_end type mismatch")
        if self.observed_end.model_call_index != observed_calls[-1]:
            raise ValueError("observed_end must equal final observed model call")
        _task2_require_int_tuple(
            "included_environment_step_indices",
            self.included_environment_step_indices,
        )
        expected_env_indices = tuple(
            item.environment_step_index
            for item in self.observed_sequence
            if item.environment_step_index is not None
        )
        if self.included_environment_step_indices != expected_env_indices:
            raise ValueError("included_environment_step_indices must derive from observed sequence")
        if type(self.source_bundle_member_sha256) is not tuple:
            raise TypeError("source_bundle_member_sha256 must be tuple")
        observed_names = tuple(name for name, _ in self.source_bundle_member_sha256)
        if observed_names != _SOURCE_BUNDLE_MEMBER_ORDER:
            raise ValueError("source bundle member identities must use frozen order")
        for name, digest in self.source_bundle_member_sha256:
            _require_text("source bundle member name", name)
            _require_lower_sha256("source bundle member sha256", digest)
        if self.source_task_id != self.registration_binding.source_task_id:
            raise ValueError("source task identity mismatch")
        if self.source_attempt_id != self.registration_binding.source_attempt_id:
            raise ValueError("source attempt identity mismatch")
        if self.source_bundle_sha256 != self.registration_binding.source_bundle_sha256:
            raise ValueError("source bundle identity mismatch")
        if self.source_gamefile_group_id != self.task_access_binding.task_gamefile_group_id:
            raise ValueError("source gamefile group identity mismatch")
        computed = self._computed_experience_id()
        if self.experience_id is None:
            object.__setattr__(self, "experience_id", computed)
        else:
            _require_lower_sha256("experience_id", self.experience_id)
            if self.experience_id != computed:
                raise ValueError("experience_id does not match canonical payload")

    def _payload_without_experience_id(self) -> dict[str, object]:
        payload = self.to_dict()
        payload.pop("experience_id")
        return payload

    def _computed_experience_id(self) -> str:
        return _hashlib.sha256(
            _SEQUENCE_FAILURE_EXPERIENCE_V1.encode("utf-8")
            + b"\0"
            + _canonical_json_bytes(self._payload_without_experience_id())
        ).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "experience_id": self.experience_id,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_round": self.source_round,
            "source_condition": self.source_condition,
            "source_task_id": self.source_task_id,
            "source_gamefile_group_id": self.source_gamefile_group_id,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_attempt_id": self.source_attempt_id,
            "task_access_binding": self.task_access_binding.to_dict(),
            "registration_binding": self.registration_binding.to_dict(),
            "relevant_start": self.relevant_start.to_dict(),
            "observed_sequence": [item.to_dict() for item in self.observed_sequence],
            "observed_end": self.observed_end.to_dict(),
            "included_environment_step_indices": list(self.included_environment_step_indices),
            "source_bundle_member_sha256": [
                {"bundle_member_name": name, "sha256": digest}
                for name, digest in self.source_bundle_member_sha256
            ],
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    def to_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @classmethod
    def from_dict(cls, value: object) -> "SequenceFailureExperienceV1":
        if not isinstance(value, dict):
            raise TypeError("sequence experience wire value must be object")
        allowed = cls._KEYS
        observed = frozenset(value)
        if observed not in {allowed, allowed - {"experience_id"}}:
            missing = sorted((allowed - {"experience_id"}) - observed)
            unknown = sorted(observed - allowed)
            raise ValueError(
                f"sequence experience fields do not match contract: missing={missing}, unknown={unknown}"
            )
        sequence = value["observed_sequence"]
        if not isinstance(sequence, list):
            raise TypeError("observed_sequence must be JSON array")
        env_indices = value["included_environment_step_indices"]
        if not isinstance(env_indices, list):
            raise TypeError("included_environment_step_indices must be JSON array")
        members = value["source_bundle_member_sha256"]
        if not isinstance(members, list):
            raise TypeError("source_bundle_member_sha256 must be JSON array")
        member_pairs = []
        for item in members:
            if not isinstance(item, dict) or set(item) != {"bundle_member_name", "sha256"}:
                raise ValueError("source bundle member identity entry invalid")
            member_pairs.append((item["bundle_member_name"], item["sha256"]))
        return cls(
            experience_id=value.get("experience_id"),
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            source_round=value["source_round"],
            source_condition=value["source_condition"],
            source_task_id=value["source_task_id"],
            source_gamefile_group_id=value["source_gamefile_group_id"],
            source_bundle_sha256=value["source_bundle_sha256"],
            source_attempt_id=value["source_attempt_id"],
            task_access_binding=SequenceSourceTaskAccessBindingV1.from_dict(
                value["task_access_binding"]
            ),
            registration_binding=RegisteredFailureSequenceWindowV1.from_dict(
                value["registration_binding"]
            ),
            relevant_start=SequenceFailureRelevantStartV1.from_dict(value["relevant_start"]),
            observed_sequence=tuple(SequenceFailureEventV1.from_dict(item) for item in sequence),
            observed_end=SequenceFailureObservedEndV1.from_dict(value["observed_end"]),
            included_environment_step_indices=tuple(env_indices),
            source_bundle_member_sha256=tuple(member_pairs),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "SequenceFailureExperienceV1":
        return cls.from_dict(_strict_json_loads(value))

# ==========================================================================
# Unit 2 / Task 3 — Source evidence binding
# ==========================================================================

from pchsi.evaluation.action_trace import (
    ActionTrace as _ActionTrace,
)
from pchsi.evaluation.episode_artifact import (
    AttemptBundleBytes as _AttemptBundleBytes,
    build_attempt_bundle_bytes as _build_attempt_bundle_bytes,
)
from pchsi.evaluation.episode_sequence import (
    EpisodeSequenceInput as _EpisodeSequenceInput,
    validate_episode_sequence as _validate_episode_sequence,
)
from pchsi.evaluation.policy_call_evidence import (
    PolicyCallEvidenceV1 as _PolicyCallEvidenceV1,
)
from pchsi.evaluation.schema_models import (
    EpisodeArtifactV1 as _EpisodeArtifactV1,
    PublicTransitionRecordV1 as _PublicTransitionRecordV1,
)
from pchsi.evaluation.canonical_evidence import (
    sha256_bytes as _sha256_bytes,
)


@dataclass(frozen=True, slots=True)
class SequenceSourceEvidenceV1:
    """Immutable Task-3 input bundle; not a scientific output schema."""

    episode_artifact: _EpisodeArtifactV1
    traces: tuple[_ActionTrace, ...]
    policy_calls: tuple[_PolicyCallEvidenceV1, ...]
    public_transitions: tuple[_PublicTransitionRecordV1, ...]
    attempt_bundle: _AttemptBundleBytes
    task_access_record_line_index: int
    task_access_record_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.episode_artifact, _EpisodeArtifactV1):
            raise TypeError("episode_artifact must be EpisodeArtifactV1")
        if type(self.traces) is not tuple or any(
            not isinstance(item, _ActionTrace) for item in self.traces
        ):
            raise TypeError("traces must be tuple[ActionTrace, ...]")
        if type(self.policy_calls) is not tuple or any(
            not isinstance(item, _PolicyCallEvidenceV1) for item in self.policy_calls
        ):
            raise TypeError("policy_calls must be tuple[PolicyCallEvidenceV1, ...]")
        if type(self.public_transitions) is not tuple or any(
            not isinstance(item, _PublicTransitionRecordV1)
            for item in self.public_transitions
        ):
            raise TypeError(
                "public_transitions must be tuple[PublicTransitionRecordV1, ...]"
            )
        if not isinstance(self.attempt_bundle, _AttemptBundleBytes):
            raise TypeError("attempt_bundle must be AttemptBundleBytes")
        _require_nonnegative_int(
            "task_access_record_line_index",
            self.task_access_record_line_index,
        )
        if not isinstance(self.task_access_record_bytes, bytes):
            raise TypeError("task_access_record_bytes must be bytes")
        if not self.task_access_record_bytes.endswith(b"\n"):
            raise ValueError("task-access record bytes must include terminal LF")


def _task3_budget_from_trace_before(trace: _ActionTrace) -> _BudgetState:
    values = (
        trace.policy_attempt_count_before,
        trace.environment_step_count_before,
        trace.protocol_failure_count_before,
        trace.inadmissible_action_count_before,
        trace.consecutive_nonexecuted_attempt_count_before,
    )
    if any(value is None for value in values):
        raise ValueError("trace budget-before fields are incomplete")
    return _BudgetState(
        policy_attempt_count=values[0],
        environment_step_count=values[1],
        protocol_failure_count=values[2],
        inadmissible_action_count=values[3],
        consecutive_nonexecuted_attempt_count=values[4],
    )


def _task3_episode_final_budget(episode: _EpisodeArtifactV1) -> _BudgetState:
    value = episode.final_budget
    return _BudgetState(
        policy_attempt_count=value.policy_attempt_count,
        environment_step_count=value.environment_step_count,
        protocol_failure_count=value.protocol_failure_count,
        inadmissible_action_count=value.inadmissible_action_count,
        consecutive_nonexecuted_attempt_count=(
            value.consecutive_nonexecuted_attempt_count
        ),
    )


def _task3_bundle_member_bytes(
    source: SequenceSourceEvidenceV1,
    bundle_member_name: str,
) -> bytes:
    for name, data in source.attempt_bundle.file_bytes():
        if name == bundle_member_name:
            return data
    raise ValueError(f"unknown source bundle member: {bundle_member_name}")


def source_record_pointer_from_bundle_v1(
    *,
    source: SequenceSourceEvidenceV1,
    bundle_member_name: str,
    zero_based_line_index: int,
) -> SourceRecordPointerV1:
    if not isinstance(source, SequenceSourceEvidenceV1):
        raise TypeError("source must be SequenceSourceEvidenceV1")
    _require_nonnegative_int("zero_based_line_index", zero_based_line_index)
    data = _task3_bundle_member_bytes(source, bundle_member_name)
    if bundle_member_name.endswith(".jsonl"):
        lines = data.splitlines(keepends=True)
        if zero_based_line_index >= len(lines):
            raise ValueError("source-record line index is outside bundle member")
        record = lines[zero_based_line_index]
        if not record.endswith(b"\n"):
            raise ValueError("JSONL source record must include terminal LF")
    else:
        if zero_based_line_index != 0:
            raise ValueError("non-JSONL source member only supports record index 0")
        record = data
    return SourceRecordPointerV1(
        bundle_member_name=bundle_member_name,
        zero_based_line_index=zero_based_line_index,
        exact_record_sha256=_sha256_bytes(record),
        whole_member_sha256=_sha256_bytes(data),
    )


def _task3_validate_policy_trace_pair(
    trace: _ActionTrace,
    policy_call: _PolicyCallEvidenceV1,
) -> None:
    if policy_call.model_call_index != trace.model_call_index:
        raise ValueError("policy-call / trace model-call mismatch")
    if policy_call.public_task_goal != trace.public_task_goal:
        raise ValueError("policy-call / trace task-goal mismatch")
    if policy_call.public_task_goal_sha256 != trace.public_task_goal_sha256:
        raise ValueError("policy-call / trace task-goal hash mismatch")
    if policy_call.observation != trace.observation:
        raise ValueError("policy-call / trace observation mismatch")
    if policy_call.observation_sha256 != trace.observation_sha256:
        raise ValueError("policy-call / trace observation hash mismatch")
    if policy_call.admissible_commands != trace.admissible_commands:
        raise ValueError("policy-call / trace menu mismatch")
    if (
        policy_call.admissible_commands_sequence_sha256
        != trace.admissible_commands_sha256
    ):
        raise ValueError("policy-call / trace menu hash mismatch")
    if policy_call.raw_response_text != trace.raw_model_response:
        raise ValueError("policy-call / trace raw-response mismatch")
    if policy_call.raw_response_text_sha256 != trace.raw_response_sha256:
        raise ValueError("policy-call / trace raw-response hash mismatch")
    if policy_call.prompt_text != trace.prompt_text:
        raise ValueError("policy-call / trace prompt mismatch")
    budget = dict(policy_call.budget_before)
    expected = _task3_budget_from_trace_before(trace)
    if budget != _task2_budget_to_dict(expected):
        raise ValueError("policy-call / trace BudgetState-before mismatch")
    if policy_call.environment_step_count_before != expected.environment_step_count:
        raise ValueError("policy-call environment-step-before mismatch")


def _task3_validate_task_access_record(
    *,
    source: SequenceSourceEvidenceV1,
    binding: SequenceSourceTaskAccessBindingV1,
) -> None:
    if source.task_access_record_line_index != binding.task_access_record_line_index:
        raise ValueError("task-access record line index mismatch")
    if _sha256_bytes(source.task_access_record_bytes) != binding.task_access_record_sha256:
        raise ValueError("task-access record SHA mismatch")
    payload = _strict_json_loads(source.task_access_record_bytes)
    if not isinstance(payload, dict):
        raise ValueError("task-access record must be JSON object")
    expected = {
        "task_gamefile_group_id": binding.task_gamefile_group_id,
        "dataset_relative_gamefile": binding.dataset_relative_gamefile,
        "gamefile_sha256": binding.gamefile_sha256,
        "task_type": binding.task_type,
        "split": binding.split,
        "access_class": binding.access_class,
    }
    for name, expected_value in expected.items():
        if payload.get(name) != expected_value:
            raise ValueError(f"task-access record field mismatch: {name}")


def validate_sequence_source_evidence_v1(
    *,
    source: SequenceSourceEvidenceV1,
    task_access_binding: SequenceSourceTaskAccessBindingV1,
    registration: RegisteredFailureSequenceWindowV1,
) -> SequenceSourceEvidenceV1:
    if not isinstance(source, SequenceSourceEvidenceV1):
        raise TypeError("source must be SequenceSourceEvidenceV1")
    if not isinstance(task_access_binding, SequenceSourceTaskAccessBindingV1):
        raise TypeError("task_access_binding type mismatch")
    if not isinstance(registration, RegisteredFailureSequenceWindowV1):
        raise TypeError("registration type mismatch")

    if source.attempt_bundle.policy_calls_jsonl is None:
        raise ValueError("POLICY_CALL_EVIDENCE_REQUIRED")

    # Whole-episode deterministic validation always precedes slicing.
    _validate_episode_sequence(
        _EpisodeSequenceInput(
            traces=source.traces,
            public_transitions=source.public_transitions,
            final_budget=_task3_episode_final_budget(source.episode_artifact),
            final_success=source.episode_artifact.success,
            final_done=source.episode_artifact.final_done,
            final_won=source.episode_artifact.final_won,
            termination_reason=source.episode_artifact.termination_reason,
        )
    )

    expected_bundle = _build_attempt_bundle_bytes(
        episode_artifact=source.episode_artifact,
        traces=source.traces,
        policy_calls=source.policy_calls,
        public_transitions=source.public_transitions,
    )
    if expected_bundle != source.attempt_bundle:
        raise ValueError("source attempt bundle bytes do not match immutable evidence")
    if registration.source_bundle_sha256 != source.attempt_bundle.attempt_bundle_sha256:
        raise ValueError("registered source bundle identity mismatch")
    if registration.source_attempt_id != source.episode_artifact.execution_attempt_id:
        raise ValueError("registered source attempt identity mismatch")
    if registration.source_task_id != source.episode_artifact.task_id:
        raise ValueError("registered source task identity mismatch")
    if source.episode_artifact.gamefile_sha256 != task_access_binding.gamefile_sha256:
        raise ValueError("episode / task-access gamefile SHA mismatch")
    if source.episode_artifact.task_type != task_access_binding.task_type:
        raise ValueError("episode / task-access task type mismatch")

    _task3_validate_task_access_record(source=source, binding=task_access_binding)

    if len(source.policy_calls) != len(source.traces):
        raise ValueError("policy call count must equal trace count")
    for trace, policy_call in zip(source.traces, source.policy_calls, strict=True):
        _task3_validate_policy_trace_pair(trace, policy_call)

    if not source.traces:
        raise ValueError("source episode has no policy calls")
    final_index = len(source.traces) - 1
    if registration.relevant_start_model_call_index > final_index:
        raise ValueError("registered range starts outside source episode")
    if registration.final_model_call_index > final_index:
        raise ValueError("registered range ends outside source episode")
    expected_calls = tuple(
        range(
            registration.relevant_start_model_call_index,
            registration.final_model_call_index + 1,
        )
    )
    observed_calls = tuple(
        source.traces[index].model_call_index for index in expected_calls
    )
    if observed_calls != expected_calls:
        raise ValueError("registered source call range is noncontiguous")

    # Force exact pointer construction for every source call now, before builder use.
    for index in expected_calls:
        source_record_pointer_from_bundle_v1(
            source=source,
            bundle_member_name="action_traces.jsonl",
            zero_based_line_index=index,
        )
        source_record_pointer_from_bundle_v1(
            source=source,
            bundle_member_name="policy_calls.jsonl",
            zero_based_line_index=index,
        )

    return source

# ==========================================================================
# Unit 2 / Task 4 — Deterministic factual reconstruction
# ==========================================================================


def _task4_trace_budget_after(trace: _ActionTrace) -> _BudgetState:
    values = (
        trace.policy_attempt_count_after,
        trace.environment_step_count_after,
        trace.protocol_failure_count,
        trace.inadmissible_action_count,
        trace.consecutive_nonexecuted_attempt_count,
    )
    if any(value is None for value in values):
        raise ValueError("trace budget-after fields are incomplete")
    return _BudgetState(
        policy_attempt_count=values[0],
        environment_step_count=values[1],
        protocol_failure_count=values[2],
        inadmissible_action_count=values[3],
        consecutive_nonexecuted_attempt_count=values[4],
    )


def _task4_transition_for_trace(
    source: SequenceSourceEvidenceV1,
    trace: _ActionTrace,
) -> tuple[int, _PublicTransitionRecordV1] | None:
    matches = [
        (index, transition)
        for index, transition in enumerate(source.public_transitions)
        if transition.model_call_index == trace.model_call_index
    ]
    if len(matches) > 1:
        raise ValueError("multiple public transitions bind one model call")
    if trace.execution_status.value == "executed":
        if len(matches) != 1:
            raise ValueError("executed trace requires exactly one public transition")
        return matches[0]
    if matches:
        raise ValueError("nonexecuted/environment-error trace cannot bind public transition")
    return None


def _task4_visible_change(
    trace: _ActionTrace,
    transition: _PublicTransitionRecordV1 | None,
) -> str:
    status = trace.execution_status.value
    if status == "not_executed":
        return "NONEXECUTED"
    if status == "environment_error":
        return "ENVIRONMENT_ERROR"
    if transition is None:
        raise ValueError("executed trace is missing public transition")
    observation_changed = transition.resulting_observation != transition.pre_action_observation
    menu_changed = (
        transition.resulting_admissible_commands
        != transition.pre_action_admissible_commands
    )
    if observation_changed and menu_changed:
        return "OBSERVATION_AND_MENU_CHANGED"
    if observation_changed:
        return "OBSERVATION_CHANGED"
    if menu_changed:
        return "MENU_CHANGED"
    return "NO_VISIBLE_STATE_CHANGE"


def _task4_event(
    *,
    source: SequenceSourceEvidenceV1,
    model_call_index: int,
) -> SequenceFailureEventV1:
    trace = source.traces[model_call_index]
    policy_call = source.policy_calls[model_call_index]
    transition_match = _task4_transition_for_trace(source, trace)
    transition_index = None if transition_match is None else transition_match[0]
    transition = None if transition_match is None else transition_match[1]
    if trace.attempt_outcome is None:
        raise ValueError("source trace attempt_outcome is missing")
    if trace.admissibility_status is None:
        raise ValueError("source trace admissibility_status is missing")
    before = _task3_budget_from_trace_before(trace)
    after = _task4_trace_budget_after(trace)
    return SequenceFailureEventV1(
        model_call_index=model_call_index,
        execution_status=trace.execution_status.value,
        attempt_outcome=trace.attempt_outcome,
        parser_status=trace.parser_status,
        parser_error=trace.parser_error,
        literal_action=trace.literal_action,
        normalized_action=trace.normalized_action,
        admissibility_status=trace.admissibility_status,
        interface_feedback_before=policy_call.interface_feedback_before,
        policy_attempt_count_before=before.policy_attempt_count,
        policy_attempt_count_after=after.policy_attempt_count,
        environment_step_count_before=before.environment_step_count,
        environment_step_count_after=after.environment_step_count,
        protocol_failure_count_before=before.protocol_failure_count,
        protocol_failure_count_after=after.protocol_failure_count,
        inadmissible_action_count_before=before.inadmissible_action_count,
        inadmissible_action_count_after=after.inadmissible_action_count,
        consecutive_nonexecuted_attempt_count_before=(
            before.consecutive_nonexecuted_attempt_count
        ),
        consecutive_nonexecuted_attempt_count_after=(
            after.consecutive_nonexecuted_attempt_count
        ),
        pre_observation=trace.observation,
        pre_observation_sha256=trace.observation_sha256,
        pre_admissible_commands=trace.admissible_commands,
        pre_admissible_commands_sha256=trace.admissible_commands_sha256,
        raw_model_response=trace.raw_model_response,
        raw_model_response_sha256=trace.raw_response_sha256,
        submitted_environment_action=trace.submitted_environment_action,
        resulting_observation=(
            None if transition is None else transition.resulting_observation
        ),
        resulting_observation_sha256=(
            None if transition is None else transition.resulting_observation_sha256
        ),
        resulting_admissible_commands=(
            None if transition is None else transition.resulting_admissible_commands
        ),
        resulting_admissible_commands_sha256=(
            None
            if transition is None
            else transition.resulting_admissible_commands_sha256
        ),
        environment_step_index=trace.environment_step_index,
        score=None if transition is None else transition.score,
        done=None if transition is None else transition.done,
        won=None if transition is None else transition.won,
        visible_state_change_disposition=_task4_visible_change(trace, transition),
        trace_source_pointer=source_record_pointer_from_bundle_v1(
            source=source,
            bundle_member_name="action_traces.jsonl",
            zero_based_line_index=model_call_index,
        ),
        policy_call_source_pointer=source_record_pointer_from_bundle_v1(
            source=source,
            bundle_member_name="policy_calls.jsonl",
            zero_based_line_index=model_call_index,
        ),
        public_transition_source_pointer=(
            None
            if transition_index is None
            else source_record_pointer_from_bundle_v1(
                source=source,
                bundle_member_name="public_transitions.jsonl",
                zero_based_line_index=transition_index,
            )
        ),
    )


def build_sequence_failure_experience_v1(
    *,
    source: SequenceSourceEvidenceV1,
    task_access_binding: SequenceSourceTaskAccessBindingV1,
    registration: RegisteredFailureSequenceWindowV1,
) -> SequenceFailureExperienceV1:
    validate_sequence_source_evidence_v1(
        source=source,
        task_access_binding=task_access_binding,
        registration=registration,
    )

    start_index = registration.relevant_start_model_call_index
    final_index = registration.final_model_call_index
    start_trace = source.traces[start_index]
    start_policy_call = source.policy_calls[start_index]
    preceding_env_indices = tuple(
        trace.environment_step_index
        for trace in source.traces[:start_index]
        if trace.environment_step_index is not None
    )
    prefix_pointers = tuple(
        source_record_pointer_from_bundle_v1(
            source=source,
            bundle_member_name="policy_calls.jsonl",
            zero_based_line_index=index,
        )
        for index in range(start_index)
    )
    relevant_start = SequenceFailureRelevantStartV1(
        model_call_index=start_index,
        public_task_goal=start_policy_call.public_task_goal,
        public_task_goal_sha256=start_policy_call.public_task_goal_sha256,
        observation=start_policy_call.observation,
        observation_sha256=start_policy_call.observation_sha256,
        admissible_commands=start_policy_call.admissible_commands,
        admissible_commands_sha256=(
            start_policy_call.admissible_commands_sequence_sha256
        ),
        interface_feedback_before=start_policy_call.interface_feedback_before,
        budget_state_before=_task3_budget_from_trace_before(start_trace),
        required_preceding_model_call_range=(
            () if start_index == 0 else (0, start_index - 1)
        ),
        required_preceding_environment_step_indices=preceding_env_indices,
        required_preceding_prefix_source_binding=prefix_pointers,
    )
    events = tuple(
        _task4_event(source=source, model_call_index=index)
        for index in range(start_index, final_index + 1)
    )
    final_trace = source.traces[final_index]
    local_budget_after = _task4_trace_budget_after(final_trace)
    reaches_terminal = final_index == len(source.traces) - 1
    if reaches_terminal:
        observed_end = SequenceFailureObservedEndV1(
            model_call_index=final_index,
            budget_state_after=local_budget_after,
            episode_terminal_disposition="INCLUDED_REGISTERED_WINDOW",
            termination_reason=source.episode_artifact.termination_reason,
            final_success=source.episode_artifact.success,
            final_done=source.episode_artifact.final_done,
            final_won=source.episode_artifact.final_won,
            final_budget=_task3_episode_final_budget(source.episode_artifact),
        )
    else:
        observed_end = SequenceFailureObservedEndV1(
            model_call_index=final_index,
            budget_state_after=local_budget_after,
            episode_terminal_disposition="OUTSIDE_REGISTERED_WINDOW",
            termination_reason=None,
            final_success=None,
            final_done=None,
            final_won=None,
            final_budget=None,
        )
    member_hashes = tuple(
        (name, _sha256_bytes(data))
        for name, data in source.attempt_bundle.file_bytes()
    )
    return SequenceFailureExperienceV1(
        experience_id=None,
        schema_id=_SEQUENCE_FAILURE_EXPERIENCE_V1,
        schema_version=1,
        source_round=registration.source_round,
        source_condition=registration.source_condition,
        source_task_id=registration.source_task_id,
        source_gamefile_group_id=task_access_binding.task_gamefile_group_id,
        source_bundle_sha256=registration.source_bundle_sha256,
        source_attempt_id=registration.source_attempt_id,
        task_access_binding=task_access_binding,
        registration_binding=registration,
        relevant_start=relevant_start,
        observed_sequence=events,
        observed_end=observed_end,
        included_environment_step_indices=tuple(
            event.environment_step_index
            for event in events
            if event.environment_step_index is not None
        ),
        source_bundle_member_sha256=member_hashes,
    )
