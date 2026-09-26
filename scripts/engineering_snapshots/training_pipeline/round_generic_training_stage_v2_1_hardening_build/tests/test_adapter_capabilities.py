from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from round_training.common import ContractError


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = (
    ROOT
    / "round_training/adapters/frozen_formal_train_peft.py"
)


def load_adapter():
    spec = importlib.util.spec_from_file_location(
        "capability_adapter",
        ADAPTER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "profiles/human_reference_t2/"
            "ROUND_LOCAL_TRAINING_CONTRACT_V1.json"
        ).read_text(encoding="utf-8")
    )


def test_runtime_adapter_accepts_exact_supported_recipe() -> None:
    adapter = load_adapter()
    adapter.validate_runtime_capabilities(current_contract())


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("optimization", "optimizer", "sgd"),
        ("optimization", "adam_beta1", 0.1),
        ("optimization", "adam_beta2", 0.2),
        ("optimization", "adam_epsilon", 0.1),
        ("optimization", "lr_scheduler", "cosine"),
        ("execution", "bf16", False),
        ("execution", "fp16", True),
        ("execution", "single_gpu_only", False),
        ("execution", "formal_cuda_required", False),
        ("peft", "method", "IA3"),
        ("dataset", "trained_region", "FULL_SEQUENCE"),
    ],
)
def test_runtime_adapter_rejects_unsupported_recipe_drift(
    section,
    key,
    value,
) -> None:
    adapter = load_adapter()
    contract = copy.deepcopy(current_contract())
    contract[section][key] = value
    with pytest.raises(
        ContractError,
        match="RUNTIME_ADAPTER_CAPABILITY_MISMATCH",
    ):
        adapter.validate_runtime_capabilities(contract)


def test_parent_adapter_config_must_match_profile_peft_contract() -> None:
    adapter = load_adapter()
    contract = current_contract()
    adapter_config = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "bias": "none",
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "base_model_name_or_path": (
            "/models/snapshots/"
            "aa8e72537993ba99e69dfaafa59ed015b17504d1"
        ),
    }
    adapter.validate_parent_adapter_config(
        contract,
        adapter_config,
    )

    changed = dict(adapter_config)
    changed["r"] = 8
    with pytest.raises(
        ContractError,
        match="PARENT_ADAPTER_CONFIG_MISMATCH",
    ):
        adapter.validate_parent_adapter_config(
            contract,
            changed,
        )
