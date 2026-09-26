"""Frozen execution contract for P4-R1-Q2-BAD formal training.

This revision intentionally contains only the deterministic scientific
training contract and ordering/grouping primitives.

The actual model-training execution layer is added only after this
contract passes its RED -> GREEN tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import random

import numpy as np
import torch
import torch.nn.functional as F
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    get_linear_schedule_with_warmup,
)


# ============================================================
# Frozen scientific identities
# ============================================================

TRAINING_CONFIG_PATH = Path(
    "/data/home/scwb204/run/pchsi/p2/"
    "p4_r1_q2_bad_training_config_v1/"
    "training_config.json"
)

EXPECTED_TRAINING_CONFIG_SHA256 = (
    "a860a77890e34e4cfcb38dff0acdf35d"
    "b0a3605d0a494c100f2b74b9f5228f9c"
)

EXPECTED_TRAINING_CONFIG_FREEZE_ROOT_SHA256 = (
    "da9096d402af8bc6e73669ba92df4974"
    "69e235b7a4a7dcadb3177f0ce1b753ba"
)

EXPECTED_MATERIALIZATION_FREEZE_ROOT_SHA256 = (
    "4cb2823b293a4bac29195ca479e47474"
    "a308b00bb062923e47c51329fe6fe6ac"
)

EXPECTED_DATASET_FREEZE_ROOT_SHA256 = (
    "564a33383118e79ffbfd07def4d241e1"
    "ff8dcb0407ea49feb252dc7d6b87895e"
)


# ============================================================
# Frozen scientific training contract
# ============================================================

FORMAL_TRAINING_SEEDS = (
    17,
    31,
    47,
)

FORMAL_EXAMPLE_COUNT = 84

FORMAL_DATASET_PASSES = 10

FORMAL_MICRO_BATCH = 1

FORMAL_GRAD_ACCUM = 4

FORMAL_EFFECTIVE_BATCH = (
    FORMAL_MICRO_BATCH
    * FORMAL_GRAD_ACCUM
)

FORMAL_STEPS_PER_PASS = 21

FORMAL_OPTIMIZER_STEPS = 210

FORMAL_TARGET_LOSS_TOKENS_PER_PASS = 967

FORMAL_TARGET_LOSS_TOKEN_BUDGET = 9670

FORMAL_WARMUP_STEPS = 21

FORMAL_MAX_SEQUENCE_LENGTH = 512

FORMAL_LEARNING_RATE = 1e-4

FORMAL_WEIGHT_DECAY = 0.0

FORMAL_MAX_GRAD_NORM = 1.0

FORMAL_LORA_R = 16

FORMAL_LORA_ALPHA = 32

FORMAL_LORA_DROPOUT = 0.05

FORMAL_LORA_TARGET_MODULES = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)


_ORDER_DOMAIN = (
    "P4_R1_Q2_BAD_TRAINING_ORDER_V1"
)


# ============================================================
# Frozen-config identity verification
# ============================================================

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_frozen_scientific_config() -> None:
    """Fail closed if the preregistered scientific config has drifted."""

    if not TRAINING_CONFIG_PATH.is_file():
        raise RuntimeError(
            "frozen training config is missing"
        )

    observed_sha = _sha256_file(
        TRAINING_CONFIG_PATH
    )

    if (
        observed_sha
        != EXPECTED_TRAINING_CONFIG_SHA256
    ):
        raise RuntimeError(
            "frozen training config SHA-256 mismatch"
        )

    config = json.loads(
        TRAINING_CONFIG_PATH.read_text(
            encoding="utf-8"
        )
    )

    checks = (
        (
            config[
                "training_materialization"
            ][
                "freeze_root_sha256"
            ],
            EXPECTED_MATERIALIZATION_FREEZE_ROOT_SHA256,
            "materialization freeze root",
        ),
        (
            config[
                "source_dataset"
            ][
                "dataset_freeze_root_sha256"
            ],
            EXPECTED_DATASET_FREEZE_ROOT_SHA256,
            "dataset freeze root",
        ),
        (
            tuple(
                config[
                    "seed_schedule"
                ][
                    "formal_training_seeds"
                ]
            ),
            FORMAL_TRAINING_SEEDS,
            "formal training seeds",
        ),
        (
            config[
                "training_budget"
            ][
                "complete_dataset_passes"
            ],
            FORMAL_DATASET_PASSES,
            "dataset passes",
        ),
        (
            config[
                "training_budget"
            ][
                "total_optimizer_steps"
            ],
            FORMAL_OPTIMIZER_STEPS,
            "optimizer steps",
        ),
        (
            config[
                "training_budget"
            ][
                "total_target_loss_token_budget_per_seed"
            ],
            FORMAL_TARGET_LOSS_TOKEN_BUDGET,
            "target-loss-token budget",
        ),
        (
            config[
                "training_budget"
            ][
                "gradient_accumulation_steps"
            ],
            FORMAL_GRAD_ACCUM,
            "gradient accumulation",
        ),
        (
            config[
                "training_budget"
            ][
                "micro_batch_size_per_device"
            ],
            FORMAL_MICRO_BATCH,
            "micro batch",
        ),
    )

    for observed, expected, name in checks:
        if observed != expected:
            raise RuntimeError(
                f"frozen scientific config mismatch: {name}"
            )


# ============================================================
# Deterministic formal training order
# ============================================================

def _ordering_key(
    *,
    seed: int,
    pass_index: int,
    example_index: int,
) -> tuple[bytes, int]:
    payload = (
        f"{_ORDER_DOMAIN}|"
        f"{seed}|"
        f"{pass_index}|"
        f"{example_index}"
    ).encode("utf-8")

    return (
        hashlib.sha256(
            payload
        ).digest(),
        example_index,
    )


def build_training_orders(
    *,
    example_count: int,
    seed: int,
    passes: int,
) -> tuple[tuple[int, ...], ...]:
    """Return one deterministic complete permutation for each dataset pass."""

    if (
        type(example_count) is not int
        or example_count <= 0
    ):
        raise ValueError(
            "example_count must be a positive int"
        )

    if type(seed) is not int:
        raise TypeError(
            "seed must be int"
        )

    if (
        type(passes) is not int
        or passes <= 0
    ):
        raise ValueError(
            "passes must be a positive int"
        )

    base = tuple(
        range(
            example_count
        )
    )

    result = []

    for pass_index in range(
        passes
    ):
        order = tuple(
            sorted(
                base,
                key=lambda example_index:
                    _ordering_key(
                        seed=seed,
                        pass_index=pass_index,
                        example_index=example_index,
                    ),
            )
        )

        if (
            len(order)
            != example_count
        ):
            raise AssertionError(
                "training order length mismatch"
            )

        if (
            set(order)
            != set(base)
        ):
            raise AssertionError(
                "training order is not a complete permutation"
            )

        result.append(
            order
        )

    return tuple(
        result
    )


# ============================================================
# Gradient-accumulation grouping
# ============================================================

def group_training_orders(
    *,
    orders: Sequence[Sequence[int]],
    group_size: int,
) -> tuple[tuple[int, ...], ...]:
    """Group examples within each pass without crossing pass boundaries."""

    if (
        type(group_size) is not int
        or group_size <= 0
    ):
        raise ValueError(
            "group_size must be a positive int"
        )

    groups = []

    for pass_index, raw_order in enumerate(
        orders
    ):
        order = tuple(
            raw_order
        )

        if not order:
            raise ValueError(
                f"training pass {pass_index} is empty"
            )

        if (
            len(order)
            % group_size
            != 0
        ):
            raise ValueError(
                "partial gradient-accumulation group "
                f"in pass {pass_index}"
            )

        for start in range(
            0,
            len(order),
            group_size,
        ):
            group = order[
                start:
                start + group_size
            ]

            if (
                len(group)
                != group_size
            ):
                raise AssertionError(
                    "partial accumulation group"
                )

            groups.append(
                group
            )

    return tuple(
        groups
    )



# ============================================================
# Frozen materialization identity
# ============================================================

MATERIALIZATION_ROOT = Path(
    "/data/home/scwb204/run/pchsi/p2/"
    "d_q2_bad_training_materialization_v1_frozen"
)

MATERIALIZED_EXAMPLES_PATH = (
    MATERIALIZATION_ROOT
    / "materialized_examples.jsonl"
)

MATERIALIZATION_CHECKSUM_LEDGER = (
    MATERIALIZATION_ROOT
    / "package_files.sha256"
)


def _verify_checksum_ledger(
    *,
    root: Path,
    ledger_path: Path,
    expected_ledger_sha256: str,
) -> None:
    """Verify a frozen package checksum ledger and every bound file."""

    if not ledger_path.is_file():
        raise RuntimeError(
            f"checksum ledger missing: {ledger_path}"
        )

    observed_root = _sha256_file(
        ledger_path
    )

    if (
        observed_root
        != expected_ledger_sha256
    ):
        raise RuntimeError(
            "frozen package checksum-ledger SHA-256 mismatch"
        )

    for line in ledger_path.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        parts = line.split(
            None,
            1,
        )

        if len(parts) != 2:
            raise RuntimeError(
                "malformed checksum-ledger line"
            )

        expected_sha, relative = parts

        relative = (
            relative
            .strip()
            .removeprefix("./")
        )

        target = (
            root
            / relative
        )

        if not target.is_file():
            raise RuntimeError(
                f"frozen bound file missing: {relative}"
            )

        observed_sha = _sha256_file(
            target
        )

        if observed_sha != expected_sha:
            raise RuntimeError(
                f"frozen bound file SHA-256 mismatch: {relative}"
            )


def verify_frozen_materialization() -> None:
    """Fail closed if the token materialization package has drifted."""

    _verify_checksum_ledger(
        root=MATERIALIZATION_ROOT,
        ledger_path=MATERIALIZATION_CHECKSUM_LEDGER,
        expected_ledger_sha256=(
            EXPECTED_MATERIALIZATION_FREEZE_ROOT_SHA256
        ),
    )


# ============================================================
# Frozen materialized records
# ============================================================

def load_frozen_materialized_records(
) -> tuple[dict[str, object], ...]:
    """Load and validate exactly the frozen 84 tokenized examples."""

    verify_frozen_materialization()

    rows = []

    for line in MATERIALIZED_EXAMPLES_PATH.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        row = json.loads(
            line
        )

        rows.append(
            row
        )

    if len(rows) != FORMAL_EXAMPLE_COUNT:
        raise RuntimeError(
            "formal materialized example-count mismatch"
        )

    case_ids = [
        row["case_id"]
        for row in rows
    ]

    if (
        len(set(case_ids))
        != FORMAL_EXAMPLE_COUNT
    ):
        raise RuntimeError(
            "duplicate formal materialized case_id"
        )

    total_shifted_targets = 0

    for row in rows:

        tokenization = row.get(
            "tokenization"
        )

        if not isinstance(
            tokenization,
            dict,
        ):
            raise RuntimeError(
                "materialized row tokenization missing"
            )

        input_ids = tokenization.get(
            "input_ids"
        )

        labels = tokenization.get(
            "labels"
        )

        completion_ids = tokenization.get(
            "completion_token_ids"
        )

        if not (
            isinstance(input_ids, list)
            and isinstance(labels, list)
            and isinstance(completion_ids, list)
        ):
            raise RuntimeError(
                "materialized token arrays malformed"
            )

        if (
            len(input_ids)
            != len(labels)
        ):
            raise RuntimeError(
                "materialized input/label length mismatch"
            )

        if (
            len(input_ids)
            > FORMAL_MAX_SEQUENCE_LENGTH
        ):
            raise RuntimeError(
                "materialized sequence exceeds frozen maximum"
            )

        prefix = tokenization.get(
            "prompt_prefix_token_count"
        )

        if (
            type(prefix) is not int
            or prefix < 0
            or prefix > len(labels)
        ):
            raise RuntimeError(
                "materialized prefix length malformed"
            )

        if (
            labels[:prefix]
            != [-100] * prefix
        ):
            raise RuntimeError(
                "materialized prompt labels are not fully masked"
            )

        if (
            labels[prefix:]
            != completion_ids
        ):
            raise RuntimeError(
                "materialized completion-label mismatch"
            )

        shifted_target_count = sum(
            value != -100
            for value in labels[1:]
        )

        if (
            shifted_target_count
            != len(completion_ids)
        ):
            raise RuntimeError(
                "materialized shifted target-count mismatch"
            )

        total_shifted_targets += (
            shifted_target_count
        )

    if (
        total_shifted_targets
        != FORMAL_TARGET_LOSS_TOKENS_PER_PASS
    ):
        raise RuntimeError(
            "one-pass target-loss-token count mismatch"
        )

    return tuple(
        rows
    )


def build_seed_training_records(
    *,
    seed: int,
) -> tuple[dict[str, object], ...]:
    """Expand the frozen dataset into exactly ten deterministic full passes."""

    validate_formal_seed(
        seed
    )

    source = (
        load_frozen_materialized_records()
    )

    orders = build_training_orders(
        example_count=FORMAL_EXAMPLE_COUNT,
        seed=seed,
        passes=FORMAL_DATASET_PASSES,
    )

    expanded = tuple(
        source[index]
        for order in orders
        for index in order
    )

    expected_count = (
        FORMAL_EXAMPLE_COUNT
        * FORMAL_DATASET_PASSES
    )

    if len(expanded) != expected_count:
        raise RuntimeError(
            "formal expanded training-record count mismatch"
        )

    target_tokens = sum(
        row[
            "tokenization"
        ][
            "completion_loss_token_count"
        ]
        for row in expanded
    )

    if (
        target_tokens
        != FORMAL_TARGET_LOSS_TOKEN_BUDGET
    ):
        raise RuntimeError(
            "formal expanded target-loss-token budget mismatch"
        )

    return expanded


# ============================================================
# Frozen singleton collator
# ============================================================

def collate_frozen_singleton(
    features,
) -> dict[str, torch.Tensor]:
    """Collate exactly one already-materialized example without padding."""

    if len(features) != 1:
        raise ValueError(
            "formal micro-batch must contain exactly one example"
        )

    feature = features[0]

    if (
        isinstance(feature, dict)
        and "tokenization" in feature
    ):
        feature = feature[
            "tokenization"
        ]

    if not isinstance(
        feature,
        dict,
    ):
        raise TypeError(
            "formal training feature must be dict"
        )

    input_ids = feature.get(
        "input_ids"
    )

    labels = feature.get(
        "labels"
    )

    if not (
        isinstance(input_ids, list)
        and isinstance(labels, list)
    ):
        raise TypeError(
            "formal input_ids and labels must be lists"
        )

    if len(input_ids) != len(labels):
        raise ValueError(
            "formal input_ids/labels length mismatch"
        )

    if not input_ids:
        raise ValueError(
            "formal sequence must be non-empty"
        )

    if (
        len(input_ids)
        > FORMAL_MAX_SEQUENCE_LENGTH
    ):
        raise ValueError(
            "formal sequence exceeds frozen max length"
        )

    return {
        "input_ids":
            torch.tensor(
                [input_ids],
                dtype=torch.long,
            ),

        "labels":
            torch.tensor(
                [labels],
                dtype=torch.long,
            ),

        "attention_mask":
            torch.ones(
                (1, len(input_ids)),
                dtype=torch.long,
            ),
    }


# ============================================================
# Token-normalized causal-LM objective
# ============================================================

def count_shifted_prediction_targets(
    labels: torch.Tensor,
) -> int:
    """Count nonignored causal-LM targets after the one-token shift."""

    if not isinstance(
        labels,
        torch.Tensor,
    ):
        raise TypeError(
            "labels must be torch.Tensor"
        )

    if labels.ndim != 2:
        raise ValueError(
            "labels must have shape [batch, sequence]"
        )

    if labels.shape[1] < 2:
        raise ValueError(
            "labels sequence length must be at least two"
        )

    return int(
        (
            labels[:, 1:]
            != -100
        )
        .sum()
        .item()
    )


def _positive_num_items(
    num_items_in_batch,
) -> int:
    """Normalize Trainer's accumulated prediction-target denominator."""

    if isinstance(
        num_items_in_batch,
        torch.Tensor,
    ):

        if (
            num_items_in_batch.numel()
            != 1
        ):
            raise ValueError(
                "num_items_in_batch must be scalar"
            )

        value = (
            num_items_in_batch
            .detach()
            .item()
        )

    else:
        value = num_items_in_batch

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
        or int(value) != value
        or value <= 0
    ):
        raise ValueError(
            "num_items_in_batch must be a positive integer"
        )

    return int(
        value
    )


