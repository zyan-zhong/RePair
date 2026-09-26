"""Typed, authority-separated ports around Failure Memory V1.

These contracts let future Analyzer, Environment Verifier, Training Researcher,
and optional policy-training components exchange content-addressed evidence with
Memory without implementing those components inside the Memory package.

Memory owns validation, persistence, projection, governance, and evidence routing.
It does not execute an Analyzer, environment, researcher, trainer, or benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)


def _require_text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in ("\x00", "\r", "\n"))
    ):
        raise ValueError(f"{name} must be nonempty one-line NUL-free text")
    return value


def _domain_sha(domain: str, payload: object) -> str:
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    )


class MemoryPortAuthorityV1(str, Enum):
    FACT_AUTHORITY = "FACT_AUTHORITY"
    SEMANTIC_HYPOTHESIS = "SEMANTIC_HYPOTHESIS"
    RECOVERY_PROPOSAL = "RECOVERY_PROPOSAL"
    REGISTERED_BOUNDARY = "REGISTERED_BOUNDARY"
    EFFECT_EVIDENCE = "EFFECT_EVIDENCE"
    GOVERNANCE_AUTHORITY = "GOVERNANCE_AUTHORITY"
    AGGREGATE_EVALUATION = "AGGREGATE_EVALUATION"


class MemorySourcePartitionV1(str, Enum):
    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"
    TRAIN_RETRIEVAL_DEV = "TRAIN_RETRIEVAL_DEV"
    VALID_SEEN = "VALID_SEEN"
    VALID_UNSEEN = "VALID_UNSEEN"
    FORMAL_EVALUATION = "FORMAL_EVALUATION"


class VerifierEffectV1(str, Enum):
    BENEFIT = "Benefit"
    HARM = "Harm"
    NEUTRAL = "Neutral"
    UNCERTAIN = "Uncertain"
    INFRASTRUCTURE_NO_OUTCOME = "INFRASTRUCTURE_NO_OUTCOME"


@dataclass(frozen=True, slots=True)
class MemoryEvidenceRefV1:
    evidence_kind: str
    artifact_sha256: str
    authority: MemoryPortAuthorityV1

    def __post_init__(self) -> None:
        _require_text("evidence_kind", self.evidence_kind)
        require_lower_sha256("artifact_sha256", self.artifact_sha256)
        if not isinstance(self.authority, MemoryPortAuthorityV1):
            raise TypeError("authority type mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_kind": self.evidence_kind,
            "artifact_sha256": self.artifact_sha256,
            "authority": self.authority.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryEvidenceRefV1":
        if not isinstance(value, dict) or set(value) != {
            "evidence_kind",
            "artifact_sha256",
            "authority",
        }:
            raise ValueError("Memory evidence reference fields mismatch")
        return cls(
            evidence_kind=value["evidence_kind"],
            artifact_sha256=value["artifact_sha256"],
            authority=MemoryPortAuthorityV1(value["authority"]),
        )


@dataclass(frozen=True, slots=True)
class AnalyzerRepairProposalV1:
    rank: int
    exact_action: str
    admissible_menu_sha256: str
    proposal_evidence_sha256: str

    def __post_init__(self) -> None:
        if type(self.rank) is not int or not 1 <= self.rank <= 3:
            raise ValueError("Analyzer repair rank must be 1..3")
        _require_text("exact_action", self.exact_action)
        require_lower_sha256(
            "admissible_menu_sha256",
            self.admissible_menu_sha256,
        )
        require_lower_sha256(
            "proposal_evidence_sha256",
            self.proposal_evidence_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "exact_action": self.exact_action,
            "admissible_menu_sha256": self.admissible_menu_sha256,
            "proposal_evidence_sha256": self.proposal_evidence_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "AnalyzerRepairProposalV1":
        if not isinstance(value, dict) or set(value) != {
            "rank",
            "exact_action",
            "admissible_menu_sha256",
            "proposal_evidence_sha256",
        }:
            raise ValueError("Analyzer repair proposal fields mismatch")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class AnalyzerProposalIngressV1:
    failure_instance_sha256: str
    source_state_sha256: str
    analyzer_condition: str
    factual_evidence_refs: tuple[MemoryEvidenceRefV1, ...]
    semantic_hypothesis_refs: tuple[MemoryEvidenceRefV1, ...]
    counterevidence_refs: tuple[MemoryEvidenceRefV1, ...]
    historical_memory_view_sha256: str | None
    repair_proposals: tuple[AnalyzerRepairProposalV1, ...]
    abstained: bool
    ingress_sha256: str | None = None

    _CONDITIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "C0_SINGLE_REFLECTION",
            "C1_HIERARCHICAL_NO_HISTORY",
            "C2_HIERARCHICAL_WITH_HISTORY",
            "EXTERNAL_ANALYZER_UNSPECIFIED",
        }
    )

    def __post_init__(self) -> None:
        for name in ("failure_instance_sha256", "source_state_sha256"):
            require_lower_sha256(name, getattr(self, name))
        if self.analyzer_condition not in self._CONDITIONS:
            raise ValueError("Analyzer condition not registered")
        for name in (
            "factual_evidence_refs",
            "semantic_hypothesis_refs",
            "counterevidence_refs",
        ):
            values = getattr(self, name)
            if type(values) is not tuple or any(
                not isinstance(item, MemoryEvidenceRefV1) for item in values
            ):
                raise TypeError(f"{name} must be MemoryEvidenceRefV1 tuple")
        if any(
            item.authority is not MemoryPortAuthorityV1.FACT_AUTHORITY
            for item in self.factual_evidence_refs
        ):
            raise ValueError("factual refs must retain FACT_AUTHORITY")
        if any(
            item.authority is not MemoryPortAuthorityV1.SEMANTIC_HYPOTHESIS
            for item in self.semantic_hypothesis_refs
        ):
            raise ValueError("semantic refs must retain hypothesis authority")
        if self.historical_memory_view_sha256 is not None:
            require_lower_sha256(
                "historical_memory_view_sha256",
                self.historical_memory_view_sha256,
            )
        if self.analyzer_condition != "C2_HIERARCHICAL_WITH_HISTORY" and (
            self.historical_memory_view_sha256 is not None
        ):
            raise ValueError("only C2 may bind a historical Memory view")
        if type(self.repair_proposals) is not tuple:
            raise TypeError("repair_proposals must be tuple")
        if len(self.repair_proposals) > 3:
            raise ValueError("at most three repair proposals")
        ranks = tuple(item.rank for item in self.repair_proposals)
        if ranks and ranks != tuple(range(1, len(ranks) + 1)):
            raise ValueError("repair proposal ranks must be contiguous")
        if self.abstained and self.repair_proposals:
            raise ValueError("abstaining Analyzer cannot propose a repair")
        if not self.abstained and not self.repair_proposals:
            raise ValueError("non-abstaining Analyzer requires a repair")
        expected = _domain_sha(
            "ANALYZER_PROPOSAL_INGRESS_V1",
            self._without_sha(),
        )
        if self.ingress_sha256 is None:
            object.__setattr__(self, "ingress_sha256", expected)
        elif self.ingress_sha256 != expected:
            raise ValueError("Analyzer ingress SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "failure_instance_sha256": self.failure_instance_sha256,
            "source_state_sha256": self.source_state_sha256,
            "analyzer_condition": self.analyzer_condition,
            "factual_evidence_refs": [
                item.to_dict() for item in self.factual_evidence_refs
            ],
            "semantic_hypothesis_refs": [
                item.to_dict() for item in self.semantic_hypothesis_refs
            ],
            "counterevidence_refs": [
                item.to_dict() for item in self.counterevidence_refs
            ],
            "historical_memory_view_sha256": (
                self.historical_memory_view_sha256
            ),
            "repair_proposals": [
                item.to_dict() for item in self.repair_proposals
            ],
            "abstained": self.abstained,
            "authority_boundary": {
                "direct_environment_action": False,
                "benefit_harm_authority": False,
                "semantic_hypotheses_are_facts": False,
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "ANALYZER_PROPOSAL_INGRESS_V1",
            "schema_version": 1,
            **self._without_sha(),
            "ingress_sha256": self.ingress_sha256,
        }


@dataclass(frozen=True, slots=True)
class SameStateVerifierIngressV1:
    failure_instance_sha256: str
    candidate_sha256: str
    source_state_sha256: str
    f0_evidence_sha256: str | None
    f1_evidence_sha256: str | None
    policy_identity_sha256: str
    environment_identity_sha256: str
    effect: VerifierEffectV1
    f0_terminal_success: bool | None
    f1_terminal_success: bool | None
    scientific_execution_complete: bool
    ingress_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "failure_instance_sha256",
            "candidate_sha256",
            "source_state_sha256",
            "policy_identity_sha256",
            "environment_identity_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        for name in ("f0_evidence_sha256", "f1_evidence_sha256"):
            value = getattr(self, name)
            if value is not None:
                require_lower_sha256(name, value)
        if not isinstance(self.effect, VerifierEffectV1):
            raise TypeError("effect type mismatch")
        if type(self.scientific_execution_complete) is not bool:
            raise TypeError("scientific_execution_complete must be bool")
        if self.effect is VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME:
            if self.scientific_execution_complete:
                raise ValueError("infrastructure incident is not an outcome")
        else:
            if not self.scientific_execution_complete:
                raise ValueError("scientific effect requires complete execution")
            if self.f0_evidence_sha256 is None or self.f1_evidence_sha256 is None:
                raise ValueError("scientific effect requires F0/F1 evidence")
            if type(self.f0_terminal_success) is not bool or type(
                self.f1_terminal_success
            ) is not bool:
                raise TypeError("scientific effect requires terminal booleans")
        if self.effect is VerifierEffectV1.BENEFIT and not (
            self.f0_terminal_success is False
            and self.f1_terminal_success is True
        ):
            raise ValueError("Benefit requires F0 fail and F1 success")
        if self.effect is VerifierEffectV1.HARM and not (
            self.f0_terminal_success is True
            and self.f1_terminal_success is False
        ):
            raise ValueError("Harm requires F0 success and F1 fail")
        expected = _domain_sha(
            "SAME_STATE_VERIFIER_INGRESS_V1",
            self._without_sha(),
        )
        if self.ingress_sha256 is None:
            object.__setattr__(self, "ingress_sha256", expected)
        elif self.ingress_sha256 != expected:
            raise ValueError("Verifier ingress SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "failure_instance_sha256": self.failure_instance_sha256,
            "candidate_sha256": self.candidate_sha256,
            "source_state_sha256": self.source_state_sha256,
            "f0_evidence_sha256": self.f0_evidence_sha256,
            "f1_evidence_sha256": self.f1_evidence_sha256,
            "policy_identity_sha256": self.policy_identity_sha256,
            "environment_identity_sha256": self.environment_identity_sha256,
            "effect": self.effect.value,
            "f0_terminal_success": self.f0_terminal_success,
            "f1_terminal_success": self.f1_terminal_success,
            "scientific_execution_complete": self.scientific_execution_complete,
            "effect_authority": "SAME_STATE_ENVIRONMENT_F0_F1",
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "SAME_STATE_VERIFIER_INGRESS_V1",
            "schema_version": 1,
            **self._without_sha(),
            "ingress_sha256": self.ingress_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResearcherMemoryEvidenceExportV1:
    round_id: str
    snapshot_sha256: str
    memory_record_sha256s: tuple[str, ...]
    analyzer_ingress_sha256s: tuple[str, ...]
    verifier_ingress_sha256s: tuple[str, ...]
    no_go_or_regression_sha256s: tuple[str, ...]
    cost_evidence_sha256s: tuple[str, ...]
    heldout_aggregate_metrics: dict[str, object]
    export_sha256: str | None = None

    _HELDOUT_RAW_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "task_gamefile_group_id",
            "dataset_relative_gamefile",
            "execution_attempt_id",
            "trajectory",
            "observation",
            "action",
            "admissible_commands",
            "gold_action",
            "expected_action",
        }
    )

    def __post_init__(self) -> None:
        _require_text("round_id", self.round_id)
        require_lower_sha256("snapshot_sha256", self.snapshot_sha256)
        for name in (
            "memory_record_sha256s",
            "analyzer_ingress_sha256s",
            "verifier_ingress_sha256s",
            "no_go_or_regression_sha256s",
            "cost_evidence_sha256s",
        ):
            values = getattr(self, name)
            if type(values) is not tuple:
                raise TypeError(f"{name} must be tuple")
            for item in values:
                require_lower_sha256(f"{name} item", item)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique")
        if not isinstance(self.heldout_aggregate_metrics, dict):
            raise TypeError("heldout_aggregate_metrics must be object")
        seen_keys: set[str] = set()

        def walk(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    seen_keys.add(key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.heldout_aggregate_metrics)
        forbidden = seen_keys & self._HELDOUT_RAW_KEYS
        if forbidden:
            raise ValueError(
                "held-out evidence must be aggregate-only: "
                + repr(sorted(forbidden))
            )
        expected = _domain_sha(
            "RESEARCHER_MEMORY_EVIDENCE_EXPORT_V1",
            self._without_sha(),
        )
        if self.export_sha256 is None:
            object.__setattr__(self, "export_sha256", expected)
        elif self.export_sha256 != expected:
            raise ValueError("Researcher export SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "round_id": self.round_id,
            "snapshot_sha256": self.snapshot_sha256,
            "memory_record_sha256s": list(self.memory_record_sha256s),
            "analyzer_ingress_sha256s": list(
                self.analyzer_ingress_sha256s
            ),
            "verifier_ingress_sha256s": list(
                self.verifier_ingress_sha256s
            ),
            "no_go_or_regression_sha256s": list(
                self.no_go_or_regression_sha256s
            ),
            "cost_evidence_sha256s": list(self.cost_evidence_sha256s),
            "heldout_aggregate_metrics": self.heldout_aggregate_metrics,
            "authority_boundary": {
                "direct_environment_action": False,
                "benefit_harm_authority": False,
                "training_execution": False,
                "research_decision": "EXTERNAL_RESEARCHER_REQUIRED",
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "RESEARCHER_MEMORY_EVIDENCE_EXPORT_V1",
            "schema_version": 1,
            **self._without_sha(),
            "export_sha256": self.export_sha256,
        }


@dataclass(frozen=True, slots=True)
class VerifiedTrainingEvidencePortV1:
    verifier_ingress_sha256: str
    source_partition: MemorySourcePartitionV1
    policy_visible_input_sha256: str
    candidate_output_sha256: str
    effect: VerifierEffectV1
    positive_sft_eligible: bool
    preference_chosen_eligible: bool
    preference_rejected_eligible: bool
    analyzer_rationale_used_as_target: bool = False
    training_execution_performed: bool = False
    port_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "verifier_ingress_sha256",
            "policy_visible_input_sha256",
            "candidate_output_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if not isinstance(self.source_partition, MemorySourcePartitionV1):
            raise TypeError("source_partition type mismatch")
        if not isinstance(self.effect, VerifierEffectV1):
            raise TypeError("effect type mismatch")
        if self.analyzer_rationale_used_as_target:
            raise ValueError("Analyzer rationale cannot be a factual target")
        if self.training_execution_performed:
            raise ValueError("Memory port cannot execute training")
        train = self.source_partition is MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE
        expected_positive = train and self.effect is VerifierEffectV1.BENEFIT
        expected_rejected = train and self.effect is VerifierEffectV1.HARM
        if self.positive_sft_eligible != expected_positive:
            raise ValueError("positive SFT eligibility mismatch")
        if self.preference_chosen_eligible != expected_positive:
            raise ValueError("preference-chosen eligibility mismatch")
        if self.preference_rejected_eligible != expected_rejected:
            raise ValueError("preference-rejected eligibility mismatch")
        expected = _domain_sha(
            "VERIFIED_TRAINING_EVIDENCE_PORT_V1",
            self._without_sha(),
        )
        if self.port_sha256 is None:
            object.__setattr__(self, "port_sha256", expected)
        elif self.port_sha256 != expected:
            raise ValueError("training evidence port SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "verifier_ingress_sha256": self.verifier_ingress_sha256,
            "source_partition": self.source_partition.value,
            "policy_visible_input_sha256": self.policy_visible_input_sha256,
            "candidate_output_sha256": self.candidate_output_sha256,
            "effect": self.effect.value,
            "positive_sft_eligible": self.positive_sft_eligible,
            "preference_chosen_eligible": self.preference_chosen_eligible,
            "preference_rejected_eligible": self.preference_rejected_eligible,
            "analyzer_rationale_used_as_target": False,
            "training_execution_performed": False,
            "authority_boundary": (
                "EXTERNAL_TRAINING_AND_OFF_OFF_EVALUATION_REQUIRED"
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "VERIFIED_TRAINING_EVIDENCE_PORT_V1",
            "schema_version": 1,
            **self._without_sha(),
            "port_sha256": self.port_sha256,
        }


def build_verified_training_evidence_port_v1(
    *,
    verifier: SameStateVerifierIngressV1,
    source_partition: MemorySourcePartitionV1,
    policy_visible_input_sha256: str,
    candidate_output_sha256: str,
) -> VerifiedTrainingEvidencePortV1:
    if not isinstance(verifier, SameStateVerifierIngressV1):
        raise TypeError("verifier type mismatch")
    train = source_partition is MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE
    positive = (
        train
        and verifier.effect is VerifierEffectV1.BENEFIT
        and verifier.scientific_execution_complete
    )
    rejected = (
        train
        and verifier.effect is VerifierEffectV1.HARM
        and verifier.scientific_execution_complete
    )
    return VerifiedTrainingEvidencePortV1(
        verifier_ingress_sha256=verifier.ingress_sha256,
        source_partition=source_partition,
        policy_visible_input_sha256=policy_visible_input_sha256,
        candidate_output_sha256=candidate_output_sha256,
        effect=verifier.effect,
        positive_sft_eligible=positive,
        preference_chosen_eligible=positive,
        preference_rejected_eligible=rejected,
    )
