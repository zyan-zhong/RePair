from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

THIS = Path(__file__).resolve()
GENERIC_ROOT = THIS.parents[1]
if str(GENERIC_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERIC_ROOT))

from round_training.common import ContractError
from round_training.contracts import validate_training_contract


def _v2_contract():
    return {
        "schema_id": "ROUND_LOCAL_TRAINING_CONTRACT_V2",
        "schema_version": 2,
        "round_id": "SYNTHETIC",
        "profile_id": "SYNTHETIC",
        "training_execution_authorized": False,
        "training_execution_count": 0,
        "dataset": {
            "row_count": 2,
            "sequence_lengths": [4, 5],
            "max_sequence_length": 5,
            "truncation": False,
            "retokenization": False,
            "reapply_chat_template": False,
            "one_pass_target_loss_token_count": 5,
            "row_adapter": {
                "identity_domain": "SOURCE_EXAMPLE_SHA256",
                "source_identity_sha_field": "source_example_sha256",
            },
        },
        "budget": {
            "epochs": 1,
            "micro_batch_size": 1,
            "gradient_accumulation_steps": 1,
            "effective_batch_size": 2,
            "partial_final_accumulation_group": False,
            "optimizer_steps": 1,
            "target_loss_token_budget": 5,
            "training_seed": 17,
            "data_seed": 17,
        },
        "execution": {
            "world_size": 2,
            "per_rank_micro_batch_size": 1,
            "distributed_backend": "nccl",
        },
        "optimization": {
            "resume_from_checkpoint": False,
            "fresh_optimizer": True,
            "fresh_scheduler": True,
            "warmup_steps": 0,
            "learning_rate": 1e-4,
            "weight_decay": 0.0,
            "max_grad_norm": 1.0,
            "adam_beta1": 0.9,
            "adam_beta2": 0.999,
            "adam_epsilon": 1e-8,
        },
        "peft": {
            "r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "target_modules": ["q_proj"],
        },
    }


def _v2_order():
    a = "a" * 64
    b = "b" * 64
    return {
        "schema_id": "ROUND_SAMPLE_ORDER_MANIFEST_V2",
        "schema_version": 2,
        "identity_domain": "SOURCE_EXAMPLE_SHA256",
        "row_count": 2,
        "dataset_passes": 1,
        "training_seed": 17,
        "data_seed": 17,
        "shuffle_during_training": False,
        "world_size": 2,
        "effective_batch_size": 2,
        "pass_orders": [[0, 1]],
        "optimizer_groups": [
            {
                "global_step": 1,
                "pass_index": 0,
                "step_in_pass": 1,
                "ordinals": [0, 1],
                "row_sha256s": [a, b],
                "source_identity_sha256s": [a, b],
                "target_loss_tokens": 5,
            }
        ],
        "ordered_row_sha256s": [a, b],
        "ordered_source_identity_sha256s": [a, b],
    }


def test_v2_distributed_batch_arithmetic_accepts_world_size():
    validate_training_contract(_v2_contract(), _v2_order())


def test_v2_rejects_fake_gradient_accumulation_world_size_alias():
    contract = _v2_contract()
    contract["budget"]["gradient_accumulation_steps"] = 2
    with pytest.raises(ContractError, match="DISTRIBUTED_EFFECTIVE_BATCH_MISMATCH"):
        validate_training_contract(contract, _v2_order())


def test_v2_rejects_policy_state_identity_alias():
    contract = _v2_contract()
    contract["dataset"]["row_adapter"]["identity_domain"] = "SOURCE_STATE_SHA256"
    with pytest.raises(ContractError, match="V2_IDENTITY_DOMAIN_UNSUPPORTED"):
        validate_training_contract(contract, _v2_order())


def test_v1_historical_profile_still_validates():
    profile_root = GENERIC_ROOT / "profiles/human_reference_t2"
    contract = json.loads(
        (profile_root / "ROUND_LOCAL_TRAINING_CONTRACT_V1.json").read_text(
            encoding="utf-8"
        )
    )
    order = json.loads(
        (profile_root / "ROUND_SAMPLE_ORDER_MANIFEST_V1.json").read_text(
            encoding="utf-8"
        )
    )
    validate_training_contract(contract, order)


def test_runtime_adapter_load_order_is_peft_before_process_group():
    adapter = (
        GENERIC_ROOT
        / "round_training/adapters/local_analyzer_ddp_runtime.py"
    )
    text = adapter.read_text(encoding="utf-8")
    peft_load = text.index("model = PeftModel.from_pretrained(")
    pg_init = text.index("dist.init_process_group(")
    ddp_wrap = text.index("ddp = DDP(")
    assert peft_load < pg_init < ddp_wrap
    assert 'gradient_checkpointing_kwargs={"use_reentrant": False}' in text
    assert "source_example_sha256" in text
    assert "source_state_sha256" not in text
