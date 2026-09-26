from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


THIS = Path(__file__).resolve()
TOOLS = THIS.parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from common import ContractError, canonical_json_bytes
from renderer_adapter_core import canonical_action_json
from pchsi.evaluation.raw_policy_parser import (
    ParserFailureCode,
    ParserStatus,
    parse_raw_policy_response,
)
from strategy_dual_view_adapter import (
    AUXILIARY_PROMPT_MARKER,
    EXECUTION_VIEW,
    STRATEGY_VIEW,
    build_strategy_dual_view_pair,
    materialize_dual_view_native_pair,
    strategy_payload_sha256,
    summarize_native_label_census,
)


class FakeTokenizer:
    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
    ):
        assert tokenize is True
        if len(messages) == 1:
            text = "USER:" + messages[0]["content"] + "\nASSISTANT:"
        else:
            text = (
                "USER:"
                + messages[0]["content"]
                + "\nASSISTANT:"
                + messages[1]["content"]
            )
        return list(text.encode("utf-8"))


def _sha(seed: str) -> str:
    import hashlib
    return hashlib.sha256(seed.encode()).hexdigest()


def _input_row():
    strategy = {
        "verified_strategy_sha256": "0" * 64,
        "principal_bottleneck": "object not yet in inventory",
        "current_subgoal": "pick up the apple",
        "expected_next_event": "inventory gains apple",
        "expected_state_change": "apple moves from table to inventory",
        "progress_criterion": "inventory observation contains apple",
        "recovery_trigger": "take action fails or inventory lacks apple",
        "fallback_condition": "re-observe and replan",
        "action": "take apple from table",
        "evidence_refs": [
            {
                "source_kind": "F0F1_PRE_DECISION_EVIDENCE",
                "source_id": "state-1",
                "source_sha256": _sha("evidence"),
            }
        ],
    }
    strategy["verified_strategy_sha256"] = strategy_payload_sha256(
        strategy
    )
    return {
        "schema_id": "VERIFIED_POLICY_STRATEGY_MATERIALIZATION_INPUT_V1",
        "schema_version": 1,
        "source_state_sha256": _sha("state"),
        "source_semantic_row_sha256": _sha("semantic"),
        "policy_visible_context": {
            "source_prompt_bound": True,
            "source_prompt_text": "Goal: put apple in fridge\nObs: apple on table",
            "admissible_commands": [
                "look",
                "take apple from table",
            ],
        },
        "strategy": strategy,
        "verification": {
            "same_state_f0f1_verified": True,
            "verification_label": "BENEFIT",
            "verified_strategy_sha256": strategy[
                "verified_strategy_sha256"
            ],
            "verification_receipt_sha256": _sha("verify"),
            "outcome_visible_to_policy": False,
            "reward_visible_to_policy": False,
        },
    }


def test_execution_view_keeps_exact_i1_action_target():
    pair = build_strategy_dual_view_pair(_input_row(), 0)
    assert pair["execution_view"]["view_kind"] == EXECUTION_VIEW
    assert pair["execution_view"]["input"]["exact_i1_execution_prompt"] is True
    assert pair["execution_view"]["target"]["target_text"] == (
        canonical_action_json("take apple from table")
    )
    assert (
        AUXILIARY_PROMPT_MARKER
        not in pair["execution_view"]["input"]["prompt_text"]
    )



def test_execution_target_passes_exact_i1_parser_and_strategy_target_does_not():
    pair = build_strategy_dual_view_pair(_input_row(), 0)

    execution = parse_raw_policy_response(
        pair["execution_view"]["target"]["target_text"]
    )
    assert execution.status == ParserStatus.SUCCESS
    assert execution.normalized_action == "take apple from table"

    strategy = parse_raw_policy_response(
        pair["strategy_view"]["target"]["target_text"]
    )
    assert strategy.status == ParserStatus.FAILED
    assert strategy.failure_code == ParserFailureCode.ENVELOPE_MEMBER_COUNT_INVALID

def test_strategy_view_is_training_only_and_contains_no_outcome_verdict():
    pair = build_strategy_dual_view_pair(_input_row(), 0)
    view = pair["strategy_view"]
    assert view["view_kind"] == STRATEGY_VIEW
    assert view["input"]["exact_i1_execution_prompt"] is False
    assert AUXILIARY_PROMPT_MARKER in view["input"]["prompt_text"]
    target = json.loads(view["target"]["target_text"])
    assert target["action"] == "take apple from table"
    assert "verification_label" not in target
    assert "reward" not in target
    assert "benefit" not in target
    assert list(target) == [
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
    ]


def test_dual_views_share_state_but_use_distinct_source_example_identity():
    pair = build_strategy_dual_view_pair(_input_row(), 0)
    assert (
        pair["execution_view"]["source_state_sha256"]
        == pair["strategy_view"]["source_state_sha256"]
    )
    assert (
        pair["execution_view"]["source_example_sha256"]
        != pair["strategy_view"]["source_example_sha256"]
    )


def test_only_verified_benefit_is_eligible():
    row = _input_row()
    row["verification"]["verification_label"] = "NEUTRAL"
    with pytest.raises(ContractError, match="NOT_VERIFIED_BENEFIT"):
        build_strategy_dual_view_pair(row, 0)


def test_native_pair_masks_prompts_and_makes_both_views_loss_bearing():
    pair = build_strategy_dual_view_pair(_input_row(), 0)
    materialized = materialize_dual_view_native_pair(
        pair=pair,
        tokenizer=FakeTokenizer(),
        ordinal_base=0,
    )
    for key in ("execution_native_row", "strategy_native_row"):
        native = materialized[key]
        labels = native["tokenization"]["labels"]
        masked = native["tokenization"]["prompt_masked_token_count"]
        assert all(value == -100 for value in labels[:masked])
        assert any(value != -100 for value in labels[masked:])
    assert materialized["action_loss_bearing_token_count"] > 0
    assert materialized["strategy_loss_bearing_token_count"] > 0


def test_census_closes_action_only_shape_at_pair_level():
    pair = build_strategy_dual_view_pair(_input_row(), 0)
    materialized = materialize_dual_view_native_pair(
        pair=pair,
        tokenizer=FakeTokenizer(),
        ordinal_base=0,
    )
    census = summarize_native_label_census([materialized])
    assert census["STRATEGY_ROW_COUNT"] == 1
    assert census["VERIFIED_BENEFIT_ROW_COUNT"] == 1
    assert census["STRATEGY_LOSS_BEARING_TOKEN_COUNT"] > 0
    assert census["ACTION_LOSS_BEARING_TOKEN_COUNT"] > 0
    assert census["ACTION_ONLY_STRATEGY_ROW_COUNT"] == 0
    assert census["NON_VERIFIED_STRATEGY_ROW_COUNT"] == 0
