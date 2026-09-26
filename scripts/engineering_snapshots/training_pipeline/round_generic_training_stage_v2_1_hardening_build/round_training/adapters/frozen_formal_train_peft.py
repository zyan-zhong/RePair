from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from round_training.common import (
    ContractError,
    load_json_object,
    require_sha,
    sha256_file,
)
from round_training.contracts import StageContext
from round_training.receipts import artifact_ref_for_output


SUPPORTED_OPTIMIZATION = {
    "optimizer": "adamw_torch",
    "adam_beta1": 0.9,
    "adam_beta2": 0.999,
    "adam_epsilon": 1e-8,
    "lr_scheduler": "linear",
}

SUPPORTED_EXECUTION = {
    "single_gpu_only": True,
    "formal_cuda_required": True,
    "bf16": True,
    "fp16": False,
    "gradient_checkpointing": False,
    "torch_compile": False,
    "dataloader_num_workers": 0,
}

SUPPORTED_DATASET = {
    "trained_region": "ASSISTANT_COMPLETION_SUFFIX_ONLY",
    "prompt_label_value": -100,
    "packing": False,
    "truncation": False,
    "retokenization": False,
    "reapply_chat_template": False,
}

SUPPORTED_PEFT = {
    "method": "LORA",
    "bias": "none",
    "base_weights_trainable": False,
    "autocast_adapter_dtype": True,
}


def validate_runtime_capabilities(
    contract: dict[str, Any],
) -> None:
    sections = (
        ("optimization", SUPPORTED_OPTIMIZATION),
        ("execution", SUPPORTED_EXECUTION),
        ("dataset", SUPPORTED_DATASET),
        ("peft", SUPPORTED_PEFT),
    )
    mismatches = []
    for section_name, supported in sections:
        section = contract.get(section_name)
        if not isinstance(section, dict):
            raise ContractError(
                f"RUNTIME_ADAPTER_SECTION_MISSING:{section_name}"
            )
        for key, expected in supported.items():
            observed = section.get(key)
            if observed != expected:
                mismatches.append(
                    (section_name, key, observed, expected)
                )
    if mismatches:
        raise ContractError(
            "RUNTIME_ADAPTER_CAPABILITY_MISMATCH:"
            + repr(mismatches)
        )


def validate_parent_adapter_config(
    contract: dict[str, Any],
    adapter_config: dict[str, Any],
) -> None:
    peft = contract["peft"]
    expected = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": peft["r"],
        "lora_alpha": peft["lora_alpha"],
        "lora_dropout": peft["lora_dropout"],
        "bias": peft["bias"],
    }
    observed = {
        key: adapter_config.get(key)
        for key in expected
    }
    mismatches = [
        (key, observed[key], expected[key])
        for key in expected
        if observed[key] != expected[key]
    ]

    observed_modules = adapter_config.get("target_modules")
    if not isinstance(observed_modules, list):
        mismatches.append(
            ("target_modules", observed_modules, peft["target_modules"])
        )
    elif set(observed_modules) != set(peft["target_modules"]):
        mismatches.append(
            ("target_modules", observed_modules, peft["target_modules"])
        )

    base_path = adapter_config.get("base_model_name_or_path")
    revision = contract["parent"]["base_model_revision"]
    if not isinstance(base_path, str) or not base_path.rstrip("/").endswith(
        revision
    ):
        mismatches.append(
            ("base_model_name_or_path", base_path, revision)
        )

    if mismatches:
        raise ContractError(
            "PARENT_ADAPTER_CONFIG_MISMATCH:"
            + repr(mismatches)
        )


def _input_artifact_ref(
    *,
    logical_name: str,
    retention_class: str,
    path: Path,
    expected_sha256: str,
    schema_id: str | None,
) -> dict[str, Any]:
    require_sha(path, expected_sha256, logical_name)
    return {
        "logical_name": logical_name,
        "retention_class": retention_class,
        "path": str(path.resolve()),
        "sha256": expected_sha256,
        "size_bytes": path.stat().st_size,
        "schema_id": schema_id,
    }


