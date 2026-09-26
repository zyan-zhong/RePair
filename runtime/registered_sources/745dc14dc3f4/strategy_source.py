"""Same-PRE strategy representation and exact source-state training projection.

The F1 causal unit remains the complete registered candidate. Its initial-state
I1 training view is not a claim about the effect of executing that action alone.
No new provider call, natural-language compiler, or effect classifier is added.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re

from .materializer import _read_ref, _seal, _sha, _verify_seal, _verify_h44_seal, canonical, digest

TEXT_FIELDS = ("principal_bottleneck", "current_subgoal", "expected_next_event", "expected_state_change",
               "progress_criterion", "recovery_trigger", "fallback_condition", "action")


def extend_pre_schema(base_schema):
    schema = copy.deepcopy(base_schema)
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    refs = {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "object", "additionalProperties": False,
        "properties": {"source_kind": {"type": "string"}, "source_id": {"type": "string"}, "source_sha256": sha},
        "required": ["source_kind", "source_id", "source_sha256"]}}
    properties = {key: {"type": "string", "minLength": 1, "maxLength": 8192} for key in TEXT_FIELDS}
    properties["evidence_refs"] = refs
    item = {"type": "object", "additionalProperties": False,
        "properties": {"source_state_sha256": sha, "source_candidate_sha256": sha,
            "strategy": {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}},
        "required": ["source_state_sha256", "source_candidate_sha256", "strategy"]}
    schema.setdefault("properties", {})["training_strategies"] = {"type": "array", "items": item}
    if "training_strategies" not in schema.setdefault("required", []): schema["required"].append("training_strategies")
    return schema


def candidate_evidence_refs(candidate):
    """Native strategy refs commit to the whole option and exact source menu."""
    return [{"source_kind": "COMPLETE_REGISTERED_CANDIDATE", "source_id": candidate["candidate_sha256"], "source_sha256": candidate["candidate_sha256"]},
        {"source_kind": "SOURCE_ADMISSIBLE_MENU", "source_id": candidate["source_state_sha256"], "source_sha256": candidate["menu_sha256"]}]


def extend_pre_prompt(original):
    return original + (
        "\n\nFor every selected candidate, also return training_strategies with its exact source_state_sha256, "
        "source_candidate_sha256 and the nine registered strategy fields. Describe the complete selected repair using "
        "only the current pre-verification evidence. Do not invent observations, F0/F1 outcomes, rewards or causal labels. "
        "For a short option retain its full ordered sequence and termination semantics in the compact strategy description; "
        "action denotes only the initial source-state command, not a replacement for the complete intervention. "
        "Use evidence_refs in this exact order: {source_kind: COMPLETE_REGISTERED_CANDIDATE, source_id: candidate_sha256, "
        "source_sha256: candidate_sha256}, {source_kind: SOURCE_ADMISSIBLE_MENU, source_id: source_state_sha256, "
        "source_sha256: menu_sha256}. The deterministic adapter will compute the strategy content hash. "
        "The independent verifier later decides eligibility for the complete candidate. No standalone-action effect "
        "is claimed by the initial-state training view. Use an empty array when no candidate is selected.\n"
    )


def _candidate(candidate, native_labels):
    from pchsi.analyzer.schema_contract import _validate, verify_domain_hash
    # Use the selected complete repository's exact schema. H4.4 also imports an
    # identical validator from its deliberately partial native source capsule.
    if candidate["schema_id"] != "ANALYZER_REPAIR_CANDIDATE_V1":
        raise ValueError("CURRENT_SELECTED_REPAIR_SCHEMA_REQUIRED")
    schema_path = native_labels.tools_root.parents[4] / "configs/analyzer/schemas/analyzer_repair_candidate_v1.json"
    _validate(candidate, json.loads(schema_path.read_bytes()), "$")
    verify_domain_hash(payload=candidate, domain=candidate["schema_id"], hash_field="candidate_sha256")
    status = candidate["candidate_status"]
    if status == "EXECUTABLE_SHORT_OPTION":
        if candidate["exact_action"] is not None or not candidate["option_actions"] or not candidate["termination_condition"]:
            raise ValueError("PRE_COMPLETE_OPTION_REQUIRED")
        return candidate["option_actions"][0]
    if status == "EXECUTABLE_EXACT_ACTION":
        if not candidate["exact_action"] or candidate["option_actions"] or candidate["termination_condition"] is not None:
            raise ValueError("PRE_EXACT_ACTION_ENCODING_INVALID")
        return candidate["exact_action"]
    raise ValueError("PRE_STRATEGY_EXECUTABLE_CANDIDATE_REQUIRED")


def validate_pre_strategies(strategies, *, accepted_pre, selected_candidates, native_labels):
    import jsonschema
    schema = extend_pre_schema({"properties": {}, "required": []})["properties"]["training_strategies"]
    jsonschema.Draft202012Validator(schema).validate(strategies)
    by_candidate = {c["candidate_sha256"]: c for c in selected_candidates}
    selected = accepted_pre["selected_candidate_sha256s"]
    if len(by_candidate) != len(selected_candidates) or set(by_candidate) != set(selected) or len(selected) != len(by_candidate):
        raise ValueError("PRE_SELECTED_CANDIDATE_SET_MISMATCH")
    if len(strategies) != len(selected): raise ValueError("PRE_STRATEGY_SET_INCOMPLETE")
    result, seen_states, seen_candidates = [], set(), set()
    for row in strategies:
        cid, state = row["source_candidate_sha256"], row["source_state_sha256"]
        if cid not in by_candidate or cid in seen_candidates or state in seen_states:
            raise ValueError("PRE_STRATEGY_CANDIDATE_OR_STATE_NOT_UNIQUE")
        seen_candidates.add(cid); seen_states.add(state)
        candidate = by_candidate[cid]
        if state != candidate["source_state_sha256"]: raise ValueError("PRE_STRATEGY_SOURCE_STATE_MISMATCH")
        action = _candidate(candidate, native_labels)
        strategy = copy.deepcopy(row["strategy"])
        if strategy["action"] != action: raise ValueError("PRE_STRATEGY_SOURCE_ACTION_CHANGED")
        if strategy["evidence_refs"] != candidate_evidence_refs(candidate):
            raise ValueError("PRE_STRATEGY_COMPLETE_CANDIDATE_EVIDENCE_REQUIRED")
        strategy["verified_strategy_sha256"] = "0" * 64
        strategy["verified_strategy_sha256"] = native_labels.adapter.strategy_payload_sha256(strategy)
        native_labels.adapter.canonical_strategy_target_json(strategy)
        result.append({"source_state_sha256": state, "source_candidate_sha256": cid, "strategy": strategy,
            "complete_registered_candidate": copy.deepcopy(candidate),
            "causal_verification_scope": "COMPLETE_REGISTERED_OPTION" if candidate["candidate_status"] == "EXECUTABLE_SHORT_OPTION" else "REGISTERED_EXACT_ACTION",
            "standalone_action_causal_effect_claimed": False})
    return result


def validate_pre_output(value, *, selected_candidates, native_finalize, native_labels):
    """Native callback helper. It returns only the unchanged native PRE schema."""
    base = copy.deepcopy(value)
    if "training_strategies" not in base: raise ValueError("PRE_TRAINING_STRATEGIES_REQUIRED")
    strategies = base.pop("training_strategies")
    accepted = native_finalize(base)
    validate_pre_strategies(strategies, accepted_pre=accepted, selected_candidates=selected_candidates, native_labels=native_labels)
    return accepted


def _file_ref(path):
    return {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def adopt_pre_strategies(*, call_dir, expected, selected_candidates, native_finalize, native_labels):
    """Recover the annex from the same native accepted response, never resend."""
    from pchsi.reference_loop.canonical import domain_hash, strict_json_loads
    from pchsi.cognitive_runtime.schema_registry import validate_artifact
    from pchsi.cognitive_runtime.response import parse_provider_response, extract_output_text
    required = {"logical_call_id", "scientific_unit_identity_sha256", "stage_id", "condition_id", "round_id", "policy_version", "request_body_sha256", "runtime_manifest_sha256"}
    if not required <= set(expected) or expected["stage_id"] != "R-PRE-PRIMARY-V2":
        raise ValueError("PRE_EXACT_NATIVE_LOGICAL_BINDING_REQUIRED")
    call = Path(call_dir).resolve(); logical_id = _sha(expected["logical_call_id"], "PRE_LOGICAL")
    if call.name != logical_id: raise ValueError("PRE_CALL_DIRECTORY_IDENTITY_MISMATCH")
    read = lambda name: strict_json_loads((call / name).read_bytes())
    logical = read("logical_call.json")
    validate_artifact("LOGICAL_CALL_RECORD_V1", logical)
    if logical["logical_call_sha256"] != domain_hash("LOGICAL_CALL_RECORD_V1", logical, excluded_field="logical_call_sha256"):
        raise ValueError("PRE_LOGICAL_DOMAIN_HASH_MISMATCH")
    if any(logical.get(k) != v for k, v in expected.items()): raise ValueError("PRE_LOGICAL_IDENTITY_MISMATCH")
    if logical["terminal_method_status"] != "ACCEPTED": raise ValueError("PRE_SAME_CALL_ACCEPTED_REQUIRED")
    attempt_id = logical.get("contributing_attempt_id")
    if not isinstance(attempt_id, str) or not re.fullmatch(re.escape(logical_id) + r":[0-9]+", attempt_id):
        raise ValueError("PRE_CONTRIBUTING_ATTEMPT_REQUIRED")
    attempt_name = "attempt_%03d.json" % int(attempt_id.split(":")[1])
    attempt = read(attempt_name)
    validate_artifact("TRANSPORT_ATTEMPT_RECORD_V1", attempt)
    if attempt["attempt_sha256"] != domain_hash("TRANSPORT_ATTEMPT_RECORD_V1", attempt, excluded_field="attempt_sha256"):
        raise ValueError("PRE_ATTEMPT_DOMAIN_HASH_MISMATCH")
    if (attempt["terminal_attempt_status"] != "SUCCEEDED" or attempt["logical_call_id"] != logical_id
            or attempt["transport_attempt_id"] != attempt_id or attempt["transport_attempt_index"] != int(attempt_id.split(":")[1])):
        raise ValueError("PRE_CONTRIBUTING_ATTEMPT_MISMATCH")
    request_ref = {"path": str(call / "raw_request.json"), "sha256": attempt["raw_request_sha256"]}
    request = strict_json_loads(_read_ref(request_ref))
    if domain_hash("COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1", request) != expected["request_body_sha256"]:
        raise ValueError("PRE_RAW_REQUEST_CURRENT_IDENTITY_MISMATCH")
    response_ref = {"path": str(call / "raw_response.json"), "sha256": attempt["raw_response_sha256"]}
    value = strict_json_loads(extract_output_text(parse_provider_response(_read_ref(response_ref))))
    artifact = read("validated_artifact.json")
    if validate_pre_output(value, selected_candidates=selected_candidates, native_finalize=native_finalize, native_labels=native_labels) != artifact:
        raise ValueError("PRE_RAW_RESPONSE_NATIVE_ARTIFACT_MISMATCH")
    strategies = validate_pre_strategies(value["training_strategies"], accepted_pre=artifact, selected_candidates=selected_candidates, native_labels=native_labels)
    return _seal({"schema_id": "CURRENT_ACCEPTED_PRE_STRATEGY_REPRESENTATION_V1", "schema_version": 1,
        "round_id": artifact["round_id"], "source_pre_primary_record_sha256": artifact["primary_record_sha256"],
        "logical_call_id": logical_id, "logical_call_status": "ACCEPTED", "strategies": strategies,
        "accepted_raw_response_ref": response_ref, "accepted_raw_request_ref": request_ref,
        "expected_logical_identity": copy.deepcopy(expected), "accepted_pre_ref": _file_ref(call / "validated_artifact.json"),
        "accepted_logical_ref": _file_ref(call / "logical_call.json"), "accepted_attempt_ref": _file_ref(call / attempt_name),
        "additional_provider_call_count": 0, "verification_effect_claimed": False, "training_execution_authorized": False}, "pre_strategy_receipt_sha256")


def _source_context(row):
    from pchsi.memory.source_state_contracts import SourceDecisionStateFingerprintV1
    from pchsi.evaluation.action_trace import sha256_string_sequence
    fp = row["fingerprint"]
    SourceDecisionStateFingerprintV1.from_dict(fp)
    call = row["source_call"]
    expected_bridge = {"source_candidate_sha256": row["candidate"]["candidate_sha256"],
        "analyzer_source_state_sha256": row["candidate"]["source_state_sha256"],
        "native_source_fingerprint_sha256": fp["fingerprint_sha256"], "source_bundle_sha256": fp["source_bundle_sha256"],
        "source_call_index": fp["model_call_index"]}
    if any(row["bridge"].get(key) != value for key, value in expected_bridge.items()) or call.model_call_index != fp["model_call_index"]:
        raise ValueError("TRAINING_ANALYZER_TO_NATIVE_SOURCE_BRIDGE_MISMATCH")
    call_bytes = call.to_json().encode("utf-8")
    if hashlib.sha256(call_bytes).hexdigest() != row["bridge"]["source_policy_call_sha256"]:
        raise ValueError("TRAINING_SOURCE_POLICY_CALL_BINDING_MISMATCH")
    if hashlib.sha256(call.prompt_text.encode()).hexdigest() != fp["base_policy_input_sha256"]:
        raise ValueError("TRAINING_SOURCE_PROMPT_FINGERPRINT_MISMATCH")
    traces = [t for t in row["bundle"].traces if t.model_call_index == fp["model_call_index"]]
    if len(traces) != 1: raise ValueError("TRAINING_SOURCE_TRACE_NOT_UNIQUE")
    trace = traces[0]
    menu, observation = list(trace.admissible_commands), trace.observation
    if sha256_string_sequence(menu) != fp["menu_sequence_sha256"] or hashlib.sha256(observation.encode()).hexdigest() != fp["observation_sha256"]:
        raise ValueError("TRAINING_SOURCE_TRACE_FINGERPRINT_MISMATCH")
    if row["candidate"]["menu_sha256"] != fp["menu_sequence_sha256"]:
        raise ValueError("TRAINING_SOURCE_ANALYZER_MENU_MISMATCH")
    semantic = {"complete_registered_candidate": row["candidate"], "native_source_fingerprint": fp,
        "source_policy_call_sha256": row["bridge"]["source_policy_call_sha256"], "source_prompt_text": call.prompt_text,
        "source_observation": observation, "admissible_commands": menu}
    return semantic


def derive_current_verified_rows(*, plan, verifier, source_rows, pre_receipt, native_labels):
    """Project complete verified candidates to their exact initial-state I1 view.

    `source_rows` is the original H4.4 `load_source_rows(capture)` result. The
    verification scope and full option are retained in each source row. Later
    option actions are neither discarded from causal evidence nor asserted to
    be executable at the original source state.
    """
    from .capture import CapturedPreStrategyReceipt
    receipt_read = _read_ref
    if isinstance(pre_receipt, CapturedPreStrategyReceipt):
        pre_receipt.validate()
        receipt_read = pre_receipt.read_ref
        pre_receipt = pre_receipt.receipt
    _verify_h44_seal(plan, "plan_sha256"); _verify_h44_seal(verifier, "environment_result_package_sha256")
    _verify_seal(pre_receipt, "pre_strategy_receipt_sha256")
    for key in ("accepted_raw_response_ref", "accepted_raw_request_ref", "accepted_pre_ref", "accepted_logical_ref", "accepted_attempt_ref"):
        receipt_read(pre_receipt[key])
    if (verifier["plan_sha256"] != plan["plan_sha256"] or verifier["round_id"] != plan["round_id"]
            or pre_receipt["round_id"] != plan["round_id"] or pre_receipt["logical_call_status"] != "ACCEPTED"
            or pre_receipt["source_pre_primary_record_sha256"] != plan["handoff"]["source_pre_primary_record_sha256"]):
        raise ValueError("CURRENT_PRE_PLAN_VERIFIER_IDENTITY_MISMATCH")
    selected = {x["source_state_sha256"]: x["candidate"] for x in plan["handoff"]["selected_states"]}
    from pchsi.cognitive_runtime.response import parse_provider_response, extract_output_text
    from pchsi.reference_loop.canonical import strict_json_loads
    accepted_pre = strict_json_loads(receipt_read(pre_receipt["accepted_pre_ref"]))
    original_output = strict_json_loads(extract_output_text(parse_provider_response(receipt_read(pre_receipt["accepted_raw_response_ref"]))))
    if accepted_pre["primary_record_sha256"] != pre_receipt["source_pre_primary_record_sha256"]:
        raise ValueError("PRE_STRATEGY_ACCEPTED_ARTIFACT_CHANGED")
    raw_strategies = validate_pre_strategies(original_output["training_strategies"], accepted_pre=accepted_pre,
        selected_candidates=list(selected.values()), native_labels=native_labels)
    if raw_strategies != pre_receipt["strategies"]:
        raise ValueError("PRE_STRATEGY_RAW_RESPONSE_ANNEX_CHANGED")
    sources = {x["candidate"]["source_state_sha256"]: x for x in source_rows}
    representations = {x["source_state_sha256"]: x for x in pre_receipt["strategies"]}
    if len(sources) != len(source_rows) or set(sources) != set(selected) or set(representations) != set(selected):
        raise ValueError("CURRENT_STRATEGY_SOURCE_SET_MISMATCH")
    benefits = [x for x in verifier["state_results"] if x["stable_effect"] == "BENEFIT"]
    if len(benefits) != verifier["stable_effect_counts"]["BENEFIT"]: raise ValueError("CURRENT_BENEFIT_CENSUS_MISMATCH")
    branches = {b["evidence_sha256"]: b for b in verifier["branch_records"]}
    output = []
    for benefit in benefits:
        state = benefit["source_state_sha256"]; source, representation = sources[state], representations[state]
        candidate = selected[state]; action = _candidate(candidate, native_labels)
        if candidate != source["candidate"] or candidate != representation["complete_registered_candidate"] or benefit["source_candidate_sha256"] != candidate["candidate_sha256"]:
            raise ValueError("VERIFIED_COMPLETE_CANDIDATE_CHANGED")
        semantic = _source_context(source); fp = source["fingerprint"]
        if benefit["native_source_fingerprint_sha256"] != fp["fingerprint_sha256"]: raise ValueError("VERIFIED_SOURCE_FINGERPRINT_MISMATCH")
        if representation["strategy"]["action"] != action or action not in semantic["admissible_commands"]:
            raise ValueError("PRE_SOURCE_ACTION_MISMATCH")
        native_labels.adapter.canonical_strategy_target_json(representation["strategy"])
        pair_rows = [p for p in verifier["pair_results"] if p["source_state_sha256"] == state and p["complete"]]
        if not pair_rows: raise ValueError("VERIFIED_OPTION_HAS_NO_COMPLETE_PAIRS")
        evidence = []
        for pair in pair_rows:
            branch = branches[pair["f1_evidence_sha256"]]; _verify_h44_seal(branch, "evidence_sha256")
            if (branch["arm"] != "F1" or branch["source_state_sha256"] != state
                    or branch["source_candidate_sha256"] != candidate["candidate_sha256"]
                    or branch["native_source_fingerprint_sha256"] != fp["fingerprint_sha256"]
                    or branch["replicate_index"] != pair["replicate_index"]
                    or branch["evidence_complete"] is not True or branch["scientific_outcome_produced"] is not True):
                raise ValueError("VERIFIED_F1_COMPLETE_CANDIDATE_BINDING_MISMATCH")
            replay = branch["source_replay_report"]
            if (replay["status"] != "PASS" or replay["failure_code"] is not None
                    or replay["source_fingerprint_sha256"] != fp["fingerprint_sha256"] or replay["replay_fingerprint_sha256"] != fp["fingerprint_sha256"]):
                raise ValueError("VERIFIED_F1_SOURCE_REPLAY_MISMATCH")
            sequence = branch["intervention_sequence"]
            if not sequence or branch["option_environment_step_count"] != len(sequence): raise ValueError("VERIFIED_F1_INTERVENTION_MISSING")
            first = sequence[0]
            if (first["action"] != action or first["pre_menu"] != semantic["admissible_commands"]
                    or first["pre_observation"] != semantic["source_observation"]
                    or first["pre_menu_sequence_sha256"] != fp["menu_sequence_sha256"] or first["pre_observation_sha256"] != fp["observation_sha256"]):
                raise ValueError("VERIFIED_F1_INITIAL_ACTION_SOURCE_MISMATCH")
            if candidate["candidate_status"] == "EXECUTABLE_SHORT_OPTION":
                if (len(sequence) > len(candidate["option_actions"])
                        or [x["action"] for x in sequence] != candidate["option_actions"][:len(sequence)]
                        or [x["registered_action_index"] for x in sequence] != list(range(len(sequence)))
                        or not branch["typed_option_stop_reason"]):
                    raise ValueError("VERIFIED_F1_FULL_OPTION_EVIDENCE_INVALID")
                if branch["typed_option_stop_reason"] == "REGISTERED_ACTIONS_EXHAUSTED" and len(sequence) != len(candidate["option_actions"]):
                    raise ValueError("VERIFIED_F1_OPTION_TRUNCATION_FORBIDDEN")
            evidence.append(branch["evidence_sha256"])
        strategy = copy.deepcopy(representation["strategy"])
        row = {"schema_id": native_labels.adapter.INPUT_SCHEMA, "schema_version": 1, "source_state_sha256": state,
            "source_semantic_row_sha256": digest(semantic),
            "policy_visible_context": {"source_prompt_bound": True, "source_prompt_text": semantic["source_prompt_text"], "admissible_commands": semantic["admissible_commands"]},
            "strategy": strategy, "verification": {"same_state_f0f1_verified": True, "verification_label": "BENEFIT",
                "verified_strategy_sha256": strategy["verified_strategy_sha256"], "verification_receipt_sha256": verifier["environment_result_package_sha256"],
                "outcome_visible_to_policy": False, "reward_visible_to_policy": False,
                "causal_verification_scope": representation["causal_verification_scope"], "standalone_action_causal_effect_claimed": False,
                "complete_registered_candidate": copy.deepcopy(candidate), "f1_complete_evidence_sha256s": evidence,
                "pre_strategy_receipt_sha256": pre_receipt["pre_strategy_receipt_sha256"], "native_source_fingerprint_sha256": fp["fingerprint_sha256"]}}
        native_labels.adapter.validate_verified_benefit_input(row)
        output.append(row)
    return output
