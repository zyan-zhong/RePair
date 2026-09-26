from __future__ import annotations

import ast
import json
from pathlib import Path

from smoke.common import require_domain_sha


ROOT = Path(__file__).resolve().parents[1]


def test_binding_and_authorization_are_content_addressed() -> None:
    binding = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1.json"
        ).read_text(encoding="utf-8")
    )
    authorization = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_AUTHORIZATION_V1.json"
        ).read_text(encoding="utf-8")
    )
    require_domain_sha(
        binding,
        schema_id=binding["schema_id"],
        sha_field="smoke_binding_sha256",
    )
    require_domain_sha(
        authorization,
        schema_id=authorization["schema_id"],
        sha_field="authorization_sha256",
    )
    assert authorization["authorized_model_load_count"] == 1
    assert authorization["authorized_forward_count"] == 0
    assert authorization["authorized_backward_count"] == 0
    assert (
        authorization["authorized_optimizer_construction_count"]
        == 0
    )
    assert authorization["authorized_optimizer_step_count"] == 0
    assert authorization["authorized_training_execution_count"] == 0


def test_smoke_adapter_contains_no_training_surface() -> None:
    path = ROOT / "smoke/model_init_adapter.py"
    text = path.read_text(encoding="utf-8")
    forbidden = (
        "build_formal_optimizer(",
        "build_formal_scheduler(",
        "execute_training_plan(",
        ".backward(",
        ".step(",
        "run_formal_training(",
        "save_pretrained(",
    )
    for token in forbidden:
        assert token not in text

    tree = ast.parse(text)
    call_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                call_names.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                call_names.append(node.func.id)
    assert "build_seeded_formal_lora_model" in call_names


def test_smoke_result_root_is_attempt_scoped() -> None:
    binding = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1.json"
        ).read_text(encoding="utf-8")
    )
    assert binding["result_root"].startswith(
        binding["attempt_root"] + "/"
    )


def test_formal_training_authorization_is_not_created() -> None:
    for path in ROOT.rglob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_id") == (
            "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1"
        ):
            assert value.get("authorization_status") != "APPROVED"
