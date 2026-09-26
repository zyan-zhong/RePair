from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.memory.scientific_decision import FM1, STAGE_1B


SCRIPT = (
    Path(__file__).parents[2]
    / "scripts/memory/aggregate_memory_live_stage_v2.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "_stage1b_fm1_role_pack_aggregate_target",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fm1_payload() -> dict[str, object]:
    return {
        "relevant_start": {
            "model_call_index": 2,
            "pre_observation": "You are in a room.",
            "interface_feedback_before": None,
        },
        "events": [
            {
                "model_call_index": 2,
                "pre_observation": "You are in a room.",
                "literal_action": "look",
                "normalized_action": "look",
                "submitted_environment_action": "look",
                "execution_status": "EXECUTED",
                "interface_feedback_before": None,
                "resulting_observation": "You see a table.",
                "visible_state_change_disposition": "STATE_CHANGED",
            }
        ],
    }


def _write_pack(tmp_path: Path, module, payload: object) -> Path:
    value = {
        "schema_id": "FAILURE_MEMORY_ROLE_PACK_V1",
        "schema_version": 1,
        "role": "POLICY",
        "cell_id": "c" * 64,
        "execution_manifest_sha256": "a" * 64,
        "payload": payload,
        "pack_sha256": "0" * 64,
    }
    value["pack_sha256"] = module.dsha(
        "FAILURE_MEMORY_ROLE_PACK_V1",
        value,
        "pack_sha256",
    )
    path = tmp_path / "POLICY_MEMORY_PACK_V1.json"
    path.write_bytes(module.canonical_json_bytes(value))
    return path


def test_stage1b_fm1_accepts_exact_frozen_raw_policy_view(tmp_path: Path) -> None:
    module = _load()
    payload = _fm1_payload()
    path = _write_pack(tmp_path, module, payload)

    value = module.validate_role_pack(
        path,
        role="policy",
        cell_id="c" * 64,
        execution_manifest_sha256="a" * 64,
        stage=STAGE_1B,
        condition=FM1,
        expected_stage1b_fm1_payload=payload,
    )

    assert value["payload"] == payload


def test_stage1b_fm1_requires_exact_template_binding(tmp_path: Path) -> None:
    module = _load()
    payload = _fm1_payload()
    path = _write_pack(tmp_path, module, payload)

    wrong = _fm1_payload()
    wrong["relevant_start"] = {
        "model_call_index": 3,
        "pre_observation": "different",
        "interface_feedback_before": None,
    }

    with pytest.raises(
        SystemExit,
        match="STAGE1B_FM1_ROLE_PACK_TEMPLATE_BINDING",
    ):
        module.validate_role_pack(
            path,
            role="policy",
            cell_id="c" * 64,
            execution_manifest_sha256="a" * 64,
            stage=STAGE_1B,
            condition=FM1,
            expected_stage1b_fm1_payload=wrong,
        )


def test_fm1_exception_is_not_global_policy_schema_broadening(
    tmp_path: Path,
) -> None:
    module = _load()
    payload = _fm1_payload()
    path = _write_pack(tmp_path, module, payload)

    with pytest.raises(
        ValueError,
        match="Policy prompt payload fields differ from frozen projection",
    ):
        module.validate_role_pack(
            path,
            role="policy",
            cell_id="c" * 64,
            execution_manifest_sha256="a" * 64,
            stage="STAGE_3_FROZEN_FORMAL_EVALUATION",
            condition=FM1,
            expected_stage1b_fm1_payload=None,
        )


def test_stage1b_fm1_template_loader_rechecks_a0_binding_sha() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "representation_template_file_sha256" in source
    assert "FM1PolicyVisiblePayloadV1.from_dict" in source
    assert "STAGE1B_FM1_ROLE_PACK_TEMPLATE_BINDING" in source
