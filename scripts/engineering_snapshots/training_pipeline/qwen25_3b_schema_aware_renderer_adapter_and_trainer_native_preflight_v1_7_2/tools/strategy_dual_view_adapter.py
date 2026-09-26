from __future__ import annotations

import hashlib
import json
from typing import Any

from common import ContractError, canonical_json_bytes, finalize
from renderer_adapter_core import (
    canonical_action_json,
    make_messages,
    mask_prompt_prefix,
    sha256_text,
)


INPUT_SCHEMA = "VERIFIED_POLICY_STRATEGY_MATERIALIZATION_INPUT_V1"
PAIR_SCHEMA = "POLICY_STRATEGY_DUAL_VIEW_PAIR_V1"
SOURCE_SCHEMA = "POLICY_STRATEGY_DUAL_VIEW_SOURCE_V1"
NATIVE_SCHEMA = "POLICY_STRATEGY_DUAL_VIEW_NATIVE_ROW_V1"

EXECUTION_VIEW = "I1_EXECUTION_ACTION"
STRATEGY_VIEW = "STRATEGY_AUXILIARY"

AUXILIARY_PROMPT_MARKER = "[TRAINING_AUXILIARY_STRATEGY_VIEW_V1]"

TARGET_FIELDS = (
    "verified_strategy_sha256",
    "principal_bottleneck",
    "current_subgoal",
    "expected_next_event",
    "expected_state_change",
    "progress_criterion",
    "recovery_trigger",
    "fallback_condition",
    "action",
    "evidence_refs",
)

HASHED_STRATEGY_FIELDS = (
    "principal_bottleneck",
    "current_subgoal",
    "expected_next_event",
    "expected_state_change",
    "progress_criterion",
    "recovery_trigger",
    "fallback_condition",
    "action",
    "evidence_refs",
)

FORBIDDEN_TARGET_KEYS = {
    "verification_label",
    "terminal_effect",
    "benefit",
    "harm",
    "reward",
    "f0_outcome",
    "f1_outcome",
    "delta_u",
    "future_outcome",
    "planner_post",
    "hidden_reasoning",
    "chain_of_thought",
}

STRATEGY_AUXILIARY_INSTRUCTION = (
    "\n\n"
    + AUXILIARY_PROMPT_MARKER
    + "\n"
    + "Training-only auxiliary view. Do not answer using the deployment I1 "
      "envelope. Return exactly one compact JSON object with the registered "
      "strategy fields in their frozen order. Do not include verification "
      "outcomes, rewards, future observations, chain-of-thought, or prose."
)


def _require_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ContractError(label + "_INVALID_SHA256")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(label + "_MISSING")
    return value


