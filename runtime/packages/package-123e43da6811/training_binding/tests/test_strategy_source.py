from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

WORK = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WORK / "v17"), str(WORK / "v17/native_bba_full/src")]


def module():
    assert (WORK / "v17/training_binding/strategy_source.py").is_file(), "same-PRE strategy source producer missing"
    from training_binding import strategy_source
    return strategy_source


def h44_seal(value, field):
    from training_binding.materializer import canonical
    result = copy.deepcopy(value)
    result[field] = hashlib.sha256(canonical({k: v for k, v in result.items() if k != field}) + b"\n").hexdigest()
    return result


def fixture(tmp_path):
    from test_native_labels import _setup
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.cognitive_runtime.identity import build_logical_call_record, build_transport_attempt_record
    from pchsi.memory.source_state_contracts import SourceDecisionStateFingerprintV1
    from pchsi.evaluation.budget import BudgetState
    from pchsi.evaluation.action_trace import sha256_string_sequence
    m = module()
    native, original = _setup()
    menu = ["look", "go to sofa 1", "go to shelf 1"]
    candidate = dict(schema_id="ANALYZER_REPAIR_CANDIDATE_V1", schema_version=1, candidate_kind="FAILURE_REPAIR",
        source_state_sha256="b" * 64, menu_sha256=sha256_string_sequence(menu), source_proposal_sha256="c" * 64,
        candidate_status="EXECUTABLE_SHORT_OPTION", exact_action=None, option_actions=["go to sofa 1", "go to shelf 1"],
        termination_condition="Entire frozen option termination; fixture only.", requires_environment_verification=True,
        live_menu_revalidation_required=True, all_intervention_actions_count_against_environment_budget=True)
    candidate["candidate_sha256"] = domain_hash(candidate["schema_id"], candidate, excluded_field="candidate_sha256")
    pre = {"round_id": "fixture-round", "primary_record_sha256": "a" * 64, "selected_candidate_sha256s": [candidate["candidate_sha256"]]}
    strategy = copy.deepcopy(original["strategy"])
    del strategy["verified_strategy_sha256"]
    strategy.update(action=menu[1], evidence_refs=m.candidate_evidence_refs(candidate))
    annex = [dict(source_state_sha256="b" * 64, source_candidate_sha256=candidate["candidate_sha256"], strategy=strategy)]
    value = {**pre, "training_strategies": annex}
    raw = json.dumps({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}]}).encode()
    raw_request = b'{"model":"fixture","input":[]}'
    expected = dict(logical_call_id="d" * 64, scientific_unit_identity_sha256="e" * 64, stage_id="R-PRE-PRIMARY-V2",
        condition_id=None, round_id=pre["round_id"], policy_version="fixture-parent", request_body_sha256=domain_hash("COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1", json.loads(raw_request)),
        runtime_manifest_sha256="a" * 64)
    call = tmp_path / expected["logical_call_id"]; call.mkdir()
    logical = build_logical_call_record(**expected, role="TRAINING_RESEARCHER", terminal_method_status="ACCEPTED", contributing_attempt_id="d" * 64 + ":0")
    attempt = build_transport_attempt_record(logical_call_id="d" * 64, transport_attempt_id="d" * 64 + ":0", transport_attempt_index=0,
        bytes_transmission_state="CONFIRMED_SENT", retry_class="INITIAL", retry_reason=None, retry_authority="NOT_APPLICABLE", provider_response_id="fixture",
        terminal_attempt_status="SUCCEEDED", ambiguous_post_send_disposition_id=None, raw_request_sha256=hashlib.sha256(raw_request).hexdigest(),
        raw_response_sha256=hashlib.sha256(raw).hexdigest(), input_tokens=None, output_tokens=None, reasoning_tokens=None, latency_ms=None, cost_usd=None)
    for name, item in [("logical_call.json", logical), ("attempt_000.json", attempt), ("validated_artifact.json", pre)]:
        (call / name).write_text(json.dumps(item))
    (call / "raw_response.json").write_bytes(raw)
    (call / "raw_request.json").write_bytes(raw_request)
    receipt = m.adopt_pre_strategies(call_dir=call, expected=expected, selected_candidates=[candidate], native_finalize=lambda value: value, native_labels=native)
    prompt, observation = "Frozen source prompt fixture", "You are beside a table."
    fp = SourceDecisionStateFingerprintV1(schema_id="SOURCE_DECISION_STATE_FINGERPRINT_V1", schema_version=1,
        source_task_id="task", source_gamefile_sha256="a" * 64, source_bundle_sha256="c" * 64, source_policy_condition="I1",
        executed_prefix_sha256="a" * 64, observation_sha256=hashlib.sha256(observation.encode()).hexdigest(),
        menu_sequence_sha256=sha256_string_sequence(menu), memory_m0_sha256="a" * 64, interface_feedback_code=None,
        budget_state=BudgetState(), model_call_index=0, base_policy_input_sha256=hashlib.sha256(prompt.encode()).hexdigest(), fingerprint_sha256=None).to_dict()
    call_obj = SimpleNamespace(prompt_text=prompt, model_call_index=0, to_json=lambda: json.dumps({"prompt_text": prompt}))
    source = dict(candidate=candidate, fingerprint=fp, source_call=call_obj,
        bridge={"source_policy_call_sha256": hashlib.sha256(call_obj.to_json().encode()).hexdigest(),
            "source_candidate_sha256": candidate["candidate_sha256"], "analyzer_source_state_sha256": "b" * 64,
            "native_source_fingerprint_sha256": fp["fingerprint_sha256"], "source_bundle_sha256": fp["source_bundle_sha256"], "source_call_index": 0},
        bundle=SimpleNamespace(traces=[SimpleNamespace(model_call_index=0, observation=observation, admissible_commands=menu)]))
    plan = dict(round_id=pre["round_id"], handoff={"source_pre_primary_record_sha256": pre["primary_record_sha256"],
        "selected_states": [{"source_state_sha256": "b" * 64, "candidate": candidate}]},
        states=[dict(source_state_sha256="b" * 64, source_candidate_sha256=candidate["candidate_sha256"], native_source_fingerprint_sha256=fp["fingerprint_sha256"])])
    from training_binding.materializer import _seal
    plan = h44_seal(plan, "plan_sha256")
    branches, pairs = [], []
    for i in range(5):
        branch = dict(source_state_sha256="b" * 64, source_candidate_sha256=candidate["candidate_sha256"], native_source_fingerprint_sha256=fp["fingerprint_sha256"],
            arm="F1", replicate_index=i, evidence_complete=True, scientific_outcome_produced=True,
            source_replay_report={"status": "PASS", "failure_code": None, "source_fingerprint_sha256": fp["fingerprint_sha256"], "replay_fingerprint_sha256": fp["fingerprint_sha256"]},
            option_environment_step_count=2, typed_option_stop_reason="REGISTERED_ACTIONS_EXHAUSTED",
            intervention_sequence=[dict(action=action, registered_action_index=j, pre_menu=menu, pre_observation=observation,
                pre_menu_sequence_sha256=sha256_string_sequence(menu), pre_observation_sha256=fp["observation_sha256"])
                for j, action in enumerate(candidate["option_actions"])])
        branch = h44_seal(branch, "evidence_sha256"); branches.append(branch)
        pairs.append(dict(source_state_sha256="b" * 64, source_candidate_sha256=candidate["candidate_sha256"], replicate_index=i,
            complete=True, effect="BENEFIT", f1_evidence_sha256=branch["evidence_sha256"]))
    verifier = h44_seal(dict(round_id=pre["round_id"], plan_sha256=plan["plan_sha256"], stable_effect_counts={"BENEFIT": 1},
        state_results=[{**plan["states"][0], "stable_effect": "BENEFIT"}], pair_results=pairs, branch_records=branches), "environment_result_package_sha256")
    return m, native, plan, verifier, source, receipt, expected


