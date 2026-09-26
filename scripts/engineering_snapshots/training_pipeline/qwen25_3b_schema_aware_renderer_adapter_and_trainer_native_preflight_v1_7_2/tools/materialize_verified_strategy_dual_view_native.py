#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from common import (
    ContractError,
    finalize,
    load_jsonl,
    sha256_file,
    write_new_json,
    write_new_jsonl,
)
from strategy_dual_view_adapter import (
    build_strategy_dual_view_pair,
    materialize_dual_view_native_pair,
    summarize_native_label_census,
)

try:
    from transformers import AutoTokenizer
except Exception as exc:
    raise SystemExit(
        "STOP=TRANSFORMERS_IMPORT_FAILED:" + type(exc).__name__
    )


def main() -> int:
    input_path = Path(os.environ["VERIFIED_STRATEGY_INPUT_JSONL"])
    output_root = Path(os.environ["OUTPUT_ROOT"])

    if output_root.exists():
        raise ContractError("OUTPUT_ROOT_ALREADY_EXISTS")
    rows = load_jsonl(input_path)
    if not rows:
        raise ContractError("VERIFIED_STRATEGY_INPUT_EMPTY")

    tokenizer = AutoTokenizer.from_pretrained(
        os.environ["QWEN_BASE_MODEL_PATH"],
        local_files_only=True,
        trust_remote_code=False,
    )
    tokenizer.chat_template = Path(
        os.environ["PI1_CHAT_TEMPLATE_PATH"]
    ).read_text(encoding="utf-8")

    source_pairs = []
    native_rows = []
    pair_census_rows = []

    for pair_index, row in enumerate(rows):
        pair = build_strategy_dual_view_pair(
            row,
            pair_index,
        )
        materialized = materialize_dual_view_native_pair(
            pair=pair,
            tokenizer=tokenizer,
            ordinal_base=pair_index * 2,
        )
        source_pairs.append(pair)
        native_rows.extend(
            [
                materialized["execution_native_row"],
                materialized["strategy_native_row"],
            ]
        )
        pair_census_rows.append(materialized)

    census = summarize_native_label_census(pair_census_rows)

    output_root.mkdir(parents=True, exist_ok=False)
    source_path = output_root / "POLICY_STRATEGY_DUAL_VIEW_SOURCE_V1.jsonl"
    native_path = output_root / "POLICY_STRATEGY_DUAL_VIEW_NATIVE_V1.jsonl"
    census_path = output_root / "STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1.json"

    write_new_jsonl(source_path, source_pairs)
    write_new_jsonl(native_path, native_rows)

    census_authority = finalize(
        "STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1",
        "census_sha256",
        {
            "schema_id": "STRATEGY_BEARING_NATIVE_LABEL_CENSUS_V1",
            "schema_version": 1,
            **census,
            "source_input_path": str(input_path.resolve()),
            "source_input_sha256": sha256_file(input_path),
            "source_pair_path": str(source_path.resolve()),
            "source_pair_sha256": sha256_file(source_path),
            "native_dataset_path": str(native_path.resolve()),
            "native_dataset_sha256": sha256_file(native_path),
            "native_example_count": len(native_rows),
            "views_per_strategy_row": 2,
            "execution_view_semantics": "EXACT_I1_ACTION_ONLY",
            "strategy_view_semantics": (
                "TRAINING_ONLY_COMPACT_STRATEGY_WITH_ACTION"
            ),
            "deployment_i1_parser_changed": False,
            "future_outcome_visible_to_policy": False,
            "training_token_fairness_required_for_ablation": True,
            "task_policy_optimizer_execution_authorized": False,
            "training_execution_count": 0,
        },
    )
    write_new_json(census_path, census_authority)

    print("STRATEGY_DUAL_VIEW_NATIVE_MATERIALIZATION_PASS")
    for key, value in census.items():
        print(f"{key}={value}")
    print("NATIVE_EXAMPLE_COUNT=" + str(len(native_rows)))
    print("DEPLOYMENT_I1_PARSER_CHANGED=false")
    print("TRAINING_TOKEN_FAIRNESS_REQUIRED_FOR_ABLATION=true")
    print("TASK_POLICY_OPTIMIZER_EXECUTION_AUTHORIZED=false")
    print("TRAINING_EXECUTION_COUNT=0")
    print("CENSUS_AUTHORITY=" + str(census_path))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