def _load_parent_module(contract: dict[str, Any]):
    parent_contract = contract["parent"]
    source = Path(parent_contract["formal_train_path"])
    require_sha(
        source,
        parent_contract["formal_train_sha256"],
        "PARENT_FORMAL_TRAIN",
    )
    source_root = str(source.parent)
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    spec = importlib.util.spec_from_file_location(
        "round_frozen_parent_formal_train",
        source,
    )
    if spec is None or spec.loader is None:
        raise ContractError("PARENT_FORMAL_TRAIN_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_parent_adapter_files(
    contract: dict[str, Any],
) -> dict[str, Any]:
    parent_contract = contract["parent"]
    manifest_path = Path(
        parent_contract["adapter_artifact_manifest_path"]
    )
    require_sha(
        manifest_path,
        parent_contract["adapter_artifact_manifest_sha256"],
        "PARENT_ADAPTER_ARTIFACT_MANIFEST",
    )
    manifest = load_json_object(manifest_path)
    if (
        manifest.get("adapter_bundle_sha256")
        != parent_contract["adapter_bundle_sha256"]
    ):
        raise ContractError("PARENT_ADAPTER_BUNDLE_SHA_MISMATCH")

    adapter_root = Path(parent_contract["adapter_path"])
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ContractError("PARENT_ADAPTER_FILE_MAP_MISSING")

    for relative, specification in files.items():
        if not isinstance(specification, dict):
            raise ContractError("PARENT_ADAPTER_FILE_SPEC_INVALID")
        path = adapter_root / relative
        if not path.is_file() or path.is_symlink():
            raise ContractError(f"PARENT_ADAPTER_FILE_INVALID:{path}")
        if path.stat().st_size != specification.get("size_bytes"):
            raise ContractError(
                f"PARENT_ADAPTER_FILE_SIZE_MISMATCH:{relative}"
            )
        require_sha(
            path,
            specification.get("sha256"),
            "PARENT_ADAPTER_FILE_" + relative.replace("/", "_"),
        )

    adapter_config = load_json_object(
        adapter_root / "adapter_config.json"
    )
    validate_parent_adapter_config(
        contract,
        adapter_config,
    )
    return manifest


