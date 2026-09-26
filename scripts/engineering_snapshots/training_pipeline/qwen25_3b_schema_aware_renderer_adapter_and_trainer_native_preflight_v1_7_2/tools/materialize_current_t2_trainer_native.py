#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import (
    ContractError,
    finalize,
    load_json_object,
    load_jsonl,
    sha256_file,
    write_new_json,
    write_new_jsonl,
)
from renderer_adapter_core import (
    build_native_row,
    build_t2_source_adapter_row,
    make_messages,
    mask_prompt_prefix,
)

try:
    from transformers import AutoTokenizer
except Exception as exc:
    raise SystemExit(
        "STOP=TRANSFORMERS_IMPORT_FAILED:" + type(exc).__name__
    )


def to_int_list(value, label: str) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, list) or not all(type(x) is int for x in value):
        raise ContractError(label + "_NOT_INT_LIST")
    return [int(x) for x in value]


CURRENT_T2_EXPECTED_SEQUENCE_LENGTHS = [
    774,
    654,
    568,
    327,
    570,
    343,
    436,
    333,
    491,
    314,
    274,
    425,
]

CURRENT_T2_NO_TRUNCATION_SEQUENCE_CEILING = 774


def load_current_t2_sequence_length_authority(
    metadata_path: Path,
) -> tuple[list[int], int]:
    metadata = load_json_object(
        metadata_path
    )

    authority = metadata.get(
        "current_t2_sequence_length_authority"
    )

    if not isinstance(authority, dict):
        raise ContractError(
            "CURRENT_T2_SEQUENCE_LENGTH_AUTHORITY_MISSING"
        )

    lengths = authority.get(
        "sequence_lengths"
    )
    ceiling = authority.get(
        "no_truncation_sequence_ceiling"
    )

    if lengths != CURRENT_T2_EXPECTED_SEQUENCE_LENGTHS:
        raise ContractError(
            "CURRENT_T2_SEQUENCE_LENGTH_CENSUS_CHANGED"
        )

    if ceiling != CURRENT_T2_NO_TRUNCATION_SEQUENCE_CEILING:
        raise ContractError(
            "CURRENT_T2_SEQUENCE_CEILING_CHANGED"
        )

    if authority.get("no_truncation") is not True:
        raise ContractError(
            "CURRENT_T2_NO_TRUNCATION_AUTHORITY_CHANGED"
        )

    if authority.get("row_count") != 12:
        raise ContractError(
            "CURRENT_T2_SEQUENCE_AUTHORITY_ROW_COUNT_CHANGED"
        )

    if max(lengths) != ceiling:
        raise ContractError(
            "CURRENT_T2_SEQUENCE_CEILING_NOT_EXACT_MAX"
        )

    return list(lengths), ceiling