def token_normalized_causal_lm_loss(
    outputs,
    labels: torch.Tensor,
    num_items_in_batch=None,
) -> torch.Tensor:
    """Causal-LM CE sum divided by the accumulated target-token count."""

    if num_items_in_batch is None:
        raise ValueError(
            "num_items_in_batch is required"
        )

    denominator = _positive_num_items(
        num_items_in_batch
    )

    if isinstance(
        outputs,
        dict,
    ):
        logits = outputs.get(
            "logits"
        )
    else:
        logits = getattr(
            outputs,
            "logits",
            None,
        )

    if not isinstance(
        logits,
        torch.Tensor,
    ):
        raise TypeError(
            "model outputs must contain tensor logits"
        )

    if not isinstance(
        labels,
        torch.Tensor,
    ):
        raise TypeError(
            "labels must be torch.Tensor"
        )

    if logits.ndim != 3:
        raise ValueError(
            "logits must have shape [batch, sequence, vocab]"
        )

    if labels.ndim != 2:
        raise ValueError(
            "labels must have shape [batch, sequence]"
        )

    if (
        logits.shape[0]
        != labels.shape[0]
        or logits.shape[1]
        != labels.shape[1]
    ):
        raise ValueError(
            "logits/labels batch or sequence dimensions mismatch"
        )

    local_target_count = (
        count_shifted_prediction_targets(
            labels
        )
    )

    if local_target_count <= 0:
        raise ValueError(
            "micro-batch contains no prediction targets"
        )

    shift_logits = (
        logits[:, :-1, :]
        .contiguous()
        .float()
    )

    shift_labels = (
        labels[:, 1:]
        .contiguous()
        .to(
            device=shift_logits.device
        )
    )

    loss_sum = F.cross_entropy(
        shift_logits.view(
            -1,
            shift_logits.shape[-1],
        ),
        shift_labels.view(-1),
        ignore_index=-100,
        reduction="sum",
    )

    return (
        loss_sum
        / denominator
    )


