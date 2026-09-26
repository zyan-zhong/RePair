from __future__ import annotations

import hashlib
import json
from typing import Any

from common import ContractError, canonical_json_bytes, finalize


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_action_json(action: str) -> str:
    if not isinstance(action, str) or not action:
        raise ContractError("TARGET_ACTION_MISSING")
    return json.dumps(
        {"action": action},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_historical_source_row(row: dict[str, Any]) -> tuple[str, str]:
    if row.get("schema_id") != "D_Q2_BAD_V1_TRAINING_EXAMPLE":
        raise ContractError("HISTORICAL_SOURCE_SCHEMA_CHANGED")
    inp = row.get("input")
    tgt = row.get("target")
    if not isinstance(inp, dict) or not isinstance(tgt, dict):
        raise ContractError("HISTORICAL_INPUT_OR_TARGET_MISSING")
    prompt = inp.get("prompt_text")
    prompt_sha = inp.get("prompt_sha256")
    action_json = tgt.get("action_json")
    exact_action = tgt.get("exact_action")
    target_sha = tgt.get("target_sha256")
    if not isinstance(prompt, str) or not prompt:
        raise ContractError("HISTORICAL_PROMPT_TEXT_MISSING")
    if prompt_sha != sha256_text(prompt):
        raise ContractError("HISTORICAL_PROMPT_SHA_MISMATCH")
    if not isinstance(exact_action, str) or not exact_action:
        raise ContractError("HISTORICAL_EXACT_ACTION_MISSING")
    expected_action_json = canonical_action_json(exact_action)
    if action_json != expected_action_json:
        raise ContractError("HISTORICAL_ACTION_JSON_NOT_CANONICAL")
    if target_sha != sha256_text(action_json):
        raise ContractError("HISTORICAL_TARGET_SHA_MISMATCH")
    return prompt, action_json


def make_messages(prompt_text: str, action_json: str) -> list[dict[str, str]]:
    return [
        {"role": "user", "content": prompt_text},
        {"role": "assistant", "content": action_json},
    ]


def mask_prompt_prefix(full_ids: list[int], prompt_ids: list[int]) -> list[int]:
    if not full_ids or not prompt_ids:
        raise ContractError("TOKEN_SEQUENCE_EMPTY")
    if len(prompt_ids) >= len(full_ids):
        raise ContractError("ASSISTANT_COMPLETION_SUFFIX_EMPTY")
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise ContractError("PROMPT_PREFIX_TOKEN_MISMATCH")
    return [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]


def find_unique_nested_key_path(value: dict[str, Any], key: str) -> tuple[str, ...]:
    found: list[tuple[str, ...]] = []

    def walk(node: Any, prefix: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for k, child in node.items():
                new = prefix + (str(k),)
                if k == key:
                    found.append(new)
                walk(child, new)

    walk(value, ())
    if len(found) != 1:
        raise ContractError(
            f"NATIVE_FIELD_PATH_NOT_UNIQUE:{key}:{found!r}"
        )
    return found[0]


def get_path(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = value
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise ContractError(f"NATIVE_FIELD_PATH_MISSING:{path!r}")
        node = node[key]
    return node


def build_t2_source_adapter_row(semantic: dict[str, Any], ordinal: int) -> dict[str, Any]:
    if semantic.get("schema_id") != "POLICY_SEMANTIC_TRAINING_ROW_V1":
        raise ContractError("T2_SEMANTIC_SCHEMA_CHANGED")
    if semantic.get("arm_id") != "T2":
        raise ContractError("NON_T2_ROW_IN_POLICY_DATASET")
    if semantic.get("diagnostic_only") is not True:
        raise ContractError("T2_DIAGNOSTIC_ONLY_CHANGED")
    if semantic.get("verified_positive") is not False:
        raise ContractError("T2_VERIFIED_POSITIVE_ESCALATED")
    if semantic.get("promotion_eligible") is not False:
        raise ContractError("T2_PROMOTION_ESCALATED")
    if semantic.get("terminal_effect") not in {"NEUTRAL", "UNCERTAIN"}:
        raise ContractError("T2_TERMINAL_EFFECT_OUTSIDE_DIAGNOSTIC_SET")

    context = semantic.get("policy_visible_context")
    if not isinstance(context, dict):
        raise ContractError("T2_POLICY_VISIBLE_CONTEXT_MISSING")
    prompt = context.get("source_prompt_text")
    if context.get("source_prompt_bound") is not True:
        raise ContractError("T2_EXACT_SOURCE_PROMPT_NOT_BOUND")
    if not isinstance(prompt, str) or not prompt:
        raise ContractError("T2_EXACT_SOURCE_PROMPT_TEXT_MISSING")

    action = semantic.get("target_action")
    menu = context.get("admissible_commands")
    if not isinstance(menu, list) or action not in menu:
        raise ContractError("T2_TARGET_ACTION_NOT_EXACT_MENU_MEMBER")
    action_json = canonical_action_json(action)

    # Only historical renderer-relevant fields go into input/target.
    # Hindsight stays in provenance, never in policy-visible prompt or target.
    return finalize(
        "POLICY_T2_SCHEMA_AWARE_RENDERER_SOURCE_V1",
        "adapter_source_row_sha256",
        {
            "schema_id": "POLICY_T2_SCHEMA_AWARE_RENDERER_SOURCE_V1",
            "schema_version": 1,
            "ordinal": ordinal,
            "source_semantic_row_sha256": semantic["row_sha256"],
            "source_state_sha256": semantic["source_state_sha256"],
            "input": {
                "prompt_text": prompt,
                "prompt_sha256": sha256_text(prompt),
            },
            "target": {
                "exact_action": action,
                "action_json": action_json,
                "target_sha256": sha256_text(action_json),
            },
            "provenance": {
                "terminal_effect": semantic["terminal_effect"],
                "mechanical_effect": semantic.get("mechanical_effect"),
                "primary_training_route": semantic.get("primary_training_route"),
                "diagnostic_only": True,
                "verified_positive": False,
                "promotion_eligible": False,
                "hindsight_visible_to_policy": False,
                "f0f1_outcome_visible_to_policy": False,
                "training_route_visible_to_policy": False,
            },
        },
    )


def build_native_row(
    *,
    adapter_row: dict[str, Any],
    input_ids: list[int],
    labels: list[int],
    ordinal: int,
) -> dict[str, Any]:
    completion_tokens = sum(value != -100 for value in labels)
    if completion_tokens <= 0:
        raise ContractError("NO_COMPLETION_LOSS_TOKENS")
    return finalize(
        "POLICY_T2_TRAINER_NATIVE_ROW_V1",
        "trainer_native_row_sha256",
        {
            "schema_id": "POLICY_T2_TRAINER_NATIVE_ROW_V1",
            "schema_version": 1,
            "ordinal": ordinal,
            "source_semantic_identity": {
                "source_semantic_row_sha256": adapter_row[
                    "source_semantic_row_sha256"
                ],
                "source_state_sha256": adapter_row["source_state_sha256"],
                "adapter_source_row_sha256": adapter_row[
                    "adapter_source_row_sha256"
                ],
            },
            "tokenization": {
                "input_ids": input_ids,
                "labels": labels,
                "sequence_token_count": len(input_ids),
                "completion_loss_token_count": completion_tokens,
                "input_ids_sha256": hashlib.sha256(
                    canonical_json_bytes(input_ids)
                ).hexdigest(),
                "labels_sha256": hashlib.sha256(
                    canonical_json_bytes(labels)
                ).hexdigest(),
            },
            "diagnostic_only": True,
            "verified_positive": False,
            "promotion_eligible": False,
        },
    )