def main() -> int:
    repro = load_json_object(
        Path(os.environ["REPRO_ROOT"])
        / "HISTORICAL_Q2_RENDERER_EXACT_REPRODUCTION_V1.json"
    )
    if repro.get("input_ids_exact_match_count") != 84:
        raise ContractError("HISTORICAL_INPUT_IDS_REPRODUCTION_NOT_84")
    if repro.get("labels_exact_match_count") != 84:
        raise ContractError("HISTORICAL_LABELS_REPRODUCTION_NOT_84")

    semantic_manifest = load_json_object(
        Path(os.environ["V13_SEMANTIC_ROOT"])
        / "DETERMINISTIC_SEMANTIC_DATASET_MATERIALIZATION_V1.json"
    )
    policy_meta = [
        row
        for row in semantic_manifest.get("datasets", [])
        if isinstance(row, dict)
        and row.get("target_component") == "POLICY"
    ]
    if len(policy_meta) != 1:
        raise ContractError("CURRENT_POLICY_DATASET_COUNT_CHANGED")
    if policy_meta[0].get("dataset_id") != (
        "POLICY_T2_UNVERIFIED_HUMAN_REPAIR_DIAGNOSTIC_V1"
    ):
        raise ContractError("CURRENT_POLICY_DATASET_ID_CHANGED")
    semantic_path = Path(policy_meta[0]["path"])
    semantic_rows = load_jsonl(semantic_path)
    if len(semantic_rows) != 12:
        raise ContractError("CURRENT_T2_SEMANTIC_ROW_COUNT_CHANGED")

    expected_sequence_lengths, ceiling = (
        load_current_t2_sequence_length_authority(
            Path(__file__).resolve().parents[1]
            / "PACKAGE_METADATA.json"
        )
    )

    tokenizer = AutoTokenizer.from_pretrained(
        os.environ["QWEN_BASE_MODEL_PATH"],
        local_files_only=True,
        trust_remote_code=False,
    )
    tokenizer.chat_template = Path(
        os.environ["PI1_CHAT_TEMPLATE_PATH"]
    ).read_text(encoding="utf-8")

    adapter_rows = []
    native_rows = []
    seen_states = set()

    for ordinal, semantic in enumerate(semantic_rows):
        adapter = build_t2_source_adapter_row(semantic, ordinal)
        state = adapter["source_state_sha256"]
        if state in seen_states:
            raise ContractError("T2_SOURCE_STATE_DUPLICATE")
        seen_states.add(state)

        prompt = adapter["input"]["prompt_text"]
        action_json = adapter["target"]["action_json"]
        messages = make_messages(prompt, action_json)

        full_ids = to_int_list(
            tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=False,
            ),
            "FULL_IDS",
        )
        prompt_ids = to_int_list(
            tokenizer.apply_chat_template(
                messages[:-1],
                tokenize=True,
                add_generation_prompt=True,
            ),
            "PROMPT_IDS",
        )
        labels = mask_prompt_prefix(full_ids, prompt_ids)

        expected_length = expected_sequence_lengths[
            ordinal
        ]

        if len(full_ids) != expected_length:
            raise ContractError(
                "T2_SEQUENCE_LENGTH_CENSUS_CHANGED:"
                f"{ordinal}:{len(full_ids)}:{expected_length}"
            )

        if len(full_ids) > ceiling:
            raise ContractError(
                "T2_SEQUENCE_EXCEEDS_FROZEN_NO_TRUNCATION_CEILING:"
                f"{ordinal}:{len(full_ids)}:{ceiling}"
            )

        native = build_native_row(
            adapter_row=adapter,
            input_ids=full_ids,
            labels=labels,
            ordinal=ordinal,
        )
        adapter_rows.append(adapter)
        native_rows.append(native)

    if len(adapter_rows) != 12 or len(native_rows) != 12:
        raise ContractError("T2_NATIVE_POPULATION_CHANGED")

    out_source = Path(os.environ["SOURCE_ADAPTER_ROOT"])
    out_native = Path(os.environ["NATIVE_ROOT"])
    out_source.mkdir(parents=True, exist_ok=False)
    out_native.mkdir(parents=True, exist_ok=False)

    adapter_path = (
        out_source / "POLICY_T2_SCHEMA_AWARE_RENDERER_SOURCE_V1.jsonl"
    )
    native_path = (
        out_native / "POLICY_T2_TRAINER_NATIVE_V1.jsonl"
    )
    write_new_jsonl(adapter_path, adapter_rows)
    write_new_jsonl(native_path, native_rows)

    seq_counts = [
        row["tokenization"]["sequence_token_count"]
        for row in native_rows
    ]
    completion_counts = [
        row["tokenization"]["completion_loss_token_count"]
        for row in native_rows
    ]

    manifest = finalize(
        "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1",
        "trainer_native_dataset_manifest_sha256",
        {
            "schema_id": "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1",
            "schema_version": 1,
            "research_planner_training_plan_sha256": os.environ[
                "EXPECTED_STRONG_PLAN_SHA256"
            ],
            "source_semantic_materialization_sha256": os.environ[
                "EXPECTED_V13_SEMANTIC_MATERIALIZATION_SHA256"
            ],
            "historical_renderer_reproduction_sha256": repro[
                "renderer_reproduction_sha256"
            ],
            "source_adapter_schema": (
                "POLICY_T2_SCHEMA_AWARE_RENDERER_SOURCE_V1"
            ),
            "source_adapter_dataset_path": str(adapter_path.resolve()),
            "source_adapter_dataset_sha256": sha256_file(adapter_path),
            "trainer_native_dataset_path": str(native_path.resolve()),
            "trainer_native_dataset_sha256": sha256_file(native_path),
            "sample_count": 12,
            "sequence_token_count_min": min(seq_counts),
            "sequence_token_count_max": max(seq_counts),
            "completion_loss_token_count_min": min(completion_counts),
            "completion_loss_token_count_max": max(completion_counts),
            "one_pass_target_loss_token_count": sum(completion_counts),
            "foundation_repository": os.environ[
                "QWEN_FOUNDATION_REPOSITORY"
            ],
            "foundation_revision": os.environ[
                "QWEN_FOUNDATION_REVISION"
            ],
            "tokenizer_bundle_sha256": os.environ[
                "EXPECTED_PI1_TOKENIZER_BUNDLE_SHA256"
            ],
            "chat_template_sha256": os.environ[
                "EXPECTED_PI1_CHAT_TEMPLATE_SHA256"
            ],
            "trained_region": "ASSISTANT_COMPLETION_SUFFIX_ONLY",
            "packing_applied": False,
            "truncation_applied": False,
            "policy_input_semantics": (
                "EXACT_FROZEN_SOURCE_PROMPT_PREFIX_ONLY"
            ),
            "assistant_target_semantics": (
                "CANONICAL_JSON_EXACT_REGISTERED_REPAIR_ACTION_ONLY"
            ),
            "hindsight_visible_to_policy": False,
            "f0f1_outcome_visible_to_policy": False,
            "training_route_visible_to_policy": False,
            "diagnostic_only": True,
            "verified_positive": False,
            "promotion_eligible": False,
            "trainer_execution_authorized": False,
            "training_execution_count": 0,
        },
    )
    write_new_json(
        out_native / "POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json",
        manifest,
    )

    print("【阶段30】当前 12 条 T2 Trainer 原生数据物化：通过")
    print("TRAINER_NATIVE_DATASET_MANIFEST_SHA256=" + manifest["trainer_native_dataset_manifest_sha256"])
    print("T2_TRAINER_NATIVE_ROW_COUNT=12")
    print("SEQUENCE_TOKEN_COUNT_RANGE=" + repr((min(seq_counts), max(seq_counts))))
    print("COMPLETION_LOSS_TOKEN_COUNT_RANGE=" + repr((min(completion_counts), max(completion_counts))))
    print("ONE_PASS_TARGET_LOSS_TOKEN_COUNT=" + str(sum(completion_counts)))
    print("HINDSIGHT_VISIBLE_TO_POLICY=false")
    print("F0F1_OUTCOME_VISIBLE_TO_POLICY=false")
    print("TRAINING_ROUTE_VISIBLE_TO_POLICY=false")
    print("TRAINER_EXECUTION_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