def _load_records(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    dataset = contract["dataset"]
    path = Path(dataset["path"])
    manifest_path = Path(dataset["manifest_path"])

    require_sha(path, dataset["sha256"], "ROUND_TRAINING_DATASET")
    require_sha(
        manifest_path,
        dataset["manifest_file_sha256"],
        "ROUND_TRAINING_DATASET_MANIFEST",
    )
    manifest = load_json_object(manifest_path)
    if (
        manifest.get(dataset["manifest_domain_sha_field"])
        != dataset["manifest_domain_sha256"]
    ):
        raise ContractError("DATASET_MANIFEST_DOMAIN_SHA_MISMATCH")

    expected_manifest_flags = dataset.get(
        "required_manifest_flags",
        {},
    )
    for key, expected in expected_manifest_flags.items():
        if manifest.get(key) != expected:
            raise ContractError(
                f"DATASET_MANIFEST_FLAG_MISMATCH:{key}:"
                f"{manifest.get(key)}:{expected}"
            )

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != dataset["row_count"]:
        raise ContractError("ROUND_TRAINING_ROW_COUNT_CHANGED")

    expected_lengths = dataset["sequence_lengths"]
    adapter = dataset["row_adapter"]
    records = []
    states = set()
    total_targets = 0

    for ordinal, row in enumerate(rows):
        if row.get("schema_id") != adapter["schema_id"]:
            raise ContractError(
                f"ROUND_TRAINING_ROW_SCHEMA_CHANGED:{ordinal}"
            )
        if row.get(adapter["ordinal_field"]) != ordinal:
            raise ContractError(
                f"ROUND_TRAINING_ROW_ORDINAL_CHANGED:{ordinal}"
            )

        for key, expected in adapter.get(
            "required_top_level_flags",
            {},
        ).items():
            if row.get(key) != expected:
                raise ContractError(
                    f"ROUND_TRAINING_ROW_FLAG_MISMATCH:{ordinal}:{key}"
                )

        tokenization = row.get(adapter["tokenization_field"])
        if not isinstance(tokenization, dict):
            raise ContractError(
                f"ROUND_TRAINING_TOKENIZATION_MISSING:{ordinal}"
            )
        input_ids = tokenization.get(adapter["input_ids_field"])
        labels = tokenization.get(adapter["labels_field"])
        if not isinstance(input_ids, list) or not isinstance(labels, list):
            raise ContractError(
                f"ROUND_TRAINING_TOKEN_ARRAYS_INVALID:{ordinal}"
            )
        if len(input_ids) != expected_lengths[ordinal]:
            raise ContractError(
                f"ROUND_TRAINING_SEQUENCE_LENGTH_CHANGED:{ordinal}:"
                f"{len(input_ids)}:{expected_lengths[ordinal]}"
            )
        if len(input_ids) != len(labels):
            raise ContractError(
                f"ROUND_TRAINING_INPUT_LABEL_LENGTH_MISMATCH:{ordinal}"
            )

        prompt_label_value = dataset["prompt_label_value"]
        target_count = sum(
            value != prompt_label_value
            for value in labels[1:]
        )
        expected_target_count = tokenization.get(
            adapter["completion_loss_token_count_field"]
        )
        if target_count != expected_target_count:
            raise ContractError(
                f"ROUND_TRAINING_TARGET_COUNT_CHANGED:{ordinal}"
            )
        total_targets += target_count

        identity = row.get(adapter["source_identity_field"])
        if not isinstance(identity, dict):
            raise ContractError(
                f"ROUND_TRAINING_SOURCE_IDENTITY_MISSING:{ordinal}"
            )
        state = identity.get(adapter["source_state_field"])
        if not isinstance(state, str) or len(state) != 64:
            raise ContractError(
                f"ROUND_TRAINING_SOURCE_STATE_INVALID:{ordinal}"
            )
        if state in states:
            raise ContractError(
                f"ROUND_TRAINING_SOURCE_STATE_DUPLICATE:{state}"
            )
        states.add(state)

        row_sha = row.get(adapter["row_sha_field"])
        if not isinstance(row_sha, str) or len(row_sha) != 64:
            raise ContractError(
                f"ROUND_TRAINING_ROW_SHA_INVALID:{ordinal}"
            )

        records.append(
            {
                "case_id": row_sha,
                "ordinal": ordinal,
                "source_state_sha256": state,
                "tokenization": tokenization,
                "trainer_native_row_sha256": row_sha,
            }
        )

    if total_targets != dataset["one_pass_target_loss_token_count"]:
        raise ContractError(
            f"ROUND_TRAINING_TARGET_TOKEN_TOTAL_CHANGED:{total_targets}"
        )
    return tuple(records)


def _verify_order(
    parent,
    *,
    records: tuple[dict[str, Any], ...],
    contract: dict[str, Any],
    sample_order: dict[str, Any],
) -> None:
    budget = contract["budget"]
    generated = parent.build_training_orders(
        example_count=contract["dataset"]["row_count"],
        seed=budget["data_seed"],
        passes=budget["epochs"],
    )
    expected = tuple(
        tuple(order)
        for order in sample_order["pass_orders"]
    )
    if generated != expected:
        raise ContractError(
            f"ROUND_TRAINING_SAMPLE_ORDER_CHANGED:{generated}:{expected}"
        )

    flat_expected_rows = []
    flat_expected_states = []
    for order in expected:
        flat_expected_rows.extend(
            records[index]["case_id"]
            for index in order
        )
        flat_expected_states.extend(
            records[index]["source_state_sha256"]
            for index in order
        )
    if flat_expected_rows != sample_order["ordered_row_sha256s"]:
        raise ContractError("ROUND_TRAINING_ORDER_ROW_SHA_MISMATCH")
    if flat_expected_states != sample_order["ordered_source_state_sha256s"]:
        raise ContractError("ROUND_TRAINING_ORDER_STATE_SHA_MISMATCH")

    effective_batch = budget["effective_batch_size"]
    groups = sample_order["optimizer_groups"]
    group_index = 0
    for pass_index, order in enumerate(expected):
        for step_in_pass, start in enumerate(
            range(0, len(order), effective_batch),
            start=1,
        ):
            group = groups[group_index]
            ordinals = list(order[start : start + effective_batch])
            expected_rows = [
                records[index]["case_id"]
                for index in ordinals
            ]
            expected_states = [
                records[index]["source_state_sha256"]
                for index in ordinals
            ]
            expected_tokens = sum(
                records[index]["tokenization"][
                    "completion_loss_token_count"
                ]
                for index in ordinals
            )
            if group["pass_index"] != pass_index:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_PASS_INDEX_CHANGED"
                )
            if group["step_in_pass"] != step_in_pass:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_STEP_IN_PASS_CHANGED"
                )
            if group["ordinals"] != ordinals:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_ORDINALS_CHANGED"
                )
            if group["row_sha256s"] != expected_rows:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_ROW_SHA_CHANGED"
                )
            if group["source_state_sha256s"] != expected_states:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_STATE_SHA_CHANGED"
                )
            if group["target_loss_tokens"] != expected_tokens:
                raise ContractError(
                    "ROUND_TRAINING_GROUP_TARGET_TOKENS_CHANGED"
                )
            group_index += 1


