from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "producer"))


def fixture_request_type():
    spec = importlib.util.spec_from_file_location(
        "request_fixture",
        ROOT / "tests" / "fixtures" / "rollout_collection.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.RoundRolloutCollectionRequestV1


def canonical_no_newline(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def native_request_value():
    cls = fixture_request_type()
    return cls(
        round_id="R2",
        execution_attempt_id="fresh-exec",
        parent_policy_id="PI0",
        parent_policy_artifact_sha256="a" * 64,
        policy_runtime_binding_sha256="b" * 64,
        execution_profile_sha256="c" * 64,
        train_update_manifest_sha256="d" * 64,
        round_memory_runtime_authority_sha256="e" * 64,
        round_start_memory_snapshot_sha256="f" * 64,
        token_budget_contract_sha256="1" * 64,
        execution_namespace="fresh-exec",
        rollout_seed=17,
    ).to_dict()


def legacy_v1233i_value():
    value = native_request_value()
    payload = {k: v for k, v in value.items() if k != "request_sha256"}
    value["request_sha256"] = hashlib.sha256(canonical_no_newline(payload)).hexdigest()
    return value


def test_v1233i_plain_hash_is_repaired_only_in_integrity_field():
    import request_hash_repair as m

    cls = fixture_request_type()
    source = legacy_v1233i_value()
    repaired, receipt = m.repair_request_value(source, request_type=cls)
    expected = native_request_value()

    assert repaired == expected
    assert repaired["request_sha256"] != source["request_sha256"]
    assert {k: v for k, v in repaired.items() if k != "request_sha256"} == {
        k: v for k, v in source.items() if k != "request_sha256"
    }
    assert receipt["source_hash_pattern"] == "V1233I_PLAIN_CANONICAL_SHA256"
    assert receipt["mutation_scope"] == "REQUEST_SHA256_ONLY"
    assert receipt["scientific_semantics_changed"] is False
    assert receipt["execution_attempt_id_preserved"] is True


def test_native_canonical_request_is_adopted_without_change():
    import request_hash_repair as m

    cls = fixture_request_type()
    source = native_request_value()
    repaired, receipt = m.repair_request_value(source, request_type=cls)
    assert repaired == source
    assert receipt["source_hash_pattern"] == "NATIVE_DOMAIN_HASH_ALREADY_VALID"
    assert receipt["mutation_scope"] == "NONE"


def test_unknown_bad_hash_fails_closed():
    import request_hash_repair as m

    cls = fixture_request_type()
    source = native_request_value()
    source["request_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="REQUEST_HASH_FAILURE_NOT_REGISTERED_V1233I_BUG"):
        m.repair_request_value(source, request_type=cls)


def test_repair_requires_exact_fixed_selection_rule():
    import request_hash_repair as m

    cls = fixture_request_type()
    source = legacy_v1233i_value()
    source["selection_rule"] = "OTHER"
    with pytest.raises(ValueError):
        m.repair_request_value(source, request_type=cls)


def test_recover_uses_repaired_request_and_preserves_original_as_source():
    text = (ROOT / "recover.py").read_text()
    assert "materialize_request_repair" in text
    assert "source_request_file_sha256" in text
    assert "serialized_integrity_hash_repaired" in text
    assert "scientific_request_semantics_changed" in text
    assert "write_new_bytes(req,ctx['request'].read_bytes())" not in text
