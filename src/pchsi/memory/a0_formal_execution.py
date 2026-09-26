"""Pure Formal Package-A scientific execution/evidence contracts.

No model, environment, retriever, network, or scheduler execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re

from pchsi.evaluation.canonical_evidence import canonical_json_bytes


_SHA = re.compile(r"^[0-9a-f]{64}$")
_ARMS = ("M0", "M1", "M2", "M3")
_DIRECT = "DIRECT_FIXED_RECORD_NO_RETRIEVAL"


def _sha(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{name} must be nonempty NUL-free str")
    return value


def _nonnegative(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int")
    return value


def _domain_sha(domain: str, payload: object) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _exact_dict(
    value: object,
    expected: set[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = set(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _payload_sha_for_runtime_arm(
    *,
    arm_id: str,
    policy_visible_payload: object,
) -> str | None:
    if arm_id == "M0":
        if policy_visible_payload != []:
            raise ValueError("runtime M0 payload must be exact empty list")
        return None
    if not isinstance(policy_visible_payload, dict):
        raise ValueError("runtime Memory arm payload must be object")
    return hashlib.sha256(
        canonical_json_bytes(policy_visible_payload)
    ).hexdigest()


def validate_a0_manifest_binding_top_level_v1(
    *,
    manifest: object,
    binding: object,
) -> None:
    if not isinstance(manifest, dict) or not isinstance(binding, dict):
        raise TypeError("manifest/binding must be objects")

    if (
        manifest.get("schema_id") != "MEMORY_A0_SCIENTIFIC_MANIFEST_V1"
        or manifest.get("schema_version") != 1
    ):
        raise ValueError("Formal A manifest schema mismatch")
    if manifest.get("scientific_execution_authorized") is not False:
        raise ValueError("Formal A manifest cannot self-authorize")
    if manifest.get("effect_scope") != "SOURCE_STATE_LOCAL_PAIRED":
        raise ValueError("Formal A manifest effect scope mismatch")
    if manifest.get("authority") != "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY":
        raise ValueError("Formal A manifest authority mismatch")
    if manifest.get("paper_main_representation_claim_authorized") is not False:
        raise ValueError("Formal A manifest overclaims representation authority")
    if manifest.get("a1_status") != "OPTIONAL_CONDITIONAL":
        raise ValueError("Formal A A1 status mismatch")

    stored_manifest_sha = _sha(
        "manifest_sha256",
        manifest.get("manifest_sha256"),
    )
    without_sha = dict(manifest)
    without_sha.pop("manifest_sha256")
    expected_manifest_sha = _domain_sha(
        "MEMORY_A0_SCIENTIFIC_MANIFEST_V1",
        without_sha,
    )
    if stored_manifest_sha != expected_manifest_sha:
        raise ValueError("Formal A manifest SHA mismatch")

    if binding.get("schema_id") != "FORMAL_A0_REAL_INPUT_BINDING_V1":
        raise ValueError("Formal A input binding schema mismatch")
    if binding.get("schema_version") != 1:
        raise ValueError("Formal A input binding version mismatch")
    if binding.get("source_count") != 3 or binding.get("cell_count") != 12:
        raise ValueError("Formal A input binding population mismatch")
    if binding.get("scientific_execution_authorized") is not False:
        raise ValueError("Formal A input binding cannot self-authorize")
    if binding.get("memory_on_scientific_execution") is not False:
        raise ValueError("Formal A input binding claims execution")
    if binding.get("effect_authority") != "UNTESTED":
        raise ValueError("Formal A input binding effect authority mismatch")
    if binding.get("a0_scientific_manifest_sha256") != stored_manifest_sha:
        raise ValueError("manifest/input-binding SHA cross-binding mismatch")

    sources = binding.get("sources")
    cells = manifest.get("cells")
    manifest_sources = manifest.get("sources")
    if not isinstance(sources, list) or len(sources) != 3:
        raise ValueError("Formal A input binding requires three sources")
    if not isinstance(manifest_sources, list) or len(manifest_sources) != 3:
        raise ValueError("Formal A manifest requires three sources")
    if not isinstance(cells, list) or len(cells) != 12:
        raise ValueError("Formal A manifest requires twelve cells")


def validate_runtime_representation_binding_v1(
    *,
    cell: object,
    binding_row: object,
    representation_template: object,
) -> dict[str, object]:
    if not isinstance(cell, dict):
        raise TypeError("cell must be object")
    if not isinstance(binding_row, dict):
        raise TypeError("binding_row must be object")
    if not isinstance(representation_template, dict):
        raise TypeError("representation_template must be object")

    frozen_arm = cell.get("arm")
    if not isinstance(frozen_arm, dict):
        raise ValueError("cell arm must be object")
    arm_id = frozen_arm.get("arm_id")
    if arm_id not in _ARMS:
        raise ValueError("cell arm ID invalid")

    template_sha = _sha(
        "representation_template_sha256",
        representation_template.get("template_sha256"),
    )
    if template_sha != cell.get("representation_template_sha256"):
        raise ValueError("runtime template SHA differs from frozen cell")
    if template_sha != binding_row.get("representation_template_sha256"):
        raise ValueError("runtime template SHA differs from input binding")

    if representation_template.get("snapshot_sha256") != cell.get("snapshot_sha256"):
        raise ValueError("runtime template snapshot differs from frozen cell")
    if representation_template.get("memory_lineage_id") != cell.get("memory_lineage_id"):
        raise ValueError("runtime template lineage differs from frozen cell")
    if representation_template.get("record_version") != cell.get("record_version"):
        raise ValueError("runtime template version differs from frozen cell")
    if binding_row.get("memory_lineage_id") != cell.get("memory_lineage_id"):
        raise ValueError("input binding lineage differs from frozen cell")
    if binding_row.get("record_version") != cell.get("record_version"):
        raise ValueError("input binding version differs from frozen cell")
    if binding_row.get("source_state_id") != cell.get("source_state_id"):
        raise ValueError("input binding source state differs from frozen cell")
    if binding_row.get("source_task_id") != cell.get("source_task_id"):
        raise ValueError("input binding source task differs from frozen cell")
    if binding_row.get("source_bundle_sha256") != cell.get("source_bundle_sha256"):
        raise ValueError("input binding source bundle differs from frozen cell")
    if binding_row.get("source_gamefile_sha256") != cell.get("task_gamefile_group_id"):
        raise ValueError("input binding gamefile group differs from frozen cell")
    if binding_row.get("continuation_seed") != cell.get("continuation_seed"):
        raise ValueError("input binding continuation seed differs from frozen cell")

    raw_arms = representation_template.get("arms")
    if not isinstance(raw_arms, list):
        raise ValueError("runtime template arms must be array")
    matches = [
        item
        for item in raw_arms
        if isinstance(item, dict) and item.get("arm_id") == arm_id
    ]
    if len(matches) != 1:
        raise ValueError("runtime representation arm match count must be one")
    actual = matches[0]

    if actual.get("availability") != "AVAILABLE":
        raise ValueError("runtime representation arm unavailable")
    if actual.get("representation_class") != frozen_arm.get("representation_class"):
        raise ValueError("runtime representation class differs from frozen cell")
    if actual.get("artifact_sha256") != frozen_arm.get("artifact_sha256"):
        raise ValueError("runtime artifact SHA differs from frozen cell")
    if actual.get("token_count") != frozen_arm.get("token_count"):
        raise ValueError("runtime token count differs from frozen cell")
    if actual.get("retrieval_mode") != frozen_arm.get("retrieval_mode"):
        raise ValueError("runtime retrieval mode differs from frozen cell")
    if actual.get("retrieval_mode") != _DIRECT:
        raise ValueError("Formal A runtime retrieval mode is not direct-fixed")

    payload_sha = _payload_sha_for_runtime_arm(
        arm_id=arm_id,
        policy_visible_payload=actual.get("policy_visible_payload"),
    )
    if payload_sha != frozen_arm.get("policy_payload_sha256"):
        raise ValueError("runtime policy payload SHA differs from frozen cell")

    return actual


@dataclass(frozen=True, slots=True)
class A0PromptCensusRecordV1:
    cell_id: str
    policy_call_index: int
    raw_prompt_sha256: str
    rendered_prompt_sha256: str
    rendered_token_ids_sha256: str
    prompt_token_count: int
    max_generation_tokens: int
    context_window_tokens: int
    truncation_applied: bool
    fits_context: bool

    def __post_init__(self) -> None:
        _sha("cell_id", self.cell_id)
        for name in (
            "raw_prompt_sha256",
            "rendered_prompt_sha256",
            "rendered_token_ids_sha256",
        ):
            _sha(name, getattr(self, name))
        _nonnegative("policy_call_index", self.policy_call_index)
        _nonnegative("prompt_token_count", self.prompt_token_count)
        _nonnegative("max_generation_tokens", self.max_generation_tokens)
        _nonnegative("context_window_tokens", self.context_window_tokens)
        if type(self.truncation_applied) is not bool or self.truncation_applied:
            raise ValueError("Formal A forbids prompt truncation")
        expected_fits = (
            self.prompt_token_count + self.max_generation_tokens
            <= self.context_window_tokens
        )
        if self.fits_context is not expected_fits:
            raise ValueError("fits_context mismatch")
        if not self.fits_context:
            raise ValueError("Formal A prompt exceeds frozen context window")

    def to_dict(self) -> dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "policy_call_index": self.policy_call_index,
            "raw_prompt_sha256": self.raw_prompt_sha256,
            "rendered_prompt_sha256": self.rendered_prompt_sha256,
            "rendered_token_ids_sha256": self.rendered_token_ids_sha256,
            "prompt_token_count": self.prompt_token_count,
            "max_generation_tokens": self.max_generation_tokens,
            "context_window_tokens": self.context_window_tokens,
            "truncation_applied": False,
            "fits_context": True,
        }


@dataclass(frozen=True, slots=True)
class A0FrozenCellExecutionIdentityV1:
    cell_id: str
    source_fingerprint_sha256: str
    arm_id: str
    continuation_seed: int
    policy_runtime_manifest_sha256: str
    decoding_contract_sha256: str
    active_snapshot_sha256: str
    representation_template_sha256: str
    execution_identity_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "cell_id",
            "source_fingerprint_sha256",
            "policy_runtime_manifest_sha256",
            "decoding_contract_sha256",
            "active_snapshot_sha256",
            "representation_template_sha256",
        ):
            _sha(name, getattr(self, name))
        if self.arm_id not in _ARMS:
            raise ValueError("arm_id must be M0/M1/M2/M3")
        _nonnegative("continuation_seed", self.continuation_seed)
        expected = _domain_sha(
            "FORMAL_A0_CELL_EXECUTION_IDENTITY_V1",
            self._payload_without_sha(),
        )
        if self.execution_identity_sha256 is None:
            object.__setattr__(self, "execution_identity_sha256", expected)
        elif self.execution_identity_sha256 != expected:
            raise ValueError("execution identity SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "arm_id": self.arm_id,
            "continuation_seed": self.continuation_seed,
            "policy_runtime_manifest_sha256": self.policy_runtime_manifest_sha256,
            "decoding_contract_sha256": self.decoding_contract_sha256,
            "active_snapshot_sha256": self.active_snapshot_sha256,
            "representation_template_sha256": self.representation_template_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "execution_identity_sha256": self.execution_identity_sha256,
        }


@dataclass(frozen=True, slots=True)
class A0InfrastructureRetryRecordV1:
    cell_id: str
    original_execution_identity_sha256: str
    retry_execution_identity_sha256: str
    failure_stage: str
    pre_result_infrastructure_failure: bool
    scientific_outcome_produced: bool

    def __post_init__(self) -> None:
        _sha("cell_id", self.cell_id)
        _sha(
            "original_execution_identity_sha256",
            self.original_execution_identity_sha256,
        )
        _sha(
            "retry_execution_identity_sha256",
            self.retry_execution_identity_sha256,
        )
        _text("failure_stage", self.failure_stage)
        if (
            self.original_execution_identity_sha256
            != self.retry_execution_identity_sha256
        ):
            raise ValueError("infrastructure retry changed frozen cell identity")
        if self.pre_result_infrastructure_failure is not True:
            raise ValueError("retry is only for pre-result infrastructure failure")
        if self.scientific_outcome_produced is not False:
            raise ValueError(
                "pre-result infrastructure failure is not scientific outcome"
            )


@dataclass(frozen=True, slots=True)
class A0ContinuationTransitionV1:
    environment_step_from_source_index: int
    policy_call_index: int
    action: str
    pre_observation_sha256: str
    pre_menu_sequence_sha256: str
    resulting_observation_sha256: str
    resulting_menu_sequence_sha256: str
    score: int | float
    done: bool
    won: bool
    budget_before_policy_attempt_sha256: str
    budget_after_environment_finalization_sha256: str
    transition_sha256: str | None = None

    def __post_init__(self) -> None:
        _nonnegative(
            "environment_step_from_source_index",
            self.environment_step_from_source_index,
        )
        _nonnegative("policy_call_index", self.policy_call_index)
        _text("action", self.action)
        for name in (
            "pre_observation_sha256",
            "pre_menu_sequence_sha256",
            "resulting_observation_sha256",
            "resulting_menu_sequence_sha256",
            "budget_before_policy_attempt_sha256",
            "budget_after_environment_finalization_sha256",
        ):
            _sha(name, getattr(self, name))
        if type(self.score) not in (int, float):
            raise TypeError("score must be int or float")
        if isinstance(self.score, float) and not math.isfinite(self.score):
            raise ValueError("score must be finite")
        if type(self.done) is not bool or type(self.won) is not bool:
            raise TypeError("done/won must be bool")
        if self.won and not self.done:
            raise ValueError("won requires done")
        expected = _domain_sha(
            "FORMAL_A0_CONTINUATION_TRANSITION_V1",
            self._payload_without_sha(),
        )
        if self.transition_sha256 is None:
            object.__setattr__(self, "transition_sha256", expected)
        elif self.transition_sha256 != expected:
            raise ValueError("continuation transition SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "environment_step_from_source_index": self.environment_step_from_source_index,
            "policy_call_index": self.policy_call_index,
            "action": self.action,
            "pre_observation_sha256": self.pre_observation_sha256,
            "pre_menu_sequence_sha256": self.pre_menu_sequence_sha256,
            "resulting_observation_sha256": self.resulting_observation_sha256,
            "resulting_menu_sequence_sha256": self.resulting_menu_sequence_sha256,
            "score": self.score,
            "done": self.done,
            "won": self.won,
            "budget_before_policy_attempt_sha256": (
                self.budget_before_policy_attempt_sha256
            ),
            "budget_after_environment_finalization_sha256": (
                self.budget_after_environment_finalization_sha256
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "transition_sha256": self.transition_sha256,
        }


@dataclass(frozen=True, slots=True)
class A0CellResultV1:
    cell_id: str
    source_state_id: str
    arm_id: str
    continuation_seed: int
    execution_identity_sha256: str
    scientific_outcome_produced: bool
    terminal_success: bool | None
    evidence_complete: bool
    pre_result_infrastructure_failure: bool
    final_budget_sha256: str | None
    prompt_census_count: int
    policy_call_count: int
    environment_step_count_from_source: int
    result_sha256: str | None = None

    _KEYS = {
        "cell_id",
        "source_state_id",
        "arm_id",
        "continuation_seed",
        "execution_identity_sha256",
        "scientific_outcome_produced",
        "terminal_success",
        "evidence_complete",
        "pre_result_infrastructure_failure",
        "final_budget_sha256",
        "prompt_census_count",
        "policy_call_count",
        "environment_step_count_from_source",
        "result_sha256",
    }

    def __post_init__(self) -> None:
        _sha("cell_id", self.cell_id)
        _sha("source_state_id", self.source_state_id)
        _sha("execution_identity_sha256", self.execution_identity_sha256)
        if self.arm_id not in _ARMS:
            raise ValueError("arm_id must be M0/M1/M2/M3")
        _nonnegative("continuation_seed", self.continuation_seed)
        for name in (
            "prompt_census_count",
            "policy_call_count",
            "environment_step_count_from_source",
        ):
            _nonnegative(name, getattr(self, name))
        if type(self.scientific_outcome_produced) is not bool:
            raise TypeError("scientific_outcome_produced must be bool")
        if type(self.evidence_complete) is not bool:
            raise TypeError("evidence_complete must be bool")
        if type(self.pre_result_infrastructure_failure) is not bool:
            raise TypeError("pre_result_infrastructure_failure must be bool")
        if (
            self.terminal_success is not None
            and type(self.terminal_success) is not bool
        ):
            raise TypeError("terminal_success must be bool or None")

        if self.pre_result_infrastructure_failure:
            if (
                self.scientific_outcome_produced
                or self.terminal_success is not None
            ):
                raise ValueError(
                    "infrastructure failure cannot carry scientific terminal outcome"
                )
            if self.final_budget_sha256 is not None:
                _sha("final_budget_sha256", self.final_budget_sha256)
        else:
            if not self.scientific_outcome_produced:
                raise ValueError(
                    "completed non-infrastructure cell must produce scientific outcome"
                )
            if self.terminal_success is None or not self.evidence_complete:
                raise ValueError(
                    "scientific cell requires resolved terminal + complete evidence"
                )
            _sha("final_budget_sha256", self.final_budget_sha256)

        expected = _domain_sha(
            "FORMAL_A0_CELL_RESULT_V1",
            self._payload_without_sha(),
        )
        if self.result_sha256 is None:
            object.__setattr__(self, "result_sha256", expected)
        elif self.result_sha256 != expected:
            raise ValueError("cell result SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "source_state_id": self.source_state_id,
            "arm_id": self.arm_id,
            "continuation_seed": self.continuation_seed,
            "execution_identity_sha256": self.execution_identity_sha256,
            "scientific_outcome_produced": self.scientific_outcome_produced,
            "terminal_success": self.terminal_success,
            "evidence_complete": self.evidence_complete,
            "pre_result_infrastructure_failure": (
                self.pre_result_infrastructure_failure
            ),
            "final_budget_sha256": self.final_budget_sha256,
            "prompt_census_count": self.prompt_census_count,
            "policy_call_count": self.policy_call_count,
            "environment_step_count_from_source": (
                self.environment_step_count_from_source
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "result_sha256": self.result_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "A0CellResultV1":
        payload = _exact_dict(value, cls._KEYS, "Formal A0 cell result")
        return cls(**payload)


def validate_cell_result_against_frozen_cell_v1(
    *,
    result: A0CellResultV1,
    cell: object,
) -> None:
    if not isinstance(result, A0CellResultV1):
        raise TypeError("result must be A0CellResultV1")
    if not isinstance(cell, dict):
        raise TypeError("cell must be object")
    frozen_arm = cell.get("arm")
    if not isinstance(frozen_arm, dict):
        raise ValueError("cell arm must be object")

    if result.cell_id != cell.get("cell_id"):
        raise ValueError("result cell ID differs from manifest")
    if result.source_state_id != cell.get("source_state_id"):
        raise ValueError("result source state differs from manifest")
    if result.arm_id != frozen_arm.get("arm_id"):
        raise ValueError("result arm differs from manifest")
    if result.continuation_seed != cell.get("continuation_seed"):
        raise ValueError("result continuation seed differs from manifest")