def input_artifact_refs(
    context: StageContext,
) -> list[dict[str, Any]]:
    contract = context.training_contract
    validate_runtime_capabilities(contract)
    _verify_parent_adapter_files(contract)
    _load_records(contract)

    parent = contract["parent"]
    dataset = contract["dataset"]
    adapter_root = Path(parent["adapter_path"])
    adapter_manifest = load_json_object(
        Path(parent["adapter_artifact_manifest_path"])
    )
    adapter_files = adapter_manifest["files"]

    refs = [
        _input_artifact_ref(
            logical_name="PARENT_FORMAL_TRAIN_SOURCE",
            retention_class="EXECUTION_SOURCE",
            path=Path(parent["formal_train_path"]),
            expected_sha256=parent["formal_train_sha256"],
            schema_id=None,
        ),
        _input_artifact_ref(
            logical_name="PARENT_TRAINING_CONFIG",
            retention_class="SCIENTIFIC_CONFIG",
            path=Path(parent["training_config_path"]),
            expected_sha256=parent["training_config_sha256"],
            schema_id="P4_R1_Q2_BAD_TRAINING_CONFIG_V1",
        ),
        _input_artifact_ref(
            logical_name="PARENT_ADAPTER_ARTIFACT_MANIFEST",
            retention_class="MODEL_ARTIFACT_MANIFEST",
            path=Path(parent["adapter_artifact_manifest_path"]),
            expected_sha256=parent[
                "adapter_artifact_manifest_sha256"
            ],
            schema_id="P4_R1_Q2_BAD_ADAPTER_ARTIFACT_MANIFEST_V1",
        ),
        _input_artifact_ref(
            logical_name="PARENT_ADAPTER_CONFIG",
            retention_class="MODEL_ARTIFACT",
            path=adapter_root / "adapter_config.json",
            expected_sha256=adapter_files[
                "adapter_config.json"
            ]["sha256"],
            schema_id=None,
        ),
        _input_artifact_ref(
            logical_name="PARENT_ADAPTER_MODEL",
            retention_class="MODEL_ARTIFACT",
            path=adapter_root / "adapter_model.safetensors",
            expected_sha256=adapter_files[
                "adapter_model.safetensors"
            ]["sha256"],
            schema_id=None,
        ),
        _input_artifact_ref(
            logical_name="BASE_MODEL_ARTIFACT_MANIFEST",
            retention_class="MODEL_ARTIFACT_MANIFEST",
            path=Path(parent["base_model_artifact_manifest_path"]),
            expected_sha256=parent[
                "base_model_artifact_manifest_sha256"
            ],
            schema_id=None,
        ),
        _input_artifact_ref(
            logical_name="TRAINER_NATIVE_DATASET",
            retention_class="TRAINING_DATASET",
            path=Path(dataset["path"]),
            expected_sha256=dataset["sha256"],
            schema_id=dataset["row_adapter"]["schema_id"],
        ),
        _input_artifact_ref(
            logical_name="TRAINER_NATIVE_DATASET_MANIFEST",
            retention_class="TRAINING_DATASET_MANIFEST",
            path=Path(dataset["manifest_path"]),
            expected_sha256=dataset["manifest_file_sha256"],
            schema_id="POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1",
        ),
    ]
    return refs