def _canonical_ordered_json(value: dict[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _normalize_evidence_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ContractError("STRATEGY_EVIDENCE_REFS_MISSING")

    normalized = []
    for index, ref in enumerate(value):
        if not isinstance(ref, dict):
            raise ContractError(
                f"STRATEGY_EVIDENCE_REF_NOT_OBJECT:{index}"
            )
        allowed = {"source_kind", "source_id", "source_sha256"}
        if set(ref) != allowed:
            raise ContractError(
                f"STRATEGY_EVIDENCE_REF_KEYS_CHANGED:{index}:{sorted(ref)}"
            )
        normalized.append(
            {
                "source_kind": _require_text(
                    ref["source_kind"],
                    f"STRATEGY_EVIDENCE_KIND_{index}",
                ),
                "source_id": _require_text(
                    ref["source_id"],
                    f"STRATEGY_EVIDENCE_ID_{index}",
                ),
                "source_sha256": _require_sha(
                    ref["source_sha256"],
                    f"STRATEGY_EVIDENCE_SHA_{index}",
                ),
            }
        )

    normalized.sort(
        key=lambda ref: (
            ref["source_kind"],
            ref["source_id"],
            ref["source_sha256"],
        )
    )
    return normalized


def _strategy_core(strategy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(strategy, dict):
        raise ContractError("STRATEGY_PAYLOAD_MISSING")

    expected = set(HASHED_STRATEGY_FIELDS) | {
        "verified_strategy_sha256"
    }
    if set(strategy) != expected:
        raise ContractError(
            "STRATEGY_PAYLOAD_KEYS_CHANGED:"
            + repr(sorted(strategy))
        )

    core: dict[str, Any] = {}
    for field in HASHED_STRATEGY_FIELDS:
        if field == "evidence_refs":
            core[field] = _normalize_evidence_refs(strategy[field])
        else:
            core[field] = _require_text(
                strategy[field],
                "STRATEGY_" + field.upper(),
            )
    return core


def strategy_payload_sha256(strategy: dict[str, Any]) -> str:
    core = _strategy_core(strategy)
    return hashlib.sha256(
        canonical_json_bytes(core)
    ).hexdigest()


def canonical_strategy_target_json(
    strategy: dict[str, Any],
) -> str:
    core = _strategy_core(strategy)
    expected_sha = strategy_payload_sha256(strategy)
    observed_sha = _require_sha(
        strategy.get("verified_strategy_sha256"),
        "VERIFIED_STRATEGY",
    )
    if observed_sha != expected_sha:
        raise ContractError(
            "VERIFIED_STRATEGY_SHA_MISMATCH:"
            + observed_sha
            + ":"
            + expected_sha
        )

    target: dict[str, Any] = {}
    for field in TARGET_FIELDS:
        if field == "verified_strategy_sha256":
            target[field] = observed_sha
        else:
            target[field] = core[field]

    if set(target) & FORBIDDEN_TARGET_KEYS:
        raise ContractError("FORBIDDEN_FUTURE_OUTCOME_IN_TARGET")
    return _canonical_ordered_json(target)


def validate_verified_benefit_input(
    row: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    if row.get("schema_id") != INPUT_SCHEMA:
        raise ContractError("VERIFIED_STRATEGY_INPUT_SCHEMA_CHANGED")
    if row.get("schema_version") != 1:
        raise ContractError("VERIFIED_STRATEGY_INPUT_VERSION_CHANGED")

    source_state = _require_sha(
        row.get("source_state_sha256"),
        "SOURCE_STATE",
    )
    semantic_sha = _require_sha(
        row.get("source_semantic_row_sha256"),
        "SOURCE_SEMANTIC_ROW",
    )

    context = row.get("policy_visible_context")
    if not isinstance(context, dict):
        raise ContractError("POLICY_VISIBLE_CONTEXT_MISSING")
    if context.get("source_prompt_bound") is not True:
        raise ContractError("SOURCE_PROMPT_NOT_BOUND")
    prompt = _require_text(
        context.get("source_prompt_text"),
        "SOURCE_PROMPT_TEXT",
    )

    menu = context.get("admissible_commands")
    if not isinstance(menu, list) or not menu:
        raise ContractError("ADMISSIBLE_COMMANDS_MISSING")

    strategy = row.get("strategy")
    if not isinstance(strategy, dict):
        raise ContractError("STRATEGY_MISSING")
    target_json = canonical_strategy_target_json(strategy)

    action = strategy["action"]
    if action not in menu:
        raise ContractError("STRATEGY_ACTION_NOT_EXACT_MENU_MEMBER")

    verification = row.get("verification")
    if not isinstance(verification, dict):
        raise ContractError("VERIFICATION_PROVENANCE_MISSING")
    if verification.get("same_state_f0f1_verified") is not True:
        raise ContractError("STRATEGY_NOT_SAME_STATE_F0F1_VERIFIED")
    if verification.get("verification_label") != "BENEFIT":
        raise ContractError("STRATEGY_NOT_VERIFIED_BENEFIT")
    if verification.get("outcome_visible_to_policy") is not False:
        raise ContractError("FUTURE_OUTCOME_VISIBLE_TO_POLICY")
    if verification.get("reward_visible_to_policy") is not False:
        raise ContractError("REWARD_VISIBLE_TO_POLICY")
    if (
        verification.get("verified_strategy_sha256")
        != strategy["verified_strategy_sha256"]
    ):
        raise ContractError("VERIFICATION_STRATEGY_SHA_MISMATCH")
    _require_sha(
        verification.get("verification_receipt_sha256"),
        "VERIFICATION_RECEIPT",
    )

    return source_state, semantic_sha, {
        "prompt": prompt,
        "strategy_target_json": target_json,
        "action_json": canonical_action_json(action),
        "strategy": strategy,
        "verification": verification,
    }


def _source_example_sha256(
    *,
    source_state_sha256: str,
    source_semantic_row_sha256: str,
    verified_strategy_sha256: str,
    view_kind: str,
    prompt_sha256: str,
    target_sha256: str,
) -> str:
    identity = {
        "source_state_sha256": source_state_sha256,
        "source_semantic_row_sha256": source_semantic_row_sha256,
        "verified_strategy_sha256": verified_strategy_sha256,
        "view_kind": view_kind,
        "prompt_sha256": prompt_sha256,
        "target_sha256": target_sha256,
    }
    return hashlib.sha256(
        canonical_json_bytes(identity)
    ).hexdigest()


def build_strategy_dual_view_pair(
    row: dict[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    source_state, semantic_sha, parsed = (
        validate_verified_benefit_input(row)
    )
    strategy = parsed["strategy"]
    strategy_sha = strategy["verified_strategy_sha256"]

    execution_prompt = parsed["prompt"]
    execution_target = parsed["action_json"]

    strategy_prompt = (
        execution_prompt + STRATEGY_AUXILIARY_INSTRUCTION
    )
    strategy_target = parsed["strategy_target_json"]

    execution_prompt_sha = sha256_text(execution_prompt)
    execution_target_sha = sha256_text(execution_target)
    strategy_prompt_sha = sha256_text(strategy_prompt)
    strategy_target_sha = sha256_text(strategy_target)

    execution_example_sha = _source_example_sha256(
        source_state_sha256=source_state,
        source_semantic_row_sha256=semantic_sha,
        verified_strategy_sha256=strategy_sha,
        view_kind=EXECUTION_VIEW,
        prompt_sha256=execution_prompt_sha,
        target_sha256=execution_target_sha,
    )
    strategy_example_sha = _source_example_sha256(
        source_state_sha256=source_state,
        source_semantic_row_sha256=semantic_sha,
        verified_strategy_sha256=strategy_sha,
        view_kind=STRATEGY_VIEW,
        prompt_sha256=strategy_prompt_sha,
        target_sha256=strategy_target_sha,
    )
    if execution_example_sha == strategy_example_sha:
        raise ContractError("DUAL_VIEW_SOURCE_EXAMPLE_IDENTITY_COLLISION")

    pair = finalize(
        PAIR_SCHEMA,
        "pair_sha256",
        {
            "schema_id": PAIR_SCHEMA,
            "schema_version": 1,
            "ordinal": ordinal,
            "verified_benefit": True,
            "verified_strategy_sha256": strategy_sha,
            "verification_receipt_sha256": parsed[
                "verification"
            ]["verification_receipt_sha256"],
            "source_state_sha256": source_state,
            "source_semantic_row_sha256": semantic_sha,
            "execution_view": {
                "schema_id": SOURCE_SCHEMA,
                "view_kind": EXECUTION_VIEW,
                "source_example_sha256": execution_example_sha,
                "source_state_sha256": source_state,
                "input": {
                    "prompt_text": execution_prompt,
                    "prompt_sha256": execution_prompt_sha,
                    "exact_i1_execution_prompt": True,
                },
                "target": {
                    "target_text": execution_target,
                    "target_sha256": execution_target_sha,
                    "target_semantics": "CANONICAL_ACTION_JSON_ONLY",
                },
            },
            "strategy_view": {
                "schema_id": SOURCE_SCHEMA,
                "view_kind": STRATEGY_VIEW,
                "source_example_sha256": strategy_example_sha,
                "source_state_sha256": source_state,
                "input": {
                    "prompt_text": strategy_prompt,
                    "prompt_sha256": strategy_prompt_sha,
                    "exact_i1_execution_prompt": False,
                    "training_auxiliary_marker": (
                        AUXILIARY_PROMPT_MARKER
                    ),
                },
                "target": {
                    "target_text": strategy_target,
                    "target_sha256": strategy_target_sha,
                    "target_semantics": (
                        "COMPACT_STRATEGY_BEARING_JSON_WITH_ACTION"
                    ),
                },
            },
            "provenance": {
                "verification_label": "BENEFIT",
                "same_state_f0f1_verified": True,
                "f0f1_outcome_visible_to_policy": False,
                "reward_visible_to_policy": False,
                "deployment_i1_parser_changed": False,
                "dual_view_training_only": True,
            },
        },
    )
    return pair


def _to_int_list(value: Any, label: str) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, list) or not all(
        type(item) is int for item in value
    ):
        raise ContractError(label + "_NOT_INT_LIST")
    return [int(item) for item in value]


def _materialize_one_view(
    *,
    view: dict[str, Any],
    tokenizer: Any,
    ordinal: int,
) -> dict[str, Any]:
    prompt = view["input"]["prompt_text"]
    target = view["target"]["target_text"]
    messages = make_messages(prompt, target)

    full_ids = _to_int_list(
        tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
        ),
        "FULL_IDS",
    )
    prompt_ids = _to_int_list(
        tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=True,
            add_generation_prompt=True,
        ),
        "PROMPT_IDS",
    )
    labels = mask_prompt_prefix(full_ids, prompt_ids)
    completion_count = sum(value != -100 for value in labels)
    if completion_count <= 0:
        raise ContractError("NO_COMPLETION_LOSS_TOKENS")

    return finalize(
        NATIVE_SCHEMA,
        "trainer_native_row_sha256",
        {
            "schema_id": NATIVE_SCHEMA,
            "schema_version": 1,
            "ordinal": ordinal,
            "view_kind": view["view_kind"],
            "source_identity": {
                "source_example_sha256": view[
                    "source_example_sha256"
                ],
                "source_state_sha256": view[
                    "source_state_sha256"
                ],
            },
            "tokenization": {
                "input_ids": full_ids,
                "labels": labels,
                "sequence_token_count": len(full_ids),
                "prompt_masked_token_count": len(prompt_ids),
                "completion_loss_token_count": completion_count,
                "input_ids_sha256": hashlib.sha256(
                    canonical_json_bytes(full_ids)
                ).hexdigest(),
                "labels_sha256": hashlib.sha256(
                    canonical_json_bytes(labels)
                ).hexdigest(),
            },
            "deployment_i1_execution_view": (
                view["view_kind"] == EXECUTION_VIEW
            ),
            "training_auxiliary_strategy_view": (
                view["view_kind"] == STRATEGY_VIEW
            ),
            "promotion_eligible": False,
        },
    )


def materialize_dual_view_native_pair(
    *,
    pair: dict[str, Any],
    tokenizer: Any,
    ordinal_base: int,
) -> dict[str, Any]:
    if pair.get("schema_id") != PAIR_SCHEMA:
        raise ContractError("DUAL_VIEW_PAIR_SCHEMA_CHANGED")
    if pair.get("verified_benefit") is not True:
        raise ContractError("DUAL_VIEW_PAIR_NOT_VERIFIED_BENEFIT")

    execution_native = _materialize_one_view(
        view=pair["execution_view"],
        tokenizer=tokenizer,
        ordinal=ordinal_base,
    )
    strategy_native = _materialize_one_view(
        view=pair["strategy_view"],
        tokenizer=tokenizer,
        ordinal=ordinal_base + 1,
    )

    execution_loss = execution_native[
        "tokenization"
    ]["completion_loss_token_count"]
    strategy_loss = strategy_native[
        "tokenization"
    ]["completion_loss_token_count"]

    if execution_loss <= 0:
        raise ContractError("ACTION_LOSS_BEARING_TOKEN_COUNT_ZERO")
    if strategy_loss <= 0:
        raise ContractError("STRATEGY_LOSS_BEARING_TOKEN_COUNT_ZERO")

    return {
        "pair_sha256": pair["pair_sha256"],
        "verified_strategy_sha256": pair[
            "verified_strategy_sha256"
        ],
        "source_state_sha256": pair["source_state_sha256"],
        "verified_benefit": True,
        "execution_native_row": execution_native,
        "strategy_native_row": strategy_native,
        "action_target_token_count": execution_loss,
        "action_loss_bearing_token_count": execution_loss,
        "strategy_target_token_count": strategy_loss,
        "strategy_loss_bearing_token_count": strategy_loss,
        "prompt_masked_token_count": (
            execution_native["tokenization"][
                "prompt_masked_token_count"
            ]
            + strategy_native["tokenization"][
                "prompt_masked_token_count"
            ]
        ),
        "total_loss_bearing_token_count": (
            execution_loss + strategy_loss
        ),
        "action_only_strategy_row": False,
    }


def summarize_native_label_census(
    materialized_pairs: list[dict[str, Any]],
) -> dict[str, int]:
    strategy_rows = len(materialized_pairs)
    if strategy_rows <= 0:
        raise ContractError("STRATEGY_ROW_COUNT_ZERO")

    census = {
        "STRATEGY_ROW_COUNT": strategy_rows,
        "VERIFIED_BENEFIT_ROW_COUNT": sum(
            row["verified_benefit"]
            for row in materialized_pairs
        ),
        "STRATEGY_TARGET_TOKEN_COUNT": sum(
            row["strategy_target_token_count"]
            for row in materialized_pairs
        ),
        "STRATEGY_LOSS_BEARING_TOKEN_COUNT": sum(
            row["strategy_loss_bearing_token_count"]
            for row in materialized_pairs
        ),
        "ACTION_TARGET_TOKEN_COUNT": sum(
            row["action_target_token_count"]
            for row in materialized_pairs
        ),
        "ACTION_LOSS_BEARING_TOKEN_COUNT": sum(
            row["action_loss_bearing_token_count"]
            for row in materialized_pairs
        ),
        "PROMPT_MASKED_TOKEN_COUNT": sum(
            row["prompt_masked_token_count"]
            for row in materialized_pairs
        ),
        "TOTAL_LOSS_BEARING_TOKEN_COUNT": sum(
            row["total_loss_bearing_token_count"]
            for row in materialized_pairs
        ),
        "ACTION_ONLY_STRATEGY_ROW_COUNT": sum(
            row["action_only_strategy_row"]
            for row in materialized_pairs
        ),
        "NON_VERIFIED_STRATEGY_ROW_COUNT": sum(
            not row["verified_benefit"]
            for row in materialized_pairs
        ),
    }

    if census["VERIFIED_BENEFIT_ROW_COUNT"] != strategy_rows:
        raise ContractError("VERIFIED_BENEFIT_ROW_COUNT_MISMATCH")
    if census["STRATEGY_LOSS_BEARING_TOKEN_COUNT"] <= 0:
        raise ContractError("STRATEGY_LOSS_BEARING_TOKEN_COUNT_ZERO")
    if census["ACTION_LOSS_BEARING_TOKEN_COUNT"] <= 0:
        raise ContractError("ACTION_LOSS_BEARING_TOKEN_COUNT_ZERO")
    if census["PROMPT_MASKED_TOKEN_COUNT"] <= 0:
        raise ContractError("PROMPT_MASKED_TOKEN_COUNT_ZERO")
    if census["ACTION_ONLY_STRATEGY_ROW_COUNT"] != 0:
        raise ContractError("ACTION_ONLY_STRATEGY_ROW_COUNT_NONZERO")
    if census["NON_VERIFIED_STRATEGY_ROW_COUNT"] != 0:
        raise ContractError("NON_VERIFIED_STRATEGY_ROW_COUNT_NONZERO")
    return census
