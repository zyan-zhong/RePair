from __future__ import annotations

import json

import pytest

from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import STAGE_1B, STAGE_2
import importlib.util
import sys
from pathlib import Path

_HELPER_PATH = Path(__file__).with_name("scientific_authority_test_helpers.py")
_SPEC = importlib.util.spec_from_file_location("_memory_science_test_helpers_authority", _HELPER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _HELPERS
_SPEC.loader.exec_module(_HELPERS)
build_authority = _HELPERS.build_authority
dsha = _HELPERS.dsha
write_json = _HELPERS.write_json


def _load(path, meta, stage=STAGE_1B):
    return load_scientific_result_authority_v2(
        path=path,
        expected_stage=stage,
        expected_fixed_code_head=meta["fixed_head"],
        expected_scientific_program_sha256=meta["program_sha"],
    )


def test_complete_artifact_backed_authority_passes(tmp_path):
    path, meta = build_authority(tmp_path / "authority")
    validated = _load(path, meta)
    assert validated.disposition("Q1") == "SUPPORTED"
    assert validated.disposition("Q2") == "NOT_SUPPORTED"


def test_unbound_identity_artifact_is_rejected(tmp_path):
    path, meta = build_authority(tmp_path / "authority")
    value = json.loads(path.read_text())
    value["supporting_artifacts"] = [
        row for row in value["supporting_artifacts"]
        if row["role"] != "EXECUTION_BINDING:runtime_identity"
    ]
    value["result_authority_sha256"] = "0" * 64
    value["result_authority_sha256"] = dsha(
        "FAILURE_MEMORY_SCIENTIFIC_RESULT_AUTHORITY_V2",
        value,
        "result_authority_sha256",
    )
    write_json(path, value)
    with pytest.raises(ValueError, match="not bound"):
        _load(path, meta)


def test_forged_registered_decision_is_rejected(tmp_path):
    path, meta = build_authority(tmp_path / "authority")
    value = json.loads(path.read_text())
    value["registered_statistical_decision"]["question_decisions"]["Q1"]["disposition"] = "NOT_SUPPORTED"
    value["result_authority_sha256"] = "0" * 64
    value["result_authority_sha256"] = dsha(
        "FAILURE_MEMORY_SCIENTIFIC_RESULT_AUTHORITY_V2",
        value,
        "result_authority_sha256",
    )
    write_json(path, value)
    with pytest.raises(ValueError, match="differs from independent recomputation"):
        _load(path, meta)


def test_same_round_readback_is_rejected(tmp_path):
    path, meta = build_authority(tmp_path / "authority", stage=STAGE_2)
    value = json.loads(path.read_text())
    role = "CELL_RESULT:r1-g1"
    support = next(row for row in value["supporting_artifacts"] if row["role"] == role)
    cell_path = path.parent / support["path"]
    cell = json.loads(cell_path.read_text())
    cell["same_round_memory_readback"] = True
    cell["cell_result_sha256"] = "0" * 64
    cell["cell_result_sha256"] = dsha(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1", cell, "cell_result_sha256"
    )
    write_json(cell_path, cell)
    with pytest.raises(ValueError):
        _load(path, meta, STAGE_2)


def test_role_pack_population_is_mandatory(tmp_path):
    path, meta = build_authority(tmp_path / "authority")
    value = json.loads(path.read_text())
    role_audit = value["audit_bindings"]["role_pack"]
    audit_path = path.parent / role_audit["path"]
    audit = json.loads(audit_path.read_text())
    audit["role_pack_presence_counts"]["researcher"] = 0
    write_json(audit_path, audit)
    with pytest.raises(ValueError):
        _load(path, meta)


def test_canonical_jsonl_terminal_lf_is_accepted(tmp_path):
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    from pchsi.memory import scientific_authority as authority_module

    path = tmp_path / "cells.jsonl"
    row = {"cell_id": "cell-1", "value": 1}
    path.write_bytes(canonical_json_bytes(row))

    assert authority_module._parse_jsonl(path) == [row]


def test_jsonl_without_terminal_lf_is_rejected(tmp_path):
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    from pchsi.memory import scientific_authority as authority_module

    path = tmp_path / "cells.jsonl"
    row = {"cell_id": "cell-1", "value": 1}
    path.write_bytes(canonical_json_bytes(row).removesuffix(b"\n"))

    with pytest.raises(ValueError, match="noncanonical JSONL row 1"):
        authority_module._parse_jsonl(path)


def test_jsonl_blank_row_is_rejected(tmp_path):
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes
    from pchsi.memory import scientific_authority as authority_module

    path = tmp_path / "cells.jsonl"
    row = {"cell_id": "cell-1", "value": 1}
    path.write_bytes(canonical_json_bytes(row) + b"\n")

    with pytest.raises(ValueError, match="blank JSONL row 2"):
        authority_module._parse_jsonl(path)


def test_stage1b_snapshot_identity_must_match_execution_binding(tmp_path):
    path, meta = build_authority(
        tmp_path / "authority",
        snapshot_binding_sha="e" * 64,
    )
    with pytest.raises(
        ValueError,
        match="cell snapshot identity differs from execution snapshot binding",
    ):
        _load(path, meta)


def test_stage2_snapshot_identities_must_be_registered(tmp_path):
    path, meta = build_authority(
        tmp_path / "authority",
        stage=STAGE_2,
        stage2_registry_snapshots=["d" * 64, "f" * 64],
    )
    with pytest.raises(
        ValueError,
        match="cell snapshot identity is absent from snapshot registry",
    ):
        _load(path, meta, STAGE_2)
