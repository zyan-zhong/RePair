"""Frozen pre-outcome token-budget contracts for Failure Memory Package B."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import ClassVar, Iterable

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)


TOKEN_BUDGET_SCHEMA_V1 = "FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT_V1"
TOKEN_BUDGET_DOMAIN_V1 = "FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT_ID_V1"

SINGLE_RECORD_CANDIDATES_V1 = (256, 384, 512, 640, 768, 1024, 2048, 4096)
LIBRARY_TOTAL_CANDIDATES_V1 = (384, 512, 640, 768)
CALIBRATION_FAILURE_TARGET_V1 = 30
MIN_VALID_CALIBRATION_RECORDS_V1 = 20
COVERAGE_TARGET_V1 = 0.90
MAX_RECORD_COUNT_V1 = 3
MAX_SUPPORTED_SINGLE_RECORD_HARD_CEILING_V1 = 4096

NO_PERFORMANCE_ESTIMAND = "NO_PERFORMANCE_ESTIMAND"
FM1_TRUNCATION_POLICY = "FORBIDDEN"
FM1_LLM_COMPRESSION_POLICY = "FORBIDDEN"
FM1_POSTHOC_EXCERPT_POLICY = "FORBIDDEN"


def _require_text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in ("\x00", "\r", "\n"))
    ):
        raise ValueError(f"{name} must be nonempty single-line str")
    return value


def _require_int_tuple(
    name: str,
    value: object,
    *,
    expected: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise TypeError(f"{name} must be nonempty tuple")
    if any(type(item) is not int or item <= 0 for item in value):
        raise ValueError(f"{name} must contain positive ints")
    if tuple(sorted(value)) != value or len(set(value)) != len(value):
        raise ValueError(f"{name} must be unique ascending values")
    if expected is not None and value != expected:
        raise ValueError(f"{name} does not match frozen candidates")
    return value


def required_coverage_count_v1(
    sample_count: int,
    target: float = COVERAGE_TARGET_V1,
) -> int:
    if type(sample_count) is not int or sample_count < 1:
        raise ValueError("sample_count must be positive int")
    if not isinstance(target, float) or not 0 < target <= 1:
        raise ValueError("target must be float in (0,1]")
    return math.ceil(sample_count * target)


def choose_smallest_ceiling_v1(
    *,
    observed_token_counts: tuple[int, ...],
    candidates: tuple[int, ...],
    coverage_target: float = COVERAGE_TARGET_V1,
) -> int:
    if type(observed_token_counts) is not tuple or not observed_token_counts:
        raise ValueError("observed_token_counts must be nonempty tuple")
    if any(type(item) is not int or item < 0 for item in observed_token_counts):
        raise ValueError("observed token counts must be nonnegative ints")
    _require_int_tuple("candidates", candidates)

    required = required_coverage_count_v1(
        len(observed_token_counts),
        coverage_target,
    )

    for candidate in candidates:
        covered = sum(
            1 for value in observed_token_counts
            if value <= candidate
        )
        if covered >= required:
            return candidate

    raise ValueError("no frozen token-budget candidate reaches coverage target")


def coverage_fraction_v1(
    observed_token_counts: tuple[int, ...],
    ceiling: int,
) -> float:
    if type(ceiling) is not int or ceiling <= 0:
        raise ValueError("ceiling must be positive int")
    if type(observed_token_counts) is not tuple or not observed_token_counts:
        raise ValueError("observed_token_counts must be nonempty tuple")
    covered = sum(1 for value in observed_token_counts if value <= ceiling)
    return covered / len(observed_token_counts)


@dataclass(frozen=True, slots=True)
class FailureMemoryTokenBudgetContractV1:
    schema_id: str
    schema_version: int
    source_panel_manifest_sha256: str
    calibration_failure_panel_sha256: str
    analyzer_prompt_sha256: str
    analyzer_model: str
    tokenizer_id: str
    tokenizer_revision: str
    calibration_failure_count: int
    valid_calibration_record_count: int
    fm1_token_counts: tuple[int, ...]
    fm2_token_counts: tuple[int, ...]
    library_pack_token_counts: tuple[int, ...]
    single_record_candidates: tuple[int, ...]
    library_total_candidates: tuple[int, ...]
    coverage_target: float
    single_record_hard_ceiling: int
    library_total_hard_ceiling: int
    max_record_count: int
    fm1_truncation_policy: str
    fm1_llm_compression_policy: str
    fm1_posthoc_excerpt_policy: str
    performance_estimand: str
    memory_on_execution_used: bool
    contract_sha256: str | None = None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "source_panel_manifest_sha256",
            "calibration_failure_panel_sha256",
            "analyzer_prompt_sha256",
            "analyzer_model",
            "tokenizer_id",
            "tokenizer_revision",
            "calibration_failure_count",
            "valid_calibration_record_count",
            "fm1_token_counts",
            "fm2_token_counts",
            "library_pack_token_counts",
            "single_record_candidates",
            "library_total_candidates",
            "coverage_target",
            "single_record_hard_ceiling",
            "library_total_hard_ceiling",
            "max_record_count",
            "fm1_truncation_policy",
            "fm1_llm_compression_policy",
            "fm1_posthoc_excerpt_policy",
            "performance_estimand",
            "memory_on_execution_used",
            "contract_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != TOKEN_BUDGET_SCHEMA_V1:
            raise ValueError("token-budget schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("token-budget schema_version mismatch")

        for name in (
            "source_panel_manifest_sha256",
            "calibration_failure_panel_sha256",
            "analyzer_prompt_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))

        _require_text("analyzer_model", self.analyzer_model)
        _require_text("tokenizer_id", self.tokenizer_id)
        _require_text("tokenizer_revision", self.tokenizer_revision)

        if self.calibration_failure_count != CALIBRATION_FAILURE_TARGET_V1:
            raise ValueError("calibration_failure_count must equal 30")
        if (
            type(self.valid_calibration_record_count) is not int
            or self.valid_calibration_record_count
            < MIN_VALID_CALIBRATION_RECORDS_V1
            or self.valid_calibration_record_count
            > self.calibration_failure_count
        ):
            raise ValueError("valid calibration record count outside frozen bounds")

        for name in (
            "fm1_token_counts",
            "fm2_token_counts",
        ):
            values = getattr(self, name)
            if type(values) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if len(values) != self.valid_calibration_record_count:
                raise ValueError(f"{name} count mismatch")
            if any(type(item) is not int or item < 0 for item in values):
                raise ValueError(f"{name} must contain nonnegative ints")

        if type(self.library_pack_token_counts) is not tuple:
            raise TypeError("library_pack_token_counts must be tuple")
        if not self.library_pack_token_counts:
            raise ValueError("library pack calibration must be nonempty")
        if any(
            type(item) is not int or item < 0
            for item in self.library_pack_token_counts
        ):
            raise ValueError("library pack counts must be nonnegative ints")

        _require_int_tuple(
            "single_record_candidates",
            self.single_record_candidates,
            expected=SINGLE_RECORD_CANDIDATES_V1,
        )
        _require_int_tuple(
            "library_total_candidates",
            self.library_total_candidates,
            expected=LIBRARY_TOTAL_CANDIDATES_V1,
        )

        if self.coverage_target != COVERAGE_TARGET_V1:
            raise ValueError("coverage_target mismatch")

        expected_single = choose_smallest_ceiling_v1(
            observed_token_counts=self.fm1_token_counts,
            candidates=self.single_record_candidates,
            coverage_target=self.coverage_target,
        )
        if self.single_record_hard_ceiling != expected_single:
            raise ValueError("single-record ceiling does not match frozen rule")

        expected_library = choose_smallest_ceiling_v1(
            observed_token_counts=self.library_pack_token_counts,
            candidates=self.library_total_candidates,
            coverage_target=self.coverage_target,
        )
        if self.library_total_hard_ceiling != expected_library:
            raise ValueError("library-total ceiling does not match frozen rule")

        if self.single_record_hard_ceiling > MAX_SUPPORTED_SINGLE_RECORD_HARD_CEILING_V1:
            raise ValueError("single-record ceiling exceeds supported maximum")
        if self.max_record_count != MAX_RECORD_COUNT_V1:
            raise ValueError("max_record_count mismatch")

        if self.fm1_truncation_policy != FM1_TRUNCATION_POLICY:
            raise ValueError("FM1 truncation must remain forbidden")
        if self.fm1_llm_compression_policy != FM1_LLM_COMPRESSION_POLICY:
            raise ValueError("FM1 LLM compression must remain forbidden")
        if self.fm1_posthoc_excerpt_policy != FM1_POSTHOC_EXCERPT_POLICY:
            raise ValueError("FM1 post-hoc excerpt selection must remain forbidden")
        if self.performance_estimand != NO_PERFORMANCE_ESTIMAND:
            raise ValueError("budget calibration must have NO_PERFORMANCE_ESTIMAND")
        if self.memory_on_execution_used is not False:
            raise ValueError("Memory-ON execution is forbidden during calibration")

        expected_sha = sha256_bytes(
            TOKEN_BUDGET_DOMAIN_V1.encode("utf-8")
            + b"\0"
            + canonical_json_bytes(self._payload_without_sha())
        )
        if self.contract_sha256 is None:
            object.__setattr__(self, "contract_sha256", expected_sha)
        elif self.contract_sha256 != expected_sha:
            raise ValueError("token-budget contract SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_panel_manifest_sha256": self.source_panel_manifest_sha256,
            "calibration_failure_panel_sha256": self.calibration_failure_panel_sha256,
            "analyzer_prompt_sha256": self.analyzer_prompt_sha256,
            "analyzer_model": self.analyzer_model,
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_revision": self.tokenizer_revision,
            "calibration_failure_count": self.calibration_failure_count,
            "valid_calibration_record_count": self.valid_calibration_record_count,
            "fm1_token_counts": list(self.fm1_token_counts),
            "fm2_token_counts": list(self.fm2_token_counts),
            "library_pack_token_counts": list(self.library_pack_token_counts),
            "single_record_candidates": list(self.single_record_candidates),
            "library_total_candidates": list(self.library_total_candidates),
            "coverage_target": self.coverage_target,
            "single_record_hard_ceiling": self.single_record_hard_ceiling,
            "library_total_hard_ceiling": self.library_total_hard_ceiling,
            "max_record_count": self.max_record_count,
            "fm1_truncation_policy": self.fm1_truncation_policy,
            "fm1_llm_compression_policy": self.fm1_llm_compression_policy,
            "fm1_posthoc_excerpt_policy": self.fm1_posthoc_excerpt_policy,
            "performance_estimand": self.performance_estimand,
            "memory_on_execution_used": self.memory_on_execution_used,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "contract_sha256": self.contract_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "FailureMemoryTokenBudgetContractV1":
        if not isinstance(value, dict):
            raise TypeError("token-budget contract must be object")
        if frozenset(value) != cls._KEYS:
            raise ValueError("token-budget contract fields mismatch")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            source_panel_manifest_sha256=value["source_panel_manifest_sha256"],
            calibration_failure_panel_sha256=value["calibration_failure_panel_sha256"],
            analyzer_prompt_sha256=value["analyzer_prompt_sha256"],
            analyzer_model=value["analyzer_model"],
            tokenizer_id=value["tokenizer_id"],
            tokenizer_revision=value["tokenizer_revision"],
            calibration_failure_count=value["calibration_failure_count"],
            valid_calibration_record_count=value["valid_calibration_record_count"],
            fm1_token_counts=tuple(value["fm1_token_counts"]),
            fm2_token_counts=tuple(value["fm2_token_counts"]),
            library_pack_token_counts=tuple(value["library_pack_token_counts"]),
            single_record_candidates=tuple(value["single_record_candidates"]),
            library_total_candidates=tuple(value["library_total_candidates"]),
            coverage_target=value["coverage_target"],
            single_record_hard_ceiling=value["single_record_hard_ceiling"],
            library_total_hard_ceiling=value["library_total_hard_ceiling"],
            max_record_count=value["max_record_count"],
            fm1_truncation_policy=value["fm1_truncation_policy"],
            fm1_llm_compression_policy=value["fm1_llm_compression_policy"],
            fm1_posthoc_excerpt_policy=value["fm1_posthoc_excerpt_policy"],
            performance_estimand=value["performance_estimand"],
            memory_on_execution_used=value["memory_on_execution_used"],
            contract_sha256=value["contract_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "FailureMemoryTokenBudgetContractV1":
        return cls.from_dict(strict_json_loads(value))
