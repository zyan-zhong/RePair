"""Pure Human Reference F0/F1 counterfactual contracts.

This module is deliberately environment/model free.  It owns only the
Training-Harness semantics that are not part of the frozen RAW Runtime Core:

* one registered F1 repair action consumes one environment step but does not
  fabricate a policy generation;
* exact-action candidates are live-menu revalidated without repair,
  normalization, sorting, heuristic matching, or case normalization;
* Environment Verifier pair labels are deterministic;
* five paired repetitions use a frozen four-of-five stability rule.

The live branch executor reuses the existing audited exact-state replay,
PolicyClient, RAW Runtime Core, and ALFWorld adapter.
"""
from __future__ import annotations

HISTORICAL_F0F1_PORT_SOURCE_COMMIT = "228f3274693a22667ef2123254625b95b9bbd50d"

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.canonical_evidence import sha256_file
from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1
from pchsi.reference_loop.canonical import domain_hash


_BRANCH_SCHEMA = "CLEAN_REFERENCE_F0F1_BRANCH_BINDING_V1"
_BRANCH_EVIDENCE_SCHEMA = "CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1"
_PAIR_SCHEMA = "CLEAN_REFERENCE_F0F1_PAIR_RESULT_V1"
_STATE_SCHEMA = "CLEAN_REFERENCE_F0F1_STATE_RESULT_V1"
_EFFECTS = {"BENEFIT", "HARM", "NEUTRAL", "UNCERTAIN"}