# ============================================================
# Frozen LoRA config
# ============================================================

def build_formal_lora_config(
) -> LoraConfig:
    """Construct exactly the preregistered LoRA adapter configuration."""

    return LoraConfig(
        r=FORMAL_LORA_R,
        lora_alpha=FORMAL_LORA_ALPHA,
        lora_dropout=FORMAL_LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(
            FORMAL_LORA_TARGET_MODULES
        ),
        init_lora_weights=True,
        use_rslora=False,
        use_dora=False,
    )


# ============================================================
# Formal seed gate
# ============================================================

def validate_formal_seed(
    seed: int,
) -> int:
    """Accept only the three preregistered formal training seeds."""

    if (
        type(seed) is not int
        or seed not in FORMAL_TRAINING_SEEDS
    ):
        raise ValueError(
            "invalid formal training seed"
        )

    return seed


# ============================================================
# Frozen TrainingArguments kwargs
# ============================================================

def build_formal_training_arguments_kwargs(
    *,
    seed: int,
    output_dir,
) -> dict[str, object]:
    """Return TrainingArguments kwargs with no scientific override surface."""

    seed = validate_formal_seed(
        seed
    )

    output = Path(
        output_dir
    )

    return {
        "output_dir":
            str(output),

        "overwrite_output_dir":
            False,

        "do_train":
            True,

        "do_eval":
            False,

        "per_device_train_batch_size":
            FORMAL_MICRO_BATCH,

        "gradient_accumulation_steps":
            FORMAL_GRAD_ACCUM,

        "learning_rate":
            FORMAL_LEARNING_RATE,

        "weight_decay":
            FORMAL_WEIGHT_DECAY,

        "adam_beta1":
            0.9,

        "adam_beta2":
            0.999,

        "adam_epsilon":
            1e-8,

        "max_grad_norm":
            FORMAL_MAX_GRAD_NORM,

        "max_steps":
            FORMAL_OPTIMIZER_STEPS,

        "lr_scheduler_type":
            "linear",

        "warmup_steps":
            FORMAL_WARMUP_STEPS,

        "optim":
            "adamw_torch",

        "bf16":
            True,

        "fp16":
            False,

        "seed":
            seed,

        "data_seed":
            seed,

        "remove_unused_columns":
            False,

        "dataloader_num_workers":
            0,

        "gradient_checkpointing":
            False,

        "torch_compile":
            False,

        "load_best_model_at_end":
            False,

        "save_strategy":
            "no",

        "eval_strategy":
            "no",

        "logging_strategy":
            "steps",

        "logging_steps":
            1,

        "report_to":
            [],

        "disable_tqdm":
            False,
    }


# ============================================================
# Trainable-parameter boundary
# ============================================================

def verify_lora_only_trainable_parameters(
    model,
) -> tuple[str, ...]:
    """Fail closed unless every trainable parameter belongs to LoRA."""

    trainable = tuple(
        name
        for name, parameter
        in model.named_parameters()
        if parameter.requires_grad
    )

    if not trainable:
        raise RuntimeError(
            "no trainable LoRA parameters found"
        )

    non_lora = tuple(
        name
        for name in trainable
        if "lora_" not in name.lower()
    )

    if non_lora:
        raise RuntimeError(
            "non-LoRA trainable parameter detected: "
            + ", ".join(
                non_lora[:10]
            )
        )

    return trainable




# ============================================================
# Exact frozen base-model artifact
# ============================================================

BASE_MODEL_SNAPSHOT_PATH = Path(
    "/data/run01/scwb204/.cache/huggingface/hub/"
    "models--Qwen--Qwen2.5-3B-Instruct/"
    "snapshots/"
    "aa8e72537993ba99e69dfaafa59ed015b17504d1"
)

