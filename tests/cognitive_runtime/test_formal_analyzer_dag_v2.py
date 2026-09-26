from __future__ import annotations

from copy import deepcopy

import pytest

from pchsi.reference_loop.canonical import domain_hash
from pchsi.cognitive_runtime.formal_registry_v2 import validate_formal_dag_v2


def _row_local(unit: str, condition: str, a1_sha):
    return {
        "source_unit_id": unit,
        "condition_id": condition,
        "common_evidence_pack_sha256": "e" * 64,
        "a1_local_result_sha256": a1_sha,
        "memory_pack_sha256": None,
        "candidate_budget": 1,
        "abstain_permitted": True,
    }


def _group_row(condition: str, memory):
    return {
        "group_id": "1" * 64,
        "group_manifest_sha256": "g" * 64,
        "condition_id": condition,
        "member_bindings": [
            {
                "source_unit_id": "formal-u1",
                "a1_local_result_sha256": "a" * 64,
                "error_instance_id": "err-1",
            },
            {
                "source_unit_id": "formal-u2",
                "a1_local_result_sha256": "b" * 64,
                "error_instance_id": "err-2",
            },
        ],
        "a1_local_result_sha256s": ["a" * 64, "b" * 64],
        "current_evidence_sha256s": [
            "1" * 64,
            "a" * 64,
            "b" * 64,
            "g" * 64,
        ],
        "memory_pack_sha256": memory,
        "candidate_budget": 1,
        "abstain_permitted": True,
    }


def _valid():
    value = {
        "schema_id": "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        "schema_version": 2,
        "round_id": "formal-round-v1",
        "registered_universe_sha256": "u" * 64,
        "registered_local_unit_ids": ["formal-u1", "formal-u2"],
        "local_condition_rows": [
            _row_local("formal-u1", "A0", None),
            _row_local("formal-u1", "A1", "a" * 64),
            _row_local("formal-u2", "A0", None),
            _row_local("formal-u2", "A1", "b" * 64),
        ],
        "registered_group_manifest_sha256s": ["g" * 64],
        "group_condition_rows": [
            _group_row("A2", None),
            _group_row("A3", "m" * 64),
        ],
        "local_runtime_input_registry_sha256": "l" * 64,
        "group_runtime_input_registry_sha256": "r" * 64,
        "formal_dag_sha256": "0" * 64,
    }
    # Replace non-hex placeholders used for readability above.
    replacements = {
        "u": "c", "g": "d", "m": "f", "l": "2", "r": "3",
    }
    def fix(obj):
        if isinstance(obj, dict):
            return {k: fix(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [fix(v) for v in obj]
        if isinstance(obj, str) and len(obj) == 64 and len(set(obj)) == 1:
            return replacements.get(obj[0], obj[0]) * 64
        return obj
    value = fix(value)
    value["formal_dag_sha256"] = domain_hash(
        "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        value,
        excluded_field="formal_dag_sha256",
    )
    return value


def _rehash(value):
    value["formal_dag_sha256"] = domain_hash(
        "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        value,
        excluded_field="formal_dag_sha256",
    )
    return value


def test_valid_grouped_formal_dag_v2():
    validate_formal_dag_v2(_valid())


def test_rejects_missing_local_condition():
    value = _valid()
    value["local_condition_rows"].pop()
    _rehash(value)
    with pytest.raises(ValueError, match="U_reg x A0-A1"):
        validate_formal_dag_v2(value)


def test_rejects_a0_a1_evidence_drift():
    value = _valid()
    value["local_condition_rows"][1]["common_evidence_pack_sha256"] = "9" * 64
    _rehash(value)
    with pytest.raises(ValueError, match="common evidence differs"):
        validate_formal_dag_v2(value)


def test_rejects_group_member_outside_local_ureg():
    value = _valid()
    for row in value["group_condition_rows"]:
        row["member_bindings"][0]["source_unit_id"] = "not-in-u-reg"
    _rehash(value)
    with pytest.raises(ValueError, match="outside Formal local U_reg"):
        validate_formal_dag_v2(value)


def test_rejects_non_reused_a1_bytes():
    value = _valid()
    for row in value["group_condition_rows"]:
        row["member_bindings"][0]["a1_local_result_sha256"] = "8" * 64
        row["a1_local_result_sha256s"] = ["8" * 64, "b" * 64]
    _rehash(value)
    with pytest.raises(ValueError, match="byte-reuse Formal A1"):
        validate_formal_dag_v2(value)


def test_rejects_a2_a3_group_evidence_drift():
    value = _valid()
    value["group_condition_rows"][1]["current_evidence_sha256s"].append("7" * 64)
    value["group_condition_rows"][1]["current_evidence_sha256s"].sort()
    _rehash(value)
    with pytest.raises(ValueError, match="grouped evidence drift"):
        validate_formal_dag_v2(value)


def test_rejects_a2_memory():
    value = _valid()
    value["group_condition_rows"][0]["memory_pack_sha256"] = "6" * 64
    _rehash(value)
    with pytest.raises(ValueError, match="A2 cannot receive Memory"):
        validate_formal_dag_v2(value)


def test_rejects_a3_without_memory():
    value = _valid()
    value["group_condition_rows"][1]["memory_pack_sha256"] = None
    _rehash(value)
    with pytest.raises(ValueError, match="A3 requires"):
        validate_formal_dag_v2(value)