def _build_model(
    parent,
    *,
    contract: dict[str, Any],
    seed: int,
    device,
):
    from peft import PeftModel

    parent.seed_formal_training(seed)
    base_model = parent.load_exact_base_model(device=device)
    parent.seed_formal_training(seed)

    model = PeftModel.from_pretrained(
        base_model,
        contract["parent"]["adapter_path"],
        is_trainable=True,
        autocast_adapter_dtype=contract["peft"][
            "autocast_adapter_dtype"
        ],
    )
    model.train()

    parent.verify_lora_only_trainable_parameters(model)
    actual_modules = parent.actual_lora_target_module_suffixes(model)
    expected_modules = set(contract["peft"]["target_modules"])
    if actual_modules != expected_modules:
        raise ContractError(
            "ROUND_TRAINING_LORA_TARGET_MODULES_CHANGED:"
            + repr(sorted(actual_modules))
            + ":"
            + repr(sorted(expected_modules))
        )

    initial_sha = parent.hash_trainable_parameters(model)
    expected_initial = contract["parent"][
        "final_trainable_parameter_sha256"
    ]
    if initial_sha != expected_initial:
        raise ContractError(
            f"ROUND_TRAINING_INITIAL_PARAMETER_SHA_MISMATCH:"
            f"{initial_sha}:{expected_initial}"
        )
    return model