BASE_MODEL_ARTIFACT_MANIFEST_PATH = (
    MATERIALIZATION_ROOT
    / "provenance"
    / "model_artifact_manifest.json"
)

EXPECTED_BASE_MODEL_REPOSITORY = (
    "Qwen/Qwen2.5-3B-Instruct"
)

EXPECTED_BASE_MODEL_REVISION = (
    "aa8e72537993ba99e69dfaafa59ed015b17504d1"
)

EXPECTED_TOKENIZER_BUNDLE_SHA256 = (
    "8fba154872aa8982e9556cb6cbdd35f3"
    "f6e83b8c3c41d782caf6fbf5931c8e0c"
)

EXPECTED_WEIGHTS_BUNDLE_SHA256 = (
    "a2e285e6b6161adb3ec7889466d8f1c0"
    "b384abdda3035f8b1630d457dcf66175"
)


_VERIFIED_BASE_ARTIFACT = None


def verify_exact_base_model_artifact(
) -> dict[str, object]:
    """Verify every frozen model/tokenizer artifact byte before model load."""

    global _VERIFIED_BASE_ARTIFACT

    if _VERIFIED_BASE_ARTIFACT is not None:
        return _VERIFIED_BASE_ARTIFACT

    verify_frozen_materialization()

    if not BASE_MODEL_ARTIFACT_MANIFEST_PATH.is_file():
        raise RuntimeError(
            "frozen base-model artifact manifest missing"
        )

    manifest = json.loads(
        BASE_MODEL_ARTIFACT_MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get("repository_id")
        != EXPECTED_BASE_MODEL_REPOSITORY
    ):
        raise RuntimeError(
            "base-model repository identity mismatch"
        )

    if (
        manifest.get("snapshot_revision")
        != EXPECTED_BASE_MODEL_REVISION
    ):
        raise RuntimeError(
            "base-model revision identity mismatch"
        )

    if (
        manifest.get("tokenizer_bundle_sha256")
        != EXPECTED_TOKENIZER_BUNDLE_SHA256
    ):
        raise RuntimeError(
            "base-model tokenizer bundle mismatch"
        )

    if (
        manifest.get("weights_bundle_sha256")
        != EXPECTED_WEIGHTS_BUNDLE_SHA256
    ):
        raise RuntimeError(
            "base-model weights bundle mismatch"
        )

    if manifest.get("project_adapter") is not None:
        raise RuntimeError(
            "base-model artifact unexpectedly carries project adapter"
        )

    if manifest.get("lora_enabled") is not False:
        raise RuntimeError(
            "base-model artifact unexpectedly enables LoRA"
        )

    candidates = manifest.get(
        "complete_local_candidates"
    )

    if not (
        isinstance(candidates, list)
        and str(BASE_MODEL_SNAPSHOT_PATH) in candidates
    ):
        raise RuntimeError(
            "selected local snapshot is not a frozen complete candidate"
        )

    if not BASE_MODEL_SNAPSHOT_PATH.is_dir():
        raise RuntimeError(
            "exact frozen local model snapshot is missing"
        )

    files = manifest.get(
        "files"
    )

    if not isinstance(
        files,
        dict,
    ):
        raise RuntimeError(
            "frozen model artifact file map malformed"
        )

    expected_file_names = {
        "config.json",
        "generation_config.json",
        "merges.txt",
        "model-00001-of-00002.safetensors",
        "model-00002-of-00002.safetensors",
        "model.safetensors.index.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
    }

    if set(files) != expected_file_names:
        raise RuntimeError(
            "frozen model artifact file set mismatch"
        )

    for file_name in sorted(files):

        specification = files[
            file_name
        ]

        target = (
            BASE_MODEL_SNAPSHOT_PATH
            / file_name
        )

        if not target.is_file():
            raise RuntimeError(
                "frozen model artifact file missing: "
                + file_name
            )

        observed_size = (
            target.stat().st_size
        )

        expected_size = (
            specification[
                "size_bytes"
            ]
        )

        if observed_size != expected_size:
            raise RuntimeError(
                "frozen model artifact size mismatch: "
                + file_name
            )

        observed_sha = _sha256_file(
            target
        )

        expected_sha = (
            specification[
                "sha256"
            ]
        )

        if observed_sha != expected_sha:
            raise RuntimeError(
                "frozen model artifact SHA-256 mismatch: "
                + file_name
            )

    _VERIFIED_BASE_ARTIFACT = manifest

    return manifest


# ============================================================
# Formal RNG boundary
# ============================================================

def seed_formal_training(
    seed: int,
) -> int:
    """Seed Python, NumPy, CPU and all visible CUDA RNGs."""

    seed = validate_formal_seed(
        seed
    )

    random.seed(
        seed
    )

    np.random.seed(
        seed
    )

    torch.manual_seed(
        seed
    )

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(
            seed
        )

    return seed


# ============================================================
# Exact frozen base-model load
# ============================================================

def load_exact_base_model(
    *,
    device,
):
    """Load only the frozen aa8e725 Qwen base checkpoint."""

    verify_exact_base_model_artifact()

    target_device = torch.device(
        device
    )

    if target_device.type != "cuda":
        raise ValueError(
            "formal base-model load requires CUDA"
        )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "formal CUDA device is unavailable"
        )

    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            "formal training requires exactly one visible CUDA device"
        )

    model = (
        AutoModelForCausalLM.from_pretrained(
            str(
                BASE_MODEL_SNAPSHOT_PATH
            ),
            local_files_only=True,
            trust_remote_code=False,
            dtype=torch.bfloat16,
        )
    )

    model.to(
        target_device
    )

    return model


# ============================================================
# Seeded LoRA construction
# ============================================================

def build_seeded_formal_lora_model(
    *,
    seed: int,
    device,
):
    """Load exact base then initialize the formal LoRA under the frozen seed."""

    seed = validate_formal_seed(
        seed
    )

    # Seed before any model/adapter execution.
    seed_formal_training(
        seed
    )

    base_model = load_exact_base_model(
        device=device
    )

    # Re-seed immediately before LoRA parameter initialization.
    # This makes the adapter initialization boundary explicit even
    # if base-model loading consumed RNG state internally.
    seed_formal_training(
        seed
    )

    model = get_peft_model(
        base_model,
        build_formal_lora_config(),
    )

    model.train()

    verify_lora_only_trainable_parameters(
        model
    )

    actual = (
        actual_lora_target_module_suffixes(
            model
        )
    )

    expected = set(
        FORMAL_LORA_TARGET_MODULES
    )

    if actual != expected:
        raise RuntimeError(
            "actual LoRA target-module boundary mismatch"
        )

    return model


# ============================================================
# Actual adapted-module inspection
# ============================================================

def actual_lora_target_module_suffixes(
    model,
) -> set[str]:
    """Read PEFT's actual targeted module list, not just requested config."""

    names = getattr(
        model,
        "targeted_module_names",
        None,
    )

    if not names:
        raise RuntimeError(
            "PEFT targeted_module_names is unavailable or empty"
        )

    suffixes = set()

    for name in names:

        if not isinstance(
            name,
            str,
        ):
            raise RuntimeError(
                "PEFT targeted module name is not string"
            )

        suffix = (
            name.rsplit(
                ".",
                1,
            )[-1]
        )

        suffixes.add(
            suffix
        )

    expected = set(
        FORMAL_LORA_TARGET_MODULES
    )

    unexpected = (
        suffixes
        - expected
    )

    missing = (
        expected
        - suffixes
    )

    if unexpected or missing:
        raise RuntimeError(
            "actual LoRA targets mismatch; "
            f"missing={sorted(missing)} "
            f"unexpected={sorted(unexpected)}"
        )

    return suffixes


