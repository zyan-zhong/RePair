"""Formal Package-B retrieval and applicability-safety evaluator.

Pure/offline scientific logic only:
- no model calls;
- no environment execution;
- no network;
- no hidden-state/Analyzer inference;
- no embedding or approximate-string retriever.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
import re
from typing import Iterable, Sequence

from pchsi.evaluation.canonical_evidence import strict_json_loads
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
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.retrieval_key import MemoryRetrievalKeyV1


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)

RANKER_ID_V1 = "CASEFOLD_WORD_JACCARD_V1"
TIE_POLICY_V1 = "ABSTAIN_ON_TOP_SCORE_TIE"
APPLICABILITY_EXPOSURE_POLICY_V1 = "ONLY_APPLICABLE_EXPOSE"
SOURCE_POPULATION_V1 = "TRAIN_RETRIEVAL_DEV"
THRESHOLD_PCTS_V1 = tuple(range(0, 51, 5))


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _domain_sha(domain: str, value: object) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\0"
        + _canonical_json_bytes(value)
    ).hexdigest()


def _require_text(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be nonempty")
    if "\x00" in value:
        raise ValueError(f"{name} contains NUL")
    return value


def _require_sha(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


class FormalBPoolV1(str, Enum):
    RETRIEVER_CALIBRATION_DEV = "RETRIEVER_CALIBRATION_DEV"
    RETRIEVER_SELECTION_VALIDATION = "RETRIEVER_SELECTION_VALIDATION"
    REGISTERED_SAFETY_STRESS = "REGISTERED_SAFETY_STRESS"


class FormalBGoldDispositionV1(str, Enum):
    EXPOSE_CORRECT_MEMORY = "EXPOSE_CORRECT_MEMORY"
    ABSTAIN_NO_APPLICABLE_MEMORY = "ABSTAIN_NO_APPLICABLE_MEMORY"


class FormalBDecisionReasonV1(str, Enum):
    EXPOSE_APPLICABLE = "EXPOSE_APPLICABLE"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    TOP_SCORE_TIE = "TOP_SCORE_TIE"
    NO_CANDIDATES = "NO_CANDIDATES"
    GATE_NOT_APPLICABLE = "GATE_NOT_APPLICABLE"
    GATE_CONFLICTING = "GATE_CONFLICTING"
    GATE_UNCERTAIN = "GATE_UNCERTAIN"


@dataclass(frozen=True, slots=True)
class FormalBGoldTargetV1:
    disposition: FormalBGoldDispositionV1
    expected_memory_lineage_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, FormalBGoldDispositionV1):
            raise TypeError("gold disposition type mismatch")
        if self.disposition is FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY:
            _require_sha(
                "expected_memory_lineage_id",
                self.expected_memory_lineage_id,
            )
        elif self.expected_memory_lineage_id is not None:
            raise ValueError("abstention gold must not carry a Memory lineage")

    def to_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "expected_memory_lineage_id": self.expected_memory_lineage_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> "FormalBGoldTargetV1":
        if not isinstance(value, dict):
            raise TypeError("gold target must be object")
        if set(value) != {"disposition", "expected_memory_lineage_id"}:
            raise ValueError("gold target fields mismatch")
        return cls(
            disposition=FormalBGoldDispositionV1(value["disposition"]),
            expected_memory_lineage_id=value["expected_memory_lineage_id"],
        )


@dataclass(frozen=True, slots=True)
class FormalBQueryV1:
    pool: FormalBPoolV1
    task_gamefile_group_id: str
    observation: str
    executed_transitions: tuple[ExecutedTransition, ...]
    admissible_commands: tuple[str, ...]
    interface_feedback: InterfaceFeedbackCode | None
    gold_target: FormalBGoldTargetV1
    independent_gold_artifact_sha256: str
    source_population: str = SOURCE_POPULATION_V1
    query_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pool, FormalBPoolV1):
            raise TypeError("pool type mismatch")
        _require_text("task_gamefile_group_id", self.task_gamefile_group_id)
        _require_text("observation", self.observation, allow_empty=True)
        if self.source_population != SOURCE_POPULATION_V1:
            raise ValueError(
                "Formal B queries must come only from TRAIN_RETRIEVAL_DEV"
            )
        if type(self.executed_transitions) is not tuple:
            raise TypeError("executed_transitions must be tuple")
        for item in self.executed_transitions:
            if not isinstance(item, ExecutedTransition):
                raise TypeError("executed transition type mismatch")
            _require_text("transition.action", item.action, allow_empty=True)
            _require_text(
                "transition.resulting_observation",
                item.resulting_observation,
                allow_empty=True,
            )
        if type(self.admissible_commands) is not tuple:
            raise TypeError("admissible_commands must be tuple")
        for item in self.admissible_commands:
            _require_text("admissible command", item, allow_empty=True)
        if self.interface_feedback is not None and not isinstance(
            self.interface_feedback,
            InterfaceFeedbackCode,
        ):
            raise TypeError("interface_feedback type mismatch")
        if not isinstance(self.gold_target, FormalBGoldTargetV1):
            raise TypeError("gold_target type mismatch")
        _require_sha(
            "independent_gold_artifact_sha256",
            self.independent_gold_artifact_sha256,
        )
        expected = _domain_sha(
            "FORMAL_B_QUERY_V1",
            self.identity_payload(),
        )
        if self.query_id is None:
            object.__setattr__(self, "query_id", expected)
        elif self.query_id != expected:
            raise ValueError("query_id mismatch")

    def identity_payload(self) -> dict[str, object]:
        return {
            "pool": self.pool.value,
            "task_gamefile_group_id": self.task_gamefile_group_id,
            "source_population": self.source_population,
            "policy_visible_query": {
                "observation": self.observation,
                "executed_transitions": [
                    {
                        "action": item.action,
                        "resulting_observation": item.resulting_observation,
                    }
                    for item in self.executed_transitions
                ],
                "admissible_commands": list(self.admissible_commands),
                "interface_feedback": (
                    None
                    if self.interface_feedback is None
                    else self.interface_feedback.value
                ),
            },
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.identity_payload(),
            "gold_target": self.gold_target.to_dict(),
            "independent_gold_artifact_sha256": (
                self.independent_gold_artifact_sha256
            ),
            "query_id": self.query_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> "FormalBQueryV1":
        if not isinstance(value, dict):
            raise TypeError("Formal B query must be object")
        expected = {
            "pool",
            "task_gamefile_group_id",
            "source_population",
            "policy_visible_query",
            "gold_target",
            "independent_gold_artifact_sha256",
            "query_id",
        }
        if set(value) != expected:
            raise ValueError("Formal B query fields mismatch")
        visible = value["policy_visible_query"]
        if not isinstance(visible, dict):
            raise TypeError("policy_visible_query must be object")
        if set(visible) != {
            "observation",
            "executed_transitions",
            "admissible_commands",
            "interface_feedback",
        }:
            raise ValueError("policy_visible_query fields mismatch")
        transitions_raw = visible["executed_transitions"]
        if not isinstance(transitions_raw, list):
            raise TypeError("executed_transitions must be array")
        transitions = []
        for raw in transitions_raw:
            if not isinstance(raw, dict) or set(raw) != {
                "action",
                "resulting_observation",
            }:
                raise ValueError("executed transition fields mismatch")
            transitions.append(
                ExecutedTransition(
                    action=raw["action"],
                    resulting_observation=raw[
                        "resulting_observation"
                    ],
                )
            )
        commands = visible["admissible_commands"]
        if not isinstance(commands, list):
            raise TypeError("admissible_commands must be array")
        feedback_raw = visible["interface_feedback"]
        feedback = (
            None
            if feedback_raw is None
            else InterfaceFeedbackCode(feedback_raw)
        )
        return cls(
            pool=FormalBPoolV1(value["pool"]),
            task_gamefile_group_id=value["task_gamefile_group_id"],
            source_population=value["source_population"],
            observation=visible["observation"],
            executed_transitions=tuple(transitions),
            admissible_commands=tuple(commands),
            interface_feedback=feedback,
            gold_target=FormalBGoldTargetV1.from_dict(
                value["gold_target"]
            ),
            independent_gold_artifact_sha256=value[
                "independent_gold_artifact_sha256"
            ],
            query_id=value["query_id"],
        )


@dataclass(frozen=True, slots=True)
class FormalBIndependentGoldRowV1:
    query_id: str
    gold_target: FormalBGoldTargetV1
    independent_gold_artifact_sha256: str

    def __post_init__(self) -> None:
        _require_sha("query_id", self.query_id)
        if not isinstance(self.gold_target, FormalBGoldTargetV1):
            raise TypeError("independent gold target type mismatch")
        _require_sha(
            "independent_gold_artifact_sha256",
            self.independent_gold_artifact_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "gold_target": self.gold_target.to_dict(),
            "independent_gold_artifact_sha256": (
                self.independent_gold_artifact_sha256
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "FormalBIndependentGoldRowV1":
        if not isinstance(value, dict):
            raise TypeError("independent gold row must be object")
        if set(value) != {
            "query_id",
            "gold_target",
            "independent_gold_artifact_sha256",
        }:
            raise ValueError("independent gold row fields mismatch")
        return cls(
            query_id=value["query_id"],
            gold_target=FormalBGoldTargetV1.from_dict(
                value["gold_target"]
            ),
            independent_gold_artifact_sha256=value[
                "independent_gold_artifact_sha256"
            ],
        )


@dataclass(frozen=True, slots=True)
class FormalBIndependentGoldAuthorityV1:
    rows: tuple[FormalBIndependentGoldRowV1, ...]
    source_population: str = SOURCE_POPULATION_V1
    scientific_execution_authorized: bool = False
    schema_id: str = "FORMAL_B_INDEPENDENT_GOLD_AUTHORITY_V1"
    schema_version: int = 1
    authority_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.schema_id != "FORMAL_B_INDEPENDENT_GOLD_AUTHORITY_V1":
            raise ValueError("independent gold authority schema mismatch")
        if self.schema_version != 1:
            raise ValueError("independent gold authority version mismatch")
        if self.source_population != SOURCE_POPULATION_V1:
            raise ValueError("independent gold source population mismatch")
        if self.scientific_execution_authorized is not False:
            raise ValueError("independent gold authority cannot self-authorize")
        if type(self.rows) is not tuple or not self.rows:
            raise ValueError("independent gold rows must be nonempty tuple")
        if any(
            not isinstance(row, FormalBIndependentGoldRowV1)
            for row in self.rows
        ):
            raise TypeError("independent gold row type mismatch")
        query_ids = tuple(row.query_id for row in self.rows)
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("independent gold query IDs must be unique")
        expected = _domain_sha(
            "FORMAL_B_INDEPENDENT_GOLD_AUTHORITY_V1",
            self._payload_without_sha(),
        )
        if self.authority_sha256 is None:
            object.__setattr__(self, "authority_sha256", expected)
        elif self.authority_sha256 != expected:
            raise ValueError("independent gold authority SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "source_population": self.source_population,
            "rows": [row.to_dict() for row in self.rows],
            "scientific_execution_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "authority_sha256": self.authority_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "FormalBIndependentGoldAuthorityV1":
        if not isinstance(value, dict):
            raise TypeError("independent gold authority must be object")
        expected = {
            "schema_id",
            "schema_version",
            "source_population",
            "rows",
            "scientific_execution_authorized",
            "authority_sha256",
        }
        if set(value) != expected:
            raise ValueError("independent gold authority fields mismatch")
        rows = value["rows"]
        if not isinstance(rows, list):
            raise TypeError("independent gold rows must be array")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            source_population=value["source_population"],
            rows=tuple(
                FormalBIndependentGoldRowV1.from_dict(row)
                for row in rows
            ),
            scientific_execution_authorized=value[
                "scientific_execution_authorized"
            ],
            authority_sha256=value["authority_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: bytes | str,
    ) -> "FormalBIndependentGoldAuthorityV1":
        return cls.from_dict(strict_json_loads(value))

@dataclass(frozen=True, slots=True)
class FormalBGoldPanelV1:
    active_snapshot_sha256: str
    independent_gold_authority_sha256: str
    queries: tuple[FormalBQueryV1, ...]
    scientific_execution_authorized: bool = False
    schema_id: str = "FORMAL_B_GOLD_PANEL_V1"
    schema_version: int = 1
    panel_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.schema_id != "FORMAL_B_GOLD_PANEL_V1":
            raise ValueError("gold panel schema mismatch")
        if self.schema_version != 1:
            raise ValueError("gold panel schema version mismatch")
        if self.scientific_execution_authorized is not False:
            raise ValueError("gold panel cannot self-authorize science")
        _require_sha("active_snapshot_sha256", self.active_snapshot_sha256)
        _require_sha(
            "independent_gold_authority_sha256",
            self.independent_gold_authority_sha256,
        )
        if type(self.queries) is not tuple or not self.queries:
            raise ValueError("gold panel queries must be nonempty tuple")
        if len({row.query_id for row in self.queries}) != len(self.queries):
            raise ValueError("gold panel query IDs must be unique")
        validate_formal_b_pool_isolation_v1(self.queries)
        expected = _domain_sha(
            "FORMAL_B_GOLD_PANEL_V1",
            self._payload_without_sha(),
        )
        if self.panel_sha256 is None:
            object.__setattr__(self, "panel_sha256", expected)
        elif self.panel_sha256 != expected:
            raise ValueError("gold panel SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "active_snapshot_sha256": self.active_snapshot_sha256,
            "independent_gold_authority_sha256": (
                self.independent_gold_authority_sha256
            ),
            "queries": [row.to_dict() for row in self.queries],
            "scientific_execution_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "panel_sha256": self.panel_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "FormalBGoldPanelV1":
        if not isinstance(value, dict):
            raise TypeError("gold panel must be object")
        expected = {
            "schema_id",
            "schema_version",
            "active_snapshot_sha256",
            "independent_gold_authority_sha256",
            "queries",
            "scientific_execution_authorized",
            "panel_sha256",
        }
        if set(value) != expected:
            raise ValueError("gold panel fields mismatch")
        rows = value["queries"]
        if not isinstance(rows, list):
            raise TypeError("gold panel queries must be array")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            active_snapshot_sha256=value["active_snapshot_sha256"],
            independent_gold_authority_sha256=value[
                "independent_gold_authority_sha256"
            ],
            queries=tuple(FormalBQueryV1.from_dict(x) for x in rows),
            scientific_execution_authorized=value[
                "scientific_execution_authorized"
            ],
            panel_sha256=value["panel_sha256"],
        )

    @classmethod
    def from_json(cls, value: bytes | str) -> "FormalBGoldPanelV1":
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        raw = strict_json_loads(value)
        return cls.from_dict(raw)


def validate_panel_against_independent_gold_authority_v1(
    *,
    panel: FormalBGoldPanelV1,
    authority: FormalBIndependentGoldAuthorityV1,
) -> None:
    if not isinstance(panel, FormalBGoldPanelV1):
        raise TypeError("panel type mismatch")
    if not isinstance(authority, FormalBIndependentGoldAuthorityV1):
        raise TypeError("independent gold authority type mismatch")
    if (
        panel.independent_gold_authority_sha256
        != authority.authority_sha256
    ):
        raise ValueError("panel/independent-gold authority SHA mismatch")

    panel_rows = {row.query_id: row for row in panel.queries}
    gold_rows = {row.query_id: row for row in authority.rows}
    if set(panel_rows) != set(gold_rows):
        raise ValueError("panel/independent-gold query population mismatch")

    for query_id in sorted(panel_rows):
        query = panel_rows[query_id]
        gold = gold_rows[query_id]
        if query.gold_target != gold.gold_target:
            raise ValueError(
                "panel gold target differs from independent authority"
            )
        if (
            query.independent_gold_artifact_sha256
            != gold.independent_gold_artifact_sha256
        ):
            raise ValueError(
                "panel row evidence SHA differs from independent authority"
            )

@dataclass(frozen=True, slots=True)
class FormalBCandidateV1:
    record: ProceduralFailureMemoryRecordV1
    retrieval_key: MemoryRetrievalKeyV1

    def __post_init__(self) -> None:
        if not isinstance(
            self.record,
            ProceduralFailureMemoryRecordV1,
        ):
            raise TypeError("record type mismatch")
        if not isinstance(self.retrieval_key, MemoryRetrievalKeyV1):
            raise TypeError("retrieval_key type mismatch")
        binding = self.retrieval_key.record_binding
        if binding.memory_lineage_id != self.record.memory_lineage_id:
            raise ValueError("candidate lineage/key binding mismatch")
        if binding.record_version != self.record.record_version:
            raise ValueError("candidate version/key binding mismatch")
        if (
            binding.canonical_record_sha256
            != self.record.canonical_record_sha256
        ):
            raise ValueError("candidate record SHA/key binding mismatch")
        hard = self.retrieval_key.hard_filter_metadata
        if hard.access_scope is not self.record.governance_state.access_scope:
            raise ValueError("candidate access-scope/key binding mismatch")
        if hard.lifecycle_status is not self.record.governance_state.lifecycle_status:
            raise ValueError("candidate lifecycle/key binding mismatch")


@dataclass(frozen=True, slots=True)
class FormalBRetrieverConfigV1:
    threshold_pct: int
    ranker_id: str = RANKER_ID_V1
    tie_policy: str = TIE_POLICY_V1
    applicability_exposure_policy: str = APPLICABILITY_EXPOSURE_POLICY_V1

    def __post_init__(self) -> None:
        if type(self.threshold_pct) is not int:
            raise TypeError("threshold_pct must be int")
        if self.threshold_pct not in THRESHOLD_PCTS_V1:
            raise ValueError("threshold_pct outside frozen grid")
        if self.ranker_id != RANKER_ID_V1:
            raise ValueError("ranker_id mismatch")
        if self.tie_policy != TIE_POLICY_V1:
            raise ValueError("tie policy mismatch")
        if (
            self.applicability_exposure_policy
            != APPLICABILITY_EXPOSURE_POLICY_V1
        ):
            raise ValueError("applicability exposure policy mismatch")

    @property
    def threshold(self) -> Fraction:
        return Fraction(self.threshold_pct, 100)

    def to_dict(self) -> dict[str, object]:
        return {
            "threshold_pct": self.threshold_pct,
            "ranker_id": self.ranker_id,
            "tie_policy": self.tie_policy,
            "applicability_exposure_policy": (
                self.applicability_exposure_policy
            ),
        }

    @property
    def config_sha256(self) -> str:
        return _domain_sha(
            "FORMAL_B_RETRIEVER_CONFIG_V1",
            self.to_dict(),
        )


@dataclass(frozen=True, slots=True)
class FormalBMetricFractionV1:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or self.numerator < 0:
            raise ValueError("metric numerator must be nonnegative int")
        if type(self.denominator) is not int or self.denominator < 0:
            raise ValueError("metric denominator must be nonnegative int")
        if self.numerator > self.denominator:
            raise ValueError("metric numerator exceeds denominator")

    @property
    def fraction(self) -> Fraction:
        if self.denominator == 0:
            return Fraction(0, 1)
        return Fraction(self.numerator, self.denominator)

    def to_dict(self) -> dict[str, int]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass(frozen=True, slots=True)
class FormalBDecisionV1:
    query_id: str
    config_sha256: str
    top_score_numerator: int
    top_score_denominator: int
    pre_gate_memory_lineage_id: str | None
    exposed_memory_lineage_id: str | None
    applicability_disposition: str | None
    decision_reason: FormalBDecisionReasonV1

    def to_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "config_sha256": self.config_sha256,
            "top_score": {
                "numerator": self.top_score_numerator,
                "denominator": self.top_score_denominator,
            },
            "pre_gate_memory_lineage_id": self.pre_gate_memory_lineage_id,
            "exposed_memory_lineage_id": self.exposed_memory_lineage_id,
            "applicability_disposition": self.applicability_disposition,
            "decision_reason": self.decision_reason.value,
        }


@dataclass(frozen=True, slots=True)
class FormalBPanelMetricsV1:
    row_count: int
    expected_exposure_count: int
    expected_abstain_count: int
    exposure_count: int
    abstention_count: int
    correct_exposure_count: int
    wrong_exposure_count: int
    non_applicable_exposure_count: int
    pre_gate_top1_hit_count: int
    disposition_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for name in (
            "row_count",
            "expected_exposure_count",
            "expected_abstain_count",
            "exposure_count",
            "abstention_count",
            "correct_exposure_count",
            "wrong_exposure_count",
            "non_applicable_exposure_count",
            "pre_gate_top1_hit_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be nonnegative int")
        if self.expected_exposure_count + self.expected_abstain_count != self.row_count:
            raise ValueError("gold denominator partition mismatch")
        if self.exposure_count + self.abstention_count != self.row_count:
            raise ValueError("decision denominator partition mismatch")

    @property
    def unsafe_exposure_count(self) -> int:
        return (
            self.wrong_exposure_count
            + self.non_applicable_exposure_count
        )

    @property
    def unsafe_memory_exposure_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.unsafe_exposure_count,
            self.row_count,
        )

    @property
    def wrong_memory_exposure_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.wrong_exposure_count,
            self.row_count,
        )

    @property
    def non_applicable_memory_exposure_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.non_applicable_exposure_count,
            self.expected_abstain_count,
        )

    @property
    def correct_memory_exposure_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.correct_exposure_count,
            self.expected_exposure_count,
        )

    @property
    def abstention_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.abstention_count,
            self.row_count,
        )

    @property
    def coverage(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.exposure_count,
            self.row_count,
        )

    @property
    def selective_accuracy(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.correct_exposure_count,
            self.exposure_count,
        )

    @property
    def pre_gate_top1_hit_rate(self) -> FormalBMetricFractionV1:
        return FormalBMetricFractionV1(
            self.pre_gate_top1_hit_count,
            self.expected_exposure_count,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "expected_exposure_count": self.expected_exposure_count,
            "expected_abstain_count": self.expected_abstain_count,
            "exposure_count": self.exposure_count,
            "abstention_count": self.abstention_count,
            "correct_exposure_count": self.correct_exposure_count,
            "wrong_exposure_count": self.wrong_exposure_count,
            "non_applicable_exposure_count": (
                self.non_applicable_exposure_count
            ),
            "pre_gate_top1_hit_count": self.pre_gate_top1_hit_count,
            "unsafe_exposure_count": self.unsafe_exposure_count,
            "unsafe_memory_exposure_rate": (
                self.unsafe_memory_exposure_rate.to_dict()
            ),
            "wrong_memory_exposure_rate": (
                self.wrong_memory_exposure_rate.to_dict()
            ),
            "non_applicable_memory_exposure_rate": (
                self.non_applicable_memory_exposure_rate.to_dict()
            ),
            "correct_memory_exposure_rate": (
                self.correct_memory_exposure_rate.to_dict()
            ),
            "abstention_rate": self.abstention_rate.to_dict(),
            "coverage": self.coverage.to_dict(),
            "selective_accuracy": self.selective_accuracy.to_dict(),
            "pre_gate_top1_hit_rate": (
                self.pre_gate_top1_hit_rate.to_dict()
            ),
            "applicability_disposition_counts": {
                key: value
                for key, value in self.disposition_counts
            },
        }


@dataclass(frozen=True, slots=True)
class FormalBThresholdReportV1:
    config: FormalBRetrieverConfigV1
    decisions: tuple[FormalBDecisionV1, ...]
    metrics: FormalBPanelMetricsV1

    def to_dict(self) -> dict[str, object]:
        return {
            "config": {
                **self.config.to_dict(),
                "config_sha256": self.config.config_sha256,
            },
            "decisions": [row.to_dict() for row in self.decisions],
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FormalBProtocolResultV1:
    calibration_reports: tuple[FormalBThresholdReportV1, ...]
    calibration_candidate_threshold_pcts: tuple[int, ...]
    validation_reports: tuple[FormalBThresholdReportV1, ...]
    selected_config: FormalBRetrieverConfigV1
    stress_report: FormalBThresholdReportV1

    def to_summary_dict(self) -> dict[str, object]:
        selected = next(
            row
            for row in self.validation_reports
            if row.config.threshold_pct == self.selected_config.threshold_pct
        )
        return {
            "schema_id": "FORMAL_B_PROTOCOL_RESULT_SUMMARY_V1",
            "schema_version": 1,
            "ranker_id": RANKER_ID_V1,
            "threshold_grid_pct": list(THRESHOLD_PCTS_V1),
            "calibration_candidate_threshold_pcts": list(
                self.calibration_candidate_threshold_pcts
            ),
            "selected_config": {
                **self.selected_config.to_dict(),
                "config_sha256": self.selected_config.config_sha256,
            },
            "selection_validation_metrics": selected.metrics.to_dict(),
            "registered_safety_stress_metrics": (
                self.stress_report.metrics.to_dict()
            ),
            "applicability_gold_role": (
                "DIAGNOSTIC_SAFETY_AUTHORITY_ONLY"
            ),
            "causal_benefit_harm_authority": False,
            "valid_seen_allowed": False,
            "valid_unseen_allowed": False,
        }


def validate_formal_b_pool_isolation_v1(
    queries: Iterable[FormalBQueryV1],
) -> None:
    rows = tuple(queries)
    pools: dict[FormalBPoolV1, set[str]] = {
        pool: set() for pool in FormalBPoolV1
    }
    for row in rows:
        if not isinstance(row, FormalBQueryV1):
            raise TypeError("Formal B pool row type mismatch")
        pools[row.pool].add(row.task_gamefile_group_id)

    pool_items = list(FormalBPoolV1)
    for index, left in enumerate(pool_items):
        for right in pool_items[index + 1 :]:
            overlap = pools[left].intersection(pools[right])
            if overlap:
                raise ValueError(
                    "Formal B task/gamefile group overlap: "
                    + f"{left.value} vs {right.value}: "
                    + repr(sorted(overlap))
                )


def _feedback_text(
    feedback: InterfaceFeedbackCode | None,
) -> str:
    if feedback is None:
        return ""
    if feedback is InterfaceFeedbackCode.FORMAT_ERROR_V1:
        return FORMAT_ERROR_V1
    if feedback is InterfaceFeedbackCode.INVALID_ACTION_V1:
        return INVALID_ACTION_V1
    raise TypeError("unsupported interface feedback")


def build_formal_b_query_scoring_text_v1(
    query: FormalBQueryV1,
) -> str:
    if not isinstance(query, FormalBQueryV1):
        raise TypeError("query type mismatch")
    lines = [query.observation]
    for item in query.executed_transitions[-8:]:
        lines.append(item.action)
        lines.append(item.resulting_observation)
    feedback = _feedback_text(query.interface_feedback)
    if feedback:
        lines.append(feedback)
    return "\n".join(lines)


def casefold_word_tokens_v1(text: str) -> frozenset[str]:
    _require_text("text", text, allow_empty=True)
    return frozenset(_WORD_RE.findall(text.casefold()))


def jaccard_score_v1(
    left_text: str,
    right_text: str,
) -> Fraction:
    left = casefold_word_tokens_v1(left_text)
    right = casefold_word_tokens_v1(right_text)
    union = left.union(right)
    if not union:
        return Fraction(0, 1)
    return Fraction(len(left.intersection(right)), len(union))


def _record_applicability_cues(
    record: ProceduralFailureMemoryRecordV1,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    applicability = record.applicability
    return (
        tuple(x.condition_text for x in applicability.activation),
        tuple(x.condition_text for x in applicability.release),
        tuple(x.condition_text for x in applicability.non_applicability),
    )


def evaluate_formal_b_query_v1(
    *,
    query: FormalBQueryV1,
    candidates: Sequence[FormalBCandidateV1],
    config: FormalBRetrieverConfigV1,
) -> FormalBDecisionV1:
    if not isinstance(query, FormalBQueryV1):
        raise TypeError("query type mismatch")
    if not isinstance(config, FormalBRetrieverConfigV1):
        raise TypeError("config type mismatch")
    candidate_tuple = tuple(candidates)
    if any(not isinstance(x, FormalBCandidateV1) for x in candidate_tuple):
        raise TypeError("candidate type mismatch")

    if not candidate_tuple:
        return FormalBDecisionV1(
            query_id=query.query_id,
            config_sha256=config.config_sha256,
            top_score_numerator=0,
            top_score_denominator=1,
            pre_gate_memory_lineage_id=None,
            exposed_memory_lineage_id=None,
            applicability_disposition=None,
            decision_reason=FormalBDecisionReasonV1.NO_CANDIDATES,
        )

    query_text = build_formal_b_query_scoring_text_v1(query)
    scored = tuple(
        (
            jaccard_score_v1(
                query_text,
                candidate.retrieval_key.scoring_payload.semantic_retrieval_text,
            ),
            candidate,
        )
        for candidate in candidate_tuple
    )
    top_score = max(score for score, _ in scored)
    top = tuple(
        candidate for score, candidate in scored if score == top_score
    )

    if len(top) != 1:
        return FormalBDecisionV1(
            query_id=query.query_id,
            config_sha256=config.config_sha256,
            top_score_numerator=top_score.numerator,
            top_score_denominator=top_score.denominator,
            pre_gate_memory_lineage_id=None,
            exposed_memory_lineage_id=None,
            applicability_disposition=None,
            decision_reason=FormalBDecisionReasonV1.TOP_SCORE_TIE,
        )

    candidate = top[0]
    lineage = candidate.record.memory_lineage_id

    if top_score < config.threshold:
        return FormalBDecisionV1(
            query_id=query.query_id,
            config_sha256=config.config_sha256,
            top_score_numerator=top_score.numerator,
            top_score_denominator=top_score.denominator,
            pre_gate_memory_lineage_id=lineage,
            exposed_memory_lineage_id=None,
            applicability_disposition=None,
            decision_reason=FormalBDecisionReasonV1.BELOW_THRESHOLD,
        )

    activation, release, nonapp = _record_applicability_cues(
        candidate.record
    )
    gate = evaluate_direct_applicability_v1(
        activation_cues=activation,
        release_cues=release,
        non_applicability_cues=nonapp,
        observation=query.observation,
        executed_transitions=query.executed_transitions,
        admissible_commands=query.admissible_commands,
        interface_feedback=query.interface_feedback,
    )

    if gate.disposition is DirectApplicabilityDispositionV1.APPLICABLE:
        exposed = lineage
        reason = FormalBDecisionReasonV1.EXPOSE_APPLICABLE
    else:
        exposed = None
        mapping = {
            DirectApplicabilityDispositionV1.NOT_APPLICABLE: (
                FormalBDecisionReasonV1.GATE_NOT_APPLICABLE
            ),
            DirectApplicabilityDispositionV1.CONFLICTING: (
                FormalBDecisionReasonV1.GATE_CONFLICTING
            ),
            DirectApplicabilityDispositionV1.UNCERTAIN: (
                FormalBDecisionReasonV1.GATE_UNCERTAIN
            ),
        }
        reason = mapping[gate.disposition]

    return FormalBDecisionV1(
        query_id=query.query_id,
        config_sha256=config.config_sha256,
        top_score_numerator=top_score.numerator,
        top_score_denominator=top_score.denominator,
        pre_gate_memory_lineage_id=lineage,
        exposed_memory_lineage_id=exposed,
        applicability_disposition=gate.disposition.value,
        decision_reason=reason,
    )


def evaluate_formal_b_panel_v1(
    *,
    queries: Sequence[FormalBQueryV1],
    candidates: Sequence[FormalBCandidateV1],
    config: FormalBRetrieverConfigV1,
) -> FormalBThresholdReportV1:
    rows = tuple(queries)
    if not rows:
        raise ValueError("Formal B panel stage must be nonempty")
    decisions = tuple(
        evaluate_formal_b_query_v1(
            query=query,
            candidates=candidates,
            config=config,
        )
        for query in rows
    )

    expected_exposure = sum(
        row.gold_target.disposition
        is FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY
        for row in rows
    )
    expected_abstain = len(rows) - expected_exposure
    exposure = sum(
        row.exposed_memory_lineage_id is not None
        for row in decisions
    )
    correct = 0
    wrong = 0
    nonapp = 0
    pre_gate_hits = 0
    dispositions: dict[str, int] = {}

    for query, decision in zip(rows, decisions, strict=True):
        if decision.applicability_disposition is not None:
            dispositions[decision.applicability_disposition] = (
                dispositions.get(decision.applicability_disposition, 0) + 1
            )

        if (
            query.gold_target.disposition
            is FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY
        ):
            expected_lineage = (
                query.gold_target.expected_memory_lineage_id
            )
            if decision.pre_gate_memory_lineage_id == expected_lineage:
                pre_gate_hits += 1
            if decision.exposed_memory_lineage_id is not None:
                if decision.exposed_memory_lineage_id == expected_lineage:
                    correct += 1
                else:
                    wrong += 1
        elif decision.exposed_memory_lineage_id is not None:
            nonapp += 1

    metrics = FormalBPanelMetricsV1(
        row_count=len(rows),
        expected_exposure_count=expected_exposure,
        expected_abstain_count=expected_abstain,
        exposure_count=exposure,
        abstention_count=len(rows) - exposure,
        correct_exposure_count=correct,
        wrong_exposure_count=wrong,
        non_applicable_exposure_count=nonapp,
        pre_gate_top1_hit_count=pre_gate_hits,
        disposition_counts=tuple(sorted(dispositions.items())),
    )
    return FormalBThresholdReportV1(
        config=config,
        decisions=decisions,
        metrics=metrics,
    )


def _selection_key(
    report: FormalBThresholdReportV1,
) -> tuple[
    Fraction,
    Fraction,
    Fraction,
    Fraction,
    Fraction,
    Fraction,
    int,
]:
    m = report.metrics
    return (
        m.unsafe_memory_exposure_rate.fraction,
        m.wrong_memory_exposure_rate.fraction,
        m.non_applicable_memory_exposure_rate.fraction,
        -m.correct_memory_exposure_rate.fraction,
        -m.selective_accuracy.fraction,
        -m.coverage.fraction,
        -report.config.threshold_pct,
    )


def select_calibration_candidates_v1(
    reports: Sequence[FormalBThresholdReportV1],
) -> tuple[int, ...]:
    report_tuple = tuple(reports)
    observed = tuple(row.config.threshold_pct for row in report_tuple)
    if observed != THRESHOLD_PCTS_V1:
        raise ValueError("calibration must evaluate the exact frozen threshold grid")
    ranked = sorted(report_tuple, key=_selection_key)
    return tuple(row.config.threshold_pct for row in ranked[:3])


def select_validation_config_v1(
    reports: Sequence[FormalBThresholdReportV1],
    calibration_candidate_threshold_pcts: Sequence[int],
) -> FormalBRetrieverConfigV1:
    report_tuple = tuple(reports)
    candidates = tuple(calibration_candidate_threshold_pcts)
    if len(candidates) != 3 or len(set(candidates)) != 3:
        raise ValueError("selection validation requires exactly three candidates")
    observed = tuple(row.config.threshold_pct for row in report_tuple)
    if set(observed) != set(candidates) or len(observed) != 3:
        raise ValueError("validation reports do not match calibration candidates")
    selected = min(report_tuple, key=_selection_key)
    return selected.config


def run_formal_b_three_stage_protocol_v1(
    *,
    panel: FormalBGoldPanelV1,
    candidates: Sequence[FormalBCandidateV1],
) -> FormalBProtocolResultV1:
    if not isinstance(panel, FormalBGoldPanelV1):
        raise TypeError("panel type mismatch")
    candidate_tuple = tuple(candidates)
    if not candidate_tuple:
        raise ValueError("Formal B active snapshot has no candidates")
    lineages = {x.record.memory_lineage_id for x in candidate_tuple}
    for row in panel.queries:
        if (
            row.gold_target.disposition
            is FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY
            and row.gold_target.expected_memory_lineage_id not in lineages
        ):
            raise ValueError(
                "gold exposure target not present in frozen active snapshot"
            )

    by_pool = {
        pool: tuple(row for row in panel.queries if row.pool is pool)
        for pool in FormalBPoolV1
    }
    for pool, rows in by_pool.items():
        if not rows:
            raise ValueError(f"Formal B pool is empty: {pool.value}")
        dispositions = {
            row.gold_target.disposition
            for row in rows
        }
        if dispositions != {
            FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY,
            FormalBGoldDispositionV1.ABSTAIN_NO_APPLICABLE_MEMORY,
        }:
            raise ValueError(
                "Formal B pool must contain both exposure and abstention gold: "
                + pool.value
            )

    lineages = tuple(
        candidate.record.memory_lineage_id
        for candidate in candidate_tuple
    )
    if len(lineages) != len(set(lineages)):
        raise ValueError("Formal B candidate Memory lineages must be unique")

    calibration_reports = tuple(
        evaluate_formal_b_panel_v1(
            queries=by_pool[FormalBPoolV1.RETRIEVER_CALIBRATION_DEV],
            candidates=candidate_tuple,
            config=FormalBRetrieverConfigV1(threshold_pct=pct),
        )
        for pct in THRESHOLD_PCTS_V1
    )
    calibration_candidates = select_calibration_candidates_v1(
        calibration_reports
    )

    validation_reports = tuple(
        evaluate_formal_b_panel_v1(
            queries=by_pool[
                FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION
            ],
            candidates=candidate_tuple,
            config=FormalBRetrieverConfigV1(threshold_pct=pct),
        )
        for pct in calibration_candidates
    )
    selected = select_validation_config_v1(
        validation_reports,
        calibration_candidates,
    )

    stress_report = evaluate_formal_b_panel_v1(
        queries=by_pool[FormalBPoolV1.REGISTERED_SAFETY_STRESS],
        candidates=candidate_tuple,
        config=selected,
    )
    return FormalBProtocolResultV1(
        calibration_reports=calibration_reports,
        calibration_candidate_threshold_pcts=calibration_candidates,
        validation_reports=validation_reports,
        selected_config=selected,
        stress_report=stress_report,
    )