def _install_parent_adapter(
    parent,
    *,
    context: StageContext,
):
    contract = context.training_contract
    sample_order = context.sample_order
    dataset = contract["dataset"]
    budget = contract["budget"]
    optimization = contract["optimization"]
    peft = contract["peft"]

    validate_runtime_capabilities(contract)
    _verify_parent_adapter_files(contract)

    parent.FORMAL_TRAINING_SEEDS = (
        budget["training_seed"],
    )
    parent.FORMAL_EXAMPLE_COUNT = dataset["row_count"]
    parent.FORMAL_DATASET_PASSES = budget["epochs"]
    parent.FORMAL_MICRO_BATCH = budget["micro_batch_size"]
    parent.FORMAL_GRAD_ACCUM = budget[
        "gradient_accumulation_steps"
    ]
    parent.FORMAL_EFFECTIVE_BATCH = budget["effective_batch_size"]
    parent.FORMAL_STEPS_PER_PASS = (
        budget["optimizer_steps"] // budget["epochs"]
    )
    parent.FORMAL_OPTIMIZER_STEPS = budget["optimizer_steps"]
    parent.FORMAL_TARGET_LOSS_TOKENS_PER_PASS = dataset[
        "one_pass_target_loss_token_count"
    ]
    parent.FORMAL_TARGET_LOSS_TOKEN_BUDGET = budget[
        "target_loss_token_budget"
    ]
    parent.FORMAL_WARMUP_STEPS = optimization["warmup_steps"]
    parent.FORMAL_MAX_SEQUENCE_LENGTH = dataset[
        "max_sequence_length"
    ]
    parent.FORMAL_LEARNING_RATE = optimization["learning_rate"]
    parent.FORMAL_WEIGHT_DECAY = optimization["weight_decay"]
    parent.FORMAL_MAX_GRAD_NORM = optimization["max_grad_norm"]
    parent.FORMAL_LORA_R = peft["r"]
    parent.FORMAL_LORA_ALPHA = peft["lora_alpha"]
    parent.FORMAL_LORA_DROPOUT = peft["lora_dropout"]
    parent.FORMAL_LORA_TARGET_MODULES = tuple(
        peft["target_modules"]
    )
    parent._ORDER_DOMAIN = sample_order["ordering_domain"]
    parent.FORMAL_EXECUTION_APPROVAL_TOKEN = contract[
        "parent_compatibility_approval_token"
    ]

    records = _load_records(contract)
    _verify_parent_adapter_files(contract)
    _verify_order(
        parent,
        records=records,
        contract=contract,
        sample_order=sample_order,
    )

    parent.verify_frozen_scientific_config = lambda: None
    parent.verify_frozen_materialization = lambda: None
    parent.load_frozen_materialized_records = lambda: records
    parent.build_seeded_formal_lora_model = (
        lambda *, seed, device: _build_model(
            parent,
            contract=contract,
            seed=seed,
            device=device,
        )
    )

    parent_manifest_builder = parent.build_adapter_artifact_manifest

    def build_adapter_manifest(adapter_dir):
        value = dict(parent_manifest_builder(adapter_dir))
        value["schema_id"] = contract[
            "output_contracts"
        ]["adapter_artifact_manifest_schema_id"]
        value["round_id"] = contract["round_id"]
        value["profile_id"] = contract["profile_id"]
        value["parent_adapter_bundle_sha256"] = contract[
            "parent"
        ]["adapter_bundle_sha256"]
        value["diagnostic_only"] = contract["diagnostic_only"]
        value["promotion_eligible"] = contract["promotion_eligible"]
        return value

    def build_run_manifest(
        *,
        seed: int,
        ledger_summary,
        initial_trainable_sha256: str,
        final_trainable_sha256: str,
        adapter_manifest,
        runner_freeze_root_sha256: str,
        infrastructure_node_exclusions=(),
    ):
        if initial_trainable_sha256 != contract["parent"][
            "final_trainable_parameter_sha256"
        ]:
            raise ContractError(
                "RUN_MANIFEST_PARENT_INITIAL_SHA_MISMATCH"
            )
        if final_trainable_sha256 == initial_trainable_sha256:
            raise ContractError("TRAINABLE_STATE_UNCHANGED")
        if ledger_summary["optimizer_step_count"] != budget[
            "optimizer_steps"
        ]:
            raise ContractError(
                "RUN_MANIFEST_OPTIMIZER_STEP_MISMATCH"
            )
        if ledger_summary["dataset_pass_count"] != budget["epochs"]:
            raise ContractError("RUN_MANIFEST_DATASET_PASS_MISMATCH")
        if ledger_summary["target_loss_token_count"] != budget[
            "target_loss_token_budget"
        ]:
            raise ContractError("RUN_MANIFEST_TARGET_TOKEN_MISMATCH")

        return {
            "schema_id": contract["output_contracts"][
                "formal_run_manifest_schema_id"
            ],
            "schema_version": 1,
            "round_id": contract["round_id"],
            "profile_id": contract["profile_id"],
            "condition_id": contract["condition_id"],
            "run_status": "FORMAL_TRAINING_COMPLETED",
            "diagnostic_only": contract["diagnostic_only"],
            "promotion_eligible": contract["promotion_eligible"],
            "formal_training_seed": seed,
            "data_seed": budget["data_seed"],
            "parent_policy_id": contract["parent"]["policy_id"],
            "parent_adapter_bundle_sha256": contract["parent"][
                "adapter_bundle_sha256"
            ],
            "parent_final_trainable_parameter_sha256": contract[
                "parent"
            ]["final_trainable_parameter_sha256"],
            "training_contract_file_sha256": context.binding[
                "training_contract_ref"
            ]["sha256"],
            "sample_order_manifest_file_sha256": context.binding[
                "sample_order_ref"
            ]["sha256"],
            "stage_binding_sha256": context.binding[
                "stage_binding_sha256"
            ],
            "trainer_native_dataset_sha256": dataset["sha256"],
            "trainer_native_dataset_manifest_domain_sha256": dataset[
                "manifest_domain_sha256"
            ],
            "research_planner_training_plan_domain_sha256": dataset[
                "research_planner_training_plan_domain_sha256"
            ],
            "runner_freeze_root_sha256": runner_freeze_root_sha256,
            "initial_trainable_parameter_sha256": (
                initial_trainable_sha256
            ),
            "final_trainable_parameter_sha256": (
                final_trainable_sha256
            ),
            "adapter_bundle_sha256": adapter_manifest[
                "adapter_bundle_sha256"
            ],
            "optimizer_step_count": ledger_summary[
                "optimizer_step_count"
            ],
            "dataset_pass_count": ledger_summary[
                "dataset_pass_count"
            ],
            "target_loss_token_count": ledger_summary[
                "target_loss_token_count"
            ],
            "all_losses_finite": ledger_summary["all_losses_finite"],
            "all_grad_norms_finite": ledger_summary[
                "all_grad_norms_finite"
            ],
            "optimizer": optimization,
            "checkpoint_rule": contract["execution"][
                "checkpoint_rule"
            ],
            "intermediate_scientific_checkpoint_used": False,
            "early_stopping_used": False,
            "within_training_evaluation_used": False,
            "resume_from_checkpoint_used": False,
            "infrastructure_node_exclusions": list(
                infrastructure_node_exclusions
            ),
        }

    parent.build_adapter_artifact_manifest = build_adapter_manifest
    parent.build_formal_run_manifest = build_run_manifest


