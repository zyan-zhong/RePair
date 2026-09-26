#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import (
    ContractError,
    load_json_object,
    load_jsonl,
    require_domain_hash,
    require_sha,
)


def validate_current_selected_arms(plan) -> None:
    policy_training_recipe = plan.get(
        "policy_training_recipe"
    )
    if not isinstance(policy_training_recipe, dict):
        raise ContractError(
            "CURRENT_POLICY_TRAINING_RECIPE_MISSING"
        )

    if policy_training_recipe.get(
        "selected_arm_ids"
    ) != ["T0", "T2"]:
        raise ContractError(
            "CURRENT_SELECTED_ARMS_CHANGED"
        )


def main() -> int:
    census = load_json_object(Path(os.environ["V16_CENSUS_PATH"]))
    bridge = load_json_object(Path(os.environ["V16_NORMATIVE_BRIDGE_PATH"]))
    require_domain_hash(
        census,
        "renderer_interface_census_sha256",
        os.environ["EXPECTED_V16_CENSUS_SHA256"],
        "V16_RENDERER_CENSUS",
    )
    require_domain_hash(
        bridge,
        "normative_bridge_sha256",
        os.environ["EXPECTED_V16_NORMATIVE_BRIDGE_SHA256"],
        "V16_NORMATIVE_BRIDGE",
    )
    require_sha(
        Path(os.environ["V16_REVIEW_ZIP"]),
        os.environ["EXPECTED_V16_REVIEW_ZIP_SHA256"],
        "V16_REVIEW_ZIP",
    )

    require_sha(
        Path(os.environ["PI1_SOURCE_TRAINING_EXAMPLES_PATH"]),
        os.environ["EXPECTED_PI1_SOURCE_TRAINING_EXAMPLES_SHA256"],
        "PI1_SOURCE_TRAINING_EXAMPLES",
    )
    require_sha(
        Path(os.environ["PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH"]),
        os.environ["EXPECTED_PI1_REFERENCE_MATERIALIZED_EXAMPLES_SHA256"],
        "PI1_REFERENCE_MATERIALIZED_EXAMPLES",
    )
    require_sha(
        Path(os.environ["PI1_FINAL_MATERIALIZATION_MANIFEST_PATH"]),
        os.environ["EXPECTED_PI1_FINAL_MATERIALIZATION_MANIFEST_SHA256"],
        "PI1_FINAL_MATERIALIZATION_MANIFEST",
    )
    require_sha(
        Path(os.environ["PI1_ROW_RENDERER_PATH"]),
        os.environ["EXPECTED_PI1_ROW_RENDERER_SHA256"],
        "PI1_ROW_RENDERER",
    )
    require_sha(
        Path(os.environ["PI1_CHAT_TEMPLATE_PATH"]),
        os.environ["EXPECTED_PI1_CHAT_TEMPLATE_SHA256"],
        "PI1_CHAT_TEMPLATE",
    )

    source = load_jsonl(Path(os.environ["PI1_SOURCE_TRAINING_EXAMPLES_PATH"]))
    native = load_jsonl(
        Path(os.environ["PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH"])
    )
    if len(source) != 84 or len(native) != 84:
        raise ContractError(
            f"HISTORICAL_ORACLE_POPULATION_CHANGED:{len(source)}:{len(native)}"
        )

    # Census must explicitly support the implementation we are about to make.
    if census.get("source_has_top_level_messages") is not False:
        raise ContractError("V16_SOURCE_SCHEMA_EXPECTATION_CHANGED")
    if census.get("source_schema_id_counts") != {
        "D_Q2_BAD_V1_TRAINING_EXAMPLE": 84
    }:
        raise ContractError("V16_SOURCE_SCHEMA_DISTRIBUTION_CHANGED")

    semantic_manifest = load_json_object(
        Path(os.environ["V13_SEMANTIC_ROOT"])
        / "DETERMINISTIC_SEMANTIC_DATASET_MATERIALIZATION_V1.json"
    )
    require_domain_hash(
        semantic_manifest,
        "semantic_materialization_sha256",
        os.environ["EXPECTED_V13_SEMANTIC_MATERIALIZATION_SHA256"],
        "V13_SEMANTIC_MATERIALIZATION",
    )

    mixture = load_json_object(
        Path(os.environ["V13_SEMANTIC_ROOT"])
        / "ACTUAL_TRAINING_MIXTURE_MANIFEST_V2.json"
    )
    require_domain_hash(
        mixture,
        "actual_mixture_manifest_sha256",
        os.environ["EXPECTED_V13_ACTUAL_MIXTURE_SHA256"],
        "V13_ACTUAL_MIXTURE",
    )

    plan = load_json_object(Path(os.environ["STRONG_PLAN_PATH"]))
    require_domain_hash(
        plan,
        "training_plan_sha256",
        os.environ["EXPECTED_STRONG_PLAN_SHA256"],
        "STRONG_PLAN",
    )
    validate_current_selected_arms(plan)

    parent = load_json_object(Path(os.environ["PARENT_CHECKPOINT_SET_MANIFEST"]))
    require_sha(
        Path(os.environ["PARENT_CHECKPOINT_SET_MANIFEST"]),
        os.environ["EXPECTED_PARENT_CHECKPOINT_SET_MANIFEST_SHA256"],
        "PARENT_CHECKPOINT_SET_MANIFEST",
    )
    checkpoints = parent.get("checkpoints")
    if not isinstance(checkpoints, list):
        raise ContractError("PARENT_CHECKPOINTS_MISSING")
    train17 = [
        row for row in checkpoints
        if isinstance(row, dict) and row.get("training_seed") == 17
    ]
    if len(train17) != 1:
        raise ContractError("PARENT_TRAIN17_NOT_EXACTLY_ONE")
    if train17[0].get("adapter_bundle_sha256") != os.environ[
        "EXPECTED_PARENT_TRAIN17_ADAPTER_BUNDLE_SHA256"
    ]:
        raise ContractError("PARENT_TRAIN17_ADAPTER_IDENTITY_CHANGED")

    print("【阶段10】上游科研与序列化权威校验：通过")
    print("V16_RENDERER_CENSUS_SHA256=" + census["renderer_interface_census_sha256"])
    print("V16_NORMATIVE_BRIDGE_SHA256=" + bridge["normative_bridge_sha256"])
    print("HISTORICAL_RENDERER_ORACLE_ROWS=84")
    print("CURRENT_POLICY_T2_SEMANTIC_ROWS=12")
    print("PARENT_POLICY=PILOT_DISTILLED_PI1")
    print("PARENT_POLICY_TRAINING_SEED=17")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))
