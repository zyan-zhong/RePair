"""Deterministic retrieval-key representation for Failure Memory V1.

This module defines only retrieval representation and its safety firewall.
It does not implement lexical, dense, hybrid, ranking, thresholding or abstention.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    LifecycleStatusV1,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    ProjectionRecordBindingV1,
)
from pchsi.memory.semantic_recovery import SemanticAnnotationTypeV1


class RetrievalScoringSafetyFailureCodeV1(str, Enum):
    SOURCE_TASK_IDENTITY_EXPOSURE = "SOURCE_TASK_IDENTITY_EXPOSURE"
    SOURCE_ATTEMPT_IDENTITY_EXPOSURE = "SOURCE_ATTEMPT_IDENTITY_EXPOSURE"
    SOURCE_GAMEFILE_MARKER = "SOURCE_GAMEFILE_MARKER"
    SOURCE_SEED_MARKER = "SOURCE_SEED_MARKER"
    RECOVERY_PROCEDURE_EXPOSURE = "RECOVERY_PROCEDURE_EXPOSURE"
    EFFECT_OR_PROMOTION_MARKER = "EFFECT_OR_PROMOTION_MARKER"
    ACTION_ORACLE_INSTRUCTION = "ACTION_ORACLE_INSTRUCTION"
    ORACLE_PATH_MARKER = "ORACLE_PATH_MARKER"


def _expect_exact_keys(
    value: object,
    expected: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields do not match contract: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _require_text(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be nonempty str")
    if "\x00" in value:
        raise ValueError(f"{name} contains forbidden NUL")
    return value


def _require_string_tuple(
    name: str,
    value: object,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    for item in value:
        _require_text(f"{name} item", item)
    return value


@dataclass(frozen=True, slots=True)
class RetrievalHardFilterMetadataV1:
    access_scope: AccessScopeV1
    lifecycle_status: LifecycleStatusV1

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {"access_scope", "lifecycle_status"}
    )

    def __post_init__(self) -> None:
        if not isinstance(self.access_scope, AccessScopeV1):
            raise TypeError("access_scope type mismatch")
        if not isinstance(self.lifecycle_status, LifecycleStatusV1):
            raise TypeError("lifecycle_status type mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "access_scope": self.access_scope.value,
            "lifecycle_status": self.lifecycle_status.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> "RetrievalHardFilterMetadataV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "retrieval hard-filter metadata",
        )
        return cls(
            access_scope=AccessScopeV1(payload["access_scope"]),
            lifecycle_status=LifecycleStatusV1(
                payload["lifecycle_status"]
            ),
        )


@dataclass(frozen=True, slots=True)
class MemoryRetrievalScoringPayloadV1:
    required_feedback_codes: tuple[str, ...]
    forbidden_feedback_codes: tuple[str, ...]
    recent_action_repetition_signature: tuple[str, ...]
    recent_nonexecuted_attempt_signature: tuple[str, ...]
    visible_state_change_signature: tuple[str, ...]
    required_visible_markers: tuple[str, ...]
    forbidden_visible_markers: tuple[str, ...]
    semantic_retrieval_text: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "required_feedback_codes",
            "forbidden_feedback_codes",
            "recent_action_repetition_signature",
            "recent_nonexecuted_attempt_signature",
            "visible_state_change_signature",
            "required_visible_markers",
            "forbidden_visible_markers",
            "semantic_retrieval_text",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "required_feedback_codes",
            "forbidden_feedback_codes",
            "recent_action_repetition_signature",
            "recent_nonexecuted_attempt_signature",
            "visible_state_change_signature",
            "required_visible_markers",
            "forbidden_visible_markers",
        ):
            _require_string_tuple(name, getattr(self, name))
        _require_text(
            "semantic_retrieval_text",
            self.semantic_retrieval_text,
            allow_empty=True,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "required_feedback_codes": list(
                self.required_feedback_codes
            ),
            "forbidden_feedback_codes": list(
                self.forbidden_feedback_codes
            ),
            "recent_action_repetition_signature": list(
                self.recent_action_repetition_signature
            ),
            "recent_nonexecuted_attempt_signature": list(
                self.recent_nonexecuted_attempt_signature
            ),
            "visible_state_change_signature": list(
                self.visible_state_change_signature
            ),
            "required_visible_markers": list(
                self.required_visible_markers
            ),
            "forbidden_visible_markers": list(
                self.forbidden_visible_markers
            ),
            "semantic_retrieval_text": self.semantic_retrieval_text,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryRetrievalScoringPayloadV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "memory retrieval scoring payload",
        )

        def items(name: str) -> tuple[str, ...]:
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(raw)

        return cls(
            required_feedback_codes=items(
                "required_feedback_codes"
            ),
            forbidden_feedback_codes=items(
                "forbidden_feedback_codes"
            ),
            recent_action_repetition_signature=items(
                "recent_action_repetition_signature"
            ),
            recent_nonexecuted_attempt_signature=items(
                "recent_nonexecuted_attempt_signature"
            ),
            visible_state_change_signature=items(
                "visible_state_change_signature"
            ),
            required_visible_markers=items(
                "required_visible_markers"
            ),
            forbidden_visible_markers=items(
                "forbidden_visible_markers"
            ),
            semantic_retrieval_text=payload[
                "semantic_retrieval_text"
            ],
        )


@dataclass(frozen=True, slots=True)
class MemoryRetrievalKeyV1:
    schema_id: str
    schema_version: int
    record_binding: ProjectionRecordBindingV1
    hard_filter_metadata: RetrievalHardFilterMetadataV1
    scoring_payload: MemoryRetrievalScoringPayloadV1
    scoring_payload_sha256: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "record_binding",
            "hard_filter_metadata",
            "scoring_payload",
            "scoring_payload_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "MEMORY_RETRIEVAL_KEY_V1":
            raise ValueError("schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("schema_version mismatch")
        if not isinstance(
            self.record_binding,
            ProjectionRecordBindingV1,
        ):
            raise TypeError("record_binding type mismatch")
        if not isinstance(
            self.hard_filter_metadata,
            RetrievalHardFilterMetadataV1,
        ):
            raise TypeError("hard_filter_metadata type mismatch")
        if not isinstance(
            self.scoring_payload,
            MemoryRetrievalScoringPayloadV1,
        ):
            raise TypeError("scoring_payload type mismatch")
        require_lower_sha256(
            "scoring_payload_sha256",
            self.scoring_payload_sha256,
        )
        expected = sha256_bytes(
            canonical_json_bytes(self.scoring_payload.to_dict())
        )
        if self.scoring_payload_sha256 != expected:
            raise ValueError("scoring_payload_sha256 mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "record_binding": self.record_binding.to_dict(),
            "hard_filter_metadata": (
                self.hard_filter_metadata.to_dict()
            ),
            "scoring_payload": self.scoring_payload.to_dict(),
            "scoring_payload_sha256": self.scoring_payload_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryRetrievalKeyV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "memory retrieval key",
        )
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            record_binding=ProjectionRecordBindingV1.from_dict(
                payload["record_binding"]
            ),
            hard_filter_metadata=(
                RetrievalHardFilterMetadataV1.from_dict(
                    payload["hard_filter_metadata"]
                )
            ),
            scoring_payload=MemoryRetrievalScoringPayloadV1.from_dict(
                payload["scoring_payload"]
            ),
            scoring_payload_sha256=payload[
                "scoring_payload_sha256"
            ],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "MemoryRetrievalKeyV1":
        return cls.from_dict(strict_json_loads(value))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


_SOURCE_GAMEFILE_RE = re.compile(
    r"\b(?:source[_ -]?gamefile|dataset_relative_gamefile|gamefile\s*=)",
    re.IGNORECASE,
)
_SOURCE_SEED_RE = re.compile(
    r"\b(?:source[_ -]?seed|seed\s*[:=])",
    re.IGNORECASE,
)
_EFFECT_RE = re.compile(
    r"\b(?:effect_status|promotion_status|lifecycle_status|benefit\s*=|harm\s*=)",
    re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"\b(?:execute exactly|the correct action is|output\s*\{\s*"
    r"[\"']action[\"']\s*:)",
    re.IGNORECASE,
)
_ORACLE_RE = re.compile(
    r"\b(?:oracle path|gold path|ground_truth_path|the correct route is)\b",
    re.IGNORECASE,
)


def _string_leaves(value: object):
    if isinstance(value, dict):
        for child in value.values():
            yield from _string_leaves(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _string_leaves(child)
    elif isinstance(value, str):
        yield value


def _unsafe(
    code: RetrievalScoringSafetyFailureCodeV1,
) -> None:
    raise ValueError(
        "RETRIEVAL_SCORING_PAYLOAD_UNSAFE:"
        + code.value
    )


def validate_retrieval_scoring_payload_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    scoring_payload: MemoryRetrievalScoringPayloadV1,
) -> None:
    if not isinstance(record, ProceduralFailureMemoryRecordV1):
        raise TypeError("record type mismatch")
    if not isinstance(
        scoring_payload,
        MemoryRetrievalScoringPayloadV1,
    ):
        raise TypeError("scoring_payload type mismatch")

    leaves = tuple(_string_leaves(scoring_payload.to_dict()))
    joined = "\n".join(leaves)

    for binding in record.provenance.factual_sequence_bindings:
        if binding.source_task_id and binding.source_task_id in joined:
            _unsafe(
                RetrievalScoringSafetyFailureCodeV1
                .SOURCE_TASK_IDENTITY_EXPOSURE
            )
        if (
            binding.source_attempt_id
            and binding.source_attempt_id in joined
        ):
            _unsafe(
                RetrievalScoringSafetyFailureCodeV1
                .SOURCE_ATTEMPT_IDENTITY_EXPOSURE
            )

    if _SOURCE_GAMEFILE_RE.search(joined):
        _unsafe(
            RetrievalScoringSafetyFailureCodeV1
            .SOURCE_GAMEFILE_MARKER
        )
    if _SOURCE_SEED_RE.search(joined):
        _unsafe(
            RetrievalScoringSafetyFailureCodeV1
            .SOURCE_SEED_MARKER
        )
    if _EFFECT_RE.search(joined):
        _unsafe(
            RetrievalScoringSafetyFailureCodeV1
            .EFFECT_OR_PROMOTION_MARKER
        )
    if _ACTION_RE.search(joined):
        _unsafe(
            RetrievalScoringSafetyFailureCodeV1
            .ACTION_ORACLE_INSTRUCTION
        )
    if _ORACLE_RE.search(joined):
        _unsafe(
            RetrievalScoringSafetyFailureCodeV1
            .ORACLE_PATH_MARKER
        )

    semantic_lines = set(
        scoring_payload.semantic_retrieval_text.splitlines()
    )
    for proposal in record.proposed_recoveries:
        for step in proposal.procedure_steps:
            if step in semantic_lines:
                _unsafe(
                    RetrievalScoringSafetyFailureCodeV1
                    .RECOVERY_PROCEDURE_EXPOSURE
                )


def _semantic_retrieval_text_v1(
    record: ProceduralFailureMemoryRecordV1,
) -> str:
    lines: list[str] = []
    lines.extend(
        item.condition_text
        for item in record.applicability.activation
    )
    lines.extend(
        item.condition_text
        for item in record.applicability.continuation
    )
    lines.extend(
        item.condition_text
        for item
        in record.applicability.policy_visible_state_change_trigger
    )

    allowed = {
        SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
        SemanticAnnotationTypeV1.CAPABILITY_COMPONENT,
        SemanticAnnotationTypeV1.CRITICAL_REGION,
    }
    for annotation in record.semantic_hypotheses:
        if annotation.annotation_type in allowed:
            lines.append(
                "SEMANTIC_HYPOTHESIS:"
                + annotation.annotation_type.value
                + ":"
                + annotation.text
            )
    return "\n".join(lines)


def build_memory_retrieval_key_v1(
    record: ProceduralFailureMemoryRecordV1,
) -> MemoryRetrievalKeyV1:
    if not isinstance(record, ProceduralFailureMemoryRecordV1):
        raise TypeError(
            "record must be ProceduralFailureMemoryRecordV1"
        )
    if record.canonical_record_sha256 is None:
        raise ValueError("record lacks canonical_record_sha256")

    binding = ProjectionRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )
    hard_filter = RetrievalHardFilterMetadataV1(
        access_scope=record.governance_state.access_scope,
        lifecycle_status=record.governance_state.lifecycle_status,
    )
    scoring = MemoryRetrievalScoringPayloadV1(
        required_feedback_codes=(),
        forbidden_feedback_codes=(),
        recent_action_repetition_signature=(),
        recent_nonexecuted_attempt_signature=(),
        visible_state_change_signature=(),
        required_visible_markers=(),
        forbidden_visible_markers=(),
        semantic_retrieval_text=_semantic_retrieval_text_v1(
            record
        ),
    )
    validate_retrieval_scoring_payload_v1(
        record=record,
        scoring_payload=scoring,
    )
    scoring_sha = sha256_bytes(
        canonical_json_bytes(scoring.to_dict())
    )
    return MemoryRetrievalKeyV1(
        schema_id="MEMORY_RETRIEVAL_KEY_V1",
        schema_version=1,
        record_binding=binding,
        hard_filter_metadata=hard_filter,
        scoring_payload=scoring,
        scoring_payload_sha256=scoring_sha,
    )