def validate_profile_without_model_load(
    context: StageContext,
) -> dict[str, Any]:
    validate_runtime_capabilities(context.training_contract)
    parent = _load_parent_module(context.training_contract)
    _install_parent_adapter(parent, context=context)
    records = _load_records(context.training_contract)
    plan = parent.build_formal_run_plan(
        seed=context.training_contract["budget"]["training_seed"]
    )
    direct_refs = input_artifact_refs(context)
    return {
        "record_count": len(records),
        "optimizer_step_count": len(plan),
        "optimizer_group_target_loss_tokens": [
            row["target_loss_tokens"]
            for row in plan
        ],
        "direct_input_artifact_count": len(direct_refs),
        "parent_adapter_bundle_sha256": context.training_contract[
            "parent"
        ]["adapter_bundle_sha256"],
    }


def execute_training_stage(
    *,
    context: StageContext,
    output_dir: Path,
    runner_freeze_root_sha256: str,
) -> dict[str, Any]:
    contract = context.training_contract
    parent = _load_parent_module(contract)
    _install_parent_adapter(parent, context=context)

    manifest = parent.run_formal_training(
        seed=contract["budget"]["training_seed"],
        output_dir=output_dir,
        approval_token=contract[
            "parent_compatibility_approval_token"
        ],
        runner_freeze_root_sha256=runner_freeze_root_sha256,
        infrastructure_node_exclusions=tuple(
            contract["execution"].get(
                "infrastructure_node_exclusions",
                [],
            )
        ),
    )

    artifacts = []
    output_contracts = contract["output_contracts"]
    for logical_name, relative_path, retention_class, schema_id in (
        (
            "TRAINING_STEP_LEDGER",
            output_contracts["training_step_ledger_relative_path"],
            "RAW_EVIDENCE",
            output_contracts["training_step_ledger_schema_id"],
        ),
        (
            "FORMAL_RUN_MANIFEST",
            output_contracts["formal_run_manifest_relative_path"],
            "VALIDATED_SCIENTIFIC_ARTIFACT",
            output_contracts["formal_run_manifest_schema_id"],
        ),
        (
            "ADAPTER_ARTIFACT_MANIFEST",
            output_contracts[
                "adapter_artifact_manifest_relative_path"
            ],
            "VALIDATED_SCIENTIFIC_ARTIFACT",
            output_contracts[
                "adapter_artifact_manifest_schema_id"
            ],
        ),
    ):
        artifacts.append(
            artifact_ref_for_output(
                logical_name=logical_name,
                retention_class=retention_class,
                path=output_dir / relative_path,
                schema_id=schema_id,
            )
        )

    return {
        "artifacts": artifacts,
        "run_manifest": manifest,
    }
