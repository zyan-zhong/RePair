#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import (
    ContractError,
    finalize,
    load_json_object,
    load_jsonl,
    write_new_json,
)
from renderer_adapter_core import (
    find_unique_nested_key_path,
    get_path,
    make_messages,
    mask_prompt_prefix,
    validate_historical_source_row,
)

try:
    import transformers
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


def main() -> int:
    source = load_jsonl(Path(os.environ["PI1_SOURCE_TRAINING_EXAMPLES_PATH"]))
    frozen = load_jsonl(
        Path(os.environ["PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH"])
    )
    if len(source) != 84 or len(frozen) != 84:
        raise ContractError("HISTORICAL_ORACLE_POPULATION_CHANGED")

    # Discover exact native field paths from the frozen oracle itself.
    input_path = find_unique_nested_key_path(frozen[0], "input_ids")
    labels_path = find_unique_nested_key_path(frozen[0], "labels")

    tokenizer = AutoTokenizer.from_pretrained(
        os.environ["QWEN_BASE_MODEL_PATH"],
        local_files_only=True,
        trust_remote_code=False,
    )
    tokenizer.chat_template = Path(
        os.environ["PI1_CHAT_TEMPLATE_PATH"]
    ).read_text(encoding="utf-8")

    first_mismatch = None
    seq_counts: list[int] = []
    completion_counts: list[int] = []

    for index, (src, expected) in enumerate(zip(source, frozen)):
        prompt_text, action_json = validate_historical_source_row(src)
        messages = make_messages(prompt_text, action_json)

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

        frozen_ids = get_path(expected, input_path)
        frozen_labels = get_path(expected, labels_path)
        if full_ids != frozen_ids:
            first_mismatch = {
                "index": index,
                "kind": "INPUT_IDS",
                "expected_length": len(frozen_ids),
                "actual_length": len(full_ids),
            }
            break
        if labels != frozen_labels:
            first_mismatch = {
                "index": index,
                "kind": "LABELS",
                "expected_length": len(frozen_labels),
                "actual_length": len(labels),
            }
            break

        seq_counts.append(len(full_ids))
        completion_counts.append(sum(x != -100 for x in labels))

    if first_mismatch is not None:
        raise ContractError(
            "HISTORICAL_RENDERER_84_EXACT_REPRODUCTION_FAILED:"
            + repr(first_mismatch)
        )

    frozen_manifest = load_json_object(
        Path(os.environ["PI1_FINAL_MATERIALIZATION_MANIFEST_PATH"])
    )
    checks = {
        "sequence_token_count_min": min(seq_counts),
        "sequence_token_count_max": max(seq_counts),
        "completion_loss_token_count_min": min(completion_counts),
        "completion_loss_token_count_max": max(completion_counts),
        "one_pass_target_loss_token_count": sum(completion_counts),
    }
    for field, observed in checks.items():
        expected = frozen_manifest.get(field)
        if expected != observed:
            raise ContractError(
                f"HISTORICAL_MANIFEST_REPRODUCTION_MISMATCH:"
                f"{field}:{observed}:{expected}"
            )

    receipt = finalize(
        "HISTORICAL_Q2_RENDERER_EXACT_REPRODUCTION_V1",
        "renderer_reproduction_sha256",
        {
            "schema_id": "HISTORICAL_Q2_RENDERER_EXACT_REPRODUCTION_V1",
            "schema_version": 1,
            "source_schema": "D_Q2_BAD_V1_TRAINING_EXAMPLE",
            "source_schema_binding": (
                "input.prompt_text + target.action_json"
            ),
            "native_input_ids_path": list(input_path),
            "native_labels_path": list(labels_path),
            "sample_count": 84,
            "input_ids_exact_match_count": 84,
            "labels_exact_match_count": 84,
            "transformers_version": transformers.__version__,
            **checks,
            "chat_template_sha256": os.environ[
                "EXPECTED_PI1_CHAT_TEMPLATE_SHA256"
            ],
            "tokenizer_bundle_sha256": os.environ[
                "EXPECTED_PI1_TOKENIZER_BUNDLE_SHA256"
            ],
            "historical_materializer_source_executed": False,
            "reproduction_algorithm": (
                "user=source.input.prompt_text;"
                "assistant=source.target.action_json;"
                "full=apply_chat_template(messages,tokenize=true,"
                "add_generation_prompt=false);"
                "prompt=apply_chat_template(user_only,tokenize=true,"
                "add_generation_prompt=true);"
                "prompt_labels=-100"
            ),
            "model_execution_count": 0,
            "environment_execution_count": 0,
            "training_execution_count": 0,
        },
    )

    out = Path(os.environ["REPRO_ROOT"])
    out.mkdir(parents=True, exist_ok=False)
    write_new_json(
        out / "HISTORICAL_Q2_RENDERER_EXACT_REPRODUCTION_V1.json",
        receipt,
    )

    print("【阶段20】历史 π1 Renderer 84/84 精确回放：通过")
    print("RENDERER_REPRODUCTION_SHA256=" + receipt["renderer_reproduction_sha256"])
    print("HISTORICAL_INPUT_IDS_EXACT_MATCH=84/84")
    print("HISTORICAL_LABELS_EXACT_MATCH=84/84")
    print("HISTORICAL_SOURCE_SCHEMA=input.prompt_text+target.action_json")
    print("MATERIALIZER_SOURCE_EXECUTED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