def test_same_pre_complete_option_source_view_preserves_causal_scope(tmp_path):
    m, native, plan, verifier, source, receipt, _ = fixture(tmp_path)
    rows = m.derive_current_verified_rows(plan=plan, verifier=verifier, source_rows=[source], pre_receipt=receipt, native_labels=native)
    assert len(rows) == 1
    native.adapter.validate_verified_benefit_input(rows[0])
    assert rows[0]["strategy"]["action"] == source["candidate"]["option_actions"][0]
    assert rows[0]["verification"]["standalone_action_causal_effect_claimed"] is False
    assert rows[0]["verification"]["causal_verification_scope"] == "COMPLETE_REGISTERED_OPTION"
    assert rows[0]["verification"]["complete_registered_candidate"] == source["candidate"]
    assert len(rows[0]["verification"]["complete_registered_candidate"]["option_actions"]) == 2


@pytest.mark.parametrize("change", ["first_action", "source_menu", "source_prompt", "termination", "pre_strategy", "raw_response", "truncated", "bridge"])
def test_source_view_rejects_changed_pre_or_real_execution(tmp_path, change):
    m, native, plan, verifier, source, receipt, _ = fixture(tmp_path)
    from training_binding.materializer import _seal
    if change == "first_action":
        verifier["branch_records"][0]["intervention_sequence"][0]["action"] = "look"
        verifier["branch_records"][0] = h44_seal(verifier["branch_records"][0], "evidence_sha256")
        verifier["pair_results"][0]["f1_evidence_sha256"] = verifier["branch_records"][0]["evidence_sha256"]
        verifier = h44_seal(verifier, "environment_result_package_sha256")
    if change == "source_menu": source["bundle"].traces[0].admissible_commands = ["look"]
    if change == "source_prompt": source["source_call"].prompt_text = "Future fabricated prompt"
    if change == "termination": source["candidate"]["termination_condition"] = "new stop condition"
    if change == "pre_strategy":
        receipt["strategies"][0]["strategy"]["current_subgoal"] = "new hindsight target"
        receipt = _seal(receipt, "pre_strategy_receipt_sha256")
    if change == "raw_response": Path(receipt["accepted_raw_response_ref"]["path"]).write_bytes(b"{}")
    if change == "bridge": source["bridge"]["source_call_index"] = 1
    if change == "truncated":
        verifier["branch_records"][0]["intervention_sequence"].pop()
        verifier["branch_records"][0]["option_environment_step_count"] = 1
        verifier["branch_records"][0] = h44_seal(verifier["branch_records"][0], "evidence_sha256")
        verifier["pair_results"][0]["f1_evidence_sha256"] = verifier["branch_records"][0]["evidence_sha256"]
        verifier = h44_seal(verifier, "environment_result_package_sha256")
    with pytest.raises((ValueError, RuntimeError)):
        m.derive_current_verified_rows(plan=plan, verifier=verifier, source_rows=[source], pre_receipt=receipt, native_labels=native)


