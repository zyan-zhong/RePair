"""Scientific program contracts for Failure Memory V1.

The program has five registered stages:

Stage 0  Memory quality, safety, retrieval, access, cost and leakage diagnostics.
Stage 1A source-state-local paired Memory OFF/ON causal probes.
Stage 1B frozen-policy FM0/FM1/FM2/FM3 system evaluation.
Stage 2  frozen-policy multi-round external-Memory accumulation.
Stage 3  fully frozen valid_seen / valid_unseen formal evaluation.

The module only freezes identities and interprets sealed result authorities. It
never self-authorizes model or environment execution and never treats engineering
tests as scientific evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import Path
from typing import Mapping

from pchsi.memory.scientific_authority import (
    ValidatedScientificResultAuthorityV2,
    load_scientific_result_authority_v2,
)

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
        raise ValueError(f"{name} must be nonempty one-line text")
    return value


def _domain_sha(domain: str, payload: object) -> str:
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    )


class MemoryScientificStageV1(str, Enum):
    STAGE_0_MEMORY_DIAGNOSTICS = "STAGE_0_MEMORY_DIAGNOSTICS"
    STAGE_1A_LOCAL_PAIRED = "STAGE_1A_LOCAL_PAIRED"
    STAGE_1B_FROZEN_POLICY_FM0_FM3 = "STAGE_1B_FROZEN_POLICY_FM0_FM3"
    STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY = (
        "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY"
    )
    STAGE_3_FROZEN_FORMAL_EVALUATION = (
        "STAGE_3_FROZEN_FORMAL_EVALUATION"
    )


class MemoryRepresentationArmV1(str, Enum):
    FM0_NO_MEMORY = "FM0_NO_MEMORY"
    FM1_MATCHED_RAW_EPISODIC = "FM1_MATCHED_RAW_EPISODIC"
    FM2_STRUCTURED_DESCRIPTIVE = "FM2_STRUCTURED_DESCRIPTIVE"
    FM3_GATED_PRESCRIPTIVE = "FM3_GATED_PRESCRIPTIVE"


class ScientificQuestionStatusV1(str, Enum):
    OPEN = "OPEN"
    PARTIAL_LOCAL_NULL = "PARTIAL_LOCAL_NULL"
    MIXED_POLICY_DIRECT = "MIXED_POLICY_DIRECT"
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    DEFERRED_OPTIONAL_EXTENSION = "DEFERRED_OPTIONAL_EXTENSION"


@dataclass(frozen=True, slots=True)
class MemoryStageCellV1:
    stage: MemoryScientificStageV1
    cell_id: str
    panel_sha256: str
    policy_identity_sha256: str
    environment_identity_sha256: str
    snapshot_sha256: str | None
    representation_arm: MemoryRepresentationArmV1 | None
    round_index: int | None
    split: str | None
    method_frozen: bool
    scientific_execution_authorized: bool = False
    cell_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, MemoryScientificStageV1):
            raise TypeError("stage type mismatch")
        _require_text("cell_id", self.cell_id)
        for name in (
            "panel_sha256",
            "policy_identity_sha256",
            "environment_identity_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.snapshot_sha256 is not None:
            require_lower_sha256("snapshot_sha256", self.snapshot_sha256)
        if self.representation_arm is not None and not isinstance(
            self.representation_arm, MemoryRepresentationArmV1
        ):
            raise TypeError("representation_arm type mismatch")
        if self.round_index is not None and (
            type(self.round_index) is not int or self.round_index < 0
        ):
            raise ValueError("round_index invalid")
        if self.split is not None and self.split not in {
            "TRAIN_RETRIEVAL_DEV",
            "TRAIN_MEMORY_SOURCE",
            "VALID_SEEN",
            "VALID_UNSEEN",
        }:
            raise ValueError("split not registered")
        if type(self.method_frozen) is not bool:
            raise TypeError("method_frozen must be bool")
        if self.scientific_execution_authorized is not False:
            raise ValueError("cell cannot self-authorize scientific execution")
        if self.stage in {
            MemoryScientificStageV1.STAGE_1B_FROZEN_POLICY_FM0_FM3,
            MemoryScientificStageV1.STAGE_3_FROZEN_FORMAL_EVALUATION,
        } and self.representation_arm is None:
            raise ValueError("FM system cell requires representation arm")
        if self.stage is MemoryScientificStageV1.STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY:
            if self.round_index is None or self.snapshot_sha256 is None:
                raise ValueError("Stage 2 cell requires round and snapshot")
        if self.stage is MemoryScientificStageV1.STAGE_3_FROZEN_FORMAL_EVALUATION:
            if self.split not in {"VALID_SEEN", "VALID_UNSEEN"}:
                raise ValueError("Stage 3 requires valid_seen or valid_unseen")
            if not self.method_frozen:
                raise ValueError("Stage 3 method must be frozen")
        expected = _domain_sha(
            "MEMORY_SCIENTIFIC_STAGE_CELL_V1",
            self._without_sha(),
        )
        if self.cell_sha256 is None:
            object.__setattr__(self, "cell_sha256", expected)
        elif self.cell_sha256 != expected:
            raise ValueError("scientific stage cell SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "cell_id": self.cell_id,
            "panel_sha256": self.panel_sha256,
            "policy_identity_sha256": self.policy_identity_sha256,
            "environment_identity_sha256": self.environment_identity_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "representation_arm": (
                None
                if self.representation_arm is None
                else self.representation_arm.value
            ),
            "round_index": self.round_index,
            "split": self.split,
            "method_frozen": self.method_frozen,
            "scientific_execution_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "MEMORY_SCIENTIFIC_STAGE_CELL_V1",
            "schema_version": 1,
            **self._without_sha(),
            "cell_sha256": self.cell_sha256,
        }


@dataclass(frozen=True, slots=True)
class MemoryScientificProgramV1:
    canonical_base_head: str
    cells: tuple[MemoryStageCellV1, ...]
    stage_metrics: Mapping[str, tuple[str, ...]]
    q4_external_analyzer_required: bool = True
    q5_parametric_internalization_deferred: bool = True
    scientific_execution_authorized: bool = False
    program_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.canonical_base_head, str)
            or len(self.canonical_base_head) != 40
            or any(
                ch not in "0123456789abcdef"
                for ch in self.canonical_base_head
            )
        ):
            raise ValueError("canonical_base_head must be 40 lowercase hex")
        if type(self.cells) is not tuple or not self.cells:
            raise ValueError("scientific program requires cells")
        ids = tuple(item.cell_sha256 for item in self.cells)
        if len(ids) != len(set(ids)):
            raise ValueError("scientific stage cells must be unique")
        if not isinstance(self.stage_metrics, Mapping):
            raise TypeError("stage_metrics must be mapping")
        expected_stages = {stage.value for stage in MemoryScientificStageV1}
        if set(self.stage_metrics) != expected_stages:
            raise ValueError("stage_metrics population mismatch")
        for name, values in self.stage_metrics.items():
            if type(values) is not tuple or not values:
                raise ValueError(f"stage metrics missing for {name}")
            for value in values:
                _require_text("metric", value)
        if self.q4_external_analyzer_required is not True:
            raise ValueError("Q4 must retain external Analyzer requirement")
        if self.q5_parametric_internalization_deferred is not True:
            raise ValueError("Q5 internalization must remain deferred in V1")
        if self.scientific_execution_authorized is not False:
            raise ValueError("program cannot self-authorize execution")
        expected = _domain_sha(
            "FAILURE_MEMORY_SCIENTIFIC_PROGRAM_V1",
            self._without_sha(),
        )
        if self.program_sha256 is None:
            object.__setattr__(self, "program_sha256", expected)
        elif self.program_sha256 != expected:
            raise ValueError("scientific program SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "canonical_base_head": self.canonical_base_head,
            "cells": [item.to_dict() for item in self.cells],
            "stage_metrics": {
                key: list(values)
                for key, values in sorted(self.stage_metrics.items())
            },
            "q4_external_analyzer_required": True,
            "q5_parametric_internalization_deferred": True,
            "scientific_execution_authorized": False,
            "authority_boundaries": {
                "memory": "EVIDENCE_REUSE_AND_GOVERNANCE",
                "analyzer": "EXTERNAL_PROPOSAL_ONLY",
                "verifier": "SAME_STATE_EFFECT_AUTHORITY",
                "off_off": "FINAL_POLICY_PROMOTION_AUTHORITY",
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "FAILURE_MEMORY_SCIENTIFIC_PROGRAM_V1",
            "schema_version": 1,
            **self._without_sha(),
            "program_sha256": self.program_sha256,
        }


@dataclass(frozen=True, slots=True)
class ScientificQuestionEvidenceRowV1:
    question_id: str
    status: ScientificQuestionStatusV1
    authorized_summary: str
    evidence_sha256s: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    required_next_authorities: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.question_id not in {"Q1", "Q2", "Q3", "Q4", "Q5"}:
            raise ValueError("question_id invalid")
        if not isinstance(self.status, ScientificQuestionStatusV1):
            raise TypeError("status type mismatch")
        _require_text("authorized_summary", self.authorized_summary)
        for name in (
            "evidence_sha256s",
            "forbidden_claims",
            "required_next_authorities",
        ):
            values = getattr(self, name)
            if type(values) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if name == "evidence_sha256s":
                for value in values:
                    require_lower_sha256("evidence SHA", value)
            else:
                for value in values:
                    _require_text(name, value)

    def to_dict(self) -> dict[str, object]:
        return {
            "question_id": self.question_id,
            "status": self.status.value,
            "authorized_summary": self.authorized_summary,
            "evidence_sha256s": list(self.evidence_sha256s),
            "forbidden_claims": list(self.forbidden_claims),
            "required_next_authorities": list(
                self.required_next_authorities
            ),
        }


@dataclass(frozen=True, slots=True)
class ScientificQuestionMatrixV1:
    rows: tuple[ScientificQuestionEvidenceRowV1, ...]
    matrix_sha256: str | None = None

    def __post_init__(self) -> None:
        if tuple(row.question_id for row in self.rows) != (
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "Q5",
        ):
            raise ValueError("Q1-Q5 row order/population mismatch")
        expected = _domain_sha(
            "FAILURE_MEMORY_Q1_Q5_MATRIX_V1",
            self._without_sha(),
        )
        if self.matrix_sha256 is None:
            object.__setattr__(self, "matrix_sha256", expected)
        elif self.matrix_sha256 != expected:
            raise ValueError("Q1-Q5 matrix SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "rows": [item.to_dict() for item in self.rows],
            "scientific_completion_rule": (
                "TESTS_AND_INTERFACE_SMOKES_NEVER_REPLACE_REAL_OUTCOMES"
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "FAILURE_MEMORY_Q1_Q5_MATRIX_V1",
            "schema_version": 1,
            **self._without_sha(),
            "matrix_sha256": self.matrix_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())



def _load_object(path: Path) -> tuple[dict[str, object], str]:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"authority path invalid: {path}")
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise TypeError("authority must be JSON object")
    return value, sha256_bytes(raw)


def _validated_optional_authority(
    *,
    path: Path | None,
    stage: str,
    expected_fixed_code_head: str | None,
    expected_scientific_program_sha256: str | None,
) -> ValidatedScientificResultAuthorityV2 | None:
    if path is None:
        return None
    if expected_fixed_code_head is None or expected_scientific_program_sha256 is None:
        raise ValueError(
            "optional scientific authorities require the expected fixed code "
            "head and scientific program SHA"
        )
    return load_scientific_result_authority_v2(
        path=path,
        expected_stage=stage,
        expected_fixed_code_head=expected_fixed_code_head,
        expected_scientific_program_sha256=expected_scientific_program_sha256,
    )


def _apply_registered_decision(
    *,
    authority: ValidatedScientificResultAuthorityV2,
    question_id: str,
    supported: ScientificQuestionStatusV1,
    not_supported: ScientificQuestionStatusV1,
    inconclusive: ScientificQuestionStatusV1,
) -> ScientificQuestionStatusV1:
    disposition = authority.disposition(question_id)
    if disposition == "SUPPORTED":
        return supported
    if disposition == "NOT_SUPPORTED":
        return not_supported
    if disposition == "INCONCLUSIVE":
        return inconclusive
    raise AssertionError("validated authority returned unknown disposition")


def build_current_q1_q5_matrix_v1(
    *,
    a0_result_path: Path,
    b_result_path: Path,
    stage0_result_path: Path | None = None,
    stage1b_result_path: Path | None = None,
    stage2_result_path: Path | None = None,
    stage3_result_path: Path | None = None,
    formal_c_result_path: Path | None = None,
    off_off_result_path: Path | None = None,
    expected_fixed_code_head: str | None = None,
    expected_scientific_program_sha256: str | None = None,
) -> ScientificQuestionMatrixV1:
    a0, a0_sha = _load_object(a0_result_path)
    b, b_sha = _load_object(b_result_path)
    stage0 = stage0_sha = None
    if stage0_result_path is not None:
        stage0, stage0_sha = _load_object(stage0_result_path)
        if stage0.get("schema_id") != (
            "FAILURE_MEMORY_STAGE0_ROLE_RETRIEVAL_RESULT_V1"
        ):
            raise ValueError("Stage0 result schema mismatch")

    stage1b = _validated_optional_authority(
        path=stage1b_result_path,
        stage="STAGE_1B_FROZEN_POLICY_FM0_FM3",
        expected_fixed_code_head=expected_fixed_code_head,
        expected_scientific_program_sha256=expected_scientific_program_sha256,
    )
    stage2 = _validated_optional_authority(
        path=stage2_result_path,
        stage="STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY",
        expected_fixed_code_head=expected_fixed_code_head,
        expected_scientific_program_sha256=expected_scientific_program_sha256,
    )
    stage3 = _validated_optional_authority(
        path=stage3_result_path,
        stage="STAGE_3_FROZEN_FORMAL_EVALUATION",
        expected_fixed_code_head=expected_fixed_code_head,
        expected_scientific_program_sha256=expected_scientific_program_sha256,
    )
    if formal_c_result_path is not None:
        raise ValueError(
            "Formal-C requires its separately Code-Approved Analyzer+Verifier authority validator; "
            "Memory closure may only emit the Q4 handoff."
        )
    if off_off_result_path is not None:
        raise ValueError(
            "OFF/OFF requires its separately Code-Approved training/evaluation authority validator; "
            "Memory closure may only emit the Q5 handoff."
        )
    formal_c = None
    off_off = None

    if a0.get("schema_id") != "FORMAL_A0_RESULT_AUTHORITY_V1":
        raise ValueError("A0 result schema mismatch")
    if a0.get("authority") != "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY":
        raise ValueError("A0 result authority mismatch")
    if a0.get("effect_counts") != {
        "Benefit": 0,
        "Harm": 0,
        "Neutral": 9,
    }:
        raise ValueError("A0 effect-count identity mismatch")
    if a0.get("general_representation_claim_authorized") is not False:
        raise ValueError("A0 unexpectedly authorizes general claim")

    if b.get("schema_id") != "FORMAL_B_MINIMAL_Q3_RESULT_AUTHORITY_V1":
        raise ValueError("B result schema mismatch")
    if b.get("result_authority_sha256") != (
        "ba2290e90631b8836ea93106fd1630237c7b45470bc465c1000e7fb18647fb7b"
    ):
        raise ValueError("B result authority identity mismatch")
    stress = b["registered_safety_stress_metrics"]
    if stress["coverage"] != {"denominator": 30, "numerator": 0}:
        raise ValueError("B stress coverage mismatch")
    if stress["unsafe_memory_exposure_rate"] != {
        "denominator": 30,
        "numerator": 0,
    }:
        raise ValueError("B stress safety mismatch")

    q1_status = ScientificQuestionStatusV1.OPEN
    q1_summary = (
        "A0 is local Neutral-only evidence; historical-experience value "
        "requires FM1-vs-FM0, multi-round accumulation, or real C2-vs-C1."
    )
    q1_evidence = [a0_sha]
    q1_next = [
        "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2",
        "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY_RESULT_AUTHORITY_V2",
        "FORMAL_C_RESULT_AUTHORITY_V1",
    ]
    q1_authority = stage1b or stage2 or formal_c
    if q1_authority is not None:
        q1_status = _apply_registered_decision(
            authority=q1_authority,
            question_id="Q1",
            supported=ScientificQuestionStatusV1.SUPPORTED,
            not_supported=ScientificQuestionStatusV1.NOT_SUPPORTED,
            inconclusive=ScientificQuestionStatusV1.OPEN,
        )
        q1_summary = q1_authority.summary("Q1")
        q1_evidence.append(q1_authority.file_sha256)
        q1_next = [] if q1_status is not ScientificQuestionStatusV1.OPEN else q1_next

    q2_status = ScientificQuestionStatusV1.PARTIAL_LOCAL_NULL
    q2_summary = (
        "A0 observed 9/9 Neutral local effects and no terminal representation "
        "superiority; a general structured-representation claim remains open."
    )
    q2_evidence = [a0_sha]
    q2_next = ["STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2"]
    q2_authority = stage1b or stage3
    if q2_authority is not None:
        q2_status = _apply_registered_decision(
            authority=q2_authority,
            question_id="Q2",
            supported=ScientificQuestionStatusV1.SUPPORTED,
            not_supported=ScientificQuestionStatusV1.NOT_SUPPORTED,
            inconclusive=ScientificQuestionStatusV1.PARTIAL_LOCAL_NULL,
        )
        q2_summary = q2_authority.summary("Q2")
        q2_evidence.append(q2_authority.file_sha256)
        q2_next = [] if q2_status in {
            ScientificQuestionStatusV1.SUPPORTED,
            ScientificQuestionStatusV1.NOT_SUPPORTED,
        } else q2_next

    q3_status = ScientificQuestionStatusV1.MIXED_POLICY_DIRECT
    q3_summary = (
        "Policy-direct B avoided unsafe exposure by complete abstention, so "
        "safety passed but retrieval utility was zero; candidate retrieval and "
        "system use remain open."
    )
    q3_evidence = [b_sha]
    if stage0 is not None:
        q3_evidence.append(stage0_sha)
        analyzer_recall = stage0.get("rates", {}).get("analyzer_recall_at_3")
        if not isinstance(analyzer_recall, dict):
            raise ValueError("Stage0 result lacks Analyzer recall@3")
        q3_summary += (
            " Stage 0 separately measured bounded Analyzer candidate recall "
            + repr(analyzer_recall)
            + "."
        )
    q3_next = [
        "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2",
        "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY_RESULT_AUTHORITY_V2",
        "STAGE_3_FROZEN_ID_OOD_RESULT_AUTHORITY_V2",
    ]
    q3_authority = stage3 or stage2 or stage1b
    if q3_authority is not None:
        q3_status = _apply_registered_decision(
            authority=q3_authority,
            question_id="Q3",
            supported=ScientificQuestionStatusV1.SUPPORTED,
            not_supported=ScientificQuestionStatusV1.NOT_SUPPORTED,
            inconclusive=ScientificQuestionStatusV1.MIXED_POLICY_DIRECT,
        )
        q3_summary = q3_authority.summary("Q3")
        q3_evidence.append(q3_authority.file_sha256)
        q3_next = [] if q3_status in {
            ScientificQuestionStatusV1.SUPPORTED,
            ScientificQuestionStatusV1.NOT_SUPPORTED,
        } else q3_next

    q4_status = ScientificQuestionStatusV1.OPEN
    q4_summary = (
        "Memory ports and same-state effect ingestion are ready, but real Analyzer "
        "proposals and real F0/F1 environment results are still required."
    )
    q4_evidence: list[str] = []
    q4_next = ["FORMAL_C_RESULT_AUTHORITY_V1"]
    if formal_c is not None:
        q4_status = _apply_registered_decision(
            authority=formal_c,
            question_id="Q4",
            supported=ScientificQuestionStatusV1.SUPPORTED,
            not_supported=ScientificQuestionStatusV1.NOT_SUPPORTED,
            inconclusive=ScientificQuestionStatusV1.OPEN,
        )
        q4_summary = formal_c.summary("Q4")
        q4_evidence.append(formal_c.file_sha256)
        q4_next = [] if q4_status is not ScientificQuestionStatusV1.OPEN else q4_next

    q5_status = ScientificQuestionStatusV1.DEFERRED_OPTIONAL_EXTENSION
    q5_summary = (
        "Parametric internalization is outside required Failure Memory V1; it "
        "requires external verified training and Memory-OFF/Harness-OFF evaluation."
    )
    q5_evidence: list[str] = []
    q5_next = [
        "VERIFIED_TRAINING_RESULT_AUTHORITY_V1",
        "OFF_OFF_POLICY_IMPROVEMENT_RESULT_AUTHORITY_V1",
    ]
    if off_off is not None:
        q5_status = _apply_registered_decision(
            authority=off_off,
            question_id="Q5",
            supported=ScientificQuestionStatusV1.SUPPORTED,
            not_supported=ScientificQuestionStatusV1.NOT_SUPPORTED,
            inconclusive=ScientificQuestionStatusV1.DEFERRED_OPTIONAL_EXTENSION,
        )
        q5_summary = off_off.summary("Q5")
        q5_evidence.append(off_off.file_sha256)
        q5_next = [] if q5_status in {
            ScientificQuestionStatusV1.SUPPORTED,
            ScientificQuestionStatusV1.NOT_SUPPORTED,
        } else q5_next

    return ScientificQuestionMatrixV1(
        rows=(
            ScientificQuestionEvidenceRowV1(
                question_id="Q1",
                status=q1_status,
                authorized_summary=q1_summary,
                evidence_sha256s=tuple(q1_evidence),
                forbidden_claims=(
                    "A0 alone proves historical Failure Memory value",
                    "Memory infrastructure tests prove repair-discovery benefit",
                ),
                required_next_authorities=tuple(q1_next),
            ),
            ScientificQuestionEvidenceRowV1(
                question_id="Q2",
                status=q2_status,
                authorized_summary=q2_summary,
                evidence_sha256s=tuple(q2_evidence),
                forbidden_claims=(
                    "A0 proves general structured representation superiority",
                    "A local null disproves procedural structure universally",
                ),
                required_next_authorities=tuple(q2_next),
            ),
            ScientificQuestionEvidenceRowV1(
                question_id="Q3",
                status=q3_status,
                authorized_summary=q3_summary,
                evidence_sha256s=tuple(q3_evidence),
                forbidden_claims=(
                    "zero unsafe exposure with zero coverage is useful retrieval",
                    "Policy exposure threshold is a universal Analyzer/Researcher gate",
                ),
                required_next_authorities=tuple(q3_next),
            ),
            ScientificQuestionEvidenceRowV1(
                question_id="Q4",
                status=q4_status,
                authorized_summary=q4_summary,
                evidence_sha256s=tuple(q4_evidence),
                forbidden_claims=(
                    "Memory ports implement a Hierarchical Analyzer",
                    "Analyzer rationale is Benefit/Harm authority",
                ),
                required_next_authorities=tuple(q4_next),
            ),
            ScientificQuestionEvidenceRowV1(
                question_id="Q5",
                status=q5_status,
                authorized_summary=q5_summary,
                evidence_sha256s=tuple(q5_evidence),
                forbidden_claims=(
                    "Memory-ON improvement is parametric policy improvement",
                    "Memory V1 infrastructure implements policy training",
                ),
                required_next_authorities=tuple(q5_next),
            ),
        )
    )