# ============================================================
# Deterministic trainable-parameter identity
# ============================================================

def hash_trainable_parameters(
    model,
) -> str:
    """SHA-256 over names, shapes, dtypes and raw bytes of trainable tensors."""

    names = (
        verify_lora_only_trainable_parameters(
            model
        )
    )

    parameters = dict(
        model.named_parameters()
    )

    digest = hashlib.sha256()

    for name in names:

        parameter = parameters[
            name
        ]

        tensor = (
            parameter
            .detach()
            .cpu()
            .contiguous()
        )

        metadata = json.dumps(
            {
                "name":
                    name,

                "shape":
                    list(
                        tensor.shape
                    ),

                "dtype":
                    str(
                        tensor.dtype
                    ),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode(
            "utf-8"
        )

        digest.update(
            len(metadata).to_bytes(
                8,
                byteorder="big",
                signed=False,
            )
        )

        digest.update(
            metadata
        )

        raw = (
            tensor
            .view(
                torch.uint8
            )
            .numpy()
            .tobytes(
                order="C"
            )
        )

        digest.update(
            len(raw).to_bytes(
                8,
                byteorder="big",
                signed=False,
            )
        )

        digest.update(
            raw
        )

    return digest.hexdigest()


# ============================================================
# Frozen optimizer and scheduler
# ============================================================

def build_formal_optimizer(
    model,
) -> torch.optim.AdamW:
    """Build exactly the preregistered adamw_torch equivalent."""

    verify_lora_only_trainable_parameters(
        model
    )

    parameters = [
        parameter
        for parameter in model.parameters()
        if parameter.requires_grad
    ]

    if not parameters:
        raise RuntimeError(
            "formal optimizer has no trainable parameters"
        )

    return torch.optim.AdamW(
        parameters,
        lr=FORMAL_LEARNING_RATE,
        betas=(
            0.9,
            0.999,
        ),
        eps=1e-8,
        weight_decay=FORMAL_WEIGHT_DECAY,
    )


def build_formal_scheduler(
    optimizer,
):
    """Build the preregistered linear 21/210 warmup-decay schedule."""

    if not isinstance(
        optimizer,
        torch.optim.Optimizer,
    ):
        raise TypeError(
            "formal scheduler requires torch optimizer"
        )

    return get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=
            FORMAL_WARMUP_STEPS,
        num_training_steps=
            FORMAL_OPTIMIZER_STEPS,
    )




# ============================================================
# Formal execution approval
# ============================================================

FORMAL_EXECUTION_APPROVAL_TOKEN = (
    "EXECUTION_APPROVED_"
    "P4_R1_Q2_BAD_FORMAL_TRAINING_V1"
)


def validate_execution_approval_token(
    token: str,
) -> str:
    """Require the exact frozen formal-execution approval token."""

    if (
        not isinstance(token, str)
        or token != FORMAL_EXECUTION_APPROVAL_TOKEN
    ):
        raise ValueError(
            "invalid formal execution approval token"
        )

    return token


# ============================================================
# Exact 210-step formal run plan
# ============================================================

def build_formal_run_plan(
    *,
    seed: int,
) -> tuple[dict[str, object], ...]:
    """Materialize the exact 10-pass / 210-step training schedule."""

    seed = validate_formal_seed(
        seed
    )

    source_rows = (
        load_frozen_materialized_records()
    )

    orders = build_training_orders(
        example_count=FORMAL_EXAMPLE_COUNT,
        seed=seed,
        passes=FORMAL_DATASET_PASSES,
    )

    plan = []

    global_step = 0

    for pass_index, order in enumerate(
        orders
    ):

        if len(order) != FORMAL_EXAMPLE_COUNT:
            raise RuntimeError(
                "formal pass example-count mismatch"
            )

        if (
            len(order)
            % FORMAL_GRAD_ACCUM
            != 0
        ):
            raise RuntimeError(
                "formal pass contains partial accumulation group"
            )

        pass_target_tokens = 0

        for group_index, start in enumerate(
            range(
                0,
                len(order),
                FORMAL_GRAD_ACCUM,
            )
        ):

            indices = tuple(
                order[
                    start:
                    start + FORMAL_GRAD_ACCUM
                ]
            )

            if (
                len(indices)
                != FORMAL_GRAD_ACCUM
            ):
                raise RuntimeError(
                    "formal accumulation-group size mismatch"
                )

            case_ids = tuple(
                source_rows[index][
                    "case_id"
                ]
                for index in indices
            )

            target_loss_tokens = sum(
                int(
                    source_rows[index][
                        "tokenization"
                    ][
                        "completion_loss_token_count"
                    ]
                )
                for index in indices
            )

            if target_loss_tokens <= 0:
                raise RuntimeError(
                    "formal step has no target-loss tokens"
                )

            global_step += 1

            plan.append(
                {
                    "global_step":
                        global_step,

                    "pass_index":
                        pass_index,

                    "step_in_pass":
                        group_index + 1,

                    "example_indices":
                        indices,

                    "case_ids":
                        case_ids,

                    "target_loss_tokens":
                        target_loss_tokens,
                }
            )

            pass_target_tokens += (
                target_loss_tokens
            )

        if (
            pass_target_tokens
            != FORMAL_TARGET_LOSS_TOKENS_PER_PASS
        ):
            raise RuntimeError(
                "formal pass target-loss-token budget mismatch"
            )

    result = tuple(
        plan
    )

    if len(result) != FORMAL_OPTIMIZER_STEPS:
        raise RuntimeError(
            "formal run-plan optimizer-step count mismatch"
        )

    if (
        sum(
            row[
                "target_loss_tokens"
            ]
            for row in result
        )
        != FORMAL_TARGET_LOSS_TOKEN_BUDGET
    ):
        raise RuntimeError(
            "formal run-plan target-loss-token budget mismatch"
        )

    return result


# ============================================================
# Create-once formal output root
# ============================================================

def prepare_new_formal_output_directory(
    path,
) -> Path:
    """Create a fresh formal output directory and refuse reuse."""

    target = Path(
        path
    )

    if target.exists():
        raise FileExistsError(
            f"formal output directory already exists: {target}"
        )

    target.mkdir(
        parents=True,
        exist_ok=False,
    )

    return target


# ============================================================
# Final adapter artifact sealing
# ============================================================

def build_adapter_artifact_manifest(
    adapter_dir,
) -> dict[str, object]:
    """Content-address a saved PEFT adapter directory."""

    root = Path(
        adapter_dir
    )

    if not root.is_dir():
        raise RuntimeError(
            "adapter artifact directory is missing"
        )

    required_files = [
        "adapter_config.json",
        "adapter_model.safetensors",
    ]

    for relative in required_files:

        target = (
            root
            / relative
        )

        if not target.is_file():
            raise RuntimeError(
                "required adapter artifact missing: "
                + relative
            )

        if target.is_symlink():
            raise RuntimeError(
                "adapter artifact must not be symlink: "
                + relative
            )

    all_files = sorted(
        target
        for target in root.rglob("*")
        if target.is_file()
    )

    files = {}

    for target in all_files:

        if target.is_symlink():
            raise RuntimeError(
                "adapter artifact tree contains symlink"
            )

        relative = str(
            target.relative_to(
                root
            )
        )

        files[
            relative
        ] = {
            "size_bytes":
                target.stat().st_size,

            "sha256":
                _sha256_file(
                    target
                ),
        }

    bundle_payload = {
        "required_files":
            required_files,

        "files":
            files,
    }

    bundle_bytes = json.dumps(
        bundle_payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return {
        "schema_id":
            "P4_R1_Q2_BAD_ADAPTER_ARTIFACT_MANIFEST_V1",

        "schema_version":
            1,

        "required_files":
            required_files,

        "files":
            files,

        "adapter_bundle_sha256":
            hashlib.sha256(
                bundle_bytes
            ).hexdigest(),
    }


# ============================================================
# Grouped optimizer-step execution
# ============================================================

def execute_training_plan(
    *,
    model,
    source_rows,
    plan,
    optimizer,
    scheduler,
    device,
) -> tuple[dict[str, object], ...]:
    """Execute an already-frozen grouped training plan.

    This primitive contains no model selection, evaluation, checkpoint
    selection, retokenization, or scientific hyperparameter overrides.
    """

    target_device = torch.device(
        device
    )

    if not isinstance(
        optimizer,
        torch.optim.Optimizer,
    ):
        raise TypeError(
            "optimizer must be torch.optim.Optimizer"
        )

    if scheduler is None:
        raise TypeError(
            "scheduler is required"
        )

    source_rows = tuple(
        source_rows
    )

    plan = tuple(
        plan
    )

    if not plan:
        raise ValueError(
            "training plan must be non-empty"
        )

    model.train()

    ledger = []

    previous_global_step = 0

    for plan_row in plan:

        global_step = int(
            plan_row[
                "global_step"
            ]
        )

        if (
            global_step
            != previous_global_step + 1
        ):
            raise RuntimeError(
                "training plan global-step sequence mismatch"
            )

        previous_global_step = (
            global_step
        )

        indices = tuple(
            plan_row[
                "example_indices"
            ]
        )

        case_ids = tuple(
            plan_row[
                "case_ids"
            ]
        )

        if len(indices) != len(case_ids):
            raise RuntimeError(
                "training plan index/case-id cardinality mismatch"
            )

        if not indices:
            raise RuntimeError(
                "training plan contains empty optimizer step"
            )

        denominator = int(
            plan_row[
                "target_loss_tokens"
            ]
        )

        if denominator <= 0:
            raise RuntimeError(
                "training plan target-loss-token denominator invalid"
            )

        recomputed_denominator = 0

        for index, expected_case_id in zip(
            indices,
            case_ids,
            strict=True,
        ):

            if (
                type(index) is not int
                or index < 0
                or index >= len(source_rows)
            ):
                raise RuntimeError(
                    "training plan example index out of range"
                )

            source_row = source_rows[
                index
            ]

            if (
                source_row[
                    "case_id"
                ]
                != expected_case_id
            ):
                raise RuntimeError(
                    "training plan case-id identity mismatch"
                )

            recomputed_denominator += int(
                source_row[
                    "tokenization"
                ][
                    "completion_loss_token_count"
                ]
            )

        if (
            recomputed_denominator
            != denominator
        ):
            raise RuntimeError(
                "training plan target-loss-token denominator mismatch"
            )

        optimizer.zero_grad(
            set_to_none=True
        )

        group_loss = 0.0

        for index in indices:

            source_row = source_rows[
                index
            ]

            batch = collate_frozen_singleton(
                [
                    source_row[
                        "tokenization"
                    ]
                ]
            )

            batch = {
                key:
                    value.to(
                        target_device
                    )
                for key, value
                in batch.items()
            }

            local_target_count = (
                count_shifted_prediction_targets(
                    batch[
                        "labels"
                    ]
                )
            )

            expected_local = int(
                source_row[
                    "tokenization"
                ][
                    "completion_loss_token_count"
                ]
            )

            if (
                local_target_count
                != expected_local
            ):
                raise RuntimeError(
                    "local shifted target-count mismatch"
                )

            outputs = model(
                input_ids=
                    batch[
                        "input_ids"
                    ],

                attention_mask=
                    batch[
                        "attention_mask"
                    ],
            )

            loss = token_normalized_causal_lm_loss(
                outputs,
                batch[
                    "labels"
                ],
                num_items_in_batch=
                    denominator,
            )

            if not torch.isfinite(
                loss
            ).item():
                raise RuntimeError(
                    "non-finite training loss"
                )

            group_loss += float(
                loss
                .detach()
                .cpu()
            )

            loss.backward()

        trainable_parameters = [
            parameter
            for parameter
            in model.parameters()
            if parameter.requires_grad
        ]

        if not trainable_parameters:
            raise RuntimeError(
                "training step has no trainable parameters"
            )

        gradients = [
            parameter.grad
            for parameter
            in trainable_parameters
            if parameter.grad is not None
        ]

        if not gradients:
            raise RuntimeError(
                "training step produced no gradients"
            )

        if not all(
            torch.isfinite(
                gradient
            ).all().item()
            for gradient in gradients
        ):
            raise RuntimeError(
                "training step produced non-finite gradient"
            )

        learning_rate_before = tuple(
            float(
                group[
                    "lr"
                ]
            )
            for group in optimizer.param_groups
        )

        grad_norm = (
            torch.nn.utils.clip_grad_norm_(
                trainable_parameters,
                max_norm=
                    FORMAL_MAX_GRAD_NORM,
            )
        )

        if not torch.isfinite(
            grad_norm
        ).item():
            raise RuntimeError(
                "training step gradient norm is non-finite"
            )

        optimizer.step()

        scheduler.step()

        learning_rate_after = tuple(
            float(
                group[
                    "lr"
                ]
            )
            for group in optimizer.param_groups
        )

        ledger.append(
            {
                "global_step":
                    global_step,

                "pass_index":
                    int(
                        plan_row[
                            "pass_index"
                        ]
                    ),

                "step_in_pass":
                    int(
                        plan_row[
                            "step_in_pass"
                        ]
                    ),

                "case_ids":
                    case_ids,

                "example_indices":
                    indices,

                "target_loss_tokens":
                    denominator,

                "group_token_normalized_loss":
                    group_loss,

                "loss_is_finite":
                    True,

                "grad_norm":
                    float(
                        grad_norm
                        .detach()
                        .cpu()
                    ),

                "grad_norm_is_finite":
                    True,

                "learning_rate_before":
                    learning_rate_before,

                "learning_rate_after":
                    learning_rate_after,
            }
        )

    return tuple(
        ledger
    )


# ============================================================
# Formal CLI surface
# ============================================================

def build_formal_argument_parser(
) -> argparse.ArgumentParser:
    """Expose execution identity only; scientific parameters are not CLI."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute the frozen "
            "P4-R1-Q2-BAD formal training configuration."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        required=True,
        choices=list(
            FORMAL_TRAINING_SEEDS
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--approval-token",
        type=str,
        required=True,
    )

    return parser




# ============================================================
# Completed-ledger validation
# ============================================================

def validate_completed_formal_ledger(
    *,
    plan,
    ledger,
) -> dict[str, object]:
    """Require the completed ledger to match the frozen plan exactly."""

    plan = tuple(plan)
    ledger = tuple(ledger)

    if len(plan) != FORMAL_OPTIMIZER_STEPS:
        raise RuntimeError(
            "ledger validation received invalid formal plan length"
        )

    if len(ledger) != len(plan):
        raise RuntimeError(
            "ledger optimizer-step count mismatch"
        )

    total_target_tokens = 0
    observed_passes = set()

    for expected, observed in zip(
        plan,
        ledger,
        strict=True,
    ):

        for key in (
            "global_step",
            "pass_index",
            "step_in_pass",
            "case_ids",
            "example_indices",
            "target_loss_tokens",
        ):
            if observed.get(key) != expected.get(key):
                raise RuntimeError(
                    "ledger identity mismatch: "
                    + key
                )

        if observed.get(
            "loss_is_finite"
        ) is not True:
            raise RuntimeError(
                "ledger contains non-finite loss"
            )

        if observed.get(
            "grad_norm_is_finite"
        ) is not True:
            raise RuntimeError(
                "ledger contains non-finite grad norm"
            )

        loss_value = observed.get(
            "group_token_normalized_loss"
        )

        grad_norm = observed.get(
            "grad_norm"
        )

        if not (
            isinstance(
                loss_value,
                (int, float),
            )
            and math.isfinite(
                float(loss_value)
            )
        ):
            raise RuntimeError(
                "ledger loss value is invalid"
            )

        if not (
            isinstance(
                grad_norm,
                (int, float),
            )
            and math.isfinite(
                float(grad_norm)
            )
        ):
            raise RuntimeError(
                "ledger grad-norm value is invalid"
            )

        target_tokens = int(
            observed[
                "target_loss_tokens"
            ]
        )

        if target_tokens <= 0:
            raise RuntimeError(
                "ledger target-loss-token value is invalid"
            )

        total_target_tokens += (
            target_tokens
        )

        observed_passes.add(
            int(
                observed[
                    "pass_index"
                ]
            )
        )

    if total_target_tokens != (
        FORMAL_TARGET_LOSS_TOKEN_BUDGET
    ):
        raise RuntimeError(
            "ledger target-loss-token budget mismatch"
        )

    expected_passes = set(
        range(
            FORMAL_DATASET_PASSES
        )
    )

    if observed_passes != expected_passes:
        raise RuntimeError(
            "ledger dataset-pass identity mismatch"
        )

    if (
        ledger[-1][
            "global_step"
        ]
        != FORMAL_OPTIMIZER_STEPS
    ):
        raise RuntimeError(
            "ledger final optimizer-step mismatch"
        )

    return {
        "optimizer_step_count":
            len(ledger),

        "dataset_pass_count":
            len(
                observed_passes
            ),

        "target_loss_token_count":
            total_target_tokens,

        "all_losses_finite":
            True,

        "all_grad_norms_finite":
            True,
    }


# ============================================================
# Canonical create-once evidence
# ============================================================

def _canonical_json_bytes(
    value,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _exclusive_write_bytes(
    path,
    payload: bytes,
) -> None:

    target = Path(path)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = os.open(
        target,
        flags,
        0o600,
    )

    try:

        view = memoryview(
            payload
        )

        while view:

            written = os.write(
                fd,
                view,
            )

            if written <= 0:
                raise OSError(
                    "short exclusive evidence write"
                )

            view = view[
                written:
            ]

        os.fsync(
            fd
        )

    finally:

        os.close(
            fd
        )


def write_canonical_json_exclusive(
    path,
    value,
) -> None:

    _exclusive_write_bytes(
        path,
        _canonical_json_bytes(
            value
        ),
    )


def write_canonical_jsonl_exclusive(
    path,
    rows,
) -> None:

    payload = b"".join(
        _canonical_json_bytes(
            row
        )
        for row in rows
    )

    _exclusive_write_bytes(
        path,
        payload,
    )


# ============================================================
# SHA identity helper
# ============================================================

def _validate_sha256_hex(
    value,
    *,
    name: str,
) -> str:

    if not (
        isinstance(value, str)
        and len(value) == 64
    ):
        raise ValueError(
            f"{name} must be a 64-character SHA-256"
        )

    try:
        int(
            value,
            16,
        )
    except ValueError as error:
        raise ValueError(
            f"{name} must be hexadecimal SHA-256"
        ) from error

    return value


# ============================================================
# Formal scientific run manifest
# ============================================================

def build_formal_run_manifest(
    *,
    seed: int,
    ledger_summary,
    initial_trainable_sha256: str,
    final_trainable_sha256: str,
    adapter_manifest,
    runner_freeze_root_sha256: str,
    infrastructure_node_exclusions=(),
) -> dict[str, object]:

    seed = validate_formal_seed(
        seed
    )

    initial_trainable_sha256 = (
        _validate_sha256_hex(
            initial_trainable_sha256,
            name=(
                "initial_trainable_sha256"
            ),
        )
    )

    final_trainable_sha256 = (
        _validate_sha256_hex(
            final_trainable_sha256,
            name=(
                "final_trainable_sha256"
            ),
        )
    )

    runner_freeze_root_sha256 = (
        _validate_sha256_hex(
            runner_freeze_root_sha256,
            name=(
                "runner_freeze_root_sha256"
            ),
        )
    )

    if (
        initial_trainable_sha256
        == final_trainable_sha256
    ):
        raise RuntimeError(
            "formal training trainable state unchanged"
        )

    adapter_bundle = (
        adapter_manifest.get(
            "adapter_bundle_sha256"
        )
    )

    adapter_bundle = (
        _validate_sha256_hex(
            adapter_bundle,
            name=(
                "adapter_bundle_sha256"
            ),
        )
    )

    if (
        ledger_summary[
            "optimizer_step_count"
        ]
        != FORMAL_OPTIMIZER_STEPS
    ):
        raise RuntimeError(
            "run manifest optimizer-step summary mismatch"
        )

    if (
        ledger_summary[
            "dataset_pass_count"
        ]
        != FORMAL_DATASET_PASSES
    ):
        raise RuntimeError(
            "run manifest dataset-pass summary mismatch"
        )

    if (
        ledger_summary[
            "target_loss_token_count"
        ]
        != FORMAL_TARGET_LOSS_TOKEN_BUDGET
    ):
        raise RuntimeError(
            "run manifest target-loss-token summary mismatch"
        )

    return {
        "schema_id":
            "P4_R1_Q2_BAD_FORMAL_RUN_MANIFEST_V1",

        "schema_version":
            1,

        "condition_id":
            "P4-R1-Q2-BAD",

        "run_status":
            "FORMAL_TRAINING_COMPLETED",

        "formal_training_seed":
            seed,

        "dataset_freeze_root_sha256":
            EXPECTED_DATASET_FREEZE_ROOT_SHA256,

        "materialization_freeze_root_sha256":
            EXPECTED_MATERIALIZATION_FREEZE_ROOT_SHA256,

        "training_config_sha256":
            EXPECTED_TRAINING_CONFIG_SHA256,

        "training_config_freeze_root_sha256":
            EXPECTED_TRAINING_CONFIG_FREEZE_ROOT_SHA256,

        "runner_freeze_root_sha256":
            runner_freeze_root_sha256,

        "base_model_repository":
            EXPECTED_BASE_MODEL_REPOSITORY,

        "base_model_revision":
            EXPECTED_BASE_MODEL_REVISION,

        "tokenizer_bundle_sha256":
            EXPECTED_TOKENIZER_BUNDLE_SHA256,

        "initial_trainable_parameter_sha256":
            initial_trainable_sha256,

        "final_trainable_parameter_sha256":
            final_trainable_sha256,

        "adapter_bundle_sha256":
            adapter_bundle,

        "optimizer_step_count":
            ledger_summary[
                "optimizer_step_count"
            ],

        "dataset_pass_count":
            ledger_summary[
                "dataset_pass_count"
            ],

        "target_loss_token_count":
            ledger_summary[
                "target_loss_token_count"
            ],

        "all_losses_finite":
            ledger_summary[
                "all_losses_finite"
            ],

        "all_grad_norms_finite":
            ledger_summary[
                "all_grad_norms_finite"
            ],

        "scientific_checkpoint_rule":
            "FINAL_STEP_ONLY",

        "intermediate_scientific_checkpoint_used":
            False,

        "early_stopping_used":
            False,

        "select_used_for_training_or_model_selection":
            False,

        "infrastructure_node_exclusions":
            list(
                infrastructure_node_exclusions
            ),
    }


# ============================================================
# Formal 210-step run
# ============================================================

def run_formal_training(
    *,
    seed: int,
    output_dir,
    approval_token: str,
    runner_freeze_root_sha256: str,
    infrastructure_node_exclusions=(
        "d1n41a11g02",
    ),
) -> dict[str, object]:
    """Execute one complete preregistered formal seed run."""

    seed = validate_formal_seed(
        seed
    )

    validate_execution_approval_token(
        approval_token
    )

    runner_freeze_root_sha256 = (
        _validate_sha256_hex(
            runner_freeze_root_sha256,
            name=(
                "runner_freeze_root_sha256"
            ),
        )
    )

    verify_formal_schedule()
    verify_frozen_scientific_config()
    verify_frozen_materialization()
    verify_exact_base_model_artifact()

    if not torch.cuda.is_available():
        raise RuntimeError(
            "formal training requires CUDA"
        )

    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            "formal training requires exactly one visible CUDA device"
        )

    output_root = (
        prepare_new_formal_output_directory(
            output_dir
        )
    )

    adapter_dir = (
        output_root
        / "adapter"
    )

    ledger_path = (
        output_root
        / "training_step_ledger.jsonl"
    )

    adapter_manifest_path = (
        output_root
        / "adapter_artifact_manifest.json"
    )

    run_manifest_path = (
        output_root
        / "formal_run_manifest.json"
    )

    source_rows = (
        load_frozen_materialized_records()
    )

    plan = build_formal_run_plan(
        seed=seed
    )

    model = None

    try:

        seed_formal_training(
            seed
        )

        model = (
            build_seeded_formal_lora_model(
                seed=seed,
                device="cuda",
            )
        )

        initial_trainable_sha256 = (
            hash_trainable_parameters(
                model
            )
        )

        optimizer = (
            build_formal_optimizer(
                model
            )
        )

        scheduler = (
            build_formal_scheduler(
                optimizer
            )
        )

        ledger = execute_training_plan(
            model=model,
            source_rows=source_rows,
            plan=plan,
            optimizer=optimizer,
            scheduler=scheduler,
            device="cuda",
        )

        ledger_summary = (
            validate_completed_formal_ledger(
                plan=plan,
                ledger=ledger,
            )
        )

        final_trainable_sha256 = (
            hash_trainable_parameters(
                model
            )
        )

        model.save_pretrained(
            adapter_dir,
            safe_serialization=True,
        )

        adapter_manifest = (
            build_adapter_artifact_manifest(
                adapter_dir
            )
        )

        run_manifest = (
            build_formal_run_manifest(
                seed=seed,

                ledger_summary=
                    ledger_summary,

                initial_trainable_sha256=
                    initial_trainable_sha256,

                final_trainable_sha256=
                    final_trainable_sha256,

                adapter_manifest=
                    adapter_manifest,

                runner_freeze_root_sha256=
                    runner_freeze_root_sha256,

                infrastructure_node_exclusions=
                    infrastructure_node_exclusions,
            )
        )

        write_canonical_jsonl_exclusive(
            ledger_path,
            ledger,
        )

        write_canonical_json_exclusive(
            adapter_manifest_path,
            adapter_manifest,
        )

        write_canonical_json_exclusive(
            run_manifest_path,
            run_manifest,
        )

        return run_manifest

    finally:

        if model is not None:
            del model

        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ============================================================
# Formal execution CLI
# ============================================================

def main(
    argv=None,
) -> int:
    """Formal CLI. Scientific hyperparameters are not configurable."""

    parser = (
        build_formal_argument_parser()
    )

    args = parser.parse_args(
        argv
    )

    # The frozen runner root is intentionally supplied through
    # the environment rather than a scientific CLI parameter.
    # The formal Slurm wrapper will bind it after runner freeze.
    runner_freeze_root_sha256 = (
        os.environ.get(
            "P4_R1_Q2_BAD_RUNNER_FREEZE_ROOT_SHA256"
        )
    )

    if runner_freeze_root_sha256 is None:
        raise RuntimeError(
            "P4_R1_Q2_BAD_RUNNER_FREEZE_ROOT_SHA256 "
            "is required"
        )

    manifest = run_formal_training(
        seed=args.seed,

        output_dir=
            args.output_dir,

        approval_token=
            args.approval_token,

        runner_freeze_root_sha256=
            runner_freeze_root_sha256,

        infrastructure_node_exclusions=(
            "d1n41a11g02",
        ),
    )

    print(
        "FORMAL_TRAINING_COMPLETED"
    )

    print(
        "formal_training_seed =",
        manifest[
            "formal_training_seed"
        ],
    )

    print(
        "optimizer_step_count =",
        manifest[
            "optimizer_step_count"
        ],
    )

    print(
        "target_loss_token_count =",
        manifest[
            "target_loss_token_count"
        ],
    )

    print(
        "adapter_bundle_sha256 =",
        manifest[
            "adapter_bundle_sha256"
        ],
    )

    return 0



# ============================================================
# Formal schedule self-check
# ============================================================

def verify_formal_schedule() -> None:
    verify_frozen_scientific_config()

    if (
        FORMAL_EFFECTIVE_BATCH
        != 4
    ):
        raise RuntimeError(
            "formal effective batch drift"
        )

    if (
        FORMAL_EXAMPLE_COUNT
        % FORMAL_EFFECTIVE_BATCH
        != 0
    ):
        raise RuntimeError(
            "formal dataset does not divide evenly "
            "into accumulation groups"
        )

    if (
        FORMAL_EXAMPLE_COUNT
        // FORMAL_EFFECTIVE_BATCH
        != FORMAL_STEPS_PER_PASS
    ):
        raise RuntimeError(
            "formal steps-per-pass drift"
        )

    if (
        FORMAL_STEPS_PER_PASS
        * FORMAL_DATASET_PASSES
        != FORMAL_OPTIMIZER_STEPS
    ):
        raise RuntimeError(
            "formal optimizer-step budget drift"
        )

    if (
        FORMAL_TARGET_LOSS_TOKENS_PER_PASS
        * FORMAL_DATASET_PASSES
        != FORMAL_TARGET_LOSS_TOKEN_BUDGET
    ):
        raise RuntimeError(
            "formal target-loss-token budget drift"
        )

    for seed in FORMAL_TRAINING_SEEDS:
        orders = build_training_orders(
            example_count=FORMAL_EXAMPLE_COUNT,
            seed=seed,
            passes=FORMAL_DATASET_PASSES,
        )

        groups = group_training_orders(
            orders=orders,
            group_size=FORMAL_GRAD_ACCUM,
        )

        if (
            len(groups)
            != FORMAL_OPTIMIZER_STEPS
        ):
            raise RuntimeError(
                f"formal group-count mismatch for seed {seed}"
            )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