def test_pre_annex_requires_same_accepted_native_call(tmp_path):
    m, native, _, _, source, receipt, expected = fixture(tmp_path)
    from pchsi.cognitive_runtime.identity import build_logical_call_record
    logical = build_logical_call_record(**expected, role="TRAINING_RESEARCHER", terminal_method_status="SEMANTIC_INVALID", contributing_attempt_id=None)
    call = Path(receipt["accepted_raw_response_ref"]["path"]).parent
    (call / "logical_call.json").write_text(json.dumps(logical))
    with pytest.raises(ValueError, match="ACCEPTED"):
        m.adopt_pre_strategies(call_dir=call, expected=expected, selected_candidates=[source["candidate"]], native_finalize=lambda v: v, native_labels=native)


def test_real_paired_canary_native_h44_identity_formulas():
    from training_binding.materializer import _verify_h44_seal
    root = WORK / "v17/server_canary_paired_03"
    plan = json.loads((root / "EXECUTION_PLAN.json").read_bytes())
    verifier = json.loads((root / "verifier/ENVIRONMENT_RESULT_PACKAGE.json").read_bytes())
    _verify_h44_seal(plan, "plan_sha256")
    _verify_h44_seal(verifier, "environment_result_package_sha256")
    assert verifier["plan_sha256"] == plan["plan_sha256"]
    assert verifier["branch_records"]
    for branch in verifier["branch_records"]:
        _verify_h44_seal(branch, "evidence_sha256")
