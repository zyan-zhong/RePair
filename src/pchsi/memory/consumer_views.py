"""Role-specific, leakage-safe views over governed Failure Memory.

The same immutable Memory library serves three different consumers:

* Task Policy: at most one strictly gated Policy-safe projection.
* Hierarchical Analyzer: bounded historical candidates, explicitly typed as
  evidence/hypothesis/proposal, with no direct action or causal authority.
* Training Researcher: train-side governed records plus round-level evidence;
  held-out evaluation is aggregate-only.

This module never calls a model, environment, network service, trainer, or
benchmark. It only materializes deterministic views from frozen evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
from typing import Mapping, Sequence

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
)
from pchsi.memory.applicability_gate import (
    DirectApplicabilityDispositionV1,
    evaluate_direct_applicability_v1,
)
from pchsi.memory.dev_snapshot_loader import (
    FM2AvailabilityV1,
    LoadedDevSnapshotMemberV2,
    LoadedDevSnapshotV2,
)
from pchsi.memory.formal_b_retrieval import (
    FormalBRetrieverConfigV1,
    jaccard_score_v1,
)
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    EvaluationContaminationStatusV1,
    LifecycleStatusV1,
)
from pchsi.memory.projection_common import ProjectionBuildDispositionV1


def _sha_domain(domain: str, value: object) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(value)
    ).hexdigest()


def _require_sha(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be 64 lowercase hex")
    return value


def _require_text(
    name: str,
    value: object,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be nonempty")
    if "\x00" in value:
        raise ValueError(f"{name} contains NUL")
    return value


class MemoryConsumerRoleV1(str, Enum):
    TASK_POLICY = "TASK_POLICY"
    HIERARCHICAL_ANALYZER = "HIERARCHICAL_ANALYZER"
    TRAINING_RESEARCHER = "TRAINING_RESEARCHER"


class ResearcherPurposeV1(str, Enum):
    TRAINING_DATA_BUILD = "TRAINING_DATA_BUILD"
    ROUND_RESEARCH_PLANNING = "ROUND_RESEARCH_PLANNING"
    POLICY_EVALUATION_REVIEW = "POLICY_EVALUATION_REVIEW"


class MemorySourcePartitionV1(str, Enum):
    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"
    TRAIN_RETRIEVAL_DEV = "TRAIN_RETRIEVAL_DEV"
    VALID_SEEN = "VALID_SEEN"
    VALID_UNSEEN = "VALID_UNSEEN"
    FORMAL_EVALUATION = "FORMAL_EVALUATION"


class MemoryPartitionAuthorityScopeV1(str, Enum):
    ACCESS_DIAGNOSTIC_ONLY = "ACCESS_DIAGNOSTIC_ONLY"
    FULL_TRAIN_SOURCE_PROVENANCE = "FULL_TRAIN_SOURCE_PROVENANCE"


@dataclass(frozen=True, slots=True)
class MemorySourcePartitionBindingV1:
    memory_lineage_id: str
    source_partition: MemorySourcePartitionV1
    partition_authority_sha256: str
    authority_scope: MemoryPartitionAuthorityScopeV1 = (
        MemoryPartitionAuthorityScopeV1.ACCESS_DIAGNOSTIC_ONLY
    )
    source_collection_manifest_sha256: str | None = None
    task_access_authority_sha256: str | None = None
    record_provenance_authority_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("memory_lineage_id", self.memory_lineage_id)
        if not isinstance(self.source_partition, MemorySourcePartitionV1):
            raise TypeError("source_partition type mismatch")
        _require_sha("partition_authority_sha256", self.partition_authority_sha256)
        if not isinstance(self.authority_scope, MemoryPartitionAuthorityScopeV1):
            raise TypeError("authority_scope type mismatch")
        fields = (
            self.source_collection_manifest_sha256,
            self.task_access_authority_sha256,
            self.record_provenance_authority_sha256,
        )
        present = tuple(value is not None for value in fields)
        if any(present) and not all(present):
            raise ValueError("source-partition provenance fields must be supplied together")
        if self.authority_scope is MemoryPartitionAuthorityScopeV1.ACCESS_DIAGNOSTIC_ONLY:
            if any(present):
                raise ValueError("diagnostic-only binding cannot claim full provenance")
        else:
            if not all(present):
                raise ValueError("full train-source provenance requires all authority SHAs")
            for name, value in (
                ("source_collection_manifest_sha256", self.source_collection_manifest_sha256),
                ("task_access_authority_sha256", self.task_access_authority_sha256),
                ("record_provenance_authority_sha256", self.record_provenance_authority_sha256),
            ):
                _require_sha(name, value)
            expected = _sha_domain(
                "MEMORY_SOURCE_PARTITION_AUTHORITY_V1",
                {
                    "memory_lineage_id": self.memory_lineage_id,
                    "source_partition": self.source_partition.value,
                    "source_collection_manifest_sha256": self.source_collection_manifest_sha256,
                    "task_access_authority_sha256": self.task_access_authority_sha256,
                    "record_provenance_authority_sha256": self.record_provenance_authority_sha256,
                },
            )
            if self.partition_authority_sha256 != expected:
                raise ValueError("full source-partition authority SHA mismatch")

    @classmethod
    def full_train_source_provenance(
        cls,
        *,
        memory_lineage_id: str,
        source_collection_manifest_sha256: str,
        task_access_authority_sha256: str,
        record_provenance_authority_sha256: str,
    ) -> "MemorySourcePartitionBindingV1":
        payload = {
            "memory_lineage_id": memory_lineage_id,
            "source_partition": MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE.value,
            "source_collection_manifest_sha256": source_collection_manifest_sha256,
            "task_access_authority_sha256": task_access_authority_sha256,
            "record_provenance_authority_sha256": record_provenance_authority_sha256,
        }
        return cls(
            memory_lineage_id=memory_lineage_id,
            source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
            partition_authority_sha256=_sha_domain(
                "MEMORY_SOURCE_PARTITION_AUTHORITY_V1", payload
            ),
            authority_scope=MemoryPartitionAuthorityScopeV1.FULL_TRAIN_SOURCE_PROVENANCE,
            source_collection_manifest_sha256=source_collection_manifest_sha256,
            task_access_authority_sha256=task_access_authority_sha256,
            record_provenance_authority_sha256=record_provenance_authority_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_lineage_id": self.memory_lineage_id,
            "source_partition": self.source_partition.value,
            "partition_authority_sha256": self.partition_authority_sha256,
            "authority_scope": self.authority_scope.value,
            "source_collection_manifest_sha256": self.source_collection_manifest_sha256,
            "task_access_authority_sha256": self.task_access_authority_sha256,
            "record_provenance_authority_sha256": self.record_provenance_authority_sha256,
        }


class PolicyMemoryDecisionReasonV1(str, Enum):
    EXPOSE_APPLICABLE = "EXPOSE_APPLICABLE"
    NO_CANDIDATES = "NO_CANDIDATES"
    TOP_SCORE_TIE = "TOP_SCORE_TIE"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    GATE_NOT_APPLICABLE = "GATE_NOT_APPLICABLE"
    GATE_CONFLICTING = "GATE_CONFLICTING"
    GATE_UNCERTAIN = "GATE_UNCERTAIN"
    POLICY_PROJECTION_UNAVAILABLE = "POLICY_PROJECTION_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class MemoryConsumerQueryV1:
    observation: str
    executed_transitions: tuple[ExecutedTransition, ...]
    admissible_commands: tuple[str, ...]
    interface_feedback: InterfaceFeedbackCode | None
    public_task_goal: str

    def __post_init__(self) -> None:
        _require_text("observation", self.observation, allow_empty=True)
        _require_text(
            "public_task_goal",
            self.public_task_goal,
            allow_empty=True,
        )
        if type(self.executed_transitions) is not tuple:
            raise TypeError("executed_transitions must be tuple")
        for item in self.executed_transitions:
            if not isinstance(item, ExecutedTransition):
                raise TypeError("executed transition type mismatch")
        if type(self.admissible_commands) is not tuple:
            raise TypeError("admissible_commands must be tuple")
        for command in self.admissible_commands:
            _require_text(
                "admissible command",
                command,
                allow_empty=True,
            )
        if (
            self.interface_feedback is not None
            and not isinstance(
                self.interface_feedback,
                InterfaceFeedbackCode,
            )
        ):
            raise TypeError("interface_feedback type mismatch")

    def scoring_text(self) -> str:
        lines = [self.observation]
        for item in self.executed_transitions[-8:]:
            lines.append(item.action)
            lines.append(item.resulting_observation)
        if (
            self.interface_feedback
            is InterfaceFeedbackCode.FORMAT_ERROR_V1
        ):
            lines.append(FORMAT_ERROR_V1)
        elif (
            self.interface_feedback
            is InterfaceFeedbackCode.INVALID_ACTION_V1
        ):
            lines.append(INVALID_ACTION_V1)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation,
            "executed_transitions": [
                {
                    "action": item.action,
                    "resulting_observation": (
                        item.resulting_observation
                    ),
                }
                for item in self.executed_transitions
            ],
            "admissible_commands": list(self.admissible_commands),
            "interface_feedback": (
                None
                if self.interface_feedback is None
                else self.interface_feedback.value
            ),
            "public_task_goal": self.public_task_goal,
        }


@dataclass(frozen=True, slots=True)
class PolicyMemoryViewV1:
    snapshot_sha256: str
    selected_config_sha256: str
    selected_threshold_pct: int
    decision_reason: PolicyMemoryDecisionReasonV1
    selected_memory_lineage_id: str | None
    projection_artifact_sha256: str | None
    score_numerator: int
    score_denominator: int
    prompt_payload: dict[str, object] | None
    view_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("snapshot_sha256", self.snapshot_sha256)
        _require_sha(
            "selected_config_sha256",
            self.selected_config_sha256,
        )
        if type(self.selected_threshold_pct) is not int:
            raise TypeError("selected_threshold_pct must be int")
        if not isinstance(
            self.decision_reason,
            PolicyMemoryDecisionReasonV1,
        ):
            raise TypeError("decision_reason type mismatch")
        for name in ("score_numerator", "score_denominator"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be nonnegative int")
        if self.score_denominator < 1:
            raise ValueError("score_denominator must be positive")

        exposed = (
            self.decision_reason
            is PolicyMemoryDecisionReasonV1.EXPOSE_APPLICABLE
        )
        if exposed:
            _require_sha(
                "selected_memory_lineage_id",
                self.selected_memory_lineage_id,
            )
            _require_sha(
                "projection_artifact_sha256",
                self.projection_artifact_sha256,
            )
            if not isinstance(self.prompt_payload, dict):
                raise TypeError(
                    "exposed Policy view requires prompt payload"
                )
            audit_policy_prompt_payload_v1(self.prompt_payload)
        else:
            if any(
                value is not None
                for value in (
                    self.selected_memory_lineage_id,
                    self.projection_artifact_sha256,
                    self.prompt_payload,
                )
            ):
                raise ValueError(
                    "abstaining Policy view must carry no Memory payload"
                )

        expected = _sha_domain(
            "POLICY_MEMORY_VIEW_V1",
            self._without_sha(),
        )
        if self.view_sha256 is None:
            object.__setattr__(self, "view_sha256", expected)
        elif self.view_sha256 != expected:
            raise ValueError("Policy view SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "snapshot_sha256": self.snapshot_sha256,
            "selected_config_sha256": (
                self.selected_config_sha256
            ),
            "selected_threshold_pct": (
                self.selected_threshold_pct
            ),
            "decision_reason": self.decision_reason.value,
            "selected_memory_lineage_id": (
                self.selected_memory_lineage_id
            ),
            "projection_artifact_sha256": (
                self.projection_artifact_sha256
            ),
            "score": {
                "numerator": self.score_numerator,
                "denominator": self.score_denominator,
            },
            "prompt_payload": self.prompt_payload,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "POLICY_MEMORY_VIEW_V1",
            "schema_version": 1,
            **self._without_sha(),
            "view_sha256": self.view_sha256,
        }

    def policy_prompt_fragment(self) -> dict[str, object] | None:
        """Return only payload permitted inside the Task Policy prompt."""
        return self.prompt_payload


@dataclass(frozen=True, slots=True)
class AnalyzerMemoryCandidateV1:
    rank: int
    score_numerator: int
    score_denominator: int
    memory_lineage_id: str
    record_version: int
    canonical_record_sha256: str
    applicability: dict[str, object]
    semantic_hypotheses: tuple[dict[str, object], ...]
    observed_recovery_bindings: tuple[dict[str, object], ...]
    proposed_recoveries: tuple[dict[str, object], ...]
    governance_state: dict[str, object]
    relations: tuple[dict[str, object], ...]
    procedural_completeness: dict[str, object]
    evidence_reference_digests: tuple[
        dict[str, str], ...
    ]

    def __post_init__(self) -> None:
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError("rank must be positive int")
        if (
            type(self.score_numerator) is not int
            or type(self.score_denominator) is not int
            or self.score_numerator < 0
            or self.score_denominator < 1
            or self.score_numerator > self.score_denominator
        ):
            raise ValueError("invalid candidate score fraction")
        _require_sha(
            "memory_lineage_id",
            self.memory_lineage_id,
        )
        _require_sha(
            "canonical_record_sha256",
            self.canonical_record_sha256,
        )
        if type(self.record_version) is not int or self.record_version < 1:
            raise ValueError("record_version invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "score": {
                "numerator": self.score_numerator,
                "denominator": self.score_denominator,
            },
            "record_binding": {
                "memory_lineage_id": self.memory_lineage_id,
                "record_version": self.record_version,
                "canonical_record_sha256": (
                    self.canonical_record_sha256
                ),
            },
            "applicability": self.applicability,
            "semantic_hypotheses": list(
                self.semantic_hypotheses
            ),
            "observed_recovery_bindings": list(
                self.observed_recovery_bindings
            ),
            "proposed_recoveries": list(
                self.proposed_recoveries
            ),
            "governance_state": self.governance_state,
            "relations": list(self.relations),
            "procedural_completeness": (
                self.procedural_completeness
            ),
            "evidence_reference_digests": list(
                self.evidence_reference_digests
            ),
            "authority_notice": {
                "factual_items_remain_source_bound": True,
                "semantic_items_are_hypotheses": True,
                "recovery_items_are_proposals_unless_verified": True,
                "candidate_support_only": True,
                "direct_action_authority": False,
                "benefit_harm_authority": False,
            },
        }


@dataclass(frozen=True, slots=True)
class AnalyzerMemoryViewV1:
    snapshot_sha256: str
    top_k: int
    candidates: tuple[AnalyzerMemoryCandidateV1, ...]
    view_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("snapshot_sha256", self.snapshot_sha256)
        if type(self.top_k) is not int or self.top_k < 1:
            raise ValueError("top_k invalid")
        if type(self.candidates) is not tuple:
            raise TypeError("candidates must be tuple")
        if len(self.candidates) > self.top_k:
            raise ValueError("candidate count exceeds top_k")
        if tuple(
            row.rank for row in self.candidates
        ) != tuple(range(1, len(self.candidates) + 1)):
            raise ValueError("Analyzer candidate ranks not contiguous")
        payload = self._without_sha()
        audit_analyzer_view_payload_v1(payload)
        expected = _sha_domain(
            "ANALYZER_MEMORY_VIEW_V1",
            payload,
        )
        if self.view_sha256 is None:
            object.__setattr__(self, "view_sha256", expected)
        elif self.view_sha256 != expected:
            raise ValueError("Analyzer view SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "snapshot_sha256": self.snapshot_sha256,
            "top_k": self.top_k,
            "selection_semantics": (
                "BOUNDED_CANDIDATE_SUPPORT_NO_POLICY_EXPOSURE_THRESHOLD"
            ),
            "candidates": [
                row.to_dict() for row in self.candidates
            ],
            "direct_action_authority": False,
            "benefit_harm_authority": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "ANALYZER_MEMORY_VIEW_V1",
            "schema_version": 1,
            **self._without_sha(),
            "view_sha256": self.view_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResearcherMemoryViewV1:
    snapshot_sha256: str
    purpose: ResearcherPurposeV1
    train_side_records: tuple[dict[str, object], ...]
    round_evidence: dict[str, object]
    heldout_aggregate_metrics: dict[str, object]
    view_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("snapshot_sha256", self.snapshot_sha256)
        if not isinstance(self.purpose, ResearcherPurposeV1):
            raise TypeError("purpose type mismatch")
        if type(self.train_side_records) is not tuple:
            raise TypeError("train_side_records must be tuple")
        if not isinstance(self.round_evidence, dict):
            raise TypeError("round_evidence must be object")
        if not isinstance(self.heldout_aggregate_metrics, dict):
            raise TypeError(
                "heldout_aggregate_metrics must be object"
            )
        payload = self._without_sha()
        audit_researcher_view_payload_v1(payload)
        expected = _sha_domain(
            "RESEARCHER_MEMORY_VIEW_V1",
            payload,
        )
        if self.view_sha256 is None:
            object.__setattr__(self, "view_sha256", expected)
        elif self.view_sha256 != expected:
            raise ValueError("Researcher view SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "snapshot_sha256": self.snapshot_sha256,
            "purpose": self.purpose.value,
            "train_side_records": list(
                self.train_side_records
            ),
            "round_evidence": self.round_evidence,
            "heldout_aggregate_metrics": (
                self.heldout_aggregate_metrics
            ),
            "direct_environment_action_authority": False,
            "benefit_harm_authority": False,
            "may_propose_one_principal_system_change": True,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "RESEARCHER_MEMORY_VIEW_V1",
            "schema_version": 1,
            **self._without_sha(),
            "view_sha256": self.view_sha256,
        }


_POLICY_FORBIDDEN_KEYS = frozenset(
    {
        "memory_lineage_id",
        "record_version",
        "record_id",
        "canonical_record_sha256",
        "provenance",
        "source_task_id",
        "source_attempt_id",
        "task_gamefile_group_id",
        "dataset_relative_gamefile",
        "gold_target",
        "effect_status",
        "effect_evidence_scope",
        "known_harm_ids",
        "training_label",
        "formal_pool",
    }
)

_ANALYZER_FORBIDDEN_KEYS = frozenset(
    {
        "source_task_id",
        "source_attempt_id",
        "task_gamefile_group_id",
        "dataset_relative_gamefile",
        "formal_pool",
        "gold_target",
        "expected_memory_lineage_id",
        "heldout_answer",
        "validation_answer",
        "test_answer",
        "training_label",
    }
)

_HELDOUT_RAW_KEYS = frozenset(
    {
        "task_gamefile_group_id",
        "dataset_relative_gamefile",
        "execution_attempt_id",
        "raw_response",
        "action",
        "admissible_commands",
        "observation",
        "trajectory",
        "gold_action",
        "expected_action",
    }
)


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def audit_policy_prompt_payload_v1(
    payload: dict[str, object],
) -> None:
    expected = {
        "activation_cues",
        "failure_pattern",
        "revalidate_on",
        "release_cues",
        "non_applicability_cues",
        "recovery_procedure",
    }
    if set(payload) != expected:
        raise ValueError(
            "Policy prompt payload fields differ from frozen projection"
        )
    forbidden = _POLICY_FORBIDDEN_KEYS.intersection(
        _walk_keys(payload)
    )
    if forbidden:
        raise ValueError(
            "Policy payload leaks forbidden keys: "
            + repr(sorted(forbidden))
        )


def audit_analyzer_view_payload_v1(
    payload: dict[str, object],
) -> None:
    forbidden = _ANALYZER_FORBIDDEN_KEYS.intersection(
        _walk_keys(payload)
    )
    if forbidden:
        raise ValueError(
            "Analyzer view leaks forbidden identity/gold keys: "
            + repr(sorted(forbidden))
        )


def _audit_heldout_aggregate_only(
    value: object,
) -> None:
    forbidden = _HELDOUT_RAW_KEYS.intersection(
        _walk_keys(value)
    )
    if forbidden:
        raise ValueError(
            "held-out Researcher evidence is not aggregate-only: "
            + repr(sorted(forbidden))
        )


def audit_researcher_view_payload_v1(
    payload: dict[str, object],
) -> None:
    _audit_heldout_aggregate_only(
        payload["heldout_aggregate_metrics"]
    )
    records = payload["train_side_records"]
    if not isinstance(records, list):
        raise TypeError("train_side_records must serialize as array")
    for row in records:
        if row.get("source_partition") != (
            MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE.value
        ):
            raise ValueError(
                "Researcher record is not TRAIN_MEMORY_SOURCE"
            )


def _eligible_analyzer_member(
    member: LoadedDevSnapshotMemberV2,
) -> bool:
    # Membership in the strictly loaded immutable snapshot is the first
    # descriptive-access authority. The Analyzer may inspect candidate/staging
    # records as candidate support, but never quarantined/disabled/superseded or
    # contaminated records. This is intentionally broader than Policy exposure.
    governance = member.record.governance_state
    if governance.lifecycle_status in {
        LifecycleStatusV1.QUARANTINE,
        LifecycleStatusV1.DISABLED,
        LifecycleStatusV1.SUPERSEDED,
    }:
        return False
    if (
        governance.evaluation_contamination_status
        is EvaluationContaminationStatusV1.CONTAMINATED
    ):
        return False
    return True


def _collect_evidence_reference_digests(
    value: object,
) -> tuple[dict[str, str], ...]:
    rows: set[tuple[str, str]] = set()

    def walk(item: object) -> None:
        if isinstance(item, dict):
            source_kind = item.get("source_kind")
            source_sha = item.get("source_sha256")
            if (
                isinstance(source_kind, str)
                and isinstance(source_sha, str)
                and len(source_sha) == 64
                and all(
                    ch in "0123456789abcdef"
                    for ch in source_sha
                )
            ):
                rows.add((source_kind, source_sha))
            for child in item.values():
                walk(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)

    walk(value)
    return tuple(
        {
            "source_kind": kind,
            "source_sha256": sha,
        }
        for kind, sha in sorted(rows)
    )


def _score_members(
    query: MemoryConsumerQueryV1,
    snapshot: LoadedDevSnapshotV2,
    *,
    include_public_task_goal: bool = False,
):
    query_text = query.scoring_text()
    if include_public_task_goal and query.public_task_goal:
        query_text = query.public_task_goal + "\n" + query_text
    rows = []
    for member in snapshot.members:
        score = jaccard_score_v1(
            query_text,
            member.retrieval_key.scoring_payload
            .semantic_retrieval_text,
        )
        rows.append((score, member))
    return tuple(rows)


def build_policy_memory_view_v1(
    *,
    query: MemoryConsumerQueryV1,
    snapshot: LoadedDevSnapshotV2,
    config: FormalBRetrieverConfigV1,
) -> PolicyMemoryViewV1:
    if not isinstance(query, MemoryConsumerQueryV1):
        raise TypeError("query type mismatch")
    if not isinstance(snapshot, LoadedDevSnapshotV2):
        raise TypeError("snapshot type mismatch")
    if not isinstance(config, FormalBRetrieverConfigV1):
        raise TypeError("config type mismatch")

    scored = _score_members(query, snapshot)
    if not scored:
        return PolicyMemoryViewV1(
            snapshot_sha256=snapshot.snapshot.snapshot_sha256,
            selected_config_sha256=config.config_sha256,
            selected_threshold_pct=config.threshold_pct,
            decision_reason=(
                PolicyMemoryDecisionReasonV1.NO_CANDIDATES
            ),
            selected_memory_lineage_id=None,
            projection_artifact_sha256=None,
            score_numerator=0,
            score_denominator=1,
            prompt_payload=None,
        )

    top_score = max(score for score, _ in scored)
    top = tuple(
        member
        for score, member in scored
        if score == top_score
    )
    if len(top) != 1:
        return PolicyMemoryViewV1(
            snapshot_sha256=snapshot.snapshot.snapshot_sha256,
            selected_config_sha256=config.config_sha256,
            selected_threshold_pct=config.threshold_pct,
            decision_reason=(
                PolicyMemoryDecisionReasonV1.TOP_SCORE_TIE
            ),
            selected_memory_lineage_id=None,
            projection_artifact_sha256=None,
            score_numerator=top_score.numerator,
            score_denominator=top_score.denominator,
            prompt_payload=None,
        )

    member = top[0]
    if top_score < config.threshold:
        return PolicyMemoryViewV1(
            snapshot_sha256=snapshot.snapshot.snapshot_sha256,
            selected_config_sha256=config.config_sha256,
            selected_threshold_pct=config.threshold_pct,
            decision_reason=(
                PolicyMemoryDecisionReasonV1.BELOW_THRESHOLD
            ),
            selected_memory_lineage_id=None,
            projection_artifact_sha256=None,
            score_numerator=top_score.numerator,
            score_denominator=top_score.denominator,
            prompt_payload=None,
        )

    record = member.record
    gate = evaluate_direct_applicability_v1(
        activation_cues=tuple(
            item.condition_text
            for item in record.applicability.activation
        ),
        release_cues=tuple(
            item.condition_text
            for item in record.applicability.release
        ),
        non_applicability_cues=tuple(
            item.condition_text
            for item in record.applicability.non_applicability
        ),
        observation=query.observation,
        executed_transitions=query.executed_transitions,
        admissible_commands=query.admissible_commands,
        interface_feedback=query.interface_feedback,
    )
    if gate.disposition is not (
        DirectApplicabilityDispositionV1.APPLICABLE
    ):
        mapping = {
            DirectApplicabilityDispositionV1.NOT_APPLICABLE: (
                PolicyMemoryDecisionReasonV1
                .GATE_NOT_APPLICABLE
            ),
            DirectApplicabilityDispositionV1.CONFLICTING: (
                PolicyMemoryDecisionReasonV1
                .GATE_CONFLICTING
            ),
            DirectApplicabilityDispositionV1.UNCERTAIN: (
                PolicyMemoryDecisionReasonV1.GATE_UNCERTAIN
            ),
        }
        return PolicyMemoryViewV1(
            snapshot_sha256=snapshot.snapshot.snapshot_sha256,
            selected_config_sha256=config.config_sha256,
            selected_threshold_pct=config.threshold_pct,
            decision_reason=mapping[gate.disposition],
            selected_memory_lineage_id=None,
            projection_artifact_sha256=None,
            score_numerator=top_score.numerator,
            score_denominator=top_score.denominator,
            prompt_payload=None,
        )

    fm2 = member.fm2
    if (
        member.fm2_availability
        is not FM2AvailabilityV1.FM2_ELIGIBLE
        or fm2.build_disposition
        is not ProjectionBuildDispositionV1.ELIGIBLE
        or fm2.policy_visible_payload is None
        or fm2.policy_visible_payload_sha256 is None
    ):
        return PolicyMemoryViewV1(
            snapshot_sha256=snapshot.snapshot.snapshot_sha256,
            selected_config_sha256=config.config_sha256,
            selected_threshold_pct=config.threshold_pct,
            decision_reason=(
                PolicyMemoryDecisionReasonV1
                .POLICY_PROJECTION_UNAVAILABLE
            ),
            selected_memory_lineage_id=None,
            projection_artifact_sha256=None,
            score_numerator=top_score.numerator,
            score_denominator=top_score.denominator,
            prompt_payload=None,
        )

    payload = fm2.policy_visible_payload.to_dict()
    audit_policy_prompt_payload_v1(payload)
    return PolicyMemoryViewV1(
        snapshot_sha256=snapshot.snapshot.snapshot_sha256,
        selected_config_sha256=config.config_sha256,
        selected_threshold_pct=config.threshold_pct,
        decision_reason=(
            PolicyMemoryDecisionReasonV1.EXPOSE_APPLICABLE
        ),
        selected_memory_lineage_id=record.memory_lineage_id,
        projection_artifact_sha256=(
            fm2.policy_visible_payload_sha256
        ),
        score_numerator=top_score.numerator,
        score_denominator=top_score.denominator,
        prompt_payload=payload,
    )


def build_analyzer_memory_view_v1(
    *,
    query: MemoryConsumerQueryV1,
    snapshot: LoadedDevSnapshotV2,
    top_k: int = 3,
) -> AnalyzerMemoryViewV1:
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k invalid")
    scored = [
        (score, member)
        for score, member in _score_members(
            query,
            snapshot,
            include_public_task_goal=True,
        )
        if _eligible_analyzer_member(member)
    ]
    scored.sort(
        key=lambda row: (
            -row[0],
            row[1].record.memory_lineage_id,
        )
    )

    candidates = []
    for rank, (score, member) in enumerate(
        scored[:top_k],
        start=1,
    ):
        record = member.record
        candidates.append(
            AnalyzerMemoryCandidateV1(
                rank=rank,
                score_numerator=score.numerator,
                score_denominator=score.denominator,
                memory_lineage_id=record.memory_lineage_id,
                record_version=record.record_version,
                canonical_record_sha256=(
                    record.canonical_record_sha256
                ),
                applicability=record.applicability.to_dict(),
                semantic_hypotheses=tuple(
                    item.to_dict()
                    for item in record.semantic_hypotheses
                ),
                observed_recovery_bindings=tuple(
                    item.to_dict()
                    for item in record
                    .observed_recovery_bindings
                ),
                proposed_recoveries=tuple(
                    item.to_dict()
                    for item in record.proposed_recoveries
                ),
                governance_state=(
                    record.governance_state.to_dict()
                ),
                relations=tuple(
                    item.to_dict()
                    for item in record.relations
                ),
                procedural_completeness=(
                    record.procedural_completeness.to_dict()
                ),
                evidence_reference_digests=(
                    _collect_evidence_reference_digests(
                        record.to_dict()
                    )
                ),
            )
        )

    return AnalyzerMemoryViewV1(
        snapshot_sha256=snapshot.snapshot.snapshot_sha256,
        top_k=top_k,
        candidates=tuple(candidates),
    )


def build_researcher_memory_view_v1(
    *,
    snapshot: LoadedDevSnapshotV2,
    purpose: ResearcherPurposeV1,
    source_partition_by_lineage: Mapping[
        str, MemorySourcePartitionBindingV1
    ],
    round_evidence: Mapping[str, object] | None = None,
    heldout_aggregate_metrics: Mapping[
        str, object
    ] | None = None,
) -> ResearcherMemoryViewV1:
    records = []
    for member in snapshot.members:
        lineage = member.record.memory_lineage_id
        binding = source_partition_by_lineage.get(lineage)
        if not isinstance(
            binding,
            MemorySourcePartitionBindingV1,
        ):
            raise ValueError(
                "Researcher governed-record access requires an "
                "explicit source-partition authority binding"
            )
        if binding.memory_lineage_id != lineage:
            raise ValueError(
                "source-partition binding lineage mismatch"
            )
        if binding.source_partition is not (
            MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE
        ):
            raise ValueError(
                "Researcher governed-record access requires explicit "
                "TRAIN_MEMORY_SOURCE binding"
            )
        if (
            purpose is ResearcherPurposeV1.TRAINING_DATA_BUILD
            and binding.authority_scope is not (
                MemoryPartitionAuthorityScopeV1.FULL_TRAIN_SOURCE_PROVENANCE
            )
        ):
            raise ValueError(
                "TRAINING_DATA_BUILD requires full source collection, task-access, "
                "and record-provenance authority"
            )
        records.append(
            {
                "source_partition": (
                    binding.source_partition.value
                ),
                "source_partition_authority_sha256": (
                    binding.partition_authority_sha256
                ),
                "source_partition_authority_scope": (
                    binding.authority_scope.value
                ),
                "source_collection_manifest_sha256": (
                    binding.source_collection_manifest_sha256
                ),
                "task_access_authority_sha256": (
                    binding.task_access_authority_sha256
                ),
                "record_provenance_authority_sha256": (
                    binding.record_provenance_authority_sha256
                ),
                "governed_record": member.record.to_dict(),
                "retrieval_key": (
                    member.retrieval_key.to_dict()
                ),
                "fm1_availability": (
                    member.fm1_availability.value
                ),
                "fm2_availability": (
                    member.fm2_availability.value
                ),
            }
        )

    return ResearcherMemoryViewV1(
        snapshot_sha256=snapshot.snapshot.snapshot_sha256,
        purpose=purpose,
        train_side_records=tuple(records),
        round_evidence=dict(round_evidence or {}),
        heldout_aggregate_metrics=dict(
            heldout_aggregate_metrics or {}
        ),
    )