def _sha64(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def reserve_registered_repair_environment_step_v1(
    state: BudgetState,
    limits: BudgetLimits = BudgetLimits(),
) -> BudgetState:
    """Reserve exactly one Harness intervention environment step.

    A registered repair is not a policy generation.  Therefore the policy
    attempt count is unchanged.  The action is sent to the environment, so the
    environment-step count increases by one.  Because an environment action is
    executed, the consecutive-nonexecuted counter resets to zero.
    """
    if not isinstance(state, BudgetState):
        raise TypeError("state must be BudgetState")
    if not isinstance(limits, BudgetLimits):
        raise TypeError("limits must be BudgetLimits")
    if state.environment_step_count >= limits.max_environment_steps:
        raise ValueError("environment step budget is exhausted")
    if state.policy_attempt_count > limits.max_policy_attempts:
        raise ValueError("policy attempt count exceeds limit")
    return BudgetState(
        policy_attempt_count=state.policy_attempt_count,
        environment_step_count=state.environment_step_count + 1,
        protocol_failure_count=state.protocol_failure_count,
        inadmissible_action_count=state.inadmissible_action_count,
        consecutive_nonexecuted_attempt_count=0,
    )


def validate_candidate_content_hash_v1(candidate: Mapping[str, object], *, expected_candidate_sha256: str) -> dict[str, object]:
    _sha64(expected_candidate_sha256, "expected_candidate_sha256")
    if not isinstance(candidate, Mapping): raise TypeError("candidate must be mapping")
    schema_id=candidate.get("schema_id")
    if not isinstance(schema_id,str) or not schema_id: raise ValueError("candidate schema_id is missing")
    if candidate.get("candidate_sha256") != expected_candidate_sha256: raise ValueError("candidate SHA differs from frozen binding")
    observed=domain_hash(schema_id,dict(candidate),excluded_field="candidate_sha256")
    if observed != expected_candidate_sha256: raise ValueError("candidate content hash differs from frozen binding")
    return dict(candidate)

def load_registered_replay_source_authority_v1(path: str | Path, *, expected_file_sha256: str) -> RegisteredReplaySourceV1:
    _sha64(expected_file_sha256,"expected_file_sha256")
    p=Path(path)
    if p.is_symlink(): raise ValueError("replay source must not be a symlink")
    if not p.is_file(): raise ValueError("replay source path is not a regular file")
    if sha256_file(p) != expected_file_sha256: raise ValueError("replay source file SHA differs from frozen binding")
    raw=p.read_bytes(); source=RegisteredReplaySourceV1.from_json(raw)
    if source.canonical_bytes()!=raw: raise ValueError("replay source is not canonical")
    gamefile=Path(source.exact_gamefile)
    if gamefile.is_symlink(): raise ValueError("registered exact gamefile must not be a symlink")
    if not gamefile.is_file(): raise ValueError("registered exact gamefile is not a regular file")
    if sha256_file(gamefile) != source.source_gamefile_sha256: raise ValueError("registered exact gamefile SHA differs from replay authority")
    return source


def validate_candidate_source_provenance_v1(
    candidate: Mapping[str, object],
    *,
    expected_source_state_sha256: str,
    expected_source_policy_condition: str,
) -> dict[str, object]:
    # The caller supplies an already validated replay fingerprint. Its hash
    # commits to source_policy_condition; the closed candidate schema stores
    # that hash, not a redundant condition field. Keep the existing call API.
    from pchsi.analyzer.candidate_projector import SCHEMA_BY_KIND
    from pchsi.analyzer.schema_contract import validate_payload_against_schema

    _sha64(expected_source_state_sha256, "expected_source_state_sha256")
    if (
        not isinstance(expected_source_policy_condition, str)
        or not expected_source_policy_condition
        or "\x00" in expected_source_policy_condition
    ):
        raise ValueError(
            "expected_source_policy_condition must be non-empty NUL-free str"
        )
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be mapping")
    payload = dict(candidate)
    schema_id = payload.get("schema_id")
    candidate_kind = payload.get("candidate_kind")
    if (
        not isinstance(candidate_kind, str)
        or SCHEMA_BY_KIND.get(candidate_kind) != schema_id
        or schema_id is None
    ):
        raise ValueError("unsupported candidate source-provenance schema")
    validate_payload_against_schema(schema_id=schema_id, payload=payload)
    validate_candidate_content_hash_v1(
        payload, expected_candidate_sha256=payload["candidate_sha256"]
    )
    if payload["source_state_sha256"] != expected_source_state_sha256:
        raise ValueError("candidate source state differs from replay authority")
    return payload

def validate_executable_exact_candidate_v1(
    candidate: Mapping[str, object],
    *,
    expected_candidate_sha256: str,
    expected_source_state_sha256: str,
    live_commands: Sequence[str],
) -> str:
    """Return the exact registered action after fail-closed live revalidation."""
    _sha64(expected_candidate_sha256, "expected_candidate_sha256")
    _sha64(expected_source_state_sha256, "expected_source_state_sha256")
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be mapping")
    if candidate.get("candidate_sha256") != expected_candidate_sha256:
        raise ValueError("candidate SHA differs from frozen binding")
    if candidate.get("source_state_sha256") != expected_source_state_sha256:
        raise ValueError("candidate source state differs from frozen binding")
    if candidate.get("candidate_status") != "EXECUTABLE_EXACT_ACTION":
        raise ValueError("Human F0/F1 V1 requires EXECUTABLE_EXACT_ACTION")
    if candidate.get("requires_environment_verification") is not True:
        raise ValueError("candidate does not require environment verification")
    if candidate.get("live_menu_revalidation_required") is not True:
        raise ValueError("candidate disabled live menu revalidation")
    if candidate.get("all_intervention_actions_count_against_environment_budget") is not True:
        raise ValueError("candidate disabled intervention budget accounting")
    action = candidate.get("exact_action")
    if not isinstance(action, str) or not action:
        raise ValueError("candidate exact action is invalid")
    if candidate.get("option_actions") != []:
        raise ValueError("exact-action candidate unexpectedly carries option actions")
    if candidate.get("termination_condition") is not None:
        raise ValueError("exact-action candidate unexpectedly carries termination condition")
    commands = tuple(live_commands)
    if any(not isinstance(item, str) or not item for item in commands):
        raise ValueError("live command sequence is invalid")
    observed_menu_sha = sha256_string_sequence(commands)
    if candidate.get("menu_sha256") != observed_menu_sha:
        raise ValueError("live menu SHA differs from registered candidate menu")
    if action not in commands:
        raise ValueError("registered exact action is not an exact live-menu member")
    return action


def classify_pair_effect_v1(
    *,
    f0_success: bool | None,
    f1_success: bool | None,
    f0_complete: bool = True,
    f1_complete: bool = True,
) -> dict[str, str]:
    """Classify one same-state F0/F1 pair using environment outcomes only."""
    if not f0_complete or not f1_complete or f0_success is None or f1_success is None:
        return {"effect": "UNCERTAIN", "terminal_relation": "INCOMPLETE_EVIDENCE"}
    if type(f0_success) is not bool or type(f1_success) is not bool:
        raise TypeError("terminal success must be bool or None")
    if (not f0_success) and f1_success:
        return {"effect": "BENEFIT", "terminal_relation": "F0_FAIL_F1_SUCCESS"}
    if f0_success and (not f1_success):
        return {"effect": "HARM", "terminal_relation": "F0_SUCCESS_F1_FAIL"}
    if f0_success and f1_success:
        return {"effect": "NEUTRAL", "terminal_relation": "BOTH_SUCCESS"}
    return {"effect": "NEUTRAL", "terminal_relation": "BOTH_FAILURE"}


def aggregate_five_pair_effects_v1(effects: Sequence[str]) -> dict[str, object]:
    """Apply the frozen five-repeat / four-of-five stability rule."""
    values = tuple(effects)
    if len(values) != 5:
        raise ValueError("exactly five paired effects are required")
    if any(value not in _EFFECTS for value in values):
        raise ValueError("unknown F0/F1 effect label")
    counts = Counter(values)
    stable = None
    for label in ("BENEFIT", "HARM", "NEUTRAL"):
        if counts[label] >= 4:
            stable = label
            break
    if stable is None:
        stable = "UNCERTAIN"
    return {
        "stable_effect": stable,
        "effect_counts": {label: counts[label] for label in sorted(_EFFECTS)},
        "four_of_five_stable": stable != "UNCERTAIN",
        "paired_repetition_count": 5,
    }


def validate_branch_binding_v1(value: Mapping[str, object]) -> dict[str, object]:
    """Validate the strict branch binding emitted by the offline manifest builder."""
    if not isinstance(value, Mapping):
        raise TypeError("branch binding must be mapping")
    required = {
        "schema_id", "schema_version", "execution_manifest_sha256",
        "handoff_sha256", "field_adjudication_file_sha256", "implementation_commit",
        "round_id", "pair_id", "state_position", "repetition", "branch", "continuation_seed",
        "source_state_sha256", "research_candidate_id", "source_candidate_sha256",
        "candidate_artifact_path", "candidate_artifact_file_sha256",
        "replay_source_path", "replay_source_file_sha256", "runtime_binding_path",
        "runtime_binding_file_sha256", "registered_repair_action",
        "active_snapshot_sha256", "token_budget_contract_sha256", "policy_model", "policy_version",
        "branch_binding_sha256",
    }
    if set(value) != required:
        raise ValueError(
            "branch binding fields mismatch: "
            f"missing={sorted(required-set(value))} unknown={sorted(set(value)-required)}"
        )
    if value["schema_id"] != _BRANCH_SCHEMA or value["schema_version"] != 1:
        raise ValueError("branch binding schema mismatch")
    for field in (
        "execution_manifest_sha256", "handoff_sha256", "field_adjudication_file_sha256",
        "source_state_sha256", "research_candidate_id", "source_candidate_sha256",
        "candidate_artifact_file_sha256", "replay_source_file_sha256",
        "runtime_binding_file_sha256", "active_snapshot_sha256", "token_budget_contract_sha256",
        "branch_binding_sha256",
    ):
        _sha64(value[field], field)
    if not isinstance(value["implementation_commit"], str) or len(value["implementation_commit"]) != 40:
        raise ValueError("implementation_commit must be 40-char git SHA")
    if value["branch"] not in {"F0", "F1"}:
        raise ValueError("branch must be F0 or F1")
    if type(value["state_position"]) is not int or value["state_position"] < 0:
        raise ValueError("state_position invalid")
    if type(value["repetition"]) is not int or not 1 <= value["repetition"] <= 5:
        raise ValueError("repetition invalid")
    if type(value["continuation_seed"]) is not int or value["continuation_seed"] < 0:
        raise ValueError("continuation_seed invalid")
    if not isinstance(value["registered_repair_action"], str) or not value["registered_repair_action"]:
        raise ValueError("registered_repair_action invalid")
    for field in ("round_id", "policy_model", "policy_version"):
        if not isinstance(value[field], str) or not value[field]:
            raise ValueError(field + " must be non-empty str")
    expected = domain_hash(
        _BRANCH_SCHEMA,
        dict(value),
        excluded_field="branch_binding_sha256",
    )
    if value["branch_binding_sha256"] != expected:
        raise ValueError("branch binding domain hash mismatch")
    return dict(value)


def build_branch_evidence_hash_v1(payload: Mapping[str, object]) -> str:
    return domain_hash(
        _BRANCH_EVIDENCE_SCHEMA,
        dict(payload),
        excluded_field="branch_evidence_sha256",
    )


def build_pair_result_hash_v1(payload: Mapping[str, object]) -> str:
    return domain_hash(
        _PAIR_SCHEMA,
        dict(payload),
        excluded_field="pair_result_sha256",
    )


def build_state_result_hash_v1(payload: Mapping[str, object]) -> str:
    return domain_hash(
        _STATE_SCHEMA,
        dict(payload),
        excluded_field="state_result_sha256",
    )


# Continuation request binding is independent of the historical pi0 service alias.
# The existing request factories remain the serialization/decode authority.
from pchsi.evaluation.canonical_evidence import canonical_json_bytes as _wire_json, strict_json_loads as _wire_loads
from pchsi.evaluation.policy_execution_profile import R0_EXECUTION_PROFILE_V1, I1_EXECUTION_PROFILE_V1
from pchsi.evaluation.interface_isolation_request import I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256
from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1


def continuation_request_contract_v1(profile_id: str) -> dict[str, object]:
    profiles = {p.profile_id: p for p in (R0_EXECUTION_PROFILE_V1, I1_EXECUTION_PROFILE_V1)}
    if not isinstance(profile_id, str) or profile_id not in profiles:
        raise ValueError("unsupported frozen continuation profile")
    profile = profiles[profile_id]
    return {
        "profile_id": profile.profile_id,
        "request_kind": profile.request_kind,
        "serialization_schema_sha256": (
            I1_STRUCTURED_SERIALIZATION_SCHEMA_SHA256 if profile.request_kind == "I1" else None
        ),
    }


def _continuation_profile_v1(runtime: Mapping[str, object]):
    contract = runtime.get("continuation_request_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("missing explicit continuation request contract; no R0 fallback")
    expected = continuation_request_contract_v1(contract.get("profile_id"))
    if dict(contract) != expected:
        raise ValueError("continuation request contract differs from frozen factory")
    name = runtime.get("served_model_name")
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("invalid bound continuation served model")
    profiles = (R0_EXECUTION_PROFILE_V1, I1_EXECUTION_PROFILE_V1)
    return next(p for p in profiles if p.profile_id == expected["profile_id"])


def load_continuation_runtime_binding_v2(path: str | Path, *, expected_file_sha256: str, expected_model: str) -> dict[str, object]:
    import hashlib
    _sha64(expected_file_sha256, "runtime binding file SHA")
    file_path = Path(path)
    if file_path.is_symlink() or not file_path.is_file():
        raise ValueError("runtime binding must be a regular non-symlink file")
    raw = file_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_file_sha256:
        raise ValueError("runtime binding file SHA mismatch")
    value = _wire_loads(raw)
    fields = {
        "schema_id", "schema_version", "served_model_name", "policy_runtime_manifest_sha256",
        "decoding_contract_sha256", "policy_base_url", "base_model_local_path", "tokenizer_revision",
        "chat_template_sha256", "context_window_tokens", "vllm_version", "scientific_execution_authorized",
        "continuation_request_contract",
    }
    if not isinstance(value, dict) or set(value) != fields or _wire_json(value) != raw:
        raise ValueError("runtime V2 fields/canonical bytes mismatch")
    if value["schema_id"] != "CLEAN_PI0_LIVE_RUNTIME_BINDING_V2" or value["schema_version"] != 2:
        raise ValueError("explicit V2 continuation binding required; legacy binding is read-only")
    if value["served_model_name"] != expected_model:
        raise ValueError("runtime served model differs from frozen parent")
    if value["scientific_execution_authorized"] is not False:
        raise ValueError("runtime binding cannot self-authorize")
    if type(value["context_window_tokens"]) is not int or value["context_window_tokens"] <= 0:
        raise ValueError("invalid runtime context window")
    for field in ("policy_runtime_manifest_sha256", "decoding_contract_sha256", "chat_template_sha256"):
        _sha64(value[field], field)
    _continuation_profile_v1(value)
    return value


@dataclass(frozen=True, slots=True)
class _ServiceBoundContinuationRequestV1:
    base_request: object
    served_model_name: str

    @property
    def prompt_text(self) -> str:
        return self.base_request.prompt_text

    @property
    def seed(self) -> int:
        return self.base_request.seed

    @property
    def request_id(self) -> str:
        return self.base_request.request_id

    def to_wire_dict(self) -> dict[str, object]:
        payload = self.base_request.to_wire_dict()
        payload["model"] = self.served_model_name
        return payload

    def to_wire_bytes(self) -> bytes:
        return _wire_json(self.to_wire_dict())


def build_bound_continuation_request_v1(*, runtime: Mapping[str, object], prompt_text: str, seed: int, request_id: str):
    profile = _continuation_profile_v1(runtime)
    request = profile.build_request(prompt_text=prompt_text, seed=seed, request_id=request_id)
    return _ServiceBoundContinuationRequestV1(request, str(runtime["served_model_name"]))


def validate_continuation_wire_v1(*, runtime: Mapping[str, object], raw: bytes, expected_prompt: str, expected_seed: int, expected_request_id: str) -> None:
    actual = _wire_loads(raw)
    expected = build_bound_continuation_request_v1(
        runtime=runtime, prompt_text=expected_prompt, seed=expected_seed, request_id=expected_request_id,
    ).to_wire_dict()
    if _wire_json(actual) != _wire_json(expected):
        changed = sorted(set(actual or {}) | set(expected)) if isinstance(actual, dict) else ["<root>"]
        if isinstance(actual, dict):
            changed = [key for key in changed if actual.get(key) != expected.get(key) or (key in actual) != (key in expected)]
        raise ValueError("continuation wire differs from bound contract: " + ",".join(changed))


def validate_continuation_record_v1(record: Mapping[str, object], expected: Mapping[str, object]) -> None:
    runtime = load_continuation_runtime_binding_v2(
        str(expected["runtime_binding_path"]),
        expected_file_sha256=str(expected["runtime_binding_file_sha256"]),
        expected_model=str(expected["policy_model"]),
    )
    if record.get("_record_kind") == "FAILURE":
        return
    if record.get("continuation_request_contract") != runtime["continuation_request_contract"]:
        raise ValueError("branch result lacks/mismatches continuation contract")
    calls = record.get("policy_calls")
    if not isinstance(calls, list) or len(calls) != record.get("policy_call_count_from_source"):
        raise ValueError("branch policy-call population mismatch")
    for item in calls:
        if not isinstance(item, Mapping) or not isinstance(item.get("policy_call"), Mapping):
            raise ValueError("branch policy-call evidence invalid")
        evidence = PolicyCallEvidenceV1.from_dict(item["policy_call"])
        wire = _wire_loads(evidence.request_wire_bytes)
        messages = wire.get("messages") if isinstance(wire, dict) else None
        if not isinstance(messages, list) or len(messages) != 1 or not isinstance(messages[0], dict) or messages[0].get("role") != "user":
            raise ValueError("continuation request message structure mismatch")
        validate_continuation_wire_v1(
            runtime=runtime, raw=evidence.request_wire_bytes,
            expected_prompt=evidence.prompt_text,
            expected_seed=int(expected["continuation_seed"]),
            expected_request_id=evidence.client_request_id,
        )
