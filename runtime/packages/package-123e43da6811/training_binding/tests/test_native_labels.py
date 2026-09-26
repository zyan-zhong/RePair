from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest

WORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORK / "v17"))
TOOLS = WORK / "v17/native_bba_full/scripts/engineering_snapshots/training_pipeline/qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools"


class TokenizerFixture:
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert tokenize
        return list(("USER:" + messages[0]["content"] + "\nASSISTANT:" + (messages[1]["content"] if len(messages) > 1 else "")).encode())


def _setup():
    assert (WORK / "v17/training_binding/native_labels.py").is_file(), "Stage6AN native label producer is absent"
    from training_binding.native_labels import NativeLabels
    names = ("common.py", "renderer_adapter_core.py", "strategy_dual_view_adapter.py")
    native = NativeLabels.load(TOOLS, {name: hashlib.sha256((TOOLS / name).read_bytes()).hexdigest() for name in names})
    strategy = {"verified_strategy_sha256": "0" * 64, "principal_bottleneck": "apple outside inventory",
        "current_subgoal": "take apple", "expected_next_event": "apple in inventory", "expected_state_change": "apple moves",
        "progress_criterion": "inventory has apple", "recovery_trigger": "take fails", "fallback_condition": "look",
        "action": "take apple from table", "evidence_refs": [{"source_kind": "PRE_EVIDENCE", "source_id": "fixture", "source_sha256": "a" * 64}]}
    strategy["verified_strategy_sha256"] = native.adapter.strategy_payload_sha256(strategy)
    row = {"schema_id": native.adapter.INPUT_SCHEMA, "schema_version": 1, "source_state_sha256": "b" * 64,
        "source_semantic_row_sha256": "c" * 64,
        "policy_visible_context": {"source_prompt_bound": True, "source_prompt_text": "Goal: apple in fridge. Obs: apple on table", "admissible_commands": ["look", "take apple from table"]},
        "strategy": strategy, "verification": {"same_state_f0f1_verified": True, "verification_label": "BENEFIT", "verified_strategy_sha256": strategy["verified_strategy_sha256"], "verification_receipt_sha256": "d" * 64, "outcome_visible_to_policy": False, "reward_visible_to_policy": False}}
    return native, row


def test_real_stage6an_producer_and_census(tmp_path):
    native, row = _setup()
    result = native.materialize(verified_rows=[row], tokenizer=TokenizerFixture(), output_root=tmp_path / "native",
        verifier_result_sha256="d" * 64, verified_benefit_state_sha256s=["b" * 64])
    census = json.loads(Path(result["dataset_manifest_ref"]["path"]).read_text())
    assert result["recipe_context"]["row_count"] == 2
    assert census["ACTION_ONLY_STRATEGY_ROW_COUNT"] == 0
    assert census["STRATEGY_LOSS_BEARING_TOKEN_COUNT"] > 0
    assert census["ACTION_LOSS_BEARING_TOKEN_COUNT"] > 0
    assert census["task_policy_optimizer_execution_authorized"] is False
    rows = [json.loads(line) for line in Path(result["dataset_ref"]["path"]).read_text().splitlines()]
    assert rows[0]["source_identity"]["source_state_sha256"] == rows[1]["source_identity"]["source_state_sha256"]
    assert rows[0]["source_identity"]["source_example_sha256"] != rows[1]["source_identity"]["source_example_sha256"]
    assert native.materialize(verified_rows=[row], tokenizer=TokenizerFixture(), output_root=tmp_path / "native",
        verifier_result_sha256="d" * 64, verified_benefit_state_sha256s=["b" * 64]) == result


@pytest.mark.parametrize("which", ["strategy", "verifier", "state", "duplicate"])
def test_native_rejects_invented_or_unbound_strategy_before_write(tmp_path, which):
    native, row = _setup()
    if which == "strategy": row["strategy"]["current_subgoal"] = "post hoc new strategy"
    if which == "verifier": row["verification"]["verification_receipt_sha256"] = "e" * 64
    if which == "state": row["source_state_sha256"] = "e" * 64
    rows = [row, copy.deepcopy(row)] if which == "duplicate" else [row]
    with pytest.raises((ValueError, RuntimeError)):
        native.materialize(verified_rows=rows, tokenizer=TokenizerFixture(), output_root=tmp_path / "rejected",
            verifier_result_sha256="d" * 64, verified_benefit_state_sha256s=["b" * 64])
    assert not (tmp_path / "rejected").exists()
