from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import (
    ContractError,
    load_json_object,
    require_domain_sha,
    require_sha,
    resolve_package_path,
)


@dataclass(frozen=True)
class StageContext:
    package_root: Path
    binding_path: Path
    binding: dict[str, Any]
    role_binding: dict[str, Any]
    training_contract: dict[str, Any]
    sample_order: dict[str, Any]
    runtime_adapter_path: Path


def _load_file_ref(
    package_root: Path,
    value: Any,
    label: str,
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(value, dict):
        raise ContractError(f"{label}_REF_INVALID")
    path_value = value.get("path")
    expected_sha = value.get("sha256")
    if not isinstance(path_value, str):
        raise ContractError(f"{label}_PATH_INVALID")
    path = resolve_package_path(package_root, path_value)
    require_sha(path, expected_sha, label)
    return path, load_json_object(path)


def _validate_training_contract_v1(
    contract: dict[str, Any],
    sample_order: dict[str, Any],
) -> None:
    if contract.get("schema_id") != "ROUND_LOCAL_TRAINING_CONTRACT_V1":
        raise ContractError("ROUND_LOCAL_TRAINING_CONTRACT_SCHEMA_CHANGED")
    if contract.get("training_execution_authorized") is not False:
        raise ContractError("BUILD_CONTRACT_MUST_NOT_AUTHORIZE_TRAINING")
    if contract.get("training_execution_count") != 0:
        raise ContractError("BUILD_CONTRACT_TRAINING_COUNT_NOT_ZERO")

    dataset = contract.get("dataset")
    budget = contract.get("budget")
    optimization = contract.get("optimization")
    execution = contract.get("execution")

    if not all(
        isinstance(value, dict)
        for value in (dataset, budget, optimization, execution)
    ):
        raise ContractError("ROUND_LOCAL_TRAINING_CONTRACT_SECTION_MISSING")

    row_count = dataset.get("row_count")
    lengths = dataset.get("sequence_lengths")
    if type(row_count) is not int or row_count <= 0:
        raise ContractError("ROW_COUNT_INVALID")
    if (
        not isinstance(lengths, list)
        or len(lengths) != row_count
        or any(type(value) is not int or value <= 0 for value in lengths)
    ):
        raise ContractError("SEQUENCE_LENGTH_VECTOR_INVALID")
    if dataset.get("max_sequence_length") != max(lengths):
        raise ContractError("MAX_SEQUENCE_LENGTH_NOT_EXACT_CURRENT_MAX")
    if dataset.get("truncation") is not False:
        raise ContractError("TRUNCATION_FORBIDDEN")
    if dataset.get("retokenization") is not False:
        raise ContractError("RETOKENIZATION_FORBIDDEN")
    if dataset.get("reapply_chat_template") is not False:
        raise ContractError("CHAT_TEMPLATE_REAPPLICATION_FORBIDDEN")

    epochs = budget.get("epochs")
    micro_batch = budget.get("micro_batch_size")
    grad_accum = budget.get("gradient_accumulation_steps")
    effective_batch = budget.get("effective_batch_size")
    partial = budget.get("partial_final_accumulation_group")
    optimizer_steps = budget.get("optimizer_steps")
    one_pass_tokens = dataset.get("one_pass_target_loss_token_count")
    total_tokens = budget.get("target_loss_token_budget")

    if type(epochs) is not int or epochs <= 0:
        raise ContractError("EPOCH_COUNT_INVALID")
    if type(micro_batch) is not int or micro_batch <= 0:
        raise ContractError("MICRO_BATCH_INVALID")
    if type(grad_accum) is not int or grad_accum <= 0:
        raise ContractError("GRADIENT_ACCUMULATION_INVALID")
    if effective_batch != micro_batch * grad_accum:
        raise ContractError("EFFECTIVE_BATCH_MISMATCH")
    if partial is not False:
        raise ContractError("PARTIAL_FINAL_ACCUMULATION_GROUP_FORBIDDEN")
    if row_count % effective_batch != 0:
        raise ContractError("ROW_COUNT_NOT_DIVISIBLE_BY_EFFECTIVE_BATCH")

    expected_steps = (row_count // effective_batch) * epochs
    if optimizer_steps != expected_steps:
        raise ContractError(
            f"OPTIMIZER_STEP_DERIVATION_MISMATCH:{optimizer_steps}:"
            f"{expected_steps}"
        )
    if type(one_pass_tokens) is not int or one_pass_tokens <= 0:
        raise ContractError("ONE_PASS_TARGET_TOKEN_COUNT_INVALID")
    if total_tokens != one_pass_tokens * epochs:
        raise ContractError("TARGET_TOKEN_BUDGET_DERIVATION_MISMATCH")

    if optimization.get("resume_from_checkpoint") is not False:
        raise ContractError("RESUME_FROM_CHECKPOINT_FORBIDDEN")
    if optimization.get("fresh_optimizer") is not True:
        raise ContractError("FRESH_OPTIMIZER_REQUIRED")
    if optimization.get("fresh_scheduler") is not True:
        raise ContractError("FRESH_SCHEDULER_REQUIRED")
    if type(optimization.get("warmup_steps")) is not int:
        raise ContractError("WARMUP_STEPS_INVALID")
    if optimization["warmup_steps"] < 0:
        raise ContractError("WARMUP_STEPS_NEGATIVE")
    if optimization["warmup_steps"] > optimizer_steps:
        raise ContractError("WARMUP_EXCEEDS_TOTAL_STEPS")

    def is_number(value) -> bool:
        return type(value) in (int, float)

    learning_rate = optimization.get("learning_rate")
    weight_decay = optimization.get("weight_decay")
    max_grad_norm = optimization.get("max_grad_norm")
    beta1 = optimization.get("adam_beta1")
    beta2 = optimization.get("adam_beta2")
    epsilon = optimization.get("adam_epsilon")

    if not is_number(learning_rate) or learning_rate <= 0:
        raise ContractError("LEARNING_RATE_INVALID")
    if not is_number(weight_decay) or weight_decay < 0:
        raise ContractError("WEIGHT_DECAY_INVALID")
    if not is_number(max_grad_norm) or max_grad_norm <= 0:
        raise ContractError("MAX_GRAD_NORM_INVALID")
    if not is_number(beta1) or not 0 <= beta1 < 1:
        raise ContractError("ADAM_BETA1_INVALID")
    if not is_number(beta2) or not 0 <= beta2 < 1:
        raise ContractError("ADAM_BETA2_INVALID")
    if not is_number(epsilon) or epsilon <= 0:
        raise ContractError("ADAM_EPSILON_INVALID")

    peft = contract.get("peft")
    if peft is not None:
        if not isinstance(peft, dict):
            raise ContractError("PEFT_SECTION_INVALID")
        rank = peft.get("r")
        alpha = peft.get("lora_alpha")
        dropout = peft.get("lora_dropout")
        modules = peft.get("target_modules")
        if type(rank) is not int or rank <= 0:
            raise ContractError("LORA_R_INVALID")
        if type(alpha) is not int or alpha <= 0:
            raise ContractError("LORA_ALPHA_INVALID")
        if not is_number(dropout) or not 0 <= dropout < 1:
            raise ContractError("LORA_DROPOUT_INVALID")
        if (
            not isinstance(modules, list)
            or not modules
            or any(not isinstance(value, str) or not value for value in modules)
            or len(modules) != len(set(modules))
        ):
            raise ContractError("LORA_TARGET_MODULES_INVALID")

    if sample_order.get("schema_id") != "ROUND_SAMPLE_ORDER_MANIFEST_V1":
        raise ContractError("ROUND_SAMPLE_ORDER_SCHEMA_CHANGED")
    if sample_order.get("row_count") != row_count:
        raise ContractError("SAMPLE_ORDER_ROW_COUNT_MISMATCH")
    if sample_order.get("dataset_passes") != epochs:
        raise ContractError("SAMPLE_ORDER_PASS_COUNT_MISMATCH")
    if sample_order.get("training_seed") != budget.get("training_seed"):
        raise ContractError("SAMPLE_ORDER_TRAINING_SEED_MISMATCH")
    if sample_order.get("data_seed") != budget.get("data_seed"):
        raise ContractError("SAMPLE_ORDER_DATA_SEED_MISMATCH")
    if sample_order.get("shuffle_during_training") is not False:
        raise ContractError("RUNTIME_SHUFFLE_FORBIDDEN")

    pass_orders = sample_order.get("pass_orders")
    if not isinstance(pass_orders, list) or len(pass_orders) != epochs:
        raise ContractError("PASS_ORDER_COUNT_MISMATCH")

    expected_ordinals = list(range(row_count))
    for pass_index, order in enumerate(pass_orders):
        if not isinstance(order, list) or sorted(order) != expected_ordinals:
            raise ContractError(
                f"PASS_ORDER_NOT_PERMUTATION:{pass_index}"
            )

    groups = sample_order.get("optimizer_groups")
    if not isinstance(groups, list) or len(groups) != optimizer_steps:
        raise ContractError("OPTIMIZER_GROUP_COUNT_MISMATCH")

    ordered_row_sha256s = sample_order.get("ordered_row_sha256s")
    ordered_source_state_sha256s = sample_order.get(
        "ordered_source_state_sha256s"
    )
    expected_flat_count = row_count * epochs
    if (
        not isinstance(ordered_row_sha256s, list)
        or len(ordered_row_sha256s) != expected_flat_count
        or any(
            not isinstance(value, str) or len(value) != 64
            for value in ordered_row_sha256s
        )
    ):
        raise ContractError("ORDERED_ROW_SHA_VECTOR_INVALID")
    if (
        not isinstance(ordered_source_state_sha256s, list)
        or len(ordered_source_state_sha256s) != expected_flat_count
        or any(
            not isinstance(value, str) or len(value) != 64
            for value in ordered_source_state_sha256s
        )
    ):
        raise ContractError("ORDERED_SOURCE_STATE_SHA_VECTOR_INVALID")

    observed_tokens = 0
    flattened_group_rows = []
    flattened_group_states = []
    group_index = 0

    for pass_index, order in enumerate(pass_orders):
        for step_in_pass, start in enumerate(
            range(0, row_count, effective_batch),
            start=1,
        ):
            group = groups[group_index]
            expected_step = group_index + 1
            expected_ordinals = order[
                start : start + effective_batch
            ]

            if not isinstance(group, dict):
                raise ContractError("OPTIMIZER_GROUP_INVALID")
            if group.get("global_step") != expected_step:
                raise ContractError("OPTIMIZER_GROUP_STEP_MISMATCH")
            if group.get("pass_index") != pass_index:
                raise ContractError("OPTIMIZER_GROUP_PASS_INDEX_MISMATCH")
            if group.get("step_in_pass") != step_in_pass:
                raise ContractError("OPTIMIZER_GROUP_STEP_IN_PASS_MISMATCH")

            ordinals = group.get("ordinals")
            if not isinstance(ordinals, list) or len(ordinals) != effective_batch:
                raise ContractError("OPTIMIZER_GROUP_SIZE_MISMATCH")
            if ordinals != expected_ordinals:
                raise ContractError(
                    f"OPTIMIZER_GROUP_ORDINALS_MISMATCH:{expected_step}"
                )

            row_sha256s = group.get("row_sha256s")
            state_sha256s = group.get("source_state_sha256s")
            if (
                not isinstance(row_sha256s, list)
                or len(row_sha256s) != effective_batch
            ):
                raise ContractError("OPTIMIZER_GROUP_ROW_SHA_VECTOR_INVALID")
            if (
                not isinstance(state_sha256s, list)
                or len(state_sha256s) != effective_batch
            ):
                raise ContractError(
                    "OPTIMIZER_GROUP_SOURCE_STATE_SHA_VECTOR_INVALID"
                )

            flattened_group_rows.extend(row_sha256s)
            flattened_group_states.extend(state_sha256s)

            token_count = group.get("target_loss_tokens")
            if type(token_count) is not int or token_count <= 0:
                raise ContractError("OPTIMIZER_GROUP_TOKEN_COUNT_INVALID")
            observed_tokens += token_count
            group_index += 1

    if flattened_group_rows != ordered_row_sha256s:
        raise ContractError("OPTIMIZER_GROUP_ROW_SHA_MISMATCH")
    if flattened_group_states != ordered_source_state_sha256s:
        raise ContractError("OPTIMIZER_GROUP_SOURCE_STATE_SHA_MISMATCH")
    if observed_tokens != total_tokens:
        raise ContractError(
            f"OPTIMIZER_GROUP_TOKEN_TOTAL_MISMATCH:{observed_tokens}:"
            f"{total_tokens}"
        )



def _validate_training_contract_v2(
    contract: dict[str, Any],
    sample_order: dict[str, Any],
) -> None:
    """Validate distributed Generic-Stage training without V1 policy-state assumptions.

    V1 remains the authority for all historical profiles. V2 exists only where
    the training object has an explicit distributed world size and a generic
    scientific source-identity domain (for example Local Analyzer
    source_example_sha256).
    """
    if contract.get("schema_id") != "ROUND_LOCAL_TRAINING_CONTRACT_V2":
        raise ContractError("ROUND_LOCAL_TRAINING_CONTRACT_V2_SCHEMA_CHANGED")
    if contract.get("training_execution_authorized") is not False:
        raise ContractError("BUILD_CONTRACT_MUST_NOT_AUTHORIZE_TRAINING")
    if contract.get("training_execution_count") != 0:
        raise ContractError("BUILD_CONTRACT_TRAINING_COUNT_NOT_ZERO")

    dataset = contract.get("dataset")
    budget = contract.get("budget")
    optimization = contract.get("optimization")
    execution = contract.get("execution")
    if not all(
        isinstance(value, dict)
        for value in (dataset, budget, optimization, execution)
    ):
        raise ContractError("ROUND_LOCAL_TRAINING_CONTRACT_SECTION_MISSING")

    row_count = dataset.get("row_count")
    lengths = dataset.get("sequence_lengths")
    if type(row_count) is not int or row_count <= 0:
        raise ContractError("ROW_COUNT_INVALID")
    if (
        not isinstance(lengths, list)
        or len(lengths) != row_count
        or any(type(value) is not int or value <= 0 for value in lengths)
    ):
        raise ContractError("SEQUENCE_LENGTH_VECTOR_INVALID")
    if dataset.get("max_sequence_length") != max(lengths):
        raise ContractError("MAX_SEQUENCE_LENGTH_NOT_EXACT_CURRENT_MAX")
    if dataset.get("truncation") is not False:
        raise ContractError("TRUNCATION_FORBIDDEN")
    if dataset.get("retokenization") is not False:
        raise ContractError("RETOKENIZATION_FORBIDDEN")
    if dataset.get("reapply_chat_template") is not False:
        raise ContractError("CHAT_TEMPLATE_REAPPLICATION_FORBIDDEN")

    row_adapter = dataset.get("row_adapter")
    if not isinstance(row_adapter, dict):
        raise ContractError("ROW_ADAPTER_MISSING")
    identity_domain = row_adapter.get("identity_domain")
    identity_sha_field = row_adapter.get("source_identity_sha_field")
    if identity_domain != "SOURCE_EXAMPLE_SHA256":
        raise ContractError(
            "V2_IDENTITY_DOMAIN_UNSUPPORTED:" + repr(identity_domain)
        )
    if identity_sha_field != "source_example_sha256":
        raise ContractError(
            "V2_SOURCE_IDENTITY_SHA_FIELD_CHANGED:"
            + repr(identity_sha_field)
        )

    epochs = budget.get("epochs")
    per_rank_micro_batch = budget.get("micro_batch_size")
    grad_accum = budget.get("gradient_accumulation_steps")
    effective_batch = budget.get("effective_batch_size")
    partial = budget.get("partial_final_accumulation_group")
    optimizer_steps = budget.get("optimizer_steps")
    one_pass_tokens = dataset.get("one_pass_target_loss_token_count")
    total_tokens = budget.get("target_loss_token_budget")

    world_size = execution.get("world_size")
    execution_micro_batch = execution.get("per_rank_micro_batch_size")
    distributed_backend = execution.get("distributed_backend")
    if type(world_size) is not int or world_size <= 0:
        raise ContractError("WORLD_SIZE_INVALID")
    if execution_micro_batch != per_rank_micro_batch:
        raise ContractError("PER_RANK_MICRO_BATCH_EXECUTION_BUDGET_MISMATCH")
    if world_size > 1 and distributed_backend != "nccl":
        raise ContractError("MULTI_GPU_DISTRIBUTED_BACKEND_MUST_BE_NCCL")

    if type(epochs) is not int or epochs <= 0:
        raise ContractError("EPOCH_COUNT_INVALID")
    if type(per_rank_micro_batch) is not int or per_rank_micro_batch <= 0:
        raise ContractError("MICRO_BATCH_INVALID")
    if type(grad_accum) is not int or grad_accum <= 0:
        raise ContractError("GRADIENT_ACCUMULATION_INVALID")

    expected_effective_batch = (
        per_rank_micro_batch * grad_accum * world_size
    )
    if effective_batch != expected_effective_batch:
        raise ContractError(
            "DISTRIBUTED_EFFECTIVE_BATCH_MISMATCH:"
            f"{effective_batch}:{expected_effective_batch}"
        )
    if partial is not False:
        raise ContractError("PARTIAL_FINAL_ACCUMULATION_GROUP_FORBIDDEN")
    if row_count % effective_batch != 0:
        raise ContractError("ROW_COUNT_NOT_DIVISIBLE_BY_EFFECTIVE_BATCH")

    expected_steps = (row_count // effective_batch) * epochs
    if optimizer_steps != expected_steps:
        raise ContractError(
            f"OPTIMIZER_STEP_DERIVATION_MISMATCH:{optimizer_steps}:"
            f"{expected_steps}"
        )
    if type(one_pass_tokens) is not int or one_pass_tokens <= 0:
        raise ContractError("ONE_PASS_TARGET_TOKEN_COUNT_INVALID")
    if total_tokens != one_pass_tokens * epochs:
        raise ContractError("TARGET_TOKEN_BUDGET_DERIVATION_MISMATCH")

    if optimization.get("resume_from_checkpoint") is not False:
        raise ContractError("RESUME_FROM_CHECKPOINT_FORBIDDEN")
    if optimization.get("fresh_optimizer") is not True:
        raise ContractError("FRESH_OPTIMIZER_REQUIRED")
    if optimization.get("fresh_scheduler") is not True:
        raise ContractError("FRESH_SCHEDULER_REQUIRED")
    if type(optimization.get("warmup_steps")) is not int:
        raise ContractError("WARMUP_STEPS_INVALID")
    if optimization["warmup_steps"] < 0:
        raise ContractError("WARMUP_STEPS_NEGATIVE")
    if optimization["warmup_steps"] > optimizer_steps:
        raise ContractError("WARMUP_EXCEEDS_TOTAL_STEPS")

    def is_number(value) -> bool:
        return type(value) in (int, float)

    learning_rate = optimization.get("learning_rate")
    weight_decay = optimization.get("weight_decay")
    max_grad_norm = optimization.get("max_grad_norm")
    beta1 = optimization.get("adam_beta1")
    beta2 = optimization.get("adam_beta2")
    epsilon = optimization.get("adam_epsilon")
    if not is_number(learning_rate) or learning_rate <= 0:
        raise ContractError("LEARNING_RATE_INVALID")
    if not is_number(weight_decay) or weight_decay < 0:
        raise ContractError("WEIGHT_DECAY_INVALID")
    if not is_number(max_grad_norm) or max_grad_norm <= 0:
        raise ContractError("MAX_GRAD_NORM_INVALID")
    if not is_number(beta1) or not 0 <= beta1 < 1:
        raise ContractError("ADAM_BETA1_INVALID")
    if not is_number(beta2) or not 0 <= beta2 < 1:
        raise ContractError("ADAM_BETA2_INVALID")
    if not is_number(epsilon) or epsilon <= 0:
        raise ContractError("ADAM_EPSILON_INVALID")

    peft = contract.get("peft")
    if not isinstance(peft, dict):
        raise ContractError("PEFT_SECTION_INVALID")
    rank = peft.get("r")
    alpha = peft.get("lora_alpha")
    dropout = peft.get("lora_dropout")
    modules = peft.get("target_modules")
    if type(rank) is not int or rank <= 0:
        raise ContractError("LORA_R_INVALID")
    if type(alpha) is not int or alpha <= 0:
        raise ContractError("LORA_ALPHA_INVALID")
    if not is_number(dropout) or not 0 <= dropout < 1:
        raise ContractError("LORA_DROPOUT_INVALID")
    if (
        not isinstance(modules, list)
        or not modules
        or any(not isinstance(value, str) or not value for value in modules)
        or len(modules) != len(set(modules))
    ):
        raise ContractError("LORA_TARGET_MODULES_INVALID")

    if sample_order.get("schema_id") != "ROUND_SAMPLE_ORDER_MANIFEST_V2":
        raise ContractError("ROUND_SAMPLE_ORDER_V2_SCHEMA_CHANGED")
    if sample_order.get("identity_domain") != identity_domain:
        raise ContractError("SAMPLE_ORDER_IDENTITY_DOMAIN_MISMATCH")
    if sample_order.get("row_count") != row_count:
        raise ContractError("SAMPLE_ORDER_ROW_COUNT_MISMATCH")
    if sample_order.get("dataset_passes") != epochs:
        raise ContractError("SAMPLE_ORDER_PASS_COUNT_MISMATCH")
    if sample_order.get("training_seed") != budget.get("training_seed"):
        raise ContractError("SAMPLE_ORDER_TRAINING_SEED_MISMATCH")
    if sample_order.get("data_seed") != budget.get("data_seed"):
        raise ContractError("SAMPLE_ORDER_DATA_SEED_MISMATCH")
    if sample_order.get("shuffle_during_training") is not False:
        raise ContractError("RUNTIME_SHUFFLE_FORBIDDEN")
    if sample_order.get("world_size") != world_size:
        raise ContractError("SAMPLE_ORDER_WORLD_SIZE_MISMATCH")
    if sample_order.get("effective_batch_size") != effective_batch:
        raise ContractError("SAMPLE_ORDER_EFFECTIVE_BATCH_MISMATCH")

    pass_orders = sample_order.get("pass_orders")
    if not isinstance(pass_orders, list) or len(pass_orders) != epochs:
        raise ContractError("PASS_ORDER_COUNT_MISMATCH")
    expected_ordinals = list(range(row_count))
    for pass_index, order in enumerate(pass_orders):
        if not isinstance(order, list) or sorted(order) != expected_ordinals:
            raise ContractError(
                f"PASS_ORDER_NOT_PERMUTATION:{pass_index}"
            )

    groups = sample_order.get("optimizer_groups")
    if not isinstance(groups, list) or len(groups) != optimizer_steps:
        raise ContractError("OPTIMIZER_GROUP_COUNT_MISMATCH")

    ordered_row_sha256s = sample_order.get("ordered_row_sha256s")
    ordered_source_identity_sha256s = sample_order.get(
        "ordered_source_identity_sha256s"
    )
    expected_flat_count = row_count * epochs
    if (
        not isinstance(ordered_row_sha256s, list)
        or len(ordered_row_sha256s) != expected_flat_count
        or any(
            not isinstance(value, str) or len(value) != 64
            for value in ordered_row_sha256s
        )
    ):
        raise ContractError("ORDERED_ROW_SHA_VECTOR_INVALID")
    if (
        not isinstance(ordered_source_identity_sha256s, list)
        or len(ordered_source_identity_sha256s) != expected_flat_count
        or any(
            not isinstance(value, str) or len(value) != 64
            for value in ordered_source_identity_sha256s
        )
    ):
        raise ContractError("ORDERED_SOURCE_IDENTITY_SHA_VECTOR_INVALID")

    observed_tokens = 0
    flattened_group_rows = []
    flattened_group_identities = []
    group_index = 0

    for pass_index, order in enumerate(pass_orders):
        for step_in_pass, start in enumerate(
            range(0, row_count, effective_batch),
            start=1,
        ):
            group = groups[group_index]
            expected_step = group_index + 1
            expected_group_ordinals = order[
                start : start + effective_batch
            ]

            if not isinstance(group, dict):
                raise ContractError("OPTIMIZER_GROUP_INVALID")
            if group.get("global_step") != expected_step:
                raise ContractError("OPTIMIZER_GROUP_STEP_MISMATCH")
            if group.get("pass_index") != pass_index:
                raise ContractError("OPTIMIZER_GROUP_PASS_INDEX_MISMATCH")
            if group.get("step_in_pass") != step_in_pass:
                raise ContractError("OPTIMIZER_GROUP_STEP_IN_PASS_MISMATCH")

            ordinals = group.get("ordinals")
            if (
                not isinstance(ordinals, list)
                or len(ordinals) != effective_batch
            ):
                raise ContractError("OPTIMIZER_GROUP_SIZE_MISMATCH")
            if ordinals != expected_group_ordinals:
                raise ContractError(
                    f"OPTIMIZER_GROUP_ORDINALS_MISMATCH:{expected_step}"
                )

            row_sha256s = group.get("row_sha256s")
            identity_sha256s = group.get("source_identity_sha256s")
            if (
                not isinstance(row_sha256s, list)
                or len(row_sha256s) != effective_batch
            ):
                raise ContractError("OPTIMIZER_GROUP_ROW_SHA_VECTOR_INVALID")
            if (
                not isinstance(identity_sha256s, list)
                or len(identity_sha256s) != effective_batch
            ):
                raise ContractError(
                    "OPTIMIZER_GROUP_SOURCE_IDENTITY_SHA_VECTOR_INVALID"
                )
            if any(
                not isinstance(value, str) or len(value) != 64
                for value in identity_sha256s
            ):
                raise ContractError(
                    "OPTIMIZER_GROUP_SOURCE_IDENTITY_SHA_INVALID"
                )

            flattened_group_rows.extend(row_sha256s)
            flattened_group_identities.extend(identity_sha256s)

            token_count = group.get("target_loss_tokens")
            if type(token_count) is not int or token_count <= 0:
                raise ContractError("OPTIMIZER_GROUP_TOKEN_COUNT_INVALID")
            observed_tokens += token_count
            group_index += 1

    if flattened_group_rows != ordered_row_sha256s:
        raise ContractError("OPTIMIZER_GROUP_ROW_SHA_MISMATCH")
    if (
        flattened_group_identities
        != ordered_source_identity_sha256s
    ):
        raise ContractError("OPTIMIZER_GROUP_SOURCE_IDENTITY_SHA_MISMATCH")
    if observed_tokens != total_tokens:
        raise ContractError(
            f"OPTIMIZER_GROUP_TOKEN_TOTAL_MISMATCH:{observed_tokens}:"
            f"{total_tokens}"
        )


def validate_training_contract(
    contract: dict[str, Any],
    sample_order: dict[str, Any],
) -> None:
    schema_id = contract.get("schema_id")
    if schema_id == "ROUND_LOCAL_TRAINING_CONTRACT_V1":
        return _validate_training_contract_v1(
            contract,
            sample_order,
        )
    if schema_id == "ROUND_LOCAL_TRAINING_CONTRACT_V2":
        return _validate_training_contract_v2(
            contract,
            sample_order,
        )
    raise ContractError(
        "ROUND_LOCAL_TRAINING_CONTRACT_SCHEMA_CHANGED:"
        + repr(schema_id)
    )

def load_stage_context(binding_path: Path) -> StageContext:
    binding_path = binding_path.resolve()
    binding = load_json_object(binding_path)
    require_domain_sha(
        binding,
        schema_id="ROUND_TRAINING_STAGE_BINDING_V1",
        sha_field="stage_binding_sha256",
    )

    package_root_value = binding.get("package_root_relative_to_binding")
    if not isinstance(package_root_value, str):
        raise ContractError("PACKAGE_ROOT_RELATIVE_PATH_INVALID")
    package_root = (
        binding_path.parent / package_root_value
    ).resolve()

    role_path, role_binding = _load_file_ref(
        package_root,
        binding.get("trainer_role_binding_ref"),
        "TRAINER_ROLE_BINDING",
    )
    del role_path
    if role_binding.get("schema_id") != "ROUND_ROLE_BINDING_MANIFEST_V1":
        raise ContractError("TRAINER_ROLE_BINDING_SCHEMA_CHANGED")
    if role_binding.get("role_id") != "TRAINER":
        raise ContractError("TRAINER_ROLE_ID_CHANGED")
    if role_binding.get("shadow_only") is not False:
        raise ContractError("TRAINER_ROLE_UNEXPECTEDLY_SHADOW_ONLY")

    contract_path, contract = _load_file_ref(
        package_root,
        binding.get("training_contract_ref"),
        "TRAINING_CONTRACT",
    )
    del contract_path
    order_path, sample_order = _load_file_ref(
        package_root,
        binding.get("sample_order_ref"),
        "SAMPLE_ORDER",
    )
    del order_path
    adapter_ref = binding.get("runtime_adapter_ref")
    if not isinstance(adapter_ref, dict):
        raise ContractError("RUNTIME_ADAPTER_REF_INVALID")
    adapter_path_value = adapter_ref.get("path")
    if not isinstance(adapter_path_value, str):
        raise ContractError("RUNTIME_ADAPTER_PATH_INVALID")
    adapter_path = resolve_package_path(
        package_root,
        adapter_path_value,
    )
    require_sha(
        adapter_path,
        adapter_ref.get("sha256"),
        "RUNTIME_ADAPTER",
    )

    if binding.get("round_id") != contract.get("round_id"):
        raise ContractError("ROUND_ID_MISMATCH")
    if binding.get("profile_id") != contract.get("profile_id"):
        raise ContractError("PROFILE_ID_MISMATCH")
    if role_binding.get("round_id") != binding.get("round_id"):
        raise ContractError("ROLE_BINDING_ROUND_ID_MISMATCH")

    validate_training_contract(contract, sample_order)

    return StageContext(
        package_root=package_root,
        binding_path=binding_path,
        binding=binding,
        role_binding=role_binding,
        training_contract=contract,
        sample_order=sample_order,
        runtime_adapter_path=adapter_path,
    )


def load_execution_authorization(
    path: Path,
    *,
    context: StageContext,
    runner_freeze_root_sha256: str,
) -> dict[str, Any]:
    authorization = load_json_object(path)
    require_domain_sha(
        authorization,
        schema_id="ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        sha_field="authorization_sha256",
    )

    contract = context.training_contract
    budget = contract["budget"]
    expected = {
        "authorization_status": "APPROVED",
        "round_id": context.binding["round_id"],
        "stage_id": context.binding["stage_id"],
        "profile_id": context.binding["profile_id"],
        "stage_binding_sha256": context.binding["stage_binding_sha256"],
        "runner_freeze_root_sha256": runner_freeze_root_sha256,
        "authorized_optimizer_steps": budget["optimizer_steps"],
        "authorized_target_loss_tokens": budget["target_loss_token_budget"],
        "diagnostic_only": contract["diagnostic_only"],
        "promotion_eligible": contract["promotion_eligible"],
        "training_execution_count_before": 0,
    }
    observed = {
        key: authorization.get(key)
        for key in expected
    }
    if observed != expected:
        raise ContractError(
            "TRAINING_AUTHORIZATION_MISMATCH:"
            + repr(observed)
            + ":"
            + repr(expected)
        )

    for key in (
        "execution_attempt_id",
        "authorized_output_dir",
        "stage_attempt_root",
    ):
        value = authorization.get(key)
        if not isinstance(value, str) or not value:
            raise ContractError(f"AUTHORIZATION_{key.upper()}_INVALID")

    output_policy = context.binding.get("output_policy")
    if not isinstance(output_policy, dict):
        raise ContractError("OUTPUT_POLICY_MISSING")

    attempt_id = authorization["execution_attempt_id"]
    output_dir = Path(authorization["authorized_output_dir"]).resolve()
    attempt_root = Path(authorization["stage_attempt_root"]).resolve()
    output_parent = Path(
        output_policy["training_output_parent"]
    ).resolve()
    attempt_parent = Path(
        output_policy["stage_attempt_parent"]
    ).resolve()

    if output_policy.get("require_direct_child") is not True:
        raise ContractError("DIRECT_CHILD_OUTPUT_POLICY_REQUIRED")
    if output_dir.parent != output_parent:
        raise ContractError("AUTHORIZED_OUTPUT_PARENT_MISMATCH")
    if attempt_root.parent != attempt_parent:
        raise ContractError("STAGE_ATTEMPT_PARENT_MISMATCH")
    if output_policy.get(
        "require_basename_equals_execution_attempt_id"
    ) is not True:
        raise ContractError("ATTEMPT_BASENAME_POLICY_REQUIRED")
    if output_dir.name != attempt_id:
        raise ContractError("AUTHORIZED_OUTPUT_BASENAME_MISMATCH")
    if attempt_root.name != attempt_id:
        raise ContractError("STAGE_ATTEMPT_BASENAME_MISMATCH")
    if output_dir.exists():
        raise ContractError("AUTHORIZED_OUTPUT_ALREADY_EXISTS")
    if attempt_root.exists():
        raise ContractError("STAGE_ATTEMPT_ROOT_ALREADY_EXISTS")

    return authorization
