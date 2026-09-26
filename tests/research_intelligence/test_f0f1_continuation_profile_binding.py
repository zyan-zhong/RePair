"""Pure request-boundary tests. No model, environment, or network calls."""
import copy
import json
from pathlib import Path
import pytest
from pchsi.research_intelligence import human_f0f1_runtime as runtime
from pchsi.evaluation.interface_isolation_request import I1StructuredPolicyRequestV1
from pchsi.evaluation.policy_request import E1PolicyRequestV1
from pchsi.evaluation.canonical_evidence import canonical_json_bytes


def test_bound_continuation_api_exists():
    assert hasattr(runtime, "build_bound_continuation_request_v1"), "MISSING_BOUND_CONTINUATION_REQUEST_API"


def _contract():
    return runtime.continuation_request_contract_v1("I1_EXECUTION_PROFILE_V1")


def _runtime():
    return {"served_model_name": "PI0-CLEAN-QWEN25-3B-INSTRUCT", "continuation_request_contract": _contract()}


def _request(value=None):
    return runtime.build_bound_continuation_request_v1(
        runtime=_runtime() if value is None else value,
        prompt_text="Frozen prompt.", seed=31, request_id="test-call-1",
    )


def test_clean_i1_preserves_factory_bytes_except_bound_model():
    expected = I1StructuredPolicyRequestV1(prompt_text="Frozen prompt.", seed=31, request_id="test-call-1").to_wire_dict()
    expected["model"] = _runtime()["served_model_name"]
    request = _request()
    assert request.to_wire_dict() == expected
    assert request.to_wire_bytes() == canonical_json_bytes(expected)
    assert "enum" not in expected["structured_outputs"]["json"]["properties"]["action"]


def test_legacy_i1_factory_identity_not_changed():
    old = I1StructuredPolicyRequestV1(prompt_text="Frozen prompt.", seed=31, request_id="test-call-1").to_wire_dict()
    raw = E1PolicyRequestV1(prompt_text="Frozen prompt.", seed=31, request_id="test-call-1").to_wire_dict()
    assert old["model"] == raw["model"]
    assert old["structured_outputs"] is not None and raw["structured_outputs"] is None


@pytest.mark.parametrize("field,value", [("profile_id", "UNKNOWN"), ("request_kind", "R0"), ("serialization_schema_sha256", "0" * 64)])
def test_contract_drift_rejected(field, value):
    current = _runtime()
    current["continuation_request_contract"][field] = value
    with pytest.raises((ValueError, TypeError)):
        _request(current)


def test_missing_contract_has_no_raw_fallback():
    with pytest.raises((ValueError, TypeError)):
        _request({"served_model_name": "PI0-CLEAN-QWEN25-3B-INSTRUCT"})


def test_i2_not_silently_enabled():
    with pytest.raises(ValueError):
        runtime.continuation_request_contract_v1("I2_EXECUTION_PROFILE_V1")


def test_explicit_r0_contract_is_not_inferred_from_missing_metadata():
    current = _runtime()
    current["continuation_request_contract"] = runtime.continuation_request_contract_v1("R0_EXECUTION_PROFILE_V1")
    assert _request(current).to_wire_dict()["structured_outputs"] is None


@pytest.mark.parametrize("mutation", ["missing_constraint", "wrong_model", "wrong_seed", "wrong_prompt", "wrong_temperature", "enum", "extra_key"])
def test_real_wire_drift_rejected(mutation):
    request = _request()
    wire = copy.deepcopy(request.to_wire_dict())
    if mutation == "missing_constraint": wire["structured_outputs"] = None
    elif mutation == "wrong_model": wire["model"] = "OTHER"
    elif mutation == "wrong_seed": wire["seed"] = 47
    elif mutation == "wrong_prompt": wire["messages"][0]["content"] = "changed"
    elif mutation == "wrong_temperature": wire["temperature"] = 0.7
    elif mutation == "enum": wire["structured_outputs"]["json"]["properties"]["action"]["enum"] = ["look"]
    else: wire["extra_key"] = True
    with pytest.raises(ValueError):
        runtime.validate_continuation_wire_v1(
            runtime=_runtime(), raw=canonical_json_bytes(wire),
            expected_prompt="Frozen prompt.", expected_seed=31, expected_request_id="test-call-1",
        )


def test_expected_wire_accepted():
    runtime.validate_continuation_wire_v1(
        runtime=_runtime(), raw=_request().to_wire_bytes(),
        expected_prompt="Frozen prompt.", expected_seed=31, expected_request_id="test-call-1",
    )


def test_no_source_population_constants_in_new_helpers():
    import inspect
    text = inspect.getsource(runtime.build_bound_continuation_request_v1)
    assert "195" not in text and "390" not in text and "130" not in text


def test_runner_and_aggregator_are_wired_to_shared_guard():
    root = Path(__file__).resolve().parents[2]
    runner = (root / "scripts/research_intelligence/run_human_reference_f0f1_branch_v2.py").read_text()
    aggregator = (root / "scripts/research_intelligence/aggregate_human_reference_f0f1_v2.py").read_text()
    assert "build_bound_continuation_request_v1(" in runner
    assert "validate_continuation_wire_v1(" in runner
    assert "validate_continuation_record_v1(value, expected)" in aggregator
    assert 'request_kind="R0"' not in runner
